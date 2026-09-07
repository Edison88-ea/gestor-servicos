from django.contrib import admin

from .models import Material, MovimentoEstoque


class MovimentoInline(admin.TabularInline):
    model = MovimentoEstoque
    extra = 0
    can_delete = False
    ordering = ("-criado_em",)
    readonly_fields = (
        "tipo",
        "quantidade",
        "saldo_apos",
        "custo_unitario",
        "ordem_servico",
        "documento",
        "observacao",
        "usuario",
        "criado_em",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "descricao",
        "unidade",
        "saldo",
        "estoque_minimo",
        "custo_unitario",
        "ativo",
    )
    list_filter = ("ativo",)
    search_fields = ("descricao",)
    readonly_fields = ("saldo", "custo_unitario", "criado_em", "atualizado_em")
    inlines = [MovimentoInline]


@admin.register(MovimentoEstoque)
class MovimentoEstoqueAdmin(admin.ModelAdmin):
    list_display = (
        "criado_em",
        "material",
        "tipo",
        "quantidade",
        "saldo_apos",
        "usuario",
    )
    list_filter = ("tipo",)
    search_fields = ("material__descricao", "documento")
    readonly_fields = [f.name for f in MovimentoEstoque._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
