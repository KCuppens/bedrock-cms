import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError

from .models import Locale

"""Django settings synchronization utilities for i18n locales.

This module provides utilities to keep Django's LANGUAGE_CODE and LANGUAGES
settings in sync with the database Locale model.
"""


logger = logging.getLogger(__name__)


class DjangoSettingsSync:
    """Utility class for synchronizing database locales with Django settings."""

    CACHE_KEY = "i18n_settings_cache"

    CACHE_TIMEOUT = 300  # 5 minutes

    @classmethod
    def get_active_languages(cls) -> list[tuple[str, str]]:
        """Generate LANGUAGES tuple from active database locales.

        Returns:
            List of tuples (code, name) for active locales, ordered by sort_order.
        """

        try:

            # Check cache first

            cached_languages = cache.get(f"{cls.CACHE_KEY}_languages")

            if cached_languages:

                return cached_languages

            # Check if database is available and tables exist

            if not cls._database_ready():

                return [("en", "English")]

            languages = [
                (locale.code, locale.name)
                for locale in Locale.objects.filter(is_active=True).order_by(
                    "sort_order"
                )
            ]

            # Fallback if no active locales

            if not languages:

                languages = [("en", "English")]

            # Cache the result

            cache.set(f"{cls.CACHE_KEY}_languages", languages, cls.CACHE_TIMEOUT)

            return languages

        except Exception as e:

            logger.warning(f"Failed to get active languages from database: {e}")

            return [("en", "English")]

    @classmethod
    def get_default_language(cls) -> str:
        """Get LANGUAGE_CODE from default database locale.

        Returns:
            Language code of the default locale, or 'en' as fallback.
        """

        try:

            # Check cache first

            cached_default = cache.get(f"{cls.CACHE_KEY}_default")

            if cached_default:

                return cached_default

            # Check if database is available and tables exist

            if not cls._database_ready():

                return "en"

            default_locale = Locale.objects.filter(
                is_default=True, is_active=True
            ).first()

            language_code = default_locale.code if default_locale else "en"

            # Cache the result

            cache.set(f"{cls.CACHE_KEY}_default", language_code, cls.CACHE_TIMEOUT)

            return language_code

        except Exception as e:

            logger.warning(f"Failed to get default language from database: {e}")

            return "en"

    @classmethod
    def get_locale_settings(cls) -> dict[str, Any]:
        """Get all locale-related settings from database.

        Returns:
            Dictionary with LANGUAGE_CODE, LANGUAGES, and additional locale info.
        """

        try:

            # Check cache first

            cached_settings = cache.get(f"{cls.CACHE_KEY}_all")

            if cached_settings:

                return cached_settings

            if not cls._database_ready():

                return {
                    "LANGUAGE_CODE": "en",
                    "LANGUAGES": [("en", "English")],
                    "RTL_LANGUAGES": [],
                    "LOCALE_CODES": ["en"],
                }

            active_locales = Locale.objects.filter(is_active=True).order_by(
                "sort_order"
            )

            default_locale = active_locales.filter(is_default=True).first()

            settings_dict = {
                "LANGUAGE_CODE": default_locale.code if default_locale else "en",
                "LANGUAGES": [(locale.code, locale.name) for locale in active_locales],
                "RTL_LANGUAGES": [
                    locale.code for locale in active_locales if locale.rtl
                ],
                "LOCALE_CODES": [locale.code for locale in active_locales],
            }

            # Fallback if no active locales

            if not settings_dict["LANGUAGES"]:

                settings_dict["LANGUAGES"] = [("en", "English")]

                settings_dict["LOCALE_CODES"] = ["en"]

            # Cache the result

            cache.set(f"{cls.CACHE_KEY}_all", settings_dict, cls.CACHE_TIMEOUT)

            return settings_dict

        except Exception as e:

            logger.warning(f"Failed to get locale settings from database: {e}")

            return {
                "LANGUAGE_CODE": "en",
                "LANGUAGES": [("en", "English")],
                "RTL_LANGUAGES": [],
                "LOCALE_CODES": ["en"],
            }

    @classmethod
    def clear_cache(cls):
        """Clear the locale settings cache."""

        try:

            cache.delete_many(
                [
                    f"{cls.CACHE_KEY}_languages",
                    f"{cls.CACHE_KEY}_default",
                    f"{cls.CACHE_KEY}_all",
                ]
            )

            logger.info("Cleared locale settings cache")

        except Exception as e:

            logger.warning(
                f"Failed to clear cache (cache backend may not be available): {e}"
            )

            # This is not a critical failure - the system will work without cache

    @classmethod
    def update_settings_file(cls, settings_path: Optional[str] = None) -> bool:
        """Update the Django settings file with current database locale settings.

        This is an advanced feature that dynamically writes to the settings file.
        Use with caution in production.

        Args:
            settings_path: Path to settings file. If None, attempts to detect current settings.

        Returns:
            True if successful, False otherwise.
        """

        try:

            if not settings_path:

                # Try to determine the settings file path

                settings_module = getattr(settings, "SETTINGS_MODULE", "")

                if not settings_module:

                    logger.error("Could not determine settings module")

                    return False

                # Convert module path to file path

                module_parts = settings_module.split(".")

                settings_file = module_parts[-1] + ".py"

                # Look for the settings file in common locations

                possible_paths = [
                    Path(settings.BASE_DIR) / "config" / "settings" / settings_file,
                    Path(settings.BASE_DIR) / "config" / "settings" / settings_file,
                    Path(settings.BASE_DIR) / settings_file,
                ]

                for path in possible_paths:

                    if path.exists():

                        settings_path = str(path)

                if not settings_path:

                    logger.error(f"Could not find settings file: {settings_file}")

                    return False

            # Get current locale settings

            locale_settings = cls.get_locale_settings()

            # Read current settings file

            with open(settings_path, encoding="utf-8") as f:

                content = f.read()

            # Update LANGUAGE_CODE

            language_code = locale_settings["LANGUAGE_CODE"]

            if "LANGUAGE_CODE" in content:

                content = re.sub(
                    r'LANGUAGE_CODE\s*=\s*["\'].*?["\']',
                    f'LANGUAGE_CODE = "{language_code}"',
                    content,
                )

            else:

                # Add LANGUAGE_CODE if not present

                content += f'\nLANGUAGE_CODE = "{language_code}"\n'

            # Update or add LANGUAGES

            languages_str = str(locale_settings["LANGUAGES"])

            if (
                "LANGUAGES" in content
                and "LANGUAGE_CODE" not in content.split("LANGUAGES")[0].split("\n")[-1]
            ):

                content = re.sub(
                    r"LANGUAGES\s*=\s*\[.*?\]",
                    f"LANGUAGES = {languages_str}",
                    content,
                    flags=re.DOTALL,
                )

            else:

                # Add LANGUAGES if not present

                content += f"\nLANGUAGES = {languages_str}\n"

            # Write back to file

            with open(settings_path, "w", encoding="utf-8") as f:

                f.write(content)

            logger.info(f"Updated settings file: {settings_path}")

            return True

        except Exception as e:

            logger.error(f"Failed to update settings file: {e}")

            return False

    @classmethod
    def validate_consistency(cls) -> dict[str, Any]:
        """Validate consistency between database locales and Django settings.

        Returns:
            Dictionary with validation results and recommendations.
        """

        validation_result: Dict[str, Any] = {
            "is_consistent": True,
            "issues": [],
            "recommendations": [],
            "database_locales": {},
            "django_settings": {},
        }

        try:

            # Get database locale settings

            db_settings = cls.get_locale_settings()

            validation_result["database_locales"] = db_settings

            # Get current Django settings

            django_settings = {
                "LANGUAGE_CODE": getattr(settings, "LANGUAGE_CODE", None),
                "LANGUAGES": getattr(settings, "LANGUAGES", None),
            }

            validation_result["django_settings"] = django_settings

            # Check LANGUAGE_CODE consistency

            if django_settings["LANGUAGE_CODE"] != db_settings["LANGUAGE_CODE"]:

                validation_result["is_consistent"] = False

                validation_result["issues"].append(
                    f"LANGUAGE_CODE mismatch: Django='{django_settings['LANGUAGE_CODE']}', "
                    f"Database='{db_settings['LANGUAGE_CODE']}'"
                )

                validation_result["recommendations"].append(
                    "Run 'python manage.py sync_locales' to synchronize settings"
                )

            # Check LANGUAGES consistency

            if django_settings["LANGUAGES"]:

                django_codes = {code for code, name in django_settings["LANGUAGES"]}

                db_codes = {code for code, name in db_settings["LANGUAGES"]}

                if django_codes != db_codes:

                    validation_result["is_consistent"] = False

                    missing_in_django = db_codes - django_codes

                    missing_in_db = django_codes - db_codes

                    if missing_in_django:

                        validation_result["issues"].append(
                            f"Languages in database but not in Django settings: {missing_in_django}"
                        )

                    if missing_in_db:

                        validation_result["issues"].append(
                            f"Languages in Django settings but not in database: {missing_in_db}"
                        )

                    validation_result["recommendations"].append(
                        "Run 'python manage.py sync_locales' to synchronize settings"
                    )

            return validation_result

        except Exception as e:

            validation_result["is_consistent"] = False

            validation_result["issues"].append(f"Validation failed: {e}")

            return validation_result

    @classmethod
    def _database_ready(cls) -> bool:
        """Check if database is available and i18n tables exist.

        Returns:
            True if database and tables are ready, False otherwise.
        """

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='i18n_locale'"
                    if connection.vendor == "sqlite"
                    else (
                        "SELECT 1 FROM information_schema.tables WHERE table_name='i18n_locale'"
                        if connection.vendor in ["postgresql", "mysql"]
                        else "SELECT 1 FROM i18n_locale LIMIT 1"
                    )
                )

                return cursor.fetchone() is not None

        except (OperationalError, ProgrammingError):

            return False

        except Exception:

            return False


# Convenience functions for use in settings files


def get_dynamic_language_code() -> str:
    """Get dynamic LANGUAGE_CODE from database."""

    return DjangoSettingsSync.get_default_language()


def get_dynamic_languages() -> list[tuple[str, str]]:
    """Get dynamic LANGUAGES from database."""

    return DjangoSettingsSync.get_active_languages()


def get_rtl_languages() -> list[str]:
    """Get list of RTL language codes from database."""

    locale_settings = DjangoSettingsSync.get_locale_settings()

    return locale_settings.get("RTL_LANGUAGES", [])
