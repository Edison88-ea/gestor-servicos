from rest_framework import permissions


class EhGestao(permissions.BasePermission):
    """Só GESTOR / RH / ADMIN. Usado no cadastro de funcionários."""

    message = "Apenas RH, gestor ou administrador."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.e_gestao)
