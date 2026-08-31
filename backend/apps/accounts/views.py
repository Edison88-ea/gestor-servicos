from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Usuario
from .serializers import UsuarioSerializer


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
        return qs

    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
