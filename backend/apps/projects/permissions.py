from rest_framework import permissions


class GestorOuAdminEscreve(permissions.BasePermission):
    """Leitura para qualquer usuário autenticado; escrita (criar obra, definir
    metas, anexar planta) só para GESTOR e ADMIN. O técnico atualiza progresso e
    envia foto por actions próprias, liberadas à parte na view."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        papel = getattr(request.user, "papel", None)
        Papel = request.user.Papel
        return papel in (Papel.GESTOR, Papel.ADMIN)
