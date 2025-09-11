"""
Search app configuration.
"""

from django.apps import AppConfig


class SearchConfig(AppConfig):
    """Configuration for the search app."""
    
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.search"
    verbose_name = "Search & Filtering"
    
    def ready(self):
        """Initialize search functionality when the app is ready."""
        # Import signals to ensure they're connected
        try:
            from . import signals  # noqa
        except ImportError:
            pass
