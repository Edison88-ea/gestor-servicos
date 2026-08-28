from django.contrib import admin

from .models import RegistroPonto, SolicitacaoPonto


@admin.register(RegistroPonto)
class RegistroPontoAdmin(admin.ModelAdmin):
    list_display = ("funcionario", "tipo", "registrado_em", "origem_offline")
    list_filter = ("tipo", "origem_offline")
    search_fields = ("funcionario__username", "funcionario__first_name")
    date_hierarchy = "registrado_em"


@admin.register(SolicitacaoPonto)
class SolicitacaoPontoAdmin(admin.ModelAdmin):
    list_display = ("funcionario", "tipo", "data_referencia", "status", "criado_em")
    list_filter = ("tipo", "status")
    search_fields = ("funcionario__username", "funcionario__first_name")
