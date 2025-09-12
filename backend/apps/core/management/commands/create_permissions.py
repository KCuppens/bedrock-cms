from django.core.management import call_command
from django.core.management.base import BaseCommand

"""
Management command to create all model permissions.
This is needed because Django only creates permissions automatically on migrate.
"""


class Command(BaseCommand):
    help = "Create all model permissions"

    def handle(self, *args, **options):
        self.stdout.write("Creating permissions for all models...")

        # This command ensures all permissions are created for all installed apps
        call_command("migrate", "--run-syncdb", verbosity=2)

        self.stdout.write(self.style.SUCCESS("Permissions created successfully!"))
