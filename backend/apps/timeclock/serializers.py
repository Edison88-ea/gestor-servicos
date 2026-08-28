from rest_framework import serializers

from config.drf_fields import CoordinateField, MetersField

from .models import RegistroPonto, SolicitacaoPonto


class RegistroPontoSerializer(serializers.ModelSerializer):
    funcionario_nome = serializers.CharField(source="funcionario.get_full_name", read_only=True)
    latitude = CoordinateField()
    longitude = CoordinateField()
    precisao_metros = MetersField()

    class Meta:
        model = RegistroPonto
        fields = (
            "id",
            "funcionario",
            "funcionario_nome",
            "tipo",
            "registrado_em",
            "sincronizado_em",
            "latitude",
            "longitude",
            "precisao_metros",
            "endereco",
            "justificativa",
            "foto",
            "origem_offline",
        )
        read_only_fields = ("funcionario", "sincronizado_em")


class SolicitacaoPontoSerializer(serializers.ModelSerializer):
    funcionario_nome = serializers.CharField(source="funcionario.get_full_name", read_only=True)
    analisado_por_nome = serializers.CharField(source="analisado_por.get_full_name", read_only=True)

    class Meta:
        model = SolicitacaoPonto
        fields = (
            "id",
            "funcionario",
            "funcionario_nome",
            "tipo",
            "data_referencia",
            "tipo_ponto_solicitado",
            "horario_solicitado",
            "pontos_propostos",
            "pontos_anteriores",
            "descricao",
            "status",
            "analisado_por",
            "analisado_por_nome",
            "analisado_em",
            "resposta_gestor",
            "criado_em",
        )
        read_only_fields = (
            "funcionario",
            "pontos_anteriores",
            "status",
            "analisado_por",
            "analisado_em",
            "resposta_gestor",
            "criado_em",
        )

    def validate(self, dados):
        if dados.get("tipo") == SolicitacaoPonto.Tipo.AJUSTE_DIA:
            pontos = dados.get("pontos_propostos") or []
            tipos_validos = set(RegistroPonto.Tipo.values)
            for p in pontos:
                if not isinstance(p, dict) or p.get("tipo") not in tipos_validos or not p.get("horario"):
                    raise serializers.ValidationError(
                        {"pontos_propostos": "Cada ponto precisa de tipo válido e horário."}
                    )
        return dados
