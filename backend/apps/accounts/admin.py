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
        (
            "Dados pessoais",
            {"fields": ("data_nascimento", "estado_civil", "genero", "nome_mae")},
        ),
        (
            "Documentos",
            {"fields": ("cpf", "rg", "pis", "ctps_numero", "ctps_serie")},
        ),
        (
            "Endereço",
            {"fields": ("cep", "logradouro", "numero_endereco", "complemento", "bairro", "cidade", "estado")},
        ),
        (
            "Contrato",
            {"fields": ("data_admissao", "data_desligamento", "salario")},
        ),
        (
            "Dados bancários",
            {"fields": ("banco", "agencia", "conta", "pix")},
        ),
        (
            "Contato de emergência",
            {"fields": ("contato_emergencia_nome", "contato_emergencia_telefone", "contato_emergencia_parentesco")},
        ),
    )
