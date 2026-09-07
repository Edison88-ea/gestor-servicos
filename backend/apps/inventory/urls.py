from rest_framework.routers import DefaultRouter

from .views import MaterialViewSet, MovimentoEstoqueViewSet

router = DefaultRouter()
router.register("materiais-estoque", MaterialViewSet, basename="material-estoque")
router.register(
    "movimentos-estoque", MovimentoEstoqueViewSet, basename="movimento-estoque"
)

urlpatterns = router.urls
