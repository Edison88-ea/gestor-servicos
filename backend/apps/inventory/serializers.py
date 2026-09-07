from rest_framework import serializers

from .models import Material, MovimentoEstoque


class MovimentoEstoqueSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    material_descricao = serializers.CharField(source="material.descricao", read_only=True)
    usuario_nome = serializers.CharField(source="usuario.get_full_name", read_only=True)
    os_numero = serializers.CharField(source="ordem_servico.numero", read_only=True)

    class Meta:
        model = MovimentoEstoque
        fields = (
            "id",
            "material",
            "material_descricao",
            "tipo",
            "tipo_display",
            "quantidade",
            "saldo_apos",
            "custo_unitario",
            "ordem_servico",
            "os_numero",
            "documento",
            "observacao",
            "usuario_nome",
            "criado_em",
        )
        read_only_fields = fields


class MaterialSerializer(serializers.ModelSerializer):
    abaixo_minimo = serializers.ReadOnlyField()
    valor_em_estoque = serializers.ReadOnlyField()

    class Meta:
        model = Material
        fields = (
            "id",
            "descricao",
            "unidade",
            "saldo",
            "estoque_minimo",
            "custo_unitario",
            "valor_em_estoque",
            "abaixo_minimo",
            "ativo",
            "criado_em",
            "atualizado_em",
        )
        # saldo e custo só mudam por movimento (entrada / ajuste), nunca por
        # PATCH direto no material.
        read_only_fields = ("saldo", "custo_unitario", "criado_em", "atualizado_em")
