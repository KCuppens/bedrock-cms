import logging

from django.apps import AppConfig
from django.core.exceptions import ValidationError

from .registry import content_registry, register_core_models

logger = logging.getLogger(__name__)


class RegistryConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "apps.registry"

    verbose_name = "Content Registry"

    def ready(self):
        """Initialize the content registry when the app is ready."""
        try:
            # Register core models
            register_core_models()
            logger.info("Core models registered successfully")
        except Exception as e:
            logger.warning("Could not register core models: %s", e)

        # Validate all registered content types
        try:
            content_registry.validate_all()
            logger.info(
                "Content registry initialized with %s configurations",
                len(content_registry.get_all_configs()),
            )
        except ValidationError as e:
            logger.error("Content registry validation failed: %s", e)
            # Don't raise in production, just log the error
        except Exception as e:
            logger.error("Unexpected error during registry validation: %s", e)
