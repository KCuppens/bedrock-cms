import logging

from django.apps import AppConfig
from django.core.exceptions import ValidationError

from .registry import content_registry, register_core_models

logger = logging.getLogger(__name__)


def _initialize_registry():
    """Initialize the content registry."""
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


class RegistryConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "apps.registry"

    verbose_name = "Content Registry"

    def ready(self):
        """Initialize the content registry when the app is ready."""
        # Defer database-dependent initialization to avoid database access during app startup
        from django.db.utils import OperationalError, ProgrammingError

        # Initialize registry without database checks to avoid warnings during app startup
        # The register_core_models() function already handles missing models gracefully
        try:
            _initialize_registry()
        except (OperationalError, ProgrammingError):
            # Database not ready yet, skip initialization
            logger.info("Database not ready, skipping registry initialization")
        except Exception as e:
            logger.warning("Registry initialization failed: %s", e)
