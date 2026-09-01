"""Painel do gestor: um endpoint agregado com os números que a gestão olha.

Fica em config/ (não num app) porque cruza service_orders, timeclock e
projects. Só gestor/RH/admin acessam.
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Usuario
from apps.projects.models import Projeto
from apps.service_orders.models import OrdemServico
from apps.timeclock.models import SolicitacaoPonto
from apps.timeclock.views import _calcular_dias

_OS_ABERTAS = [
    OrdemServico.Status.ABERTA,
    OrdemServico.Status.ATRIBUIDA,
    OrdemServico.Status.EM_ANDAMENTO,
    OrdemServico.Status.PAUSADA,
]
_OBRAS_ATIVAS = [Projeto.Status.PLANEJADO, Projeto.Status.EM_ANDAMENTO]


def _saldo_horas_mes(inicio_mes, ate):
    """Soma, de todos os funcionários de campo, as horas extras e faltantes do
    mês até `ate` (exclui hoje, que ainda está em curso)."""
    extras = faltantes = 0
    if ate < inicio_mes:
        return 0, 0
    funcionarios = Usuario.objects.filter(
        is_active=True,
        papel__in=[Usuario.Papel.TECNICO, Usuario.Papel.ENCARREGADO],
    )
    for func in funcionarios:
        for dia in _calcular_dias(func, inicio_mes.isoformat(), ate.isoformat(), None):
            if dia["saldo_minutos"] > 0:
                extras += dia["saldo_minutos"]
            elif dia["saldo_minutos"] < 0:
                faltantes += -dia["saldo_minutos"]
    return extras, faltantes


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def painel(request):
    if not request.user.e_gestao:
        raise PermissionDenied("Apenas gestor, RH ou admin.")

    hoje = timezone.localdate()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1)

    os_qs = OrdemServico.objects.all()
    extras, faltantes = _saldo_horas_mes(inicio_mes, hoje - timedelta(days=1))

    kpis = {
        "os_abertas": os_qs.filter(status__in=_OS_ABERTAS).count(),
        "os_concluidas_semana": os_qs.filter(
            status=OrdemServico.Status.CONCLUIDA,
            data_conclusao__date__gte=inicio_semana,
        ).count(),
        "os_concluidas_mes": os_qs.filter(
            status=OrdemServico.Status.CONCLUIDA,
            data_conclusao__date__gte=inicio_mes,
        ).count(),
        "solicitacoes_pendentes": SolicitacaoPonto.objects.filter(
            status=SolicitacaoPonto.Status.PENDENTE
        ).count(),
        "obras_ativas": Projeto.objects.filter(status__in=_OBRAS_ATIVAS).count(),
        "horas_extras_mes_min": extras,
        "horas_faltantes_mes_min": faltantes,
    }

    return Response({"kpis": kpis, "gerado_em": timezone.now()})
