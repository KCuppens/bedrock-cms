from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.db.models import Count

from apps.registry.registry import content_registry
from apps.search.models import SearchIndex
from apps.search.services import get_search_service

"""Django management command for search indexing.

Usage:
    python manage.py search_index --reindex-all
    python manage.py search_index --model blog.blogpost
    python manage.py search_index --clear
"""


class Command(BaseCommand):
    """Management command for search indexing operations."""

    help = "Manage search index operations"

    def add_arguments(self, parser):
        """Add command arguments."""

        parser.add_argument(
            "--reindex-all",
            action="store_true",
            help="Reindex all registered content types",
        )

        parser.add_argument(
            "--model", type=str, help="Specific model to reindex (e.g., blog.blogpost)"
        )

        parser.add_argument(
            "--clear", action="store_true", help="Clear all search index entries"
        )

        parser.add_argument(
            "--stats", action="store_true", help="Show search index statistics"
        )

        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Batch size for indexing operations (default: 100)",
        )

        parser.add_argument(
            "--verbose", action="store_true", help="Enable verbose output"
        )

    def handle(self, *args, **options):
        """Handle the command."""

        self.verbosity = options.get("verbosity", 1)

        self.verbose = options.get("verbose", False)

        if options["clear"]:

            self.clear_index()

        elif options["stats"]:

            self.show_stats()

        elif options["reindex_all"]:

            self.reindex_all(options["batch_size"])

        elif options["model"]:

            self.reindex_model(options["model"], options["batch_size"])

        else:

            self.show_help()

    def show_help(self):
        """Show command help."""

        self.stdout.write(self.style.SUCCESS("Search Index Management"))

        self.stdout.write("")

        self.stdout.write("Available operations:")

        self.stdout.write("  --reindex-all      Reindex all registered content")

        self.stdout.write("  --model <label>    Reindex specific model")

        self.stdout.write("  --clear           Clear all index entries")

        self.stdout.write("  --stats           Show index statistics")

        self.stdout.write("")

        self.stdout.write("Examples:")

        self.stdout.write("  python manage.py search_index --reindex-all")

        self.stdout.write("  python manage.py search_index --model blog.blogpost")

        self.stdout.write("  python manage.py search_index --clear")

        self.stdout.write("  python manage.py search_index --stats")

    def show_stats(self):
        """Show search index statistics."""

        self.stdout.write(self.style.SUCCESS("Search Index Statistics"))

        self.stdout.write("=" * 50)

        # Total entries

        total_entries = SearchIndex.objects.count()

        published_entries = SearchIndex.objects.filter(is_published=True).count()

        self.stdout.write(f"Total index entries: {total_entries}")

        self.stdout.write(f"Published entries: {published_entries}")

        self.stdout.write("")

        # By content type

        self.stdout.write("By content type:")

        content_types = (
            SearchIndex.objects.values("content_type__app_label", "content_type__model")
            .annotate(
                total=Count("id"),
                published=Count("id", filter=models.Q(is_published=True)),
            )
            .order_by("-total")
        )

        for ct in content_types:

            app_label = ct["content_type__app_label"]

            model = ct["content_type__model"]

            total = ct["total"]

            published = ct["published"]

            self.stdout.write(
                f"  {app_label}.{model}: {total} total, {published} published"
            )

        self.stdout.write("")

        # By category

        self.stdout.write("By search category:")

        categories = (
            SearchIndex.objects.values("search_category")
            .annotate(
                total=Count("id"),
                published=Count("id", filter=models.Q(is_published=True)),
            )
            .order_by("-total")
        )

        for cat in categories:

            category = cat["search_category"]

            total = cat["total"]

            published = cat["published"]

            self.stdout.write(f"  {category}: {total} total, {published} published")

    def clear_index(self):
        """Clear all search index entries."""

        self.stdout.write(self.style.WARNING("Clearing all search index entries..."))

        if not self.confirm_action("This will delete all search index data. Continue?"):

            self.stdout.write(self.style.ERROR("Operation cancelled."))

        with transaction.atomic():

            count = SearchIndex.objects.count()

            SearchIndex.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully cleared {count} search index entries.")
        )

    def reindex_all(self, batch_size):
        """Reindex all registered content types."""

        self.stdout.write(
            self.style.SUCCESS("Reindexing all registered content types...")
        )

        configs = content_registry.get_all_configs()

        if not configs:

            self.stdout.write(self.style.WARNING("No content types registered."))

        self.stdout.write(f"Found {len(configs)} registered content types:")

        for config in configs:

            self.stdout.write(f"  - {config.model_label} ({config.name})")

        if not self.confirm_action("Continue with reindexing?"):

            self.stdout.write(self.style.ERROR("Operation cancelled."))

        total_indexed = 0

        for config in configs:

            indexed_count = self.index_model_objects(
                config.model, config.model_label, batch_size
            )

            total_indexed += indexed_count

        self.stdout.write(
            self.style.SUCCESS(f"Successfully indexed {total_indexed} objects total.")
        )

    def reindex_model(self, model_label, batch_size):
        """Reindex a specific model."""

        self.stdout.write(self.style.SUCCESS(f"Reindexing model: {model_label}"))

        # Get model configuration

        config = content_registry.get_config(model_label)

        if not config:
            raise CommandError(
                f"Model {model_label} is not registered with content registry"
            )

        indexed_count = self.index_model_objects(config.model, model_label, batch_size)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully indexed {indexed_count} objects.")
        )

    def index_model_objects(self, model, model_label, batch_size):
        """Index objects for a specific model."""

        # Get all objects for this model

        queryset = model.objects.all()

        # Apply filters for publishable content

        if hasattr(model, "status"):

            # For models with status field (like BlogPost)

            queryset = queryset.filter(status="published")

        elif hasattr(model, "is_published"):

            # For models with is_published field

            queryset = queryset.filter(is_published=True)

        # For models without publish status (like Category, Tag), index all active ones

        elif hasattr(model, "is_active"):

            queryset = queryset.filter(is_active=True)

        total_objects = queryset.count()

        if total_objects == 0:

            self.stdout.write(
                self.style.WARNING(f"  No objects found for {model_label}")
            )

            return 0

        self.stdout.write(f"  Indexing {total_objects} objects for {model_label}...")

        indexed_count = 0

        errors = 0

        # Process in batches

        for i in range(0, total_objects, batch_size):

            batch = queryset[i : i + batch_size]

            for obj in batch:

                try:

                    get_search_service().index_object(obj)

                    indexed_count += 1

                    if self.verbose and indexed_count % 50 == 0:

                        self.stdout.write(
                            f"    Indexed {indexed_count}/{total_objects}..."
                        )

                except Exception as e:

                    errors += 1

                    if self.verbose:

                        self.stdout.write(
                            self.style.ERROR(f"    Error indexing {obj}: {e}")
                        )

        success_msg = f"  {model_label}: {indexed_count} indexed"

        if errors > 0:

            success_msg += f", {errors} errors"

        self.stdout.write(self.style.SUCCESS(success_msg))

        return indexed_count

    def confirm_action(self, message):
        """Ask for user confirmation."""

        if self.verbosity < 2:  # Non-interactive mode

            return True

        response = input(f"{message} (y/N): ")

        return response.lower() in ["y", "yes"]
