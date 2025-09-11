# Generated manually for data migration

from django.db import migrations
from django.contrib.contenttypes.models import ContentType


def migrate_page_scheduling_data(apps, schema_editor):
    """Migrate existing scheduled pages and create ScheduledTask entries."""
    Page = apps.get_model('cms', 'Page')
    ScheduledTask = apps.get_model('cms', 'ScheduledTask')
    
    # Get ContentType for Page
    page_content_type = ContentType.objects.get_for_model(Page)
    
    # Update all scheduled pages
    for page in Page.objects.filter(status='scheduled', published_at__isnull=False):
        # Move published_at to scheduled_publish_at for scheduled pages
        page.scheduled_publish_at = page.published_at
        page.published_at = None
        page.save(update_fields=['scheduled_publish_at', 'published_at'])
        
        # Create a ScheduledTask for this page
        ScheduledTask.objects.create(
            content_type=page_content_type,
            object_id=page.id,
            task_type='publish',
            scheduled_for=page.scheduled_publish_at,
            status='pending'
        )


def reverse_migration(apps, schema_editor):
    """Reverse the migration if needed."""
    Page = apps.get_model('cms', 'Page')
    ScheduledTask = apps.get_model('cms', 'ScheduledTask')
    
    # Get ContentType for Page
    page_content_type = ContentType.objects.get_for_model(Page)
    
    # Delete all scheduled tasks for pages
    ScheduledTask.objects.filter(content_type=page_content_type).delete()
    
    # Restore published_at for scheduled pages
    for page in Page.objects.filter(status='scheduled', scheduled_publish_at__isnull=False):
        page.published_at = page.scheduled_publish_at
        page.scheduled_publish_at = None
        page.save(update_fields=['published_at', 'scheduled_publish_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0016_add_scheduling_fields'),
    ]

    operations = [
        migrations.RunPython(migrate_page_scheduling_data, reverse_migration),
    ]