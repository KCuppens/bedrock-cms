"""
Deactivate a locale.
"""

from django.core.management.base import BaseCommand

from apps.i18n.models import Locale


class Command(BaseCommand):
    help = "Deactivate a locale"

    def add_arguments(self, parser):
        parser.add_argument(
            "locale_code", type=str, help="Locale code to deactivate (e.g., es, fr, de)"
        )

    def handle(self, *args, **options):
        locale_code = options["locale_code"]

        try:
            locale = Locale.objects.get(code=locale_code)
            if locale.is_default:
                self.stdout.write(
                    self.style.ERROR(f"Cannot deactivate default locale: {locale_code}")
                )
            elif not locale.is_active:
                self.stdout.write(f"Locale {locale_code} is already inactive")
            else:
                locale.is_active = False
                locale.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully deactivated locale: {locale_code}"
                    )
                )
        except Locale.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Locale {locale_code} does not exist"))
