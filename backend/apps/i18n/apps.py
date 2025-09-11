from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class I18nConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.i18n'
    verbose_name = 'Internationalization'
    
    def ready(self):
        """Import signal handlers and initialize dynamic language settings when the app is ready."""
        # from . import signals  # Commented out - Page model not available
        
        # Initialize dynamic language settings after Django is ready
        self._initialize_dynamic_languages()
    
    def _initialize_dynamic_languages(self):
        """Load languages from database and update Django settings."""
        try:
            from django.conf import settings
            from django.db import connection
            from .settings_sync import DjangoSettingsSync
            
            # Check if we're in a migration or other special context
            if connection.introspection.table_names() and 'i18n_locale' in connection.introspection.table_names():
                # Get dynamic settings from database
                locale_settings = DjangoSettingsSync.get_locale_settings()
                
                # Update Django settings at runtime
                if locale_settings:
                    # Update LANGUAGE_CODE
                    if 'LANGUAGE_CODE' in locale_settings:
                        settings.LANGUAGE_CODE = locale_settings['LANGUAGE_CODE']
                    
                    # Update LANGUAGES
                    if 'LANGUAGES' in locale_settings and locale_settings['LANGUAGES']:
                        settings.LANGUAGES = locale_settings['LANGUAGES']
                    
                    # Update RTL_LANGUAGES
                    if 'RTL_LANGUAGES' in locale_settings:
                        if not hasattr(settings, 'RTL_LANGUAGES'):
                            settings.RTL_LANGUAGES = []
                        settings.RTL_LANGUAGES = locale_settings['RTL_LANGUAGES']
                    
                    logger.info(f"Dynamic language settings loaded: LANGUAGE_CODE={settings.LANGUAGE_CODE}, "
                              f"LANGUAGES={len(settings.LANGUAGES)} languages")
            else:
                logger.debug("Database tables not ready, using default language settings")
                
        except Exception as e:
            # Don't fail the app initialization if language loading fails
            logger.debug(f"Could not load dynamic language settings: {e}")
            # Settings will fall back to the static defaults in base.py