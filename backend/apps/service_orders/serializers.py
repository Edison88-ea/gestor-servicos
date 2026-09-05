from rest_framework import serializers

from apps.clients.serializers import ClienteSerializer
from config.drf_fields import CoordinateField, RelativeImageField

from .models import (
    FotoOrdemServico,
    MaterialCatalogo,
    OrdemServico,
    PausaOrdemServico,
    ServicoCatalogo,
)


class FotoOrdemServicoSerializer(serializers.ModelSerializer):
    imagem = RelativeImageField()

    class Meta:
        model = FotoOrdemServico
        fields = ("id", "ordem_servico", "imagem", "legenda", "enviado_em")
        read_only_fields = ("ordem_servico", "enviado_em")


class ServicoCatalogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicoCatalogo
        fields = ("descricao",)


class MaterialCatalogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialCatalogo
        fields = ("descricao", "unidade_padrao")


class PausaOrdemServicoSerializer(serializers.ModelSerializer):
    motivo_display = serializers.CharField(source="get_motivo_display", read_only=True)

    class Meta:
        model = PausaOrdemServico
        fields = ("id", "motivo", "motivo_display", "observacao", "iniciada_em", "retomada_em")
        read_only_fields = ("iniciada_em", "retomada_em")


class OrdemServicoSerializer(serializers.ModelSerializer):
    fotos = FotoOrdemServicoSerializer(many=True, read_only=True)
    pausas = PausaOrdemServicoSerializer(many=True, read_only=True)
    assinatura_cliente = RelativeImageField(required=False, allow_null=True)
    latitude_abertura = CoordinateField()
    longitude_abertura = CoordinateField()
    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True)
    # Dados completos do cliente para o comprovante de atendimento (PDF).
    cliente_detalhe = ClienteSerializer(source="cliente", read_only=True)
    tecnico_nome = serializers.CharField(source="tecnico.get_full_name", read_only=True)
    criado_por_nome = serializers.CharField(source="criado_por.get_full_name", read_only=True)

    class Meta:
        model = OrdemServico
        fields = (
            "id",
            "numero",
            "cliente",
            "cliente_nome",
            "cliente_detalhe",
            "tecnico",
            "tecnico_nome",
            "criado_por",
            "criado_por_nome",
            "tipo_servico",
            "descricao",
            "prioridade",
            "status",
            "checklist",
            "relato",
            "observacoes_tecnico",
            "assinatura_cliente",
            "latitude_abertura",
            "longitude_abertura",
            "data_agendada",
            "data_inicio",
            "data_conclusao",
            "criado_em",
            "atualizado_em",
            "fotos",
            "pausas",
        )
        read_only_fields = ("numero", "criado_por", "criado_em", "atualizado_em", "status")


class OrdemServicoListSerializer(serializers.ModelSerializer):
    """Versão enxuta para a listagem. As telas de lista (OrdensServico,
    Painel do Gestor) só mostram número, cliente, técnico, status e datas —
    não precisam de checklist, relato, assinatura, fotos, pausas nem do
    cliente_detalhe. Isso corta o payload de ~1 KB para ~250 B por OS.
    """

    cliente_nome = serializers.CharField(source="cliente.nome", read_only=True)
    tecnico_nome = serializers.CharField(source="tecnico.get_full_name", read_only=True)

    class Meta:
        model = OrdemServico
        fields = (
            "id",
            "numero",
            "cliente",
            "cliente_nome",
            "tecnico",
            "tecnico_nome",
            "tipo_servico",
            "prioridade",
            "status",
            "data_agendada",
            "data_inicio",
            "data_conclusao",
            "criado_em",
        )
