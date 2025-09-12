import logging

import time



from django.conf import settings

from django.core.cache import cache

from django.utils import translation

from django.utils.deprecation import MiddlewareMixin



from apps.i18n.settings_sync import DjangoSettingsSync



Dynamic language middleware for i18n.



This middleware ensures that the available languages are always

up-to-date with the database configuration.



logger = logging.getLogger(__name__)



class DynamicLanguageMiddleware(MiddlewareMixin):



    Middleware to ensure Django's language settings are synchronized

    with the database on each request.



    This middleware runs after Django is fully initialized, avoiding

    the circular dependency issue of trying to access the database

    during settings import.



    # Cache key for tracking when we last updated settings

    LAST_UPDATE_KEY = "i18n_settings_last_update"

    UPDATE_INTERVAL = 300  # 5 minutes



    def __init__(self, get_response):

        self.get_response = get_response

        self._languages_loaded = False



    def process_request(self, request):

        """Check and update language settings if needed."""

        # Skip for static files and media

        if request.path.startswith("/static/") or request.path.startswith("/media/"):

            return None



        # Only update periodically to avoid performance impact

        try:



            last_update = cache.get(self.LAST_UPDATE_KEY, 0)

            current_time = time.time()



            if current_time - last_update > self.UPDATE_INTERVAL:

                self._update_language_settings()

                cache.set(self.LAST_UPDATE_KEY, current_time, self.UPDATE_INTERVAL)

        except Exception as e:

            # Don't break the request if language update fails

            logger.debug(f"Could not update language settings: {e}")



        return None



    def _update_language_settings(self):

        """Update Django's language settings from database."""

        try:



            # Get current settings from database

            locale_settings = DjangoSettingsSync.get_locale_settings()



            if locale_settings:

                # Check if settings have changed

                current_languages = getattr(settings, "LANGUAGES", [])

                new_languages = locale_settings.get("LANGUAGES", [])



                if current_languages != new_languages:

                    # Update settings

                    settings.LANGUAGES = new_languages

                    settings.LANGUAGE_CODE = locale_settings.get("LANGUAGE_CODE", "en")



                    if "RTL_LANGUAGES" in locale_settings:

                        settings.RTL_LANGUAGES = locale_settings["RTL_LANGUAGES"]



                    logger.debug(

                        f"Updated language settings: {len(new_languages)} languages available"

                    )



                    # Clear Django's language cache to pick up new languages



                    translation._trans = None



        except Exception as e:

            logger.debug(f"Could not update language settings in middleware: {e}")

