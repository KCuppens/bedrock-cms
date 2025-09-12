from django.core.management.base import BaseCommand

from apps.i18n.models import Locale

"""Management command to initialize default locales."""


class Command(BaseCommand):

    help = "Initialize default locales for the application"

    def add_arguments(self, parser):

        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing locales before creating new ones",
        )

    def handle(self, *args, **options):
        """Create default locales."""

        # If reset flag is set, delete all existing locales

        if options.get("reset"):

            Locale.objects.all().delete()

            self.stdout.write(self.style.WARNING("Deleted all existing locales"))

        # Define default locales

        default_locales = [
            {
                "code": "en",
                "name": "English",
                "native_name": "English",
                "rtl": False,
                "sort_order": 1,
                "is_active": True,
                "is_default": True,
            },
            {
                "code": "es",
                "name": "Spanish",
                "native_name": "Español",
                "rtl": False,
                "sort_order": 2,
                "is_active": True,
                "is_default": False,
            },
            {
                "code": "fr",
                "name": "French",
                "native_name": "Français",
                "rtl": False,
                "sort_order": 3,
                "is_active": True,
                "is_default": False,
            },
            {
                "code": "de",
                "name": "German",
                "native_name": "Deutsch",
                "rtl": False,
                "sort_order": 4,
                "is_active": True,
                "is_default": False,
            },
            {
                "code": "it",
                "name": "Italian",
                "native_name": "Italiano",
                "rtl": False,
                "sort_order": 5,
                "is_active": True,
                "is_default": False,
            },
            {
                "code": "pt",
                "name": "Portuguese",
                "native_name": "Português",
                "rtl": False,
                "sort_order": 6,
                "is_active": False,
                "is_default": False,
            },
            {
                "code": "zh",
                "name": "Chinese",
                "native_name": "中文",
                "rtl": False,
                "sort_order": 7,
                "is_active": False,
                "is_default": False,
            },
            {
                "code": "ja",
                "name": "Japanese",
                "native_name": "日本語",
                "rtl": False,
                "sort_order": 8,
                "is_active": False,
                "is_default": False,
            },
            {
                "code": "ar",
                "name": "Arabic",
                "native_name": "العربية",
                "rtl": True,
                "sort_order": 9,
                "is_active": False,
                "is_default": False,
            },
            {
                "code": "he",
                "name": "Hebrew",
                "native_name": "עברית",
                "rtl": True,
                "sort_order": 10,
                "is_active": False,
                "is_default": False,
            },
        ]

        created_count = 0

        updated_count = 0

        for locale_data in default_locales:

            locale, created = Locale.objects.update_or_create(
                code=locale_data["code"], defaults=locale_data
            )

            if created:

                created_count += 1

                self.stdout.write(
                    self.style.SUCCESS(f"Created locale: {locale.name} ({locale.code})")
                )

            else:

                updated_count += 1

                self.stdout.write(
                    self.style.WARNING(f"Updated locale: {locale.name} ({locale.code})")
                )

        # Set English as fallback for all other locales

        english = Locale.objects.get(code="en")

        Locale.objects.exclude(code="en").update(fallback=english)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary: Created {created_count} locales, updated {updated_count} locales."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "English set as default locale and fallback for all other locales."
            )
        )
