from django.apps import AppConfig

from . import signals  # noqa

Search app configuration.

class SearchConfig(AppConfig):
    """Configuration for the search app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.search"
    verbose_name = "Search & Filtering"

    def ready(self):
        """Initialize search functionality when the app is ready."""
        # Import signals to ensure they're connected
        try:
        except ImportError:
