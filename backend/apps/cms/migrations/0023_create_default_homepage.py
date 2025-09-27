"""
Migration to create default homepage.
"""

from django.db import migrations
from django.utils import timezone


def create_default_homepage(apps, schema_editor):
    """Create the default homepage with route '/'."""
    Page = apps.get_model("cms", "Page")
    Locale = apps.get_model("i18n", "Locale")

    # Get or create the English locale
    locale, _ = Locale.objects.get_or_create(
        code="en",
        defaults={
            "name": "English",
            "native_name": "English",
            "is_default": True,
            "is_active": True,
        },
    )

    # Check if a homepage already exists
    if not Page.objects.filter(path="/").exists():
        # Create the homepage
        homepage = Page.objects.create(
            title="Welcome to Bedrock CMS",
            slug="home",
            path="/",
            blocks=[
                {
                    "type": "heading",
                    "content": {"text": "Welcome to Bedrock CMS", "level": 1},
                },
                {
                    "type": "paragraph",
                    "content": {
                        "text": "This is your default homepage. You can customize this page by editing it in the CMS admin panel."
                    },
                },
                {"type": "heading", "content": {"text": "Getting Started", "level": 2}},
                {
                    "type": "paragraph",
                    "content": {
                        "text": "Start building your website by creating new pages, adding content blocks, and customizing the design to match your needs."
                    },
                },
            ],
            seo={
                "title": "Welcome to Bedrock CMS - Modern Content Management",
                "description": "A modern, flexible content management system built with Django and React. Create beautiful, performant websites with ease.",
                "keywords": ["CMS", "Content Management", "Django", "React"],
                "og_title": "Welcome to Bedrock CMS",
                "og_description": "A modern, flexible content management system built with Django and React.",
                "og_image": None,
            },
            status="published",
            published_at=timezone.now(),
            locale=locale,
            parent=None,
            is_homepage=True,
            in_main_menu=True,
        )


def reverse_default_homepage(apps, schema_editor):
    """Remove the default homepage."""
    Page = apps.get_model("cms", "Page")
    Page.objects.filter(path="/", title="Welcome to Bedrock CMS").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0022_blocktype_order"),
        ("i18n", "0005_create_default_locale"),
    ]

    operations = [
        migrations.RunPython(create_default_homepage, reverse_default_homepage),
    ]
