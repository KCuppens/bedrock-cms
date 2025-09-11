from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.blog"
    verbose_name = "Blog"

    def ready(self):
        """Initialize the blog app when ready."""
        # Import signals to register them
        from . import models  # This will register the signals
