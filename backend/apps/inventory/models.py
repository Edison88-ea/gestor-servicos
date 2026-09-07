from decimal import Decimal

from django.conf import settings
from django.db import models


class Material(models.Model):
    """Um item que a empresa controla em estoque.

    Diferente do ``service_orders.MaterialCatalogo`` (que é só o dicionário de
    autocomplete do relato de OS): aqui há saldo, custo e mínimo. Nem todo
    material que aparece num relato precisa virar item de estoque — só os que a
    gestão decide rastrear.
    """

    descricao = models.CharField(max_length=200, unique=True)
    unidade = models.CharField(max_length=10, blank=True)
    saldo = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    estoque_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    custo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Custo médio ponderado, atualizado a cada entrada.",
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["descricao"]
        verbose_name = "material"
        verbose_name_plural = "materiais"

    def __str__(self):
        return self.descricao

    @property
    def abaixo_minimo(self):
        return self.estoque_minimo > 0 and self.saldo < self.estoque_minimo

    @property
    def valor_em_estoque(self):
        return (self.saldo * self.custo_unitario).quantize(Decimal("0.01"))


class MovimentoEstoque(models.Model):
    """Cada entrada, saída ou ajuste de um material.

    Imutável depois de criado — o histórico é a trilha de auditoria do estoque
    (como o ``HistoricoEtapa`` das obras). O saldo do material acompanha a soma
    dos movimentos; ``saldo_apos`` guarda o snapshot na hora do movimento.
    """

    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SAIDA = "SAIDA", "Saída"
        AJUSTE = "AJUSTE", "Ajuste de inventário"

    material = models.ForeignKey(
        Material, on_delete=models.PROTECT, related_name="movimentos"
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    quantidade = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Sempre positiva. Em AJUSTE, é o saldo que foi contado.",
    )
    saldo_apos = models.DecimalField(max_digits=12, decimal_places=3)
    custo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Preenchido na ENTRADA (custo da compra).",
    )
    ordem_servico = models.ForeignKey(
        "service_orders.OrdemServico",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentos_estoque",
    )
    documento = models.CharField(
        max_length=120,
        blank=True,
        help_text="Nota fiscal / fornecedor / referência.",
    )
    observacao = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="movimentos_estoque",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-id"]
        verbose_name = "movimento de estoque"
        verbose_name_plural = "movimentos de estoque"
        indexes = [
            models.Index(fields=["material", "-criado_em"]),
            models.Index(fields=["ordem_servico"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.material.descricao} · {self.quantidade}"
