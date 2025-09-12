from django.core.management.base import BaseCommand

from django.db import transaction


from apps.cms.models import BlockType, BlockTypeCategory


class Command(BaseCommand):

    help = "Seed the database with default block types from existing configurations"

    def add_arguments(self, parser):

        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing block types",
        )

    def handle(self, *args, **options):
        """Seed block types from existing hardcoded configurations."""

        # Define the default block types based on current system

        default_block_types = [
            {
                "type": "hero",
                "component": "HeroBlock",
                "label": "Hero Section",
                "description": "Large banner section with title, subtitle, and call-to-action button",
                "category": BlockTypeCategory.LAYOUT,
                "icon": "layout",
                "preload": True,
                "editing_mode": "inline",
                "default_props": {
                    "title": "Welcome to Our Website",
                    "subtitle": "Discover amazing content and services that will transform your experience",
                    "buttonText": "Get Started",
                    "buttonUrl": "#",
                    "backgroundImage": "",
                },
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "title": "Title"},
                        "subtitle": {"type": "string", "title": "Subtitle"},
                        "buttonText": {"type": "string", "title": "Button Text"},
                        "buttonUrl": {"type": "string", "title": "Button URL"},
                        "backgroundImage": {
                            "type": "string",
                            "title": "Background Image URL",
                        },
                    },
                },
            },
            {
                "type": "richtext",
                "component": "RichtextBlock",
                "label": "Rich Text",
                "description": "Rich text content with HTML formatting support",
                "category": BlockTypeCategory.CONTENT,
                "icon": "type",
                "preload": False,
                "editing_mode": "inline",
                "default_props": {
                    "content": "<p>Enter your rich text content here. You can use <strong>bold</strong>, <em>italic</em>, and other HTML formatting.</p>",
                    "alignment": "left",
                },
                "schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "title": "Content"},
                        "alignment": {
                            "type": "string",
                            "enum": ["left", "center", "right", "justify"],
                            "title": "Alignment",
                        },
                    },
                },
            },
            {
                "type": "faq",
                "component": "FaqBlock",
                "label": "FAQ Section",
                "description": "Frequently Asked Questions with expandable accordion items",
                "category": BlockTypeCategory.CONTENT,
                "icon": "help-circle",
                "preload": False,
                "editing_mode": "inline",
                "default_props": {
                    "title": "Frequently Asked Questions",
                    "items": [
                        {
                            "question": "What is this service about?",
                            "answer": "This is a sample FAQ answer that explains the service in detail.",
                        },
                        {
                            "question": "How do I get started?",
                            "answer": "Getting started is easy! Simply follow these steps...",
                        },
                    ],
                },
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "title": "Title"},
                        "items": {
                            "type": "array",
                            "title": "FAQ Items",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string", "title": "Question"},
                                    "answer": {"type": "string", "title": "Answer"},
                                },
                            },
                        },
                    },
                },
            },
            {
                "type": "image",
                "component": "ImageBlock",
                "label": "Image",
                "description": "Single image with caption",
                "category": BlockTypeCategory.MEDIA,
                "icon": "image",
                "preload": False,
                "editing_mode": "inline",
                "default_props": {"src": "", "alt": "", "caption": ""},
                "schema": {
                    "type": "object",
                    "properties": {
                        "src": {"type": "string", "title": "Image URL"},
                        "alt": {"type": "string", "title": "Alt Text"},
                        "caption": {"type": "string", "title": "Caption"},
                    },
                },
            },
            {
                "type": "gallery",
                "component": "GalleryBlock",
                "label": "Image Gallery",
                "description": "Multiple images in a grid layout",
                "category": BlockTypeCategory.MEDIA,
                "icon": "grid",
                "preload": False,
                "editing_mode": "inline",
                "default_props": {"images": []},
                "schema": {
                    "type": "object",
                    "properties": {
                        "images": {
                            "type": "array",
                            "title": "Images",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "src": {"type": "string", "title": "Image URL"},
                                    "alt": {"type": "string", "title": "Alt Text"},
                                    "caption": {"type": "string", "title": "Caption"},
                                },
                            },
                        }
                    },
                },
            },
            {
                "type": "cta_band",
                "component": "CtaBandBlock",
                "label": "Call to Action",
                "description": "Call-to-action section with button and compelling text",
                "category": BlockTypeCategory.MARKETING,
                "icon": "megaphone",
                "preload": False,
                "editing_mode": "inline",
                "default_props": {
                    "title": "Ready to Get Started?",
                    "subtitle": "Join thousands of satisfied customers today",
                    "cta_text": "Sign Up Now",
                    "cta_url": "#",
                    "background_color": "#f8f9fa",
                },
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "title": "Title"},
                        "subtitle": {"type": "string", "title": "Subtitle"},
                        "cta_text": {"type": "string", "title": "CTA Text"},
                        "cta_url": {"type": "string", "title": "CTA URL"},
                        "background_color": {
                            "type": "string",
                            "title": "Background Color",
                        },
                    },
                },
            },
            {
                "type": "columns",
                "component": "ColumnsBlock",
                "label": "Columns",
                "description": "Multi-column layout container",
                "category": BlockTypeCategory.LAYOUT,
                "icon": "columns",
                "preload": False,
                "editing_mode": "inline",
                "default_props": {"columns": [], "gap": "md"},
                "schema": {
                    "type": "object",
                    "properties": {
                        "columns": {
                            "type": "array",
                            "title": "Columns",
                            "items": {"type": "object"},
                        },
                        "gap": {
                            "type": "string",
                            "enum": ["sm", "md", "lg"],
                            "title": "Gap Size",
                        },
                    },
                },
            },
            {
                "type": "content_detail",
                "component": "ContentDetailBlock",
                "label": "Content Detail",
                "description": "Dynamic content display for registered models",
                "category": BlockTypeCategory.DYNAMIC,
                "icon": "layout-grid",
                "preload": False,
                "editing_mode": "inline",
                "default_props": {
                    "label": "",
                    "source": "route",
                    "options": {
                        "show_toc": True,
                        "show_author": True,
                        "show_dates": True,
                        "show_share": True,
                        "show_reading_time": True,
                    },
                },
                "schema": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "title": "Content Type"},
                        "source": {"type": "string", "title": "Data Source"},
                        "options": {
                            "type": "object",
                            "title": "Display Options",
                            "properties": {
                                "show_toc": {
                                    "type": "boolean",
                                    "title": "Show Table of Contents",
                                },
                                "show_author": {
                                    "type": "boolean",
                                    "title": "Show Author",
                                },
                                "show_dates": {
                                    "type": "boolean",
                                    "title": "Show Dates",
                                },
                                "show_share": {
                                    "type": "boolean",
                                    "title": "Show Share",
                                },
                                "show_reading_time": {
                                    "type": "boolean",
                                    "title": "Show Reading Time",
                                },
                            },
                        },
                    },
                },
            },
        ]

        created_count = 0

        updated_count = 0

        with transaction.atomic():

            for block_data in default_block_types:

                block_type, created = BlockType.objects.get_or_create(
                    type=block_data["type"], defaults=block_data
                )

                if created:

                    created_count += 1

                    self.stdout.write(
                        self.style.SUCCESS(f"Created block type: {block_type.label}")
                    )

                elif options["overwrite"]:

                    # Update existing block type

                    for key, value in block_data.items():

                        setattr(block_type, key, value)

                    block_type.save()

                    updated_count += 1

                    self.stdout.write(
                        self.style.WARNING(f"Updated block type: {block_type.label}")
                    )

                else:

                    self.stdout.write(
                        self.style.WARNING(
                            f"Block type already exists: {block_type.label}"
                        )
                    )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )

        if not options["overwrite"] and BlockType.objects.count() > created_count:

            self.stdout.write(
                self.style.WARNING(
                    "Some block types already existed. Use --overwrite to update them."
                )
            )
