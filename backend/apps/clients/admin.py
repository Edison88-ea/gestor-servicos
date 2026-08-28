from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "documento", "telefone", "cidade", "ativo")
    list_filter = ("ativo", "estado")
    search_fields = ("nome", "documento", "email")
