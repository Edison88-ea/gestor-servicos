"""Consolida nomes duplicados no catálogo de materiais (mistura dos nomes livres
das OSs antigas com as listas semeadas). Decisões da equipe:

- "Curvas" (contexto perfilado)      -> "Curvas de perfilado"
- "Curva PPR" + "Curvas de PPR"      -> "Curva de PPR"
- "RJ45 cat6" + "Conector RJ45"      -> "RJ45 cat6"
- "Cabo de rede *" + "Cabo UTP"      -> "Cabo de rede"
- "T PPR" + "TE PPR"                 -> "TE PPR"

"Válvula" e "Válvula de PPR" são itens diferentes — ficam como estão.
Ao unir, os contadores de uso são somados. Idempotente. Irreversível
(não dá pra separar de volta o que foi somado)."""

from django.db import migrations


def _rows(Model, nomes):
    vistos, achados = set(), []
    for nome in nomes:
        for r in Model.objects.filter(descricao__iexact=nome):
            if r.pk not in vistos:
                vistos.add(r.pk)
                achados.append(r)
    return achados


def unificar(Model, nomes, alvo, unidade=None):
    rows = _rows(Model, nomes)
    if not rows:
        return
    total = sum(r.usos for r in rows)
    if unidade is None:
        unidade = next((r.unidade_padrao for r in rows if r.unidade_padrao), "")
    principal = next((r for r in rows if r.descricao.lower() == alvo.lower()), rows[0])
    for r in rows:
        if r.pk != principal.pk:
            r.delete()
    principal.descricao = alvo
    principal.usos = total
    principal.unidade_padrao = unidade
    principal.save()


def renomear(Model, de, para):
    row = Model.objects.filter(descricao__iexact=de).first()
    if not row:
        return
    if Model.objects.filter(descricao__iexact=para).exclude(pk=row.pk).exists():
        unificar(Model, [de, para], para)
        return
    row.descricao = para
    row.save()


def limpar(apps, schema_editor):
    M = apps.get_model("service_orders", "MaterialCatalogo")
    renomear(M, "Curvas", "Curvas de perfilado")
    unificar(M, ["Curva PPR", "Curvas de PPR", "Curva de PPR"], "Curva de PPR")
    unificar(M, ["RJ45 cat6", "Conector RJ45"], "RJ45 cat6")
    unificar(
        M,
        ["Cabo de rede", "Cabo de rede Cat6", "Cabo de rede cat6 Soho Plus", "Cabo UTP"],
        "Cabo de rede",
        unidade="m",
    )
    unificar(M, ["T PPR", "TE PPR"], "TE PPR")


class Migration(migrations.Migration):
    dependencies = [
        ("service_orders", "0008_seed_materiais_catalogo_3"),
    ]

    operations = [
        migrations.RunPython(limpar, migrations.RunPython.noop),
    ]
