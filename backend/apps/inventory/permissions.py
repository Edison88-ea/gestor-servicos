from rest_framework import permissions


class PodeGerenciarEstoque(permissions.BasePermission):
    """Leitura para qualquer usuário autenticado; escrita (cadastrar material,
    registrar entrada, ajuste de inventário) para GESTOR e ADMIN."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        Papel = request.user.Papel
        return request.user.papel in (Papel.GESTOR, Papel.ADMIN)
