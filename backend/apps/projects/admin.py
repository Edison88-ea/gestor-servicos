from django.contrib import admin

from .models import (
    AssinaturaProjeto,
    Etapa,
    FotoEtapa,
    HistoricoEtapa,
    PlantaProjeto,
    Projeto,
)


class EtapaInline(admin.TabularInline):
    model = Etapa
    extra = 0


class PlantaInline(admin.TabularInline):
    model = PlantaProjeto
    extra = 0


class AssinaturaInline(admin.TabularInline):
    model = AssinaturaProjeto
    extra = 0
    readonly_fields = ("assinado_em",)


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("numero", "nome", "tipo", "status", "progresso", "data_termino_previsto")
    list_filter = ("status", "tipo")
    search_fields = ("numero", "nome", "responsavel")
    readonly_fields = ("numero", "criado_em", "atualizado_em")
    inlines = [EtapaInline, PlantaInline, AssinaturaInline]

    @admin.display(description="Progresso")
    def progresso(self, obj):
        return f"{obj.progresso}%"


class FotoEtapaInline(admin.TabularInline):
    model = FotoEtapa
    extra = 0
    readonly_fields = ("enviado_em",)


class HistoricoEtapaInline(admin.TabularInline):
    model = HistoricoEtapa
    extra = 0
    readonly_fields = ("data", "quantidade_anterior", "quantidade_nova", "usuario", "observacao")
    can_delete = False


@admin.register(Etapa)
class EtapaAdmin(admin.ModelAdmin):
    list_display = ("nome", "projeto", "tipo_ponto", "localizacao", "realizado", "meta")
    list_filter = ("tipo_ponto",)
    search_fields = ("nome", "projeto__numero", "projeto__nome", "localizacao")
    inlines = [FotoEtapaInline, HistoricoEtapaInline]
