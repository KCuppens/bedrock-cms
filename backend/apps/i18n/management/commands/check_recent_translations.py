"""
Check recently created translations.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.i18n.models import Locale, UiMessageTranslation


class Command(BaseCommand):
    help = "Check recently created translations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--locale",
            type=str,
            default="fr",
            help="Locale code to check (default: fr)",
        )
        parser.add_argument(
            "--hours",
            type=int,
            default=1,
            help="Check translations from last N hours (default: 1)",
        )

    def handle(self, *args, **options):
        locale_code = options["locale"]
        hours = options["hours"]

        try:
            locale = Locale.objects.get(code=locale_code)
        except Locale.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Locale {locale_code} not found"))
            return

        # Get translations created recently
        recent_time = timezone.now() - timedelta(hours=hours)
        recent_translations = (
            UiMessageTranslation.objects.filter(
                locale=locale, created_at__gte=recent_time
            )
            .select_related("message")
            .order_by("-created_at")
        )

        total_count = recent_translations.count()

        self.stdout.write(
            f"Translations for {locale.name} ({locale.code}) created in the last {hours} hour(s):"
        )
        self.stdout.write(f"Total found: {total_count}")
        self.stdout.write("-" * 50)

        if total_count == 0:
            self.stdout.write("No recent translations found.")

            # Check if there are ANY translations for this locale
            total_translations = UiMessageTranslation.objects.filter(
                locale=locale
            ).count()
            self.stdout.write(
                f"\nTotal translations for {locale.code}: {total_translations}"
            )

            # Show the most recent translation
            latest = (
                UiMessageTranslation.objects.filter(locale=locale)
                .order_by("-created_at")
                .first()
            )
            if latest:
                self.stdout.write(
                    f"Most recent translation was created at: {latest.created_at}"
                )
                self.stdout.write(f"Key: {latest.message.key}")
                self.stdout.write(f'Value: "{latest.value}"')
        else:
            # Show first 10 recent translations
            for i, trans in enumerate(recent_translations[:10], 1):
                self.stdout.write(f"{i}. {trans.message.key}:")
                self.stdout.write(f'   Original: "{trans.message.default_value}"')
                self.stdout.write(f'   Translation: "{trans.value}"')
                self.stdout.write(f"   Status: {trans.status}")
                self.stdout.write(f"   Created: {trans.created_at}")
                self.stdout.write("")
