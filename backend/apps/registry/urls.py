"""Dynamic URL routing for registered content models."""

import logging

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .registry import content_registry
from .viewsets import RegistryViewSet, get_viewset_for_config

logger = logging.getLogger(__name__)


def create_dynamic_router():
    """Create a dynamic router with routes for all registered content models.

    Returns:
        DefaultRouter with all registered content model routes
    """

    router = DefaultRouter()

    # Add registry management endpoints

    router.register(r"registry/content", RegistryViewSet, basename="content-registry")

    # Add routes for each registered content model

    for config in content_registry.get_all_configs():

        try:

            viewset_class = get_viewset_for_config(config)

            # Create route pattern based on model label

            route_pattern = f"content/{config.model_label}"

            basename = f"content-{config.model_label}"

            router.register(route_pattern, viewset_class, basename=basename)

        except Exception as e:

            # Log error but don't fail the entire routing

            logger.error(
                "Failed to register routes for %s: %s", config.model_label, str(e)
            )

    return router


# Create the dynamic router

dynamic_router = create_dynamic_router()


urlpatterns = [
    path("api/", include(dynamic_router.urls)),
]
