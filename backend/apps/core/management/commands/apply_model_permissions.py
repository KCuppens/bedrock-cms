"""
Management command to apply custom permissions to all models.

Usage:
    python manage.py apply_model_permissions
    python manage.py apply_model_permissions --dry-run
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.model_permissions import get_all_custom_permissions


class Command(BaseCommand):
    help = "Apply custom permissions to all models"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating permissions",
        )
        parser.add_argument(
            "--delete-orphaned",
            action="store_true",
            help="Delete orphaned permissions (permissions for non-existent models)",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry-run", False)
        delete_orphaned = options.get("delete_orphaned", False)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Get all custom permissions
        all_permissions = get_all_custom_permissions()

        created_count = 0
        skipped_count = 0
        error_count = 0

        with transaction.atomic():
            for model_path, permissions in all_permissions.items():
                app_label, model_name = model_path.split(".")

                try:
                    # Get the content type
                    content_type = ContentType.objects.get(
                        app_label=app_label, model=model_name
                    )

                    self.stdout.write(f"\nProcessing {app_label}.{model_name}:")

                    for codename, name in permissions:
                        # Check if permission already exists
                        exists = Permission.objects.filter(
                            content_type=content_type, codename=codename
                        ).exists()

                        if exists:
                            self.stdout.write(f"  ✓ {codename} already exists")
                            skipped_count += 1
                        else:
                            if dry_run:
                                self.stdout.write(
                                    f"  → Would create: {codename} - {name}"
                                )
                            else:
                                Permission.objects.create(
                                    content_type=content_type,
                                    codename=codename,
                                    name=name,
                                )
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"  ✓ Created: {codename} - {name}"
                                    )
                                )
                            created_count += 1

                except ContentType.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f"\n✗ Model {app_label}.{model_name} does not exist"
                        )
                    )
                    error_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"\n✗ Error processing {app_label}.{model_name}: {str(e)}"
                        )
                    )
                    error_count += 1

            # Handle orphaned permissions
            if delete_orphaned:
                self.stdout.write("\n" + "=" * 50)
                self.stdout.write("Checking for orphaned permissions...")

                # Find permissions with invalid content types
                orphaned = []
                for perm in Permission.objects.all():
                    try:
                        # Try to access the model class
                        perm.content_type.model_class()
                    except:
                        orphaned.append(perm)

                if orphaned:
                    self.stdout.write(f"Found {len(orphaned)} orphaned permissions:")
                    for perm in orphaned:
                        self.stdout.write(
                            f"  - {perm.content_type.app_label}.{perm.codename}"
                        )

                    if not dry_run:
                        for perm in orphaned:
                            perm.delete()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Deleted {len(orphaned)} orphaned permissions"
                            )
                        )
                    else:
                        self.stdout.write(
                            f"Would delete {len(orphaned)} orphaned permissions"
                        )
                else:
                    self.stdout.write("No orphaned permissions found")

            # Show default Django permissions
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write("Default Django permissions (automatically created):")
            default_perms = ["add", "change", "delete", "view"]

            for model_path in all_permissions.keys():
                app_label, model_name = model_path.split(".")
                self.stdout.write(f"\n{app_label}.{model_name}:")
                for action in default_perms:
                    perm_name = f"{action}_{model_name}"
                    self.stdout.write(f"  • {perm_name}")

            # Summary
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write("SUMMARY:")
            if dry_run:
                self.stdout.write(f"Would create: {created_count} permissions")
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"Created: {created_count} permissions")
                )
            self.stdout.write(f"Skipped (already exist): {skipped_count} permissions")
            if error_count:
                self.stdout.write(self.style.ERROR(f"Errors: {error_count}"))

            if dry_run:
                # Rollback transaction in dry run mode
                transaction.set_rollback(True)
