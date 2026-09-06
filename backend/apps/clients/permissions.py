from rest_framework import permissions


class LerCriarTodos_EditarExcluirGestao(permissions.BasePermission):
    """Qualquer funcionário autenticado lê e cadastra cliente (o técnico
    cadastra em campo ao abrir uma OS). Editar e excluir é só da gestão."""

    message = "Editar ou excluir cliente é só da gestão."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS or request.method == "POST":
            return True
        return user.e_gestao
