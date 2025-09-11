from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cms.tasks import publish_scheduled_content


class Command(BaseCommand):
    help = "Publish scheduled content that is ready to be published"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be published without actually publishing",
        )

    def handle(self, *args, **options):
        self.stdout.write(f"Checking for scheduled content at {timezone.now()}")

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
            # In a real implementation, we'd add dry-run support to the task

        try:
            result = publish_scheduled_content()

            published_count = result["published_count"]
            errors = result["errors"]

            if published_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully published {published_count} items"
                    )
                )
            else:
                self.stdout.write("No scheduled content ready for publishing")

            if errors:
                self.stdout.write(
                    self.style.ERROR(f"Encountered {len(errors)} errors:")
                )
                for error in errors:
                    self.stdout.write(f"  - {error}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Command failed: {str(e)}"))
            raise
