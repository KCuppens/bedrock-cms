from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core"

    def ready(self):
        """Initialize core functionality when the app is ready."""
        # Import signals to ensure they're connected
        try:
            from . import signals  # noqa
        except ImportError:
