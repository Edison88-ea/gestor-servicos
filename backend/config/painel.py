"""Painel do gestor: um endpoint agregado com o que a gestão olha no dia a dia.

Fica em config/ (não num app) porque cruza service_orders, timeclock e
projects.

Escopo:
- GESTOR / RH / ADMIN: a empresa toda.
- ENCARREGADO: a própria equipe (ele + quem se reporta a ele). Não vê
  solicitações de ponto (não aprova).
"""

from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Usuario
from apps.projects.models import Projeto
from apps.service_orders.models import OrdemServico
from apps.timeclock.models import RegistroPonto, SolicitacaoPonto
from apps.timeclock.views import _calcular_dias

_OS_ABERTAS = [
    OrdemServico.Status.ABERTA,
    OrdemServico.Status.ATRIBUIDA,
    OrdemServico.Status.EM_ANDAMENTO,
    OrdemServico.Status.PAUSADA,
]
_OBRAS_ATIVAS = [Projeto.Status.PLANEJADO, Projeto.Status.EM_ANDAMENTO]
_PONTO_ROTULO = {
    "ENTRADA": "Em jornada",
    "VOLTA_INTERVALO": "Em jornada",
    "SAIDA_INTERVALO": "Em intervalo",
    "SAIDA": "Jornada encerrada",
}


def _funcionarios(user):
    base = Usuario.objects.filter(
        is_active=True,
        papel__in=[Usuario.Papel.TECNICO, Usuario.Papel.ENCARREGADO],
    )
    if user.e_gestao:
        return base
    return base.filter(Q(encarregado_responsavel=user) | Q(id=user.id))


def _ordens(user):
    qs = OrdemServico.objects.select_related("cliente", "tecnico")
    if user.e_gestao:
        return qs
    ids = [user.id, *user.equipe.values_list("id", flat=True)]
    return qs.filter(tecnico_id__in=ids)


def _saldo_horas_mes(funcionarios, inicio_mes, ate):
    extras = faltantes = 0
    if ate >= inicio_mes:
        for func in (f for f in funcionarios if f.registra_ponto):
            for dia in _calcular_dias(
                func, inicio_mes.isoformat(), ate.isoformat(), None, resumo=True
            ):
                extras += dia["extra_minutos"]
                faltantes += dia["falta_minutos"]
    return extras, faltantes


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def painel(request):
    user = request.user
    if not (user.e_gestao or user.papel == Usuario.Papel.ENCARREGADO):
        raise PermissionDenied("Sem acesso ao painel.")

    agora = timezone.now()
    hoje = timezone.localdate()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1)

    funcionarios = list(_funcionarios(user))
    os_qs = _ordens(user)

    # --- KPIs ---
    extras, faltantes = _saldo_horas_mes(funcionarios, inicio_mes, hoje - timedelta(days=1))
    # três contagens de OS numa query só (Count com filtro condicional)
    os_contagens = os_qs.aggregate(
        abertas=Count("id", filter=Q(status__in=_OS_ABERTAS)),
        concl_semana=Count(
            "id",
            filter=Q(
                status=OrdemServico.Status.CONCLUIDA,
                data_conclusao__date__gte=inicio_semana,
            ),
        ),
        concl_mes=Count(
            "id",
            filter=Q(
                status=OrdemServico.Status.CONCLUIDA,
                data_conclusao__date__gte=inicio_mes,
            ),
        ),
    )
    kpis = {
        "os_abertas": os_contagens["abertas"],
        "os_concluidas_semana": os_contagens["concl_semana"],
        "os_concluidas_mes": os_contagens["concl_mes"],
        "solicitacoes_pendentes": (
            SolicitacaoPonto.objects.filter(status=SolicitacaoPonto.Status.PENDENTE).count()
            if user.e_gestao
            else 0
        ),
        "obras_ativas": Projeto.objects.filter(status__in=_OBRAS_ATIVAS).count(),
        "horas_extras_mes_min": extras,
        "horas_faltantes_mes_min": faltantes,
    }

    # --- Operação de hoje: ponto + OS em andamento de cada um ---
    ids = [f.id for f in funcionarios]
    ultimo_ponto = {}
    for r in RegistroPonto.objects.filter(
        funcionario_id__in=ids, registrado_em__date=hoje
    ).order_by("registrado_em"):
        ultimo_ponto[r.funcionario_id] = r

    os_em_andamento = {}
    for o in os_qs.filter(status=OrdemServico.Status.EM_ANDAMENTO, tecnico_id__in=ids).order_by(
        "-data_inicio"
    ):
        os_em_andamento.setdefault(o.tecnico_id, o)

    equipe = []
    for f in funcionarios:
        r = ultimo_ponto.get(f.id)
        o = os_em_andamento.get(f.id)
        equipe.append(
            {
                "id": f.id,
                "nome": f.get_full_name() or f.username,
                "cargo": f.cargo,
                "papel": f.papel,
                "ponto": (
                    {
                        "rotulo": _PONTO_ROTULO.get(r.tipo, r.tipo),
                        "hora": timezone.localtime(r.registrado_em).strftime("%H:%M"),
                    }
                    if r
                    else {"rotulo": "Não bateu ponto", "hora": None}
                ),
                "os_atual": (
                    {
                        "id": o.id,
                        "numero": o.numero,
                        "cliente": o.cliente.nome,
                        "desde": timezone.localtime(o.data_inicio).strftime("%H:%M")
                        if o.data_inicio
                        else None,
                    }
                    if o
                    else None
                ),
            }
        )

    # --- Pendências ---
    solicitacoes = []
    if user.e_gestao:
        for s in SolicitacaoPonto.objects.filter(
            status=SolicitacaoPonto.Status.PENDENTE
        ).select_related("funcionario").order_by("criado_em"):
            solicitacoes.append(
                {
                    "id": s.id,
                    "funcionario_nome": s.funcionario.get_full_name() or s.funcionario.username,
                    "tipo_display": s.get_tipo_display(),
                    "data_referencia": s.data_referencia.isoformat(),
                    "descricao": s.descricao,
                }
            )

    os_sem_tecnico = [
        {
            "id": o.id,
            "numero": o.numero,
            "cliente_nome": o.cliente.nome,
            "dias": (agora - o.criado_em).days,
        }
        for o in os_qs.filter(status__in=_OS_ABERTAS, tecnico__isnull=True).order_by("criado_em")
    ]

    limite_atribuida = agora - timedelta(days=2)
    limite_andamento = agora - timedelta(days=3)
    paradas = []
    paradas_por_tec = defaultdict(int)
    for o in os_qs.filter(status__in=_OS_ABERTAS).exclude(tecnico__isnull=True).order_by("criado_em"):
        if o.status == OrdemServico.Status.ATRIBUIDA and o.data_inicio is None and o.criado_em < limite_atribuida:
            motivo = "sem iniciar"
            base = o.criado_em
        elif o.status in (OrdemServico.Status.EM_ANDAMENTO, OrdemServico.Status.PAUSADA) and o.atualizado_em < limite_andamento:
            motivo = "sem movimento"
            base = o.atualizado_em
        else:
            continue
        paradas_por_tec[o.tecnico_id] += 1
        paradas.append(
            {
                "id": o.id,
                "numero": o.numero,
                "cliente_nome": o.cliente.nome,
                "tecnico_nome": o.tecnico.get_full_name() or o.tecnico.username,
                "status": o.status,
                "motivo": motivo,
                "dias": (agora - base).days,
            }
        )

    os_abertas_lista = [
        {
            "id": o.id,
            "numero": o.numero,
            "cliente_nome": o.cliente.nome,
            "tecnico_nome": (o.tecnico.get_full_name() or o.tecnico.username) if o.tecnico else None,
            "status": o.status,
            "prioridade": o.prioridade,
        }
        for o in os_qs.filter(
            status__in=[OrdemServico.Status.ATRIBUIDA, OrdemServico.Status.EM_ANDAMENTO, OrdemServico.Status.PAUSADA]
        ).order_by("-criado_em")
    ]

    # --- Produtividade por técnico ---
    concl_mes = dict(
        os_qs.filter(status=OrdemServico.Status.CONCLUIDA, data_conclusao__date__gte=inicio_mes, tecnico_id__in=ids)
        .values("tecnico_id")
        .annotate(n=Count("id"))
        .values_list("tecnico_id", "n")
    )
    abertas_tec = dict(
        os_qs.filter(status__in=_OS_ABERTAS, tecnico_id__in=ids)
        .values("tecnico_id")
        .annotate(n=Count("id"))
        .values_list("tecnico_id", "n")
    )
    produtividade = [
        {
            "id": f.id,
            "nome": f.get_full_name() or f.username,
            "os_em_aberto": abertas_tec.get(f.id, 0),
            "os_concluidas_mes": concl_mes.get(f.id, 0),
            "os_paradas": paradas_por_tec.get(f.id, 0),
        }
        for f in funcionarios
    ]

    # --- Obras ativas ---
    obras = []
    for p in (
        Projeto.objects.filter(status__in=_OBRAS_ATIVAS)
        .annotate(_meta=Sum("etapas__meta"), _real=Sum("etapas__realizado"), _n=Count("etapas", distinct=True))
        .order_by("data_termino_previsto", "numero")
    ):
        meta = p._meta or 0
        real = p._real or 0
        obras.append(
            {
                "id": p.id,
                "numero": p.numero,
                "nome": p.nome,
                "status": p.status,
                "progresso": int(min(real / meta * 100, 100)) if meta else 0,
                "realizado": real,
                "meta": meta,
                "etapas": p._n,
                "termino_previsto": p.data_termino_previsto.isoformat() if p.data_termino_previsto else None,
                "atrasada": bool(p.data_termino_previsto and p.data_termino_previsto < hoje),
            }
        )

    return Response(
        {
            "kpis": kpis,
            "equipe": equipe,
            "pendencias": {
                "solicitacoes": solicitacoes,
                "os_sem_tecnico": os_sem_tecnico,
                "os_paradas": paradas,
            },
            "os_abertas": os_abertas_lista,
            "produtividade": produtividade,
            "obras": obras,
            "e_gestao": user.e_gestao,
            "gerado_em": agora,
        }
    )
