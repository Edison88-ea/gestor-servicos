from django.contrib import admin

from .models import (
    FotoOrdemServico,
    MaterialCatalogo,
    OrdemServico,
    PausaOrdemServico,
    ServicoCatalogo,
)


class FotoInline(admin.TabularInline):
    model = FotoOrdemServico
    extra = 0


class PausaInline(admin.TabularInline):
    model = PausaOrdemServico
    extra = 0
    readonly_fields = ("iniciada_em",)


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ("numero", "cliente", "tecnico", "status", "prioridade", "criado_em")
    list_filter = ("status", "prioridade")
    search_fields = ("numero", "cliente__nome", "tecnico__username")
    inlines = [PausaInline, FotoInline]


@admin.register(ServicoCatalogo)
class ServicoCatalogoAdmin(admin.ModelAdmin):
    list_display = ("descricao", "usos")
    search_fields = ("descricao",)


@admin.register(MaterialCatalogo)
class MaterialCatalogoAdmin(admin.ModelAdmin):
    list_display = ("descricao", "unidade_padrao", "usos")
    list_editable = ("unidade_padrao",)
    search_fields = ("descricao",)
