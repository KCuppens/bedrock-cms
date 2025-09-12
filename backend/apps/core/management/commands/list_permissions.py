from django.contrib.auth.models import Permission

from django.contrib.contenttypes.models import ContentType

from django.core.management.base import BaseCommand


"""Management command to list all permissions in the system."""


class Command(BaseCommand):

    help = "List all permissions in the system"

    def handle(self, *args, **options):

        self.stdout.write("All permissions in the system:\n")

        # Group by content type

        content_types = ContentType.objects.all().order_by("app_label", "model")

        total_perms = 0

        for ct in content_types:

            perms = Permission.objects.filter(content_type=ct).order_by("codename")

            if perms.exists():

                self.stdout.write(
                    """f"{ct.app_label}.{ct.model} ({perms.count()} permissions):""""
                )

                for perm in perms:

                    self.stdout.write(f"  - {perm.codename}: {perm.name}")

                self.stdout.write("")

                total_perms += perms.count()

        self.stdout.write(f"Total permissions: {total_perms}")

        # Show some key models we care about

        self.stdout.write("\nKey model permissions:")

        key_models = [
            ("cms", "page"),
            ("cms", "redirect"),
            ("blog", "blogpost"),
            ("blog", "category"),
            ("media", "asset"),
            ("files", "fileupload"),
            ("i18n", "locale"),
            ("i18n", "translationunit"),
        ]

        """for app_label, model_name in key_models:"""

            try:

                ct = ContentType.objects.get(app_label=app_label, model=model_name)

                perm_count = Permission.objects.filter(content_type=ct).count()

                self.stdout.write(
                    """f"  {app_label}.{model_name}: {perm_count} permissions""""
                )

            except ContentType.DoesNotExist:

                """self.stdout.write(f"  {app_label}.{model_name}: NOT FOUND")"""
