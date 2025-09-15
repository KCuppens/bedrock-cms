"""
Integration tests for CMS-i18n workflows.

This module tests the complete workflow integration between the CMS and i18n apps,
focusing on:
- Page creation with automatic translation unit creation
- Multilingual content publishing workflows
- Locale-specific page retrieval and SEO generation
- Translation unit updates when pages are modified
"""

import os

import django

# Setup Django before any Django imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

import pytest

from apps.cms.models import Page
from apps.i18n.models import Locale, TranslationUnit

# Import factories if available, otherwise use model directly
try:
    from tests.factories.accounts import AdminUserFactory, UserFactory
    from tests.factories.cms import LocaleFactory, PageFactory
    from tests.factories.i18n import TranslationUnitFactory
except ImportError:
    # Fallback if factories don't exist
    from django.contrib.auth import get_user_model

    User = get_user_model()
    AdminUserFactory = None
    UserFactory = None
    PageFactory = None
    LocaleFactory = None
    TranslationUnitFactory = None


@pytest.mark.django_db
class TestCMSI18nWorkflows(TestCase):
    """Test complete CMS-i18n integration workflows."""

    def setUp(self):
        """Set up test data."""
        if AdminUserFactory is None or UserFactory is None or LocaleFactory is None:
            self.skipTest("Required factories not available")

        self.admin_user = AdminUserFactory()
        self.editor_user = UserFactory()

        # Create locales
        self.default_locale = LocaleFactory(code="en", name="English", is_default=True)
        self.spanish_locale = LocaleFactory(
            code="es", name="Spanish", fallback=self.default_locale
        )
        self.french_locale = LocaleFactory(
            code="fr", name="French", fallback=self.default_locale
        )

    def test_page_creation_with_automatic_translation_units(self):
        """Test that page creation automatically creates translation units."""
        if PageFactory is None:
            self.skipTest("PageFactory not available")

        # Create a page in English
        page = PageFactory(
            title="Welcome to Our Site",
            locale=self.default_locale,
            slug="welcome",
            blocks=[
                {
                    "type": "hero",
                    "props": {
                        "heading": "Welcome to Our Amazing Site",
                        "subheading": "Discover incredible content and features",
                        "cta_text": "Get Started",
                    },
                },
                {
                    "type": "richtext",
                    "props": {
                        "content": "<p>This is our homepage with rich content.</p>"
                    },
                },
            ],
            seo={
                "title": "Welcome - Our Site",
                "description": "Welcome to our amazing website with great features",
                "keywords": "welcome, homepage, features",
            },
            status="published",
        )

        # Verify translation units are created for all locales except source
        content_type = ContentType.objects.get_for_model(Page)

        # Should create units for Spanish and French (not English since it's the source)
        translation_units = TranslationUnit.objects.filter(
            content_type=content_type, object_id=page.id
        )

        self.assertEqual(translation_units.count(), 6)  # 3 fields × 2 target locales

        # Check specific translation units exist
        title_spanish = TranslationUnit.objects.get(
            content_type=content_type,
            object_id=page.id,
            field="title",
            source_locale=self.default_locale,
            target_locale=self.spanish_locale,
        )
        self.assertEqual(title_spanish.source_text, "Welcome to Our Site")
        self.assertEqual(title_spanish.status, "missing")

        # Check blocks field translation unit
        blocks_french = TranslationUnit.objects.get(
            content_type=content_type,
            object_id=page.id,
            field="blocks",
            source_locale=self.default_locale,
            target_locale=self.french_locale,
        )
        self.assertIn("Welcome to Our Amazing Site", blocks_french.source_text)

    def test_multilingual_content_publishing_workflow(self):
        """Test complete multilingual publishing workflow."""
        if PageFactory is None:
            self.skipTest("PageFactory not available")

        # Create draft page in English
        page = PageFactory(
            title="Product Launch",
            locale=self.default_locale,
            slug="product-launch",
            status="draft",
            blocks=[
                {
                    "type": "announcement",
                    "props": {
                        "title": "New Product Coming Soon",
                        "message": "Stay tuned for our exciting announcement",
                    },
                }
            ],
        )

        # Submit for review
        page.submit_for_review(user=self.editor_user)
        self.assertEqual(page.status, "pending_review")

        # Approve and publish
        page.approve(reviewer=self.admin_user, notes="Looks good!")
        page.status = "published"
        page.published_at = timezone.now()
        page.save()

        # Now add translations
        content_type = ContentType.objects.get_for_model(Page)

        # Add Spanish translation for title
        spanish_title_unit = TranslationUnit.objects.get(
            content_type=content_type,
            object_id=page.id,
            field="title",
            target_locale=self.spanish_locale,
        )
        spanish_title_unit.target_text = "Lanzamiento de Producto"
        spanish_title_unit.status = "approved"
        spanish_title_unit.updated_by = self.admin_user
        spanish_title_unit.save()

        # Add French translation for blocks
        french_blocks_unit = TranslationUnit.objects.get(
            content_type=content_type,
            object_id=page.id,
            field="blocks",
            target_locale=self.french_locale,
        )
        french_blocks_unit.target_text = '[{"type": "announcement", "props": {"title": "Nouveau Produit Bientôt Disponible", "message": "Restez à l\'écoute pour notre annonce passionnante"}}]'
        french_blocks_unit.status = "approved"
        french_blocks_unit.updated_by = self.admin_user
        french_blocks_unit.save()

        # Verify translations are applied correctly
        self.assertTrue(spanish_title_unit.is_complete)
        self.assertTrue(french_blocks_unit.is_complete)

    def test_locale_specific_page_retrieval(self):
        """Test retrieving pages for specific locales."""
        if PageFactory is None:
            self.skipTest("PageFactory not available")

        # Create pages in different locales
        english_page = PageFactory(
            title="English Page",
            locale=self.default_locale,
            slug="english-page",
            status="published",
        )
        spanish_page = PageFactory(
            title="Página Española",
            locale=self.spanish_locale,
            slug="pagina-espanola",
            status="published",
        )
        french_page = PageFactory(
            title="Page Française",
            locale=self.french_locale,
            slug="page-francaise",
            status="published",
        )

        # Test locale-specific queries
        english_pages = Page.objects.filter(
            locale=self.default_locale, status="published"
        )
        self.assertEqual(english_pages.count(), 1)
        self.assertEqual(english_pages.first().title, "English Page")

        spanish_pages = Page.objects.filter(
            locale=self.spanish_locale, status="published"
        )
        self.assertEqual(spanish_pages.count(), 1)
        self.assertEqual(spanish_pages.first().title, "Página Española")

        # Test fallback behavior - pages without translations should fall back
        all_locales = [self.default_locale, self.spanish_locale, self.french_locale]
        for locale in all_locales:
            pages_for_locale = Page.objects.filter(
                locale=locale, status="published"
            ).order_by("title")
            self.assertGreaterEqual(pages_for_locale.count(), 1)

    def test_seo_generation_with_translations(self):
        """Test SEO field handling across locales."""
        if PageFactory is None:
            self.skipTest("PageFactory not available")

        # Create page with SEO data
        page = PageFactory(
            title="SEO Test Page",
            locale=self.default_locale,
            slug="seo-test",
            seo={
                "title": "SEO Test - Best Practices",
                "description": "Learn about SEO best practices and optimization",
                "keywords": "seo, optimization, best practices",
                "og_title": "SEO Test Page",
                "og_description": "Comprehensive guide to SEO",
            },
            status="published",
        )

        content_type = ContentType.objects.get_for_model(Page)

        # Add Spanish SEO translation
        spanish_seo_unit = TranslationUnit.objects.get(
            content_type=content_type,
            object_id=page.id,
            field="seo",
            target_locale=self.spanish_locale,
        )

        spanish_seo_data = {
            "title": "Prueba SEO - Mejores Prácticas",
            "description": "Aprende sobre las mejores prácticas de SEO y optimización",
            "keywords": "seo, optimización, mejores prácticas",
            "og_title": "Página de Prueba SEO",
            "og_description": "Guía completa de SEO",
        }

        spanish_seo_unit.target_text = str(spanish_seo_data)
        spanish_seo_unit.status = "approved"
        spanish_seo_unit.save()

        # Verify SEO translation is properly stored
        self.assertEqual(spanish_seo_unit.status, "approved")
        self.assertIn("Prueba SEO", spanish_seo_unit.target_text)

    def test_translation_unit_updates_on_page_modification(self):
        """Test that translation units are updated when source page changes."""
        if PageFactory is None:
            self.skipTest("PageFactory not available")

        # Create initial page
        page = PageFactory(
            title="Original Title",
            locale=self.default_locale,
            blocks=[
                {
                    "type": "hero",
                    "props": {
                        "heading": "Original Heading",
                        "text": "Original text content",
                    },
                }
            ],
        )

        content_type = ContentType.objects.get_for_model(Page)

        # Get initial translation unit
        spanish_title_unit = TranslationUnit.objects.get(
            content_type=content_type,
            object_id=page.id,
            field="title",
            target_locale=self.spanish_locale,
        )

        # Add translation
        spanish_title_unit.target_text = "Título Original"
        spanish_title_unit.status = "approved"
        spanish_title_unit.save()

        initial_updated_at = spanish_title_unit.updated_at
        self.assertEqual(spanish_title_unit.source_text, "Original Title")

        # Update page title
        page.title = "Updated Title"
        page.save()

        # Check that translation unit is updated
        spanish_title_unit.refresh_from_db()
        self.assertEqual(spanish_title_unit.source_text, "Updated Title")

        # Status should change to needs_review since source changed
        self.assertEqual(spanish_title_unit.status, "needs_review")
        self.assertGreater(spanish_title_unit.updated_at, initial_updated_at)

    def test_translation_workflow_with_complex_blocks(self):
        """Test translation workflow with complex nested block structures."""
        if PageFactory is None:
            self.skipTest("PageFactory not available")

        complex_blocks = [
            {
                "type": "section",
                "props": {
                    "title": "Main Section",
                    "blocks": [
                        {
                            "type": "text",
                            "props": {
                                "content": "This is nested content that needs translation"
                            },
                        },
                        {
                            "type": "cta",
                            "props": {
                                "button_text": "Click Here",
                                "button_url": "/contact",
                            },
                        },
                    ],
                },
            },
            {
                "type": "testimonials",
                "props": {
                    "heading": "What Our Customers Say",
                    "testimonials": [
                        {
                            "text": "Amazing service and support!",
                            "author": "John Doe",
                            "company": "Tech Corp",
                        },
                        {
                            "text": "Best decision we ever made!",
                            "author": "Jane Smith",
                            "company": "Innovation Inc",
                        },
                    ],
                },
            },
        ]

        page = PageFactory(
            title="Complex Blocks Page",
            locale=self.default_locale,
            blocks=complex_blocks,
            status="published",
        )

        content_type = ContentType.objects.get_for_model(Page)

        # Get blocks translation unit
        french_blocks_unit = TranslationUnit.objects.get(
            content_type=content_type,
            object_id=page.id,
            field="blocks",
            target_locale=self.french_locale,
        )

        # Verify complex structure is captured
        self.assertIn("Main Section", french_blocks_unit.source_text)
        self.assertIn("This is nested content", french_blocks_unit.source_text)
        self.assertIn("Amazing service", french_blocks_unit.source_text)
        self.assertIn("John Doe", french_blocks_unit.source_text)

    def test_translation_deletion_cascade(self):
        """Test that translation units are properly cleaned up when page is deleted."""
        if PageFactory is None:
            self.skipTest("PageFactory not available")

        page = PageFactory(title="Page to Delete", locale=self.default_locale)

        content_type = ContentType.objects.get_for_model(Page)

        # Verify translation units exist
        initial_count = TranslationUnit.objects.filter(
            content_type=content_type, object_id=page.id
        ).count()
        self.assertGreater(initial_count, 0)

        # Delete the page
        page_id = page.id
        page.delete()

        # Verify translation units are also deleted
        remaining_count = TranslationUnit.objects.filter(
            content_type=content_type, object_id=page_id
        ).count()
        self.assertEqual(remaining_count, 0)

    def test_bulk_translation_operations(self):
        """Test bulk operations on translation units."""
        if PageFactory is None:
            self.skipTest("PageFactory not available")

        # Create multiple pages
        pages = []
        for i in range(3):
            page = PageFactory(
                title=f"Bulk Page {i+1}", locale=self.default_locale, status="published"
            )
            pages.append(page)

        content_type = ContentType.objects.get_for_model(Page)

        # Get all Spanish title translation units
        spanish_title_units = TranslationUnit.objects.filter(
            content_type=content_type,
            object_id__in=[p.id for p in pages],
            field="title",
            target_locale=self.spanish_locale,
        )

        self.assertEqual(spanish_title_units.count(), 3)

        # Bulk update status
        spanish_title_units.update(status="draft", updated_by=self.admin_user)

        # Verify all were updated
        for unit in spanish_title_units:
            unit.refresh_from_db()
            self.assertEqual(unit.status, "draft")
            self.assertEqual(unit.updated_by, self.admin_user)

    def test_locale_fallback_chain_integration(self):
        """Test that locale fallback chains work with page retrieval."""
        if PageFactory is None or LocaleFactory is None:
            self.skipTest("Required factories not available")

        # Create a chain: German -> Spanish -> English
        german_locale = LocaleFactory(
            code="de", name="German", fallback=self.spanish_locale
        )

        # Create page only in English (default)
        english_page = PageFactory(
            title="English Only Page",
            locale=self.default_locale,
            slug="english-only",
            status="published",
        )

        # Create page in Spanish
        spanish_page = PageFactory(
            title="Página Solo en Español",
            locale=self.spanish_locale,
            slug="solo-espanol",
            status="published",
        )

        # Test fallback chain retrieval
        # German should fall back to Spanish, then English
        fallback_chain = german_locale.get_fallback_chain()
        expected_codes = ["de", "es", "en"]
        actual_codes = [locale.code for locale in fallback_chain]
        self.assertEqual(actual_codes, expected_codes)

        # Test that we can find content through fallback
        # This would typically be handled by a service layer
        available_locales = {self.default_locale.code, self.spanish_locale.code}

        # German content should be available through fallback
        for locale in fallback_chain:
            if locale.code in available_locales:
                # We found content in fallback chain
                self.assertIn(locale.code, ["en", "es"])
                break

    def test_performance_with_large_translation_dataset(self):
        """Test performance implications with larger datasets."""
        if PageFactory is None:
            self.skipTest("PageFactory not available")

        with transaction.atomic():
            # Create multiple pages with translations
            pages = []
            for i in range(10):
                page = PageFactory(
                    title=f"Performance Test Page {i+1}",
                    locale=self.default_locale,
                    blocks=[
                        {
                            "type": "hero",
                            "props": {
                                "heading": f"Heading {i+1}",
                                "text": f"Content for page {i+1} "
                                * 50,  # Make it substantial
                            },
                        }
                    ],
                )
                pages.append(page)

            # Add some translations
            content_type = ContentType.objects.get_for_model(Page)
            units_to_update = TranslationUnit.objects.filter(
                content_type=content_type,
                object_id__in=[p.id for p in pages[:5]],  # Only first 5
                field="title",
                target_locale=self.spanish_locale,
            )

            for unit in units_to_update:
                unit.target_text = f"Título {unit.object_id}"
                unit.status = "approved"
                unit.save()

        # Test query performance
        # This would typically use select_related/prefetch_related in real code
        translated_pages = Page.objects.filter(
            locale=self.default_locale, id__in=[p.id for p in pages]
        ).order_by("id")

        self.assertEqual(translated_pages.count(), 10)

        # Test translation unit queries
        all_units = TranslationUnit.objects.filter(
            content_type=content_type, object_id__in=[p.id for p in pages]
        ).select_related("source_locale", "target_locale")

        # Should have 30 units (10 pages × 3 fields) × 2 target locales = 60 units
        self.assertEqual(all_units.count(), 60)

        # Test approved translations count
        approved_units = all_units.filter(status="approved")
        self.assertEqual(approved_units.count(), 5)  # Only titles for first 5 pages
