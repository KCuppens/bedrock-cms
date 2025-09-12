from rest_framework.routers import DefaultRouter

from .views.redirect import RedirectViewSet

Direct URL configuration for redirects endpoint.
This provides a simpler URL path for redirect management.

router = DefaultRouter()
router.register(r"", RedirectViewSet, basename="redirect")

urlpatterns = router.urls
