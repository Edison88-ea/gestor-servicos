"""Terceira leva de materiais (hidráulica PPR + cabos/conectores) informada pela
equipe. Idempotente: não recria o que já existe (comparação case-insensitive)."""

from django.db import migrations

# descrição -> unidade padrão (só onde a medida é conhecida)
MATERIAIS = [
    ("PPR", ""),
    ("Emendas de PPR", ""),
    ("Curvas de PPR", ""),
    ("T PPR", ""),
    ("Presilha de PPR", ""),
    ("Válvula de PPR", ""),
    ("Emendas com rosca", ""),
    ("Emendas com rosca macho", ""),
    ("Steck 380V", ""),
    ("Cabo PP 5x2,5mm²", "m"),
    ("Cabo PP 5x4mm²", "m"),
    ("Mangueira PU", "m"),
    ("Cabo de rede cat6 Soho Plus", "m"),
    ("RJ45 cat6", ""),
]


def semear(apps, schema_editor):
    MaterialCatalogo = apps.get_model("service_orders", "MaterialCatalogo")
    for descricao, unidade in MATERIAIS:
        if not MaterialCatalogo.objects.filter(descricao__iexact=descricao).exists():
            MaterialCatalogo.objects.create(descricao=descricao, unidade_padrao=unidade, usos=0)


def desfazer(apps, schema_editor):
    MaterialCatalogo = apps.get_model("service_orders", "MaterialCatalogo")
    MaterialCatalogo.objects.filter(descricao__in=[d for d, _ in MATERIAIS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("service_orders", "0007_seed_materiais_catalogo_2"),
    ]

    operations = [
        migrations.RunPython(semear, desfazer),
    ]
