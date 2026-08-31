from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "papel", "is_active")
    list_filter = ("papel", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Dados profissionais",
            {"fields": ("papel", "encarregado_responsavel", "telefone", "cargo", "ativo_desde")},
        ),
        (
            "Jornada de trabalho (segunda a sexta)",
            {
                "fields": ("periodo1_inicio", "periodo1_fim", "periodo2_inicio", "periodo2_fim"),
                "description": "Definida pelo RH. Deixe um período em branco (início e fim) se o funcionário só tiver um turno.",
            },
        ),
    )
