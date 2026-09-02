from rest_framework.routers import DefaultRouter

from .views import FuncionarioViewSet, UsuarioViewSet

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("funcionarios", FuncionarioViewSet, basename="funcionario")

urlpatterns = router.urls
