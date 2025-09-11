# Generated manually for data migration

from django.db import migrations
from django.utils import timezone


def migrate_scheduling_data(apps, schema_editor):
    """Migrate existing scheduled_for data to scheduled_publish_at."""
    BlogPost = apps.get_model("blog", "BlogPost")

    # Skip migration if field doesn't exist (new installation)
    # Just ensure scheduled posts have publish dates
    for post in BlogPost.objects.filter(
        status="scheduled", scheduled_publish_at__isnull=True
    ):
        # If somehow a scheduled post doesn't have a time, set it to future
        post.scheduled_publish_at = timezone.now() + timezone.timedelta(days=1)
        post.save(update_fields=["scheduled_publish_at"])


def reverse_migration(apps, schema_editor):
    """Reverse the migration if needed."""
    # Nothing to reverse for this simplified migration
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0010_add_scheduling_fields"),
    ]

    operations = [
        migrations.RunPython(migrate_scheduling_data, reverse_migration),
    ]
