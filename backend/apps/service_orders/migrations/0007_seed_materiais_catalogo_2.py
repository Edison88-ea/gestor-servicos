"""Segunda leva de materiais de uso corrente informada pela equipe. Idempotente:
não recria o que já existe (comparação sem diferenciar maiúsculas/minúsculas)."""

from django.db import migrations

# descrição -> unidade padrão (só onde a equipe já indicou a medida)
MATERIAIS = [
    ("Perfilado", ""),
    ("Curvas", ""),
    ("Emendas de perfilado", ""),
    ("Pé de calha", ""),
    ("Pé de perfilado", ""),
    ("Tomada steck 220V", ""),
    ("Lentilha, arruela e porca nº 11", ""),
    ("Lentilha, arruela e porca nº 13", ""),
    ("Cabo PP 3x2,5mm²", "m"),
    ("Cabo singelo preto", "m"),
    ("Cabo singelo azul", "m"),
    ("Caixa daisa", ""),
    ("Tampa daisa para tomada dupla", ""),
    ("Tomada dupla vermelha (220V)", ""),
    ("Keystone", ""),
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
        ("service_orders", "0006_seed_materiais_catalogo"),
    ]

    operations = [
        migrations.RunPython(semear, desfazer),
    ]
