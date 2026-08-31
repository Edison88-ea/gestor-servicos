from rest_framework import permissions


class PodeGerenciarObra(permissions.BasePermission):
    """Leitura para qualquer usuário autenticado; escrita (criar obra, definir
    metas, anexar planta) para ENCARREGADO, GESTOR e ADMIN. O técnico atualiza
    progresso e envia foto por actions próprias, liberadas à parte na view."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        Papel = request.user.Papel
        return request.user.papel in (Papel.ENCARREGADO, Papel.GESTOR, Papel.ADMIN)
