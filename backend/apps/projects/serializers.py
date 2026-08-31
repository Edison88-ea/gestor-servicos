from rest_framework import serializers

from config.drf_fields import RelativeFileField, RelativeImageField

from .catalogos import AREAS_AFETADAS_VALIDAS
from .models import (
    AssinaturaProjeto,
    Etapa,
    FotoEtapa,
    HistoricoEtapa,
    PlantaProjeto,
    Projeto,
)


class FotoEtapaSerializer(serializers.ModelSerializer):
    imagem = RelativeImageField()
    enviado_por_nome = serializers.CharField(
        source="enviado_por.get_full_name", read_only=True
    )

    class Meta:
        model = FotoEtapa
        fields = ("id", "etapa", "imagem", "legenda", "enviado_por_nome", "enviado_em")
        read_only_fields = ("etapa", "enviado_por_nome", "enviado_em")


class HistoricoEtapaSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.get_full_name", read_only=True)

    class Meta:
        model = HistoricoEtapa
        fields = (
            "id",
            "usuario_nome",
            "data",
            "quantidade_anterior",
            "quantidade_nova",
            "observacao",
        )
        read_only_fields = fields


class EtapaSerializer(serializers.ModelSerializer):
    fotos = FotoEtapaSerializer(many=True, read_only=True)
    historico = HistoricoEtapaSerializer(many=True, read_only=True)
    porcentagem = serializers.ReadOnlyField()
    concluida = serializers.ReadOnlyField()
    tipo_ponto_display = serializers.CharField(source="get_tipo_ponto_display", read_only=True)

    class Meta:
        model = Etapa
        fields = (
            "id",
            "projeto",
            "nome",
            "tipo_ponto",
            "tipo_ponto_display",
            "localizacao",
            "meta",
            "realizado",
            "ordem",
            "porcentagem",
            "concluida",
            "fotos",
            "historico",
        )
        # 'realizado' só muda pela action /progresso/, que grava o histórico.
        read_only_fields = ("realizado",)


class PlantaProjetoSerializer(serializers.ModelSerializer):
    arquivo = RelativeFileField()

    class Meta:
        model = PlantaProjeto
        fields = ("id", "projeto", "arquivo", "pagina", "descricao", "enviado_em")
        read_only_fields = ("projeto", "enviado_em")


class AssinaturaProjetoSerializer(serializers.ModelSerializer):
    assinatura = RelativeImageField()
    papel_display = serializers.CharField(source="get_papel_display", read_only=True)

    class Meta:
        model = AssinaturaProjeto
        fields = ("id", "projeto", "papel", "papel_display", "nome", "assinatura", "assinado_em")
        read_only_fields = ("projeto", "assinado_em")


class ProjetoSerializer(serializers.ModelSerializer):
    etapas = EtapaSerializer(many=True, read_only=True)
    plantas = PlantaProjetoSerializer(many=True, read_only=True)
    assinaturas = AssinaturaProjetoSerializer(many=True, read_only=True)
    progresso = serializers.ReadOnlyField()
    total_meta = serializers.ReadOnlyField()
    total_realizado = serializers.ReadOnlyField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    criado_por_nome = serializers.CharField(source="criado_por.get_full_name", read_only=True)

    class Meta:
        model = Projeto
        fields = (
            "id",
            "numero",
            "nome",
            "descricao",
            "responsavel",
            "tipo",
            "tipo_display",
            "status",
            "status_display",
            "areas_afetadas",
            "data_mudanca",
            "data_termino_previsto",
            "data_conclusao",
            "criado_por_nome",
            "criado_em",
            "atualizado_em",
            "progresso",
            "total_meta",
            "total_realizado",
            "etapas",
            "plantas",
            "assinaturas",
        )
        read_only_fields = ("numero", "criado_por", "criado_em", "atualizado_em")

    def validate_areas_afetadas(self, valor):
        if not isinstance(valor, list):
            raise serializers.ValidationError("Envie uma lista de códigos de área.")
        invalidas = [v for v in valor if v not in AREAS_AFETADAS_VALIDAS]
        if invalidas:
            raise serializers.ValidationError(
                f"Área(s) desconhecida(s): {', '.join(map(str, invalidas))}"
            )
        return valor


class ProjetoResumoSerializer(serializers.ModelSerializer):
    """Versão enxuta para a listagem (sem etapas/plantas aninhadas)."""

    progresso = serializers.ReadOnlyField()
    total_meta = serializers.ReadOnlyField()
    total_realizado = serializers.ReadOnlyField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Projeto
        fields = (
            "id",
            "numero",
            "nome",
            "responsavel",
            "tipo",
            "status",
            "status_display",
            "areas_afetadas",
            "data_mudanca",
            "data_termino_previsto",
            "progresso",
            "total_meta",
            "total_realizado",
            "criado_em",
        )
