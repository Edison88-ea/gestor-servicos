"""Semeia o catálogo de materiais com os itens de uso corrente informados pela
equipe. Idempotente: não recria o que já existe (comparação sem diferenciar
maiúsculas/minúsculas, igual ao alimentar_catalogo)."""

from django.db import migrations

MATERIAIS = [
    "Keystone",
    "Disjuntor 25",
    "Canaleta",
    "Caixa daisa",
    "Tampa daisa de Keystone dupla",
    "Tampa daisa de keystone unica",
    "Espelho Keystone dupla",
    "Espelho Keystone única",
    "Tampa de perfilado",
    "Perfilado",
]


def semear(apps, schema_editor):
    MaterialCatalogo = apps.get_model("service_orders", "MaterialCatalogo")
    for descricao in MATERIAIS:
        if not MaterialCatalogo.objects.filter(descricao__iexact=descricao).exists():
            MaterialCatalogo.objects.create(descricao=descricao, usos=0)


def desfazer(apps, schema_editor):
    MaterialCatalogo = apps.get_model("service_orders", "MaterialCatalogo")
    MaterialCatalogo.objects.filter(descricao__in=MATERIAIS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("service_orders", "0005_materialcatalogo_servicocatalogo"),
    ]

    operations = [
        migrations.RunPython(semear, desfazer),
    ]
