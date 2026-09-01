import csv
import json

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.models import Usuario
from apps.notifications.models import Notificacao
from apps.notifications.utils import notificar

from .catalogo import alimentar_catalogo
from .models import (
    FotoOrdemServico,
    MaterialCatalogo,
    OrdemServico,
    PausaOrdemServico,
    ServicoCatalogo,
)
from .relato_ia import RelatoIAIndisponivel, padronizar_relato
from .relato_texto import montar_relato_texto
from .serializers import (
    FotoOrdemServicoSerializer,
    MaterialCatalogoSerializer,
    OrdemServicoSerializer,
    ServicoCatalogoSerializer,
)


class OrdemServicoViewSet(viewsets.ModelViewSet):
    serializer_class = OrdemServicoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = OrdemServico.objects.select_related("cliente", "tecnico").prefetch_related(
            "fotos", "pausas"
        )
        user = self.request.user
        params = self.request.query_params
        if user.papel == user.Papel.TECNICO:
            qs = qs.filter(tecnico=user)
        elif user.papel == user.Papel.ENCARREGADO:
            # O encarregado vê as próprias OS e as dos funcionários que
            # respondem a ele (o campo Usuario.encarregado_responsavel).
            ids_equipe = list(user.equipe.values_list("id", flat=True))
            qs = qs.filter(tecnico_id__in=[user.id, *ids_equipe])

        status_param = params.get("status")
        if status_param:
            qs = qs.filter(status=status_param.upper())

        # Filtros usados pela exportação de comprovantes no Painel do Gestor.
        if params.get("tecnico"):
            qs = qs.filter(tecnico_id=params["tecnico"])
        mes = params.get("concluida_mes")  # 'AAAA-MM'
        if mes and "-" in mes:
            ano, num = mes.split("-")[:2]
            if ano.isdigit() and num.isdigit():
                qs = qs.filter(data_conclusao__year=int(ano), data_conclusao__month=int(num))
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        # Um funcionário de campo (técnico/encarregado) abrindo sua própria OS
        # já entra atribuída a ele; gestor/RH podem informar o técnico ao criar.
        tecnico = serializer.validated_data.get("tecnico")
        if not tecnico and not user.e_gestao:
            tecnico = user
        os_criada = serializer.save(criado_por=user, tecnico=tecnico)
        if os_criada.tecnico_id:
            os_criada.status = OrdemServico.Status.ATRIBUIDA
            os_criada.save(update_fields=["status"])
            if os_criada.tecnico_id != user.id:
                notificar(
                    os_criada.tecnico,
                    Notificacao.Tipo.OS_ATRIBUIDA,
                    f"Nova OS {os_criada.numero} atribuída a você: {os_criada.tipo_servico}.",
                    link=f"/ordens-servico/{os_criada.id}",
                )

    @action(detail=True, methods=["post"])
    def iniciar(self, request, pk=None):
        ordem = self.get_object()
        ordem.status = OrdemServico.Status.EM_ANDAMENTO
        ordem.data_inicio = timezone.now()
        ordem.save(update_fields=["status", "data_inicio"])
        return Response(self.get_serializer(ordem).data)

    @action(detail=True, methods=["post"])
    def pausar(self, request, pk=None):
        ordem = self.get_object()
        if ordem.status != OrdemServico.Status.EM_ANDAMENTO:
            raise ValidationError("Só é possível pausar uma OS em andamento.")

        motivo = request.data.get("motivo")
        if motivo not in PausaOrdemServico.Motivo.values:
            raise ValidationError({"motivo": "Motivo inválido."})

        PausaOrdemServico.objects.create(
            ordem_servico=ordem,
            motivo=motivo,
            observacao=request.data.get("observacao", ""),
        )
        ordem.status = OrdemServico.Status.PAUSADA
        ordem.save(update_fields=["status"])
        return Response(self.get_serializer(self._recarregar(ordem)).data)

    @action(detail=True, methods=["post"])
    def retomar(self, request, pk=None):
        ordem = self.get_object()
        if ordem.status != OrdemServico.Status.PAUSADA:
            raise ValidationError("Esta OS não está pausada.")

        pausa_aberta = ordem.pausas.filter(retomada_em__isnull=True).first()
        if pausa_aberta:
            pausa_aberta.retomada_em = timezone.now()
            pausa_aberta.save(update_fields=["retomada_em"])

        ordem.status = OrdemServico.Status.EM_ANDAMENTO
        ordem.save(update_fields=["status"])
        return Response(self.get_serializer(self._recarregar(ordem)).data)

    def _recarregar(self, ordem):
        # Recarrega a OS numa query nova para que os dados aninhados (pausas,
        # fotos) não venham do cache de prefetch feito antes das mudanças.
        return self.get_queryset().get(pk=ordem.pk)

    @action(detail=True, methods=["post"])
    def concluir(self, request, pk=None):
        ordem = self.get_object()
        ordem.status = OrdemServico.Status.CONCLUIDA
        ordem.data_conclusao = timezone.now()

        if "relato" in request.data:
            relato = request.data["relato"]
            if isinstance(relato, str):
                try:
                    relato = json.loads(relato)
                except json.JSONDecodeError:
                    raise ValidationError({"relato": "JSON inválido."})
            if not isinstance(relato, dict):
                raise ValidationError({"relato": "Formato inválido."})
            ordem.relato = relato
            ordem.observacoes_tecnico = montar_relato_texto(relato)
            alimentar_catalogo(relato)
        elif "observacoes_tecnico" in request.data:
            ordem.observacoes_tecnico = request.data["observacoes_tecnico"]

        if "checklist" in request.data:
            ordem.checklist = request.data["checklist"]
        if "assinatura_cliente" in request.FILES:
            ordem.assinatura_cliente = request.FILES["assinatura_cliente"]
        ordem.save()

        self._avisar_conclusao(ordem, request.user)
        return Response(self.get_serializer(ordem).data)

    def _avisar_conclusao(self, ordem, autor):
        """Avisa o encarregado do técnico e a gestão de que a OS foi concluída.
        Não avisa quem fez a conclusão."""
        tecnico = ordem.tecnico
        nome_tecnico = (tecnico.get_full_name() or tecnico.username) if tecnico else "Alguém"
        mensagem = f"{nome_tecnico} concluiu a OS {ordem.numero} — {ordem.cliente.nome}."
        link = f"/ordens-servico/{ordem.id}"

        destinatarios = set(
            Usuario.objects.filter(
                papel__in=[Usuario.Papel.GESTOR, Usuario.Papel.RH, Usuario.Papel.ADMIN],
                is_active=True,
            )
        )
        if tecnico and tecnico.encarregado_responsavel_id:
            destinatarios.add(tecnico.encarregado_responsavel)
        destinatarios.discard(autor)

        for destinatario in destinatarios:
            notificar(destinatario, Notificacao.Tipo.OS_CONCLUIDA, mensagem, link=link)

    @action(detail=False, methods=["get"], url_path="exportar")
    def exportar(self, request):
        """CSV das OS concluídas (respeita o escopo do usuário e o filtro
        ?concluida_mes=AAAA-MM / ?tecnico=)."""
        qs = (
            self.get_queryset()
            .filter(status=OrdemServico.Status.CONCLUIDA)
            .order_by("data_conclusao")
        )
        mes = request.query_params.get("concluida_mes") or "todas"

        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="os-{mes}.csv"'
        resp.write("﻿")  # BOM: Excel abre os acentos certo
        escritor = csv.writer(resp, delimiter=";")
        escritor.writerow(
            ["Número", "Cliente", "Técnico", "Tipo de serviço", "Prioridade",
             "Aberta em", "Início", "Conclusão", "Relato"]
        )

        def dt(valor):
            return timezone.localtime(valor).strftime("%d/%m/%Y %H:%M") if valor else ""

        for o in qs:
            escritor.writerow(
                [
                    o.numero,
                    o.cliente.nome,
                    (o.tecnico.get_full_name() or o.tecnico.username) if o.tecnico else "",
                    o.tipo_servico,
                    o.get_prioridade_display(),
                    dt(o.criado_em),
                    dt(o.data_inicio),
                    dt(o.data_conclusao),
                    (o.observacoes_tecnico or "").replace("\n", " | "),
                ]
            )
        return resp

    @action(detail=False, methods=["get"], url_path="relatos-anteriores")
    def relatos_anteriores(self, request):
        """OS concluídas recentes com relato preenchido, para o técnico copiar
        num novo relato ("é a mesma coisa da semana passada")."""
        qs = (
            self.get_queryset()
            .filter(status=OrdemServico.Status.CONCLUIDA)
            .exclude(relato={})
            .order_by("-data_conclusao")[:20]
        )
        dados = [
            {
                "id": o.id,
                "numero": o.numero,
                "cliente_nome": o.cliente.nome,
                "tipo_servico": o.tipo_servico,
                "data_conclusao": o.data_conclusao,
                "relato": o.relato,
            }
            for o in qs
        ]
        return Response(dados)

    @action(detail=True, methods=["post"], url_path="padronizar-relato")
    def padronizar_relato(self, request, pk=None):
        ordem = self.get_object()
        texto = request.data.get("texto") or ordem.observacoes_tecnico or ""
        try:
            texto_padronizado = padronizar_relato(texto)
        except RelatoIAIndisponivel as exc:
            return Response({"detail": str(exc)}, status=503)
        return Response({"texto_padronizado": texto_padronizado})

    @action(detail=True, methods=["post"], url_path="fotos")
    def adicionar_foto(self, request, pk=None):
        ordem = self.get_object()
        serializer = FotoOrdemServicoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(ordem_servico=ordem)
        return Response(serializer.data, status=201)


class ServicoCatalogoViewSet(viewsets.ReadOnlyModelViewSet):
    """Sugestões de serviço para o formulário de relato (mais usados primeiro)."""

    serializer_class = ServicoCatalogoSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return ServicoCatalogo.objects.all()[:300]


class MaterialCatalogoViewSet(viewsets.ReadOnlyModelViewSet):
    """Sugestões de material (com unidade) para o formulário de relato."""

    serializer_class = MaterialCatalogoSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return MaterialCatalogo.objects.all()[:300]
