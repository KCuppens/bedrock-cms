"""
Management command to synchronize database locales with Django settings.

This command provides comprehensive synchronization between the Locale model
and Django's i18n settings (LANGUAGE_CODE and LANGUAGES).
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.cache import cache

from apps.i18n.models import Locale
from apps.i18n.settings_sync import DjangoSettingsSync


class Command(BaseCommand):
    help = "Synchronize database locales with Django i18n settings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--direction",
            type=str,
            choices=["db-to-django", "django-to-db", "validate", "clear-cache"],
            default="validate",
            help="Direction of sync: db-to-django (update Django settings from DB), "
            "django-to-db (update DB from Django settings), "
            "validate (check consistency), clear-cache (clear settings cache)",
        )
        parser.add_argument(
            "--fix-inconsistencies",
            action="store_true",
            help="Automatically fix detected inconsistencies (implies db-to-django direction)",
        )
        parser.add_argument(
            "--update-settings-file",
            action="store_true",
            help="Update the Django settings file with database values (advanced feature)",
        )
        parser.add_argument(
            "--settings-path",
            type=str,
            help="Path to Django settings file to update (if --update-settings-file is used)",
        )
        parser.add_argument(
            "--json", action="store_true", help="Output results in JSON format"
        )
        parser.add_argument(
            "--default-locale",
            type=str,
            help="Set a specific locale as default (locale code)",
        )

    def handle(self, *args, **options):
        """Handle the sync command."""

        direction = options["direction"]
        fix_inconsistencies = options.get("fix_inconsistencies", False)
        update_settings_file = options.get("update_settings_file", False)
        settings_path = options.get("settings_path")
        json_output = options.get("json", False)
        default_locale_code = options.get("default_locale")

        # If fix_inconsistencies is True, force direction to db-to-django
        if fix_inconsistencies:
            direction = "db-to-django"

        try:
            if direction == "clear-cache":
                self.clear_cache(json_output)
            elif direction == "validate":
                self.validate_consistency(json_output, fix_inconsistencies)
            elif direction == "db-to-django":
                self.sync_db_to_django(json_output, update_settings_file, settings_path)
            elif direction == "django-to-db":
                self.sync_django_to_db(json_output, default_locale_code)

        except Exception as e:
            if json_output:
                self.stdout.write(json.dumps({"error": str(e)}, indent=2))
            else:
                raise CommandError(f"Command failed: {e}")

    def clear_cache(self, json_output=False):
        """Clear the locale settings cache."""
        DjangoSettingsSync.clear_cache()

        if json_output:
            result = {
                "action": "clear_cache",
                "success": True,
                "message": "Locale settings cache cleared",
            }
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS("✓ Locale settings cache cleared"))

    def validate_consistency(self, json_output=False, fix_inconsistencies=False):
        """Validate consistency between database and Django settings."""
        validation_result = DjangoSettingsSync.validate_consistency()

        if json_output:
            self.stdout.write(json.dumps(validation_result, indent=2))
        else:
            if validation_result["is_consistent"]:
                self.stdout.write(
                    self.style.SUCCESS(
                        "✓ Database locales and Django settings are consistent"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠ Inconsistencies detected between database and Django settings:"
                    )
                )

                for issue in validation_result["issues"]:
                    self.stdout.write(f"  • {issue}")

                self.stdout.write("\nRecommendations:")
                for rec in validation_result["recommendations"]:
                    self.stdout.write(f"  • {rec}")

                if fix_inconsistencies:
                    self.stdout.write("\n" + "=" * 50)
                    self.stdout.write(
                        "Fixing inconsistencies by syncing database to Django settings..."
                    )
                    self.sync_db_to_django(json_output=False)

        return validation_result

    def sync_db_to_django(
        self, json_output=False, update_settings_file=False, settings_path=None
    ):
        """Sync database locales to Django settings."""

        # Get current database settings
        db_settings = DjangoSettingsSync.get_locale_settings()

        # Clear cache to ensure fresh data
        DjangoSettingsSync.clear_cache()

        result = {
            "action": "db_to_django_sync",
            "database_settings": db_settings,
            "django_settings": {
                "LANGUAGE_CODE": getattr(settings, "LANGUAGE_CODE", None),
                "LANGUAGES": getattr(settings, "LANGUAGES", None),
            },
            "cache_cleared": True,
            "file_updated": False,
        }

        if update_settings_file:
            success = DjangoSettingsSync.update_settings_file(settings_path)
            result["file_updated"] = success

            if success:
                result["message"] = (
                    "Database locales synced to Django settings and settings file updated"
                )
            else:
                result["message"] = (
                    "Database locales synced to Django cache, but settings file update failed"
                )
                result["warning"] = (
                    "Settings file was not updated. Changes are only in cache until server restart."
                )
        else:
            result["message"] = "Database locales synced to Django settings cache"
            result["note"] = (
                "Changes are cached and will persist until server restart. Use --update-settings-file for permanent changes."
            )

        if json_output:
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS("✓ Synced database locales to Django settings")
            )
            self.stdout.write(f'  LANGUAGE_CODE: {db_settings["LANGUAGE_CODE"]}')
            self.stdout.write(f'  LANGUAGES: {db_settings["LANGUAGES"]}')
            self.stdout.write(f'  RTL_LANGUAGES: {db_settings["RTL_LANGUAGES"]}')

            if update_settings_file:
                if result["file_updated"]:
                    self.stdout.write(
                        self.style.SUCCESS("✓ Settings file updated successfully")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "⚠ Settings file update failed - changes are only cached"
                        )
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "ⓘ Changes are cached. Use --update-settings-file for permanent changes."
                    )
                )

    def sync_django_to_db(self, json_output=False, default_locale_code=None):
        """Sync Django settings to database locales."""

        django_language_code = getattr(settings, "LANGUAGE_CODE", None)
        django_languages = getattr(settings, "LANGUAGES", None)

        if not django_language_code:
            raise CommandError("LANGUAGE_CODE not found in Django settings")

        created_count = 0
        updated_count = 0
        made_default = None

        result = {
            "action": "django_to_db_sync",
            "django_settings": {
                "LANGUAGE_CODE": django_language_code,
                "LANGUAGES": django_languages,
            },
            "created_locales": [],
            "updated_locales": [],
            "default_locale": None,
        }

        # Create/update locales from Django LANGUAGES setting
        if django_languages:
            for code, name in django_languages:
                locale, created = Locale.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": name,
                        "native_name": name,  # Could be enhanced with proper native names
                        "is_active": True,
                        "is_default": code == django_language_code,
                    },
                )

                if created:
                    created_count += 1
                    result["created_locales"].append({"code": code, "name": name})
                else:
                    updated_count += 1
                    result["updated_locales"].append({"code": code, "name": name})

                if code == django_language_code:
                    made_default = code
        else:
            # No LANGUAGES setting, just create from LANGUAGE_CODE
            locale, created = Locale.objects.update_or_create(
                code=django_language_code,
                defaults={
                    "name": django_language_code.title(),
                    "native_name": django_language_code.title(),
                    "is_active": True,
                    "is_default": True,
                },
            )

            if created:
                created_count += 1
                result["created_locales"].append(
                    {"code": django_language_code, "name": django_language_code.title()}
                )
            else:
                updated_count += 1
                result["updated_locales"].append(
                    {"code": django_language_code, "name": django_language_code.title()}
                )

            made_default = django_language_code

        # Handle explicit default locale setting
        if default_locale_code:
            try:
                locale = Locale.objects.get(code=default_locale_code)
                Locale.objects.filter(is_default=True).update(is_default=False)
                locale.is_default = True
                locale.save()
                made_default = default_locale_code
                result["explicit_default_set"] = default_locale_code
            except Locale.DoesNotExist:
                raise CommandError(
                    f'Locale with code "{default_locale_code}" not found'
                )

        result["default_locale"] = made_default
        result["summary"] = f"Created {created_count}, updated {updated_count} locales"

        # Clear cache after database changes
        DjangoSettingsSync.clear_cache()
        result["cache_cleared"] = True

        if json_output:
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Synced Django settings to database: {result["summary"]}'
                )
            )

            if result["created_locales"]:
                self.stdout.write("  Created locales:")
                for locale in result["created_locales"]:
                    self.stdout.write(f'    • {locale["name"]} ({locale["code"]})')

            if result["updated_locales"]:
                self.stdout.write("  Updated locales:")
                for locale in result["updated_locales"]:
                    self.stdout.write(f'    • {locale["name"]} ({locale["code"]})')

            if made_default:
                self.stdout.write(f"  Default locale: {made_default}")

            self.stdout.write(
                self.style.SUCCESS("✓ Settings cache cleared - changes are active")
            )
