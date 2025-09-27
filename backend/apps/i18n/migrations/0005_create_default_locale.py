"""
Migration to create default English locale.
"""

from django.db import migrations


def create_default_locale(apps, schema_editor):
    """Create the default English locale."""
    Locale = apps.get_model("i18n", "Locale")

    # Check if English locale already exists
    if not Locale.objects.filter(code="en").exists():
        Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )


def reverse_default_locale(apps, schema_editor):
    """Remove the default English locale."""
    Locale = apps.get_model("i18n", "Locale")
    Locale.objects.filter(code="en").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("i18n", "0004_alter_translationunit_status_translationqueue_and_more"),
    ]

    operations = [
        migrations.RunPython(create_default_locale, reverse_default_locale),
    ]
