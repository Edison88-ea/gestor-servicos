from django.utils import timezone
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Usuario
from .permissions import EhGestao
from .serializers import FuncionarioSerializer, UsuarioSerializer


class UsuarioViewSet(viewsets.ReadOnlyModelViewSet):
    """Lista funcionários. Usado, por exemplo, para escolher o técnico ao criar uma OS."""

    queryset = Usuario.objects.filter(is_active=True).order_by("first_name", "last_name", "id")
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        papel = self.request.query_params.get("papel")
        if papel:
            # aceita lista separada por vírgula (ex.: "TECNICO,ENCARREGADO")
            papeis = [p.strip().upper() for p in papel.split(",") if p.strip()]
            qs = qs.filter(papel__in=papeis)
        registra_ponto = self.request.query_params.get("registra_ponto")
        if registra_ponto is not None:
            qs = qs.filter(registra_ponto=registra_ponto in ("1", "true", "True"))
        return qs

    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class FuncionarioViewSet(viewsets.ModelViewSet):
    """Cadastro de funcionários (RH). Criar, editar e desligar.

    Desligar = inativar (is_active=False); o histórico de ponto/OS é preservado.
    O próprio funcionário consulta seus dados por /funcionarios/meu/ (leitura)."""

    serializer_class = FuncionarioSerializer
    permission_classes = [EhGestao]
    filter_backends = [filters.SearchFilter]
    search_fields = ["first_name", "last_name", "username", "cpf", "cargo"]

    def get_queryset(self):
        qs = Usuario.objects.order_by("first_name", "last_name", "id")
        incluir_inativos = self.request.query_params.get("incluir_inativos") in ("1", "true", "True")
        if not incluir_inativos:
            qs = qs.filter(is_active=True)
        return qs

    def perform_destroy(self, instance):
        instance.is_active = False
        if not instance.data_desligamento:
            instance.data_desligamento = timezone.localdate()
        instance.save(update_fields=["is_active", "data_desligamento"])

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def meu(self, request):
        """Os próprios dados cadastrais, em leitura, para qualquer funcionário."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
