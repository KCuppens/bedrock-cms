from django.core.management.base import BaseCommand

from apps.i18n.models import Locale

List all available locales.

class Command(BaseCommand):
    help = "List all available locales"

    def handle(self, *args, **options):
        locales = Locale.objects.all()
        self.stdout.write("All locales:")
        for locale in locales:
            status = []
            if locale.is_active:
                status.append("active")
            if locale.is_default:
                status.append("default")
            status_str = f" ({', '.join(status)})" if status else " (inactive)"

            self.stdout.write(f"- {locale.code}: {locale.name}{status_str}")

        active_locales = Locale.objects.filter(is_active=True)
        self.stdout.write(f"\nTotal locales: {locales.count()}")
        self.stdout.write(f"Active locales: {active_locales.count()}")
