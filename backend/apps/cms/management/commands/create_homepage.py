"""
Management command to create a default homepage.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cms.models import Page
from apps.i18n.models import Locale


class Command(BaseCommand):
    help = "Creates a default homepage with route / if it doesn't exist"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force recreate the homepage even if it exists",
        )
        parser.add_argument(
            "--locale",
            type=str,
            default="en",
            help="Locale code for the homepage (default: en)",
        )

    def handle(self, *args, **options):
        force = options["force"]
        locale_code = options["locale"]

        # Get or create the locale
        locale, created = Locale.objects.get_or_create(
            code=locale_code,
            defaults={
                "name": "English" if locale_code == "en" else locale_code.upper(),
                "native_name": (
                    "English" if locale_code == "en" else locale_code.upper()
                ),
                "is_default": locale_code == "en",
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Created locale: {locale_code}"))

        # Check if homepage exists
        homepage_exists = Page.objects.filter(path="/").exists()

        if homepage_exists and not force:
            self.stdout.write(
                self.style.WARNING(
                    "Homepage already exists. Use --force to recreate it."
                )
            )
            return

        if homepage_exists and force:
            Page.objects.filter(path="/").delete()
            self.stdout.write(self.style.WARNING("Existing homepage deleted."))

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
                    "type": "list",
                    "content": {
                        "style": "unordered",
                        "items": [
                            "Create new pages from the admin panel",
                            "Add and customize content blocks",
                            "Configure SEO settings for better visibility",
                            "Set up multilingual content if needed",
                            "Customize the design and layout",
                        ],
                    },
                },
                {"type": "heading", "content": {"text": "Features", "level": 2}},
                {
                    "type": "list",
                    "content": {
                        "style": "unordered",
                        "items": [
                            "📄 Flexible page builder with content blocks",
                            "🌍 Multilingual support",
                            "🔍 SEO optimization tools",
                            "📊 Analytics integration",
                            "🚀 High performance and caching",
                            "🔒 Secure and scalable architecture",
                        ],
                    },
                },
                {
                    "type": "paragraph",
                    "content": {
                        "text": "For more information, visit the documentation or contact support."
                    },
                },
            ],
            seo={
                "title": "Welcome to Bedrock CMS - Modern Content Management",
                "description": "A modern, flexible content management system built with Django and React. Create beautiful, performant websites with ease.",
                "keywords": [
                    "CMS",
                    "Content Management",
                    "Django",
                    "React",
                    "Headless CMS",
                ],
                "og_title": "Welcome to Bedrock CMS",
                "og_description": "A modern, flexible content management system built with Django and React.",
                "og_image": None,
                "twitter_card": "summary_large_image",
            },
            status="published",
            published_at=timezone.now(),
            locale=locale,
            parent=None,
            is_homepage=True,
            in_main_menu=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created homepage at path: /")
        )
        self.stdout.write(self.style.SUCCESS(f"Homepage ID: {homepage.id}"))
        self.stdout.write(self.style.SUCCESS(f"Locale: {locale.code} ({locale.name})"))
