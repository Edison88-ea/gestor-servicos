from rest_framework import serializers

from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "papel",
            "telefone",
            "cargo",
            "periodo1_inicio",
            "periodo1_fim",
            "periodo2_inicio",
            "periodo2_fim",
            "carga_horaria_diaria_minutos",
            "is_active",
        )
        read_only_fields = ("carga_horaria_diaria_minutos",)
