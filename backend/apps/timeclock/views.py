from collections import defaultdict
from datetime import date, datetime, time as _time, timedelta

from django.utils import timezone
from rest_framework import permissions, status as http_status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.models import Usuario
from apps.notifications.models import Notificacao
from apps.notifications.utils import notificar

from .models import RegistroPonto, SolicitacaoPonto
from .serializers import RegistroPontoSerializer, SolicitacaoPontoSerializer

_T = RegistroPonto.Tipo
TIPOS_ENTRADA = {_T.ENTRADA, _T.VOLTA_INTERVALO}
TIPOS_SAIDA = {_T.SAIDA_INTERVALO, _T.SAIDA}

# A partir do último ponto do dia, quais tipos fazem sentido em seguida.
TRANSICOES_PONTO = {
    None: {_T.ENTRADA},
    _T.ENTRADA: {_T.SAIDA_INTERVALO, _T.SAIDA},
    _T.SAIDA_INTERVALO: {_T.VOLTA_INTERVALO},
    _T.VOLTA_INTERVALO: {_T.SAIDA_INTERVALO, _T.SAIDA},
    _T.SAIDA: {_T.ENTRADA},  # segundo período / turno partido
}

_MSG_SEQUENCIA = {
    (None, _T.SAIDA_INTERVALO): "Bata a Entrada primeiro.",
    (None, _T.VOLTA_INTERVALO): "Bata a Entrada primeiro.",
    (None, _T.SAIDA): "Bata a Entrada primeiro.",
    (_T.ENTRADA, _T.ENTRADA): "Você já está em jornada.",
    (_T.ENTRADA, _T.VOLTA_INTERVALO): "Você não saiu para o intervalo.",
    (_T.SAIDA_INTERVALO, _T.ENTRADA): "Registre a Volta do intervalo primeiro.",
    (_T.SAIDA_INTERVALO, _T.SAIDA_INTERVALO): "Você já saiu para o intervalo.",
    (_T.SAIDA_INTERVALO, _T.SAIDA): "Registre a Volta do intervalo primeiro.",
    (_T.VOLTA_INTERVALO, _T.VOLTA_INTERVALO): "Você já voltou do intervalo.",
    (_T.SAIDA, _T.SAIDA): "Você já bateu a Saída.",
    (_T.SAIDA, _T.SAIDA_INTERVALO): "Bata a Entrada primeiro.",
    (_T.SAIDA, _T.VOLTA_INTERVALO): "Bata a Entrada primeiro.",
}

# Uma jornada (Entrada -> ... -> Saída) pode cruzar a meia-noite. Mas se ficar
# aberta por mais de 24h, é quase certeza que o funcionário esqueceu de bater a
# Saída — a partir daí a próxima batida válida volta a ser Entrada, e o cálculo
# do cartão ignora as horas da jornada abandonada (o acerto vira Solicitação de
# ajuste).
GUARDA_JORNADA = timedelta(hours=24)


def validar_sequencia_ponto(funcionario, tipo, registrado_em):
    """Levanta ValidationError se a batida não faz sentido na sequência ou se é
    uma duplicata (toque duplo / reenvio da fila offline).

    A "sequência" é a jornada, não o dia do calendário: uma Saída às 00:21 que
    fecha uma Entrada das 19:00 do dia anterior é válida."""
    # Janela larga o suficiente para conter uma jornada que abriu no dia anterior
    # e ainda pegar batidas offline que cheguem fora de ordem.
    recentes = list(
        RegistroPonto.objects.filter(
            funcionario=funcionario,
            registrado_em__gte=registrado_em - timedelta(hours=30),
            registrado_em__lte=registrado_em + timedelta(hours=30),
        ).order_by("registrado_em")
    )

    for r in recentes:
        if r.tipo == tipo and abs((r.registrado_em - registrado_em).total_seconds()) < 90:
            raise ValidationError(
                {"tipo": f"'{_T(tipo).label}' já foi registrado agora há pouco."}
            )

    # Encaixa a nova batida no lugar cronológico e caminha a máquina de estados.
    # Só a transição *para a batida nova* bloqueia — inconsistência entre batidas
    # já salvas não trava um registro legítimo.
    nova = (registrado_em, tipo)
    sequencia = sorted([(r.registrado_em, r.tipo) for r in recentes] + [nova])
    anterior, inicio_jornada = None, None
    for quando, t in sequencia:
        # jornada aberta há 24h+ = Saída esquecida: a máquina recomeça
        if inicio_jornada is not None and quando - inicio_jornada >= GUARDA_JORNADA:
            anterior, inicio_jornada = None, None
        if (quando, t) == nova and t not in TRANSICOES_PONTO.get(anterior, set()):
            msg = _MSG_SEQUENCIA.get(
                (anterior, t), "Essa batida não faz sentido na sequência."
            )
            raise ValidationError({"tipo": msg})
        if t == _T.ENTRADA:
            inicio_jornada = quando
        elif t == _T.SAIDA:
            inicio_jornada = None
        anterior = t


def _intervalo_datas(data_inicio, data_fim):
    atual = date.fromisoformat(data_inicio)
    fim = date.fromisoformat(data_fim)
    while atual <= fim:
        yield atual
        atual += timedelta(days=1)


def _agrupar_jornadas(registros):
    """Agrupa uma lista de RegistroPonto (ordenada por horário) em jornadas.

    Uma jornada vai de uma Entrada até a Saída e pode cruzar a meia-noite. Se
    ficar aberta 24h+ (Saída esquecida), é fechada como `abandonada` e a
    próxima batida inicia outra. Cada jornada é atribuída ao dia local em que
    começou."""
    jornadas = []
    atual = None

    def fechar(jornada, *, abandonada=False):
        jornada["abandonada"] = abandonada
        jornadas.append(jornada)

    for r in registros:
        if atual is not None and r.registrado_em - atual["inicio"] >= GUARDA_JORNADA:
            fechar(atual, abandonada=True)
            atual = None

        if atual is None:
            atual = {"inicio": r.registrado_em, "registros": [r], "fechada_em": None}
            if r.tipo != _T.ENTRADA:
                # batida órfã (Saída sem Entrada): jornada inconsistente de 1 item
                atual["inconsistente"] = True
                fechar(atual)
                atual = None
            continue

        atual["registros"].append(r)
        if r.tipo == _T.SAIDA:
            atual["fechada_em"] = r.registrado_em
            fechar(atual)
            atual = None

    if atual is not None:
        fechar(atual)  # jornada ainda em aberto
    return jornadas


def _minutos_trabalhados(jornada):
    total = timedelta()
    inicio_par = None
    for r in jornada["registros"]:
        if r.tipo in TIPOS_ENTRADA:
            inicio_par = r.registrado_em
        elif r.tipo in TIPOS_SAIDA and inicio_par:
            total += r.registrado_em - inicio_par
            inicio_par = None
    return int(total.total_seconds() // 60)


def _calcular_dias(funcionario, data_inicio, data_fim, request):
    """Para cada dia do período: registros, minutos trabalhados, esperados e
    saldo. Trabalha por jornada — um turno que vira a noite conta inteiro no
    dia em que começou."""
    d_ini = date.fromisoformat(data_inicio)
    d_fim = date.fromisoformat(data_fim)

    # margem de 1 dia de cada lado para pegar jornadas que cruzam a borda do
    # período (turno começando no último dia do mês, fechando no 1º do seguinte)
    registros = list(
        RegistroPonto.objects.filter(
            funcionario=funcionario,
            registrado_em__date__gte=d_ini - timedelta(days=1),
            registrado_em__date__lte=d_fim + timedelta(days=1),
        ).order_by("registrado_em")
    )

    trabalhado_por_dia = defaultdict(int)
    regs_por_dia = defaultdict(list)
    dias_em_aberto = set()
    for jornada in _agrupar_jornadas(registros):
        dia_j = timezone.localtime(jornada["inicio"]).date()
        trabalhado_por_dia[dia_j] += _minutos_trabalhados(jornada)
        regs_por_dia[dia_j].extend(jornada["registros"])
        if jornada["fechada_em"] is None and not jornada.get("abandonada") and not jornada.get("inconsistente"):
            dias_em_aberto.add(dia_j)

    dias = []
    for dia in _intervalo_datas(data_inicio, data_fim):
        regs = sorted(regs_por_dia.get(dia, []), key=lambda r: r.registrado_em)
        folga = dia.weekday() >= 5  # sábado/domingo
        futuro = dia > timezone.localdate()
        total_minutos = trabalhado_por_dia.get(dia, 0)
        # dias futuros ainda não aconteceram: não contam como falta nem extra
        esperado_minutos = 0 if (folga or futuro) else funcionario.carga_horaria_diaria_minutos
        saldo_minutos = total_minutos - esperado_minutos

        dias.append(
            {
                "data": dia,
                "folga": folga,
                "futuro": futuro,
                "registros": RegistroPontoSerializer(regs, many=True, context={"request": request}).data,
                "total_minutos": total_minutos,
                "esperado_minutos": esperado_minutos,
                "saldo_minutos": saldo_minutos,
                "em_aberto": dia in dias_em_aberto,
            }
        )
    return dias


class RegistroPontoViewSet(viewsets.ModelViewSet):
    """
    Bater ponto = criar um RegistroPonto (POST). O funcionário é sempre o
    usuário autenticado - a API não permite bater ponto por outra pessoa.
    Gestor/RH podem listar registros de todos; técnico só vê os próprios.
    """

    serializer_class = RegistroPontoSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = RegistroPonto.objects.select_related("funcionario")
        user = self.request.user
        params = self.request.query_params
        if user.papel == user.Papel.TECNICO:
            # técnico sempre vê só os próprios
            qs = qs.filter(funcionario=user)
        elif params.get("funcionario"):
            # gestor/RH pedindo os de um funcionário específico
            qs = qs.filter(funcionario_id=params["funcionario"])
        elif params.get("equipe"):
            # gestor/RH pedindo os de todo mundo (Painel) — sem filtro de pessoa
            pass
        else:
            # padrão: os próprios pontos (tela "Bater ponto")
            qs = qs.filter(funcionario=user)

        data_inicio = self.request.query_params.get("data_inicio")
        data_fim = self.request.query_params.get("data_fim")
        if data_inicio:
            qs = qs.filter(registrado_em__date__gte=data_inicio)
        if data_fim:
            qs = qs.filter(registrado_em__date__lte=data_fim)
        return qs

    def perform_create(self, serializer):
        validar_sequencia_ponto(
            self.request.user,
            serializer.validated_data["tipo"],
            serializer.validated_data["registrado_em"],
        )
        serializer.save(funcionario=self.request.user)

    def _funcionario_e_periodo(self, request):
        user = request.user
        funcionario_id = request.query_params.get("funcionario")
        if user.papel == user.Papel.TECNICO or not funcionario_id:
            funcionario_id = user.id

        hoje = timezone.localdate()
        data_inicio = request.query_params.get("data_inicio") or hoje.replace(day=1).isoformat()
        data_fim = request.query_params.get("data_fim") or hoje.isoformat()
        funcionario = Usuario.objects.get(id=funcionario_id)
        return funcionario, data_inicio, data_fim

    @action(detail=False, methods=["get"])
    def espelho(self, request):
        """Cartão/espelho de ponto: um registro por dia do período, com saldo
        (extra/faltante) em relação à carga horária esperada."""
        funcionario, data_inicio, data_fim = self._funcionario_e_periodo(request)
        dias = _calcular_dias(funcionario, data_inicio, data_fim, request)

        total_minutos = sum(d["total_minutos"] for d in dias)
        for d in dias:
            d["data"] = d["data"].isoformat()

        return Response(
            {
                "funcionario": funcionario.id,
                "periodo": {"inicio": data_inicio, "fim": data_fim},
                "dias": dias,
                "total_minutos": total_minutos,
            }
        )

    @action(detail=False, methods=["get"])
    def indicadores(self, request):
        """Horas extras e horas faltantes agrupadas por dia, semana ou mês."""
        funcionario, data_inicio, data_fim = self._funcionario_e_periodo(request)
        agrupar_por = request.query_params.get("agrupar_por", "semana")
        dias = _calcular_dias(funcionario, data_inicio, data_fim, request)

        grupos = {}
        ordem = []
        for d in dias:
            dia = d["data"]
            if agrupar_por == "dia":
                chave = dia.isoformat()
                rotulo = dia.strftime("%d/%m")
            elif agrupar_por == "mes":
                chave = dia.strftime("%Y-%m")
                rotulo = dia.strftime("%m/%Y")
            else:
                ano_iso, semana_iso, _ = dia.isocalendar()
                chave = f"{ano_iso}-W{semana_iso:02d}"
                rotulo = f"Sem{semana_iso}"

            if chave not in grupos:
                grupos[chave] = {"chave": chave, "rotulo": rotulo, "horas_extras_minutos": 0, "horas_faltantes_minutos": 0}
                ordem.append(chave)

            if d["saldo_minutos"] > 0:
                grupos[chave]["horas_extras_minutos"] += d["saldo_minutos"]
            elif d["saldo_minutos"] < 0:
                grupos[chave]["horas_faltantes_minutos"] += -d["saldo_minutos"]

        grupos_ordenados = [grupos[chave] for chave in ordem]

        return Response(
            {
                "funcionario": funcionario.id,
                "periodo": {"inicio": data_inicio, "fim": data_fim},
                "agrupar_por": agrupar_por,
                "grupos": grupos_ordenados,
                "total_horas_extras_minutos": sum(g["horas_extras_minutos"] for g in grupos_ordenados),
                "total_horas_faltantes_minutos": sum(g["horas_faltantes_minutos"] for g in grupos_ordenados),
            }
        )


class SolicitacaoPontoViewSet(viewsets.ModelViewSet):
    """
    Ajuste de ponto / justificativa de ausência. O funcionário cria a
    solicitação; só entra em vigor (cria um RegistroPonto, no caso de
    ajuste) depois que um gestor/RH aprova.
    """

    serializer_class = SolicitacaoPontoSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = SolicitacaoPonto.objects.select_related("funcionario", "analisado_por")
        user = self.request.user
        if user.papel == user.Papel.TECNICO:
            qs = qs.filter(funcionario=user)
        else:
            funcionario_id = self.request.query_params.get("funcionario")
            if funcionario_id:
                qs = qs.filter(funcionario_id=funcionario_id)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param.upper())
        return qs

    def perform_create(self, serializer):
        extra = {}
        if serializer.validated_data.get("tipo") == SolicitacaoPonto.Tipo.AJUSTE_DIA:
            dia = serializer.validated_data["data_referencia"]
            atuais = RegistroPonto.objects.filter(
                funcionario=self.request.user, registrado_em__date=dia
            ).order_by("registrado_em")
            extra["pontos_anteriores"] = [
                {"tipo": r.tipo, "horario": timezone.localtime(r.registrado_em).strftime("%H:%M")}
                for r in atuais
            ]
        solicitacao = serializer.save(funcionario=self.request.user, **extra)
        # avisa quem vai analisar (qualquer gestor/RH/admin)
        for aprovador in Usuario.objects.filter(
            papel__in=[Usuario.Papel.GESTOR, Usuario.Papel.RH, Usuario.Papel.ADMIN], is_active=True
        ):
            notificar(
                aprovador,
                Notificacao.Tipo.NOVA_SOLICITACAO,
                f"{solicitacao.funcionario.get_full_name() or solicitacao.funcionario.username} enviou uma solicitação de ponto.",
                link="/gestor/solicitacoes",
            )

    def _checar_permissao_analise(self, request):
        if request.user.papel == request.user.Papel.TECNICO:
            return Response(
                {"detail": "Apenas gestor/RH podem analisar solicitações."},
                status=http_status.HTTP_403_FORBIDDEN,
            )
        return None

    @action(detail=True, methods=["post"])
    def aprovar(self, request, pk=None):
        erro = self._checar_permissao_analise(request)
        if erro:
            return erro
        solicitacao = self.get_object()

        if solicitacao.tipo == SolicitacaoPonto.Tipo.AJUSTE and solicitacao.tipo_ponto_solicitado and solicitacao.horario_solicitado:
            momento = timezone.make_aware(
                datetime.combine(solicitacao.data_referencia, solicitacao.horario_solicitado)
            )
            RegistroPonto.objects.create(
                funcionario=solicitacao.funcionario,
                tipo=solicitacao.tipo_ponto_solicitado,
                registrado_em=momento,
                justificativa=f"Ajuste aprovado: {solicitacao.descricao}",
            )

        if solicitacao.tipo == SolicitacaoPonto.Tipo.AJUSTE_DIA:
            dia = solicitacao.data_referencia
            RegistroPonto.objects.filter(
                funcionario=solicitacao.funcionario, registrado_em__date=dia
            ).delete()
            for p in solicitacao.pontos_propostos:
                try:
                    h, m = str(p["horario"]).split(":")[:2]
                    momento = timezone.make_aware(datetime.combine(dia, _time(int(h), int(m))))
                except (KeyError, ValueError):
                    continue
                RegistroPonto.objects.create(
                    funcionario=solicitacao.funcionario,
                    tipo=p["tipo"],
                    registrado_em=momento,
                    justificativa=f"Ajuste de dia aprovado (solic. #{solicitacao.id}): {solicitacao.descricao}",
                )

        solicitacao.status = SolicitacaoPonto.Status.APROVADA
        solicitacao.analisado_por = request.user
        solicitacao.analisado_em = timezone.now()
        solicitacao.resposta_gestor = request.data.get("resposta", "")
        solicitacao.save()

        notificar(
            solicitacao.funcionario,
            Notificacao.Tipo.SOLICITACAO_APROVADA,
            "Sua solicitação de ponto foi aprovada.",
            link="/ponto/solicitacoes",
        )
        return Response(self.get_serializer(solicitacao).data)

    @action(detail=True, methods=["post"])
    def rejeitar(self, request, pk=None):
        erro = self._checar_permissao_analise(request)
        if erro:
            return erro
        solicitacao = self.get_object()
        solicitacao.status = SolicitacaoPonto.Status.REJEITADA
        solicitacao.analisado_por = request.user
        solicitacao.analisado_em = timezone.now()
        solicitacao.resposta_gestor = request.data.get("resposta", "")
        solicitacao.save()

        notificar(
            solicitacao.funcionario,
            Notificacao.Tipo.SOLICITACAO_REJEITADA,
            "Sua solicitação de ponto foi rejeitada.",
            link="/ponto/solicitacoes",
        )
        return Response(self.get_serializer(solicitacao).data)
