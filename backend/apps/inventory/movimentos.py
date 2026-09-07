"""Aplicação de movimentos de estoque.

Toda alteração de saldo passa por aqui, sempre dentro de transação e com lock na
linha do material (``select_for_update``) para não perder movimento concorrente.
"""

import logging
import re
from decimal import Decimal, InvalidOperation

from django.db import transaction

from .models import Material, MovimentoEstoque

logger = logging.getLogger(__name__)

_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
_CENTAVO = Decimal("0.01")


def parse_quantidade(valor):
    """Extrai o número do começo de uma quantidade escrita solta pelo técnico.

    ``'10'`` -> 10 ; ``'10,5 m'`` -> 10.5 ; ``'3x2,5'`` -> None (ambíguo) ;
    ``''`` -> None. Só devolve um número quando dá pra ter certeza.
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    # '3x2,5', '2 un + 1', '10/2' — mais de um número ou operador: não arrisca.
    if any(s in texto.lower() for s in ("x", "+", "/", "*", "~", "a ")):
        return None
    m = _NUM_RE.match(texto)
    if not m:
        return None
    try:
        q = Decimal(m.group(0).replace(",", "."))
    except InvalidOperation:
        return None
    return q if q > 0 else None


@transaction.atomic
def aplicar_entrada(
    material,
    quantidade,
    *,
    custo_unitario=None,
    documento="",
    observacao="",
    usuario=None,
):
    """Entrada de compra: soma ao saldo e recalcula o custo médio ponderado."""
    material = Material.objects.select_for_update().get(pk=material.pk)
    quantidade = Decimal(quantidade)
    saldo_anterior = material.saldo

    if custo_unitario is not None and Decimal(custo_unitario) >= 0:
        custo_entrada = Decimal(custo_unitario)
        base = saldo_anterior if saldo_anterior > 0 else Decimal("0")
        total = base + quantidade
        if total > 0:
            material.custo_unitario = (
                (base * material.custo_unitario + quantidade * custo_entrada) / total
            ).quantize(_CENTAVO)
    else:
        custo_entrada = material.custo_unitario

    material.saldo = saldo_anterior + quantidade
    material.save(update_fields=["saldo", "custo_unitario", "atualizado_em"])
    return MovimentoEstoque.objects.create(
        material=material,
        tipo=MovimentoEstoque.Tipo.ENTRADA,
        quantidade=quantidade,
        saldo_apos=material.saldo,
        custo_unitario=custo_entrada,
        documento=documento,
        observacao=observacao,
        usuario=usuario,
    )


@transaction.atomic
def aplicar_ajuste(material, saldo_contado, *, observacao="", usuario=None):
    """Ajuste de inventário: define o saldo absoluto ('contei, tem 12')."""
    material = Material.objects.select_for_update().get(pk=material.pk)
    saldo_contado = Decimal(saldo_contado)
    material.saldo = saldo_contado
    material.save(update_fields=["saldo", "atualizado_em"])
    return MovimentoEstoque.objects.create(
        material=material,
        tipo=MovimentoEstoque.Tipo.AJUSTE,
        quantidade=saldo_contado,
        saldo_apos=saldo_contado,
        observacao=observacao,
        usuario=usuario,
    )


@transaction.atomic
def aplicar_saida(
    material, quantidade, *, ordem_servico=None, observacao="", usuario=None
):
    """Saída de material. Pode deixar o saldo negativo (o técnico usou o que o
    sistema não sabia que existia) — o item fica sinalizado na tela."""
    material = Material.objects.select_for_update().get(pk=material.pk)
    quantidade = Decimal(quantidade)
    material.saldo = material.saldo - quantidade
    material.save(update_fields=["saldo", "atualizado_em"])
    return MovimentoEstoque.objects.create(
        material=material,
        tipo=MovimentoEstoque.Tipo.SAIDA,
        quantidade=quantidade,
        saldo_apos=material.saldo,
        ordem_servico=ordem_servico,
        observacao=observacao,
        usuario=usuario,
    )


def sincronizar_saida_os(ordem, relato, *, usuario=None):
    """(Re)aplica as saídas de estoque de uma OS a partir do relato.

    Idempotente: reverte as saídas anteriores desta OS e regera. Só baixa
    material que casa (nome exato, ignorando maiúsculas) com um ``Material``
    ativo e cuja quantidade é um número. Devolve um resumo do que baixou e do
    que ficou de fora. **Nunca levanta** — estoque não pode travar a conclusão
    de uma OS.
    """
    resultado = {"baixados": [], "ignorados": []}
    try:
        with transaction.atomic():
            anteriores = list(
                MovimentoEstoque.objects.filter(
                    ordem_servico=ordem, tipo=MovimentoEstoque.Tipo.SAIDA
                )
            )
            for mov in anteriores:
                m = Material.objects.select_for_update().get(pk=mov.material_id)
                m.saldo = m.saldo + mov.quantidade
                m.save(update_fields=["saldo", "atualizado_em"])
            MovimentoEstoque.objects.filter(
                ordem_servico=ordem, tipo=MovimentoEstoque.Tipo.SAIDA
            ).delete()

            for item in (relato or {}).get("materiais", []):
                descricao = (item.get("descricao") or "").strip()
                if not descricao:
                    continue
                material = Material.objects.filter(
                    descricao__iexact=descricao, ativo=True
                ).first()
                if material is None:
                    resultado["ignorados"].append(
                        {"descricao": descricao, "motivo": "material não cadastrado no estoque"}
                    )
                    continue
                qtd = parse_quantidade(item.get("quantidade"))
                if qtd is None:
                    resultado["ignorados"].append(
                        {"descricao": descricao, "motivo": "quantidade não numérica"}
                    )
                    continue
                aplicar_saida(
                    material,
                    qtd,
                    ordem_servico=ordem,
                    observacao=f"Baixa automática — OS {ordem.numero}",
                    usuario=usuario,
                )
                resultado["baixados"].append(
                    {
                        "descricao": material.descricao,
                        "quantidade": str(qtd),
                        "unidade": material.unidade,
                    }
                )
    except Exception:  # pragma: no cover - trilha de segurança
        logger.exception("Falha ao sincronizar baixa de estoque da OS %s", ordem.pk)
        return {"baixados": [], "ignorados": [], "erro": True}
    return resultado
