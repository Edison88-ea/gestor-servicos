from rest_framework import filters, viewsets

from .models import Cliente
from .permissions import LerCriarTodos_EditarExcluirGestao
from .serializers import ClienteSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.filter(ativo=True)
    serializer_class = ClienteSerializer
    permission_classes = [LerCriarTodos_EditarExcluirGestao]
    filter_backends = [filters.SearchFilter]
    search_fields = ["nome", "documento", "cidade"]
