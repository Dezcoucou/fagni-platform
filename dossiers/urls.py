from rest_framework.routers import DefaultRouter
from .views import DossierViewSet

router = DefaultRouter()
router.register(r"dossiers", DossierViewSet, basename="dossier")

urlpatterns = router.urls
