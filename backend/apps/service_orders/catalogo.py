"""Alimenta o catálogo de serviços/materiais a partir do relato de uma OS.

Chamado quando a OS é concluída. Deduplica por texto (case-insensitive) e
conta os usos, para o formulário sugerir primeiro o que é mais comum.
"""

from django.db.models import F

from .models import MaterialCatalogo, ServicoCatalogo


def _registrar(modelo, descricao, extra_defaults=None):
    descricao = (descricao or "").strip()
    if not descricao:
        return
    existente = modelo.objects.filter(descricao__iexact=descricao).first()
    if existente:
        campos = {"usos": F("usos") + 1}
        if extra_defaults:
            for campo, valor in extra_defaults.items():
                # só preenche o que ainda está vazio
                if valor and not getattr(existente, campo):
                    campos[campo] = valor
        modelo.objects.filter(pk=existente.pk).update(**campos)
    else:
        modelo.objects.create(descricao=descricao, usos=1, **(extra_defaults or {}))


def alimentar_catalogo(relato: dict):
    relato = relato or {}

    for servico in relato.get("servicos", []):
        _registrar(ServicoCatalogo, servico)

    for material in relato.get("materiais", []):
        _registrar(
            MaterialCatalogo,
            material.get("descricao"),
            {"unidade_padrao": (material.get("unidade") or "").strip()},
        )
