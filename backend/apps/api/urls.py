from django.urls import include, path


from rest_framework.routers import DefaultRouter


from apps.cms.views.redirect import RedirectViewSet


from .blocks import BlockSchemaAPIView, BlockTypesAPIView

from .views import HealthCheckViewSet, NoteViewSet


# Create router and register viewsets

router = DefaultRouter()

router.register(r"notes", NoteViewSet, basename="note")

router.register(r"health", HealthCheckViewSet, basename="health")

router.register(r"redirects", RedirectViewSet, basename="redirects")


urlpatterns = [
    # API v1 endpoints
    path("", include(router.urls)),
    # Blocks API - standalone endpoints
    path("blocks/", BlockTypesAPIView.as_view(), name="api-block-types"),
    path(
        "blocks/<str:block_type>/schema/",
        BlockSchemaAPIView.as_view(),
        name="api-block-schema",
    ),
    # Include other app APIs
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.files.urls")),  # Files API
    # path("cms/", include("apps.cms.urls")),  # CMS API - temporarily disabled due to import issues
    path("search/", include("apps.search.urls")),  # Search API
    path("system/", include("apps.core.urls")),  # System/Core API
]
