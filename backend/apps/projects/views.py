from django.db.models import Prefetch
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .catalogos import AREAS_AFETADAS
from .models import Etapa, HistoricoEtapa, Projeto
from .permissions import GestorOuAdminEscreve
from .serializers import (
    AssinaturaProjetoSerializer,
    EtapaSerializer,
    FotoEtapaSerializer,
    PlantaProjetoSerializer,
    ProjetoResumoSerializer,
    ProjetoSerializer,
)


class ProjetoViewSet(viewsets.ModelViewSet):
    permission_classes = [GestorOuAdminEscreve]
    filter_backends = [filters.SearchFilter]
    search_fields = ["numero", "nome", "responsavel"]

    def get_queryset(self):
        qs = Projeto.objects.select_related("criado_por").prefetch_related(
            Prefetch("etapas", queryset=Etapa.objects.prefetch_related("fotos", "historico")),
            "plantas",
            "assinaturas",
        )
        params = self.request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"].upper())
        if params.get("tipo"):
            qs = qs.filter(tipo=params["tipo"].upper())
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ProjetoResumoSerializer
        return ProjetoSerializer

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def opcoes(self, request):
        """Vocabulário para os selects do formulário de obra."""
        return Response(
            {
                "areas_afetadas": [{"valor": c, "rotulo": r} for c, r in AREAS_AFETADAS],
                "tipos": [{"valor": v, "rotulo": r} for v, r in Projeto.Tipo.choices],
                "status": [{"valor": v, "rotulo": r} for v, r in Projeto.Status.choices],
                "tipos_ponto": [{"valor": v, "rotulo": r} for v, r in Etapa.TipoPonto.choices],
            }
        )

    @action(detail=True, methods=["post"])
    def plantas(self, request, pk=None):
        projeto = self.get_object()
        serializer = PlantaProjetoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(projeto=projeto)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def assinaturas(self, request, pk=None):
        """Assinatura do "ciente da alteração" / "supervisor de processos".
        Liberado a qualquer autenticado — a assinatura é coletada em campo, como
        a assinatura do cliente numa OS."""
        projeto = self.get_object()
        serializer = AssinaturaProjetoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(projeto=projeto)
        return Response(serializer.data, status=201)


class EtapaViewSet(viewsets.ModelViewSet):
    serializer_class = EtapaSerializer

    def get_permissions(self):
        # Técnico pode atualizar progresso e enviar foto; o resto (criar/editar
        # etapa = "definir metas") é só GESTOR/ADMIN.
        if self.action in ("progresso", "fotos"):
            return [permissions.IsAuthenticated()]
        return [GestorOuAdminEscreve()]

    def get_queryset(self):
        qs = Etapa.objects.select_related("projeto").prefetch_related("fotos", "historico")
        projeto_id = self.request.query_params.get("projeto")
        if projeto_id:
            qs = qs.filter(projeto_id=projeto_id)
        return qs

    def _recarregar(self, etapa):
        return self.get_queryset().get(pk=etapa.pk)

    @action(detail=True, methods=["post"])
    def progresso(self, request, pk=None):
        etapa = self.get_object()
        try:
            novo = int(request.data.get("realizado"))
        except (TypeError, ValueError):
            raise ValidationError({"realizado": "Informe a quantidade instalada (número)."})

        novo = max(0, min(novo, etapa.meta))
        anterior = etapa.realizado
        if novo != anterior:
            HistoricoEtapa.objects.create(
                etapa=etapa,
                usuario=request.user,
                quantidade_anterior=anterior,
                quantidade_nova=novo,
                observacao=request.data.get("observacao", ""),
            )
            etapa.realizado = novo
            etapa.save(update_fields=["realizado"])
        return Response(self.get_serializer(self._recarregar(etapa)).data)

    @action(detail=True, methods=["post"])
    def fotos(self, request, pk=None):
        etapa = self.get_object()
        serializer = FotoEtapaSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(etapa=etapa, enviado_por=request.user)
        return Response(serializer.data, status=201)
