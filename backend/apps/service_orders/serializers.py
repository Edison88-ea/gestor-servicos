from rest_framework import serializers

from apps.clients.serializers import ClienteSerializer
from config.drf_fields import CoordinateField

from .models import (
    FotoOrdemServico,
    MaterialCatalogo,
    OrdemServico,
    PausaOrdemServico,
    ServicoCatalogo,
)


class RelativeImageField(serializers.ImageField):
    """Serializa o caminho relativo (/media/...) em vez da URL absoluta.

    A URL absoluta do DRF usa o Host/scheme que chega no Django, que atrás do
    proxy do Vite / de um túnel vira `http://localhost:5173/...` — quebra como
    conteúdo misto no celular. O caminho relativo funciona em qualquer origem
    (dev, túnel, produção)."""

    def to_representation(self, value):
        if not value:
            return None
        return value.url


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
