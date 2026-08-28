from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notificacao
from .serializers import NotificacaoSerializer


class NotificacaoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificacaoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notificacao.objects.filter(destinatario=self.request.user)

    @action(detail=False, methods=["get"])
    def nao_lidas(self, request):
        return Response({"total": self.get_queryset().filter(lida=False).count()})

    @action(detail=True, methods=["post"], url_path="marcar-lida")
    def marcar_lida(self, request, pk=None):
        notificacao = self.get_object()
        notificacao.lida = True
        notificacao.save(update_fields=["lida"])
        return Response(self.get_serializer(notificacao).data)

    @action(detail=False, methods=["post"], url_path="marcar-todas-lidas")
    def marcar_todas_lidas(self, request):
        self.get_queryset().filter(lida=False).update(lida=True)
        return Response({"ok": True})
