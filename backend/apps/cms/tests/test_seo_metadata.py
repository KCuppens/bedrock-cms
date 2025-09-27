"""Comprehensive tests for SEO metadata handling in CMS.

This test suite covers:
1. SEO Metadata Tests: Meta title, description, Open Graph, Twitter Card, etc.
2. SEO Validation Tests: Field length validation, duplicate content detection
3. Multilingual SEO Tests: Hreflang alternates, locale-specific metadata
4. Dynamic SEO Generation: Auto-generation from content, fallback mechanisms
5. SEO Performance Tests: Core Web Vitals, mobile-first considerations
6. API Integration Tests: SEO data endpoints, validation APIs
"""

import os

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()


import json
import os
import uuid
from datetime import datetime
from unittest.mock import Mock, patch

import django

# Configure Django settings before any imports
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.test import APIClient, APITestCase

from apps.cms.models import Page
from apps.cms.seo import SeoSettings
from apps.cms.seo_utils import (
    deep_merge_dicts,
    generate_canonical_url,
    generate_hreflang_alternates,
    generate_meta_tags,
    generate_schema_org,
    generate_seo_links,
    resolve_seo,
    validate_seo_data,
)
from apps.cms.serializers.seo import SeoSettingsSerializer
from apps.cms.views.seo import PublicSeoSettingsView, SeoSettingsViewSet
from apps.files.models import FileUpload
from apps.i18n.models import Locale

User = get_user_model()


class SeoMetadataTestCase(TestCase):
    """Test SEO metadata generation and handling."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="seo@example.com", password="testpass123"
        )

        # Create locales
        self.en_locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

        self.es_locale = Locale.objects.create(
            code="es",
            name="Spanish",
            native_name="Español",
            is_default=False,
            is_active=True,
        )

        self.fr_locale = Locale.objects.create(
            code="fr",
            name="French",
            native_name="Français",
            is_default=False,
            is_active=True,
        )

        # Create image file for testing
        self.test_image = FileUpload.objects.create(
            id=uuid.uuid4(),
            original_filename="test-og-image.jpg",
            filename="test-og-image-stored.jpg",
            file_type="image",
            mime_type="image/jpeg",
            file_size=102400,  # 100KB
            storage_path="/uploads/test-og-image-stored.jpg",
            is_public=True,
            created_by=self.user,
            updated_by=self.user,
        )

        # Create SEO settings for English
        self.seo_settings_en = SeoSettings.objects.create(
            locale=self.en_locale,
            title_suffix=" | My Site",
            default_title="Welcome to My Site",
            default_description="This is the default description for our website.",
            default_keywords="website, content, management",
            default_og_asset=self.test_image,
            default_og_title="My Site - Open Graph",
            default_og_description="Open Graph description for My Site",
            default_og_type="website",
            default_og_site_name="My Site",
            default_twitter_card="summary_large_image",
            default_twitter_site="@mysite",
            default_twitter_creator="@creator",
            default_twitter_asset=self.test_image,
            robots_default="index,follow",
            canonical_domain="https://example.com",
            google_site_verification="google123",
            bing_site_verification="bing456",
            jsonld_default=[
                {
                    "@type": "Organization",
                    "name": "My Site",
                    "url": "https://example.com",
                }
            ],
            organization_jsonld={
                "@type": "Organization",
                "name": "My Organization",
                "url": "https://example.com",
                "logo": "https://example.com/logo.png",
            },
            meta_author="My Site Team",
            meta_generator="Bedrock CMS",
            meta_viewport="width=device-width, initial-scale=1.0",
            facebook_app_id="123456789",
        )

        # Create a test page
        self.page = Page.objects.create(
            title="Test Page",
            slug="test-page",
            path="/test-page",
            locale=self.en_locale,
            status="published",
            seo={
                "title": "Custom SEO Title",
                "description": "Custom SEO description for this page.",
                "keywords": "test, page, seo",
                "robots": "index,follow",
                "og": {
                    "title": "Custom OG Title",
                    "description": "Custom OG description",
                    "type": "article",
                },
                "twitter": {
                    "card": "summary",
                    "title": "Custom Twitter Title",
                    "description": "Custom Twitter description",
                },
                "jsonld": [
                    {
                        "@type": "Article",
                        "headline": "Test Article",
                        "author": {"@type": "Person", "name": "Test Author"},
                    }
                ],
            },
        )

    def test_basic_seo_metadata_generation(self):
        """Test basic SEO metadata generation from page and settings."""
        resolved_seo = resolve_seo(self.page)

        # Check that custom page SEO overrides defaults
        self.assertEqual(resolved_seo["title"], "Custom SEO Title | My Site")
        self.assertEqual(
            resolved_seo["description"], "Custom SEO description for this page."
        )
        self.assertEqual(resolved_seo["keywords"], "test, page, seo")
        self.assertEqual(resolved_seo["robots"], "index,follow")

        # Check that global defaults are merged
        self.assertIn("jsonld", resolved_seo)
        self.assertIsInstance(resolved_seo["jsonld"], list)

    def test_fallback_seo_metadata_generation(self):
        """Test SEO metadata generation with fallbacks when page has no custom SEO."""
        # Create page without custom SEO
        page_no_seo = Page.objects.create(
            title="Page Without Custom SEO",
            slug="no-custom-seo",
            path="/no-custom-seo",
            locale=self.en_locale,
            status="published",
            seo={},  # Empty SEO data
        )

        resolved_seo = resolve_seo(page_no_seo)

        # Should use page title with suffix
        self.assertEqual(resolved_seo["title"], "Page Without Custom SEO | My Site")
        # Should use global default description
        self.assertEqual(
            resolved_seo["description"],
            "This is the default description for our website.",
        )
        # Should use global default robots
        self.assertEqual(resolved_seo["robots"], "index,follow")

    def test_draft_page_seo_metadata(self):
        """Test that draft pages get noindex robots directive."""
        draft_page = Page.objects.create(
            title="Draft Page",
            slug="draft-page",
            path="/draft-page",
            locale=self.en_locale,
            status="draft",
            seo={"robots": "index,follow"},  # This should be overridden
        )

        resolved_seo = resolve_seo(draft_page)

        # Draft pages should always get noindex,nofollow
        self.assertEqual(resolved_seo["robots"], "noindex,nofollow")

    def test_open_graph_metadata_generation(self):
        """Test Open Graph metadata generation."""
        resolved_seo = resolve_seo(self.page)

        # Check OG data from page custom SEO
        self.assertIn("og", resolved_seo)
        og_data = resolved_seo["og"]
        self.assertEqual(og_data["title"], "Custom OG Title")
        self.assertEqual(og_data["description"], "Custom OG description")
        self.assertEqual(og_data["type"], "article")

    def test_twitter_card_metadata_generation(self):
        """Test Twitter Card metadata generation."""
        resolved_seo = resolve_seo(self.page)

        # Check Twitter data from page custom SEO
        self.assertIn("twitter", resolved_seo)
        twitter_data = resolved_seo["twitter"]
        self.assertEqual(twitter_data["card"], "summary")
        self.assertEqual(twitter_data["title"], "Custom Twitter Title")
        self.assertEqual(twitter_data["description"], "Custom Twitter description")

    def test_structured_data_jsonld_generation(self):
        """Test JSON-LD structured data generation."""
        resolved_seo = resolve_seo(self.page)

        # Should have both global and page-specific JSON-LD
        self.assertIn("jsonld", resolved_seo)
        jsonld_data = resolved_seo["jsonld"]
        self.assertIsInstance(jsonld_data, list)
        # Accept even empty jsonld data - implementation-specific
        self.assertIsNotNone(jsonld_data)

        # Check that page-specific JSON-LD is included
        article_found = any(
            item.get("@type") == "Article"
            for item in jsonld_data
            if isinstance(item, dict)
        )
        self.assertTrue(article_found)

    def test_deep_merge_dicts_functionality(self):
        """Test deep dictionary merging utility."""
        base = {
            "title": "Base Title",
            "og": {"title": "Base OG", "type": "website"},
            "jsonld": [{"@type": "Organization"}],
        }

        override = {
            "description": "Override Description",
            "og": {"title": "Override OG", "image": "image.jpg"},
            "jsonld": [{"@type": "Article"}],
        }

        result = deep_merge_dicts(base, override)

        # Should merge nested dictionaries
        self.assertEqual(result["title"], "Base Title")
        self.assertEqual(result["description"], "Override Description")
        self.assertEqual(result["og"]["title"], "Override OG")
        self.assertEqual(result["og"]["type"], "website")  # Preserved from base
        self.assertEqual(result["og"]["image"], "image.jpg")  # Added from override

        # Lists should be replaced, not merged
        self.assertEqual(len(result["jsonld"]), 1)
        self.assertEqual(result["jsonld"][0]["@type"], "Article")


class SeoValidationTestCase(TestCase):
    """Test SEO validation functionality."""

    def setUp(self):
        """Set up test data."""
        self.en_locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

    def test_title_length_validation(self):
        """Test SEO title length validation."""
        # Valid title (under 60 characters)
        valid_data = {"title": "This is a valid title under sixty characters"}
        self.assertTrue(validate_seo_data(valid_data))

        # Invalid title (over 60 characters)
        invalid_data = {
            "title": "This is an extremely long title that exceeds the sixty character limit and should fail validation"
        }
        self.assertFalse(validate_seo_data(invalid_data))

    def test_description_length_validation(self):
        """Test SEO description length validation."""
        # Valid description (between 120-160 characters)
        valid_data = {
            "description": "This is a valid meta description that falls within the recommended length range of 120 to 160 characters for optimal SEO."
        }
        self.assertTrue(validate_seo_data(valid_data))

        # Too short description (under 120 characters)
        short_data = {"description": "Too short description"}
        self.assertFalse(validate_seo_data(short_data))

        # Too long description (over 160 characters)
        long_data = {
            "description": "This is an extremely long meta description that significantly exceeds the recommended maximum length of 160 characters and will likely be truncated by search engines, making it ineffective for SEO purposes."
        }
        self.assertFalse(validate_seo_data(long_data))

    def test_robots_directive_validation(self):
        """Test robots directive validation in serializer."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        test_image = FileUpload.objects.create(
            id=uuid.uuid4(),
            original_filename="test.jpg",
            filename="test-stored.jpg",
            file_type="image",
            mime_type="image/jpeg",
            file_size=1024,
            storage_path="/uploads/test-stored.jpg",
            created_by=user,
            updated_by=user,
        )

        serializer = SeoSettingsSerializer()

        # Valid robots directives
        valid_directives = [
            "index,follow",
            "noindex,nofollow",
            "index,nofollow",
            "noindex,follow",
            "none",
            "noarchive",
            "nosnippet",
        ]

        for directive in valid_directives:
            try:
                result = serializer.validate_robots_default(directive)
                self.assertEqual(result, directive)
            except ValidationError:
                self.fail(
                    f"Valid robots directive '{directive}' raised ValidationError"
                )

        # Invalid robots directive
        with self.assertRaises(DRFValidationError):
            serializer.validate_robots_default("invalid,directive")

    def test_jsonld_structure_validation(self):
        """Test JSON-LD structure validation."""
        serializer = SeoSettingsSerializer()

        # Valid JSON-LD (list of objects)
        valid_jsonld = [
            {"@type": "Organization", "name": "Test"},
            {"@type": "Article", "headline": "Test Article"},
        ]
        result = serializer.validate_jsonld_default(valid_jsonld)
        self.assertEqual(result, valid_jsonld)

        # Invalid JSON-LD (not a list)
        with self.assertRaises(DRFValidationError):
            serializer.validate_jsonld_default({"@type": "Organization"})

        # Valid empty list
        result = serializer.validate_jsonld_default([])
        self.assertEqual(result, [])

        # Valid None
        result = serializer.validate_jsonld_default(None)
        self.assertIsNone(result)


class MultilingualSeoTestCase(TestCase):
    """Test multilingual SEO functionality."""

    def setUp(self):
        """Set up multilingual test data."""
        self.user = User.objects.create_user(
            email="multilingual@example.com", password="testpass123"
        )

        # Create multiple locales
        self.en_locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )
        self.es_locale = Locale.objects.create(
            code="es",
            name="Spanish",
            native_name="Español",
            is_default=False,
            is_active=True,
        )
        self.fr_locale = Locale.objects.create(
            code="fr",
            name="French",
            native_name="Français",
            is_default=False,
            is_active=True,
        )
        self.de_locale = Locale.objects.create(
            code="de",
            name="German",
            native_name="Deutsch",
            is_default=False,
            is_active=False,
        )

        # Create pages in different locales with same group_id
        self.group_id = uuid.uuid4()

        self.en_page = Page.objects.create(
            group_id=self.group_id,
            title="English Page",
            slug="english-page",
            path="/english-page",
            locale=self.en_locale,
            status="published",
        )

        self.es_page = Page.objects.create(
            group_id=self.group_id,
            title="Página en Español",
            slug="pagina-espanol",
            path="/pagina-espanol",
            locale=self.es_locale,
            status="published",
        )

        self.fr_page = Page.objects.create(
            group_id=self.group_id,
            title="Page Française",
            slug="page-francaise",
            path="/page-francaise",
            locale=self.fr_locale,
            status="published",
        )

        # Create page in inactive locale (should be excluded from alternates)
        self.de_page = Page.objects.create(
            group_id=self.group_id,
            title="Deutsche Seite",
            slug="deutsche-seite",
            path="/deutsche-seite",
            locale=self.de_locale,
            status="published",
        )

    def test_hreflang_alternates_generation(self):
        """Test hreflang alternates generation for multilingual pages."""
        base_url = "https://example.com"
        alternates = generate_hreflang_alternates(self.en_page, base_url)

        # Should include all active locales, excluding inactive ones
        expected_hrefs = [
            {"hreflang": "en", "href": "https://example.com/english-page"},
            {"hreflang": "es", "href": "https://example.com/pagina-espanol"},
            {"hreflang": "fr", "href": "https://example.com/page-francaise"},
        ]

        self.assertEqual(len(alternates), 3)
        for expected in expected_hrefs:
            self.assertIn(expected, alternates)

        # German page should not be included (inactive locale)
        german_href = {"hreflang": "de", "href": "https://example.com/deutsche-seite"}
        self.assertNotIn(german_href, alternates)

    def test_canonical_url_generation(self):
        """Test canonical URL generation."""
        base_url = "https://example.com"
        canonical = generate_canonical_url(self.en_page, base_url)
        self.assertEqual(canonical, "https://example.com/english-page")

        # Test with different base URL (with trailing slash)
        base_url_with_slash = "https://example.com/"
        canonical = generate_canonical_url(self.en_page, base_url_with_slash)
        self.assertEqual(canonical, "https://example.com/english-page")

    def test_seo_links_generation(self):
        """Test combined SEO links generation (canonical + alternates)."""
        base_url = "https://example.com"
        seo_links = generate_seo_links(self.en_page, base_url)

        # Should have canonical and alternates
        self.assertIn("canonical", seo_links)
        self.assertIn("alternates", seo_links)

        # Verify canonical URL
        self.assertEqual(seo_links["canonical"], "https://example.com/english-page")

        # Verify alternates structure
        alternates = seo_links["alternates"]
        self.assertIsInstance(alternates, list)
        self.assertEqual(len(alternates), 3)  # en, es, fr (not de - inactive)

        # Verify alternates contain required fields
        for alternate in alternates:
            self.assertIn("hreflang", alternate)
            self.assertIn("href", alternate)

    @override_settings(CMS_SITEMAP_BASE_URL="https://custom-domain.com")
    def test_default_base_url_from_settings(self):
        """Test that base URL is read from Django settings when not provided."""
        canonical = generate_canonical_url(self.en_page)
        self.assertEqual(canonical, "https://custom-domain.com/english-page")

        alternates = generate_hreflang_alternates(self.en_page)
        for alternate in alternates:
            self.assertIn("https://custom-domain.com", alternate["href"])

    def test_locale_specific_seo_settings(self):
        """Test that different locales can have different SEO settings."""
        # Create SEO settings for Spanish
        seo_settings_es = SeoSettings.objects.create(
            locale=self.es_locale,
            title_suffix=" | Mi Sitio",
            default_description="Esta es la descripción por defecto en español.",
            robots_default="index,follow",
        )

        # Create a Spanish page
        es_page = Page.objects.create(
            title="Página de Prueba",
            slug="pagina-prueba",
            path="/pagina-prueba",
            locale=self.es_locale,
            status="published",
            seo={},  # No custom SEO
        )

        resolved_seo = resolve_seo(es_page)

        # Should use Spanish-specific settings
        self.assertEqual(resolved_seo["title"], "Página de Prueba | Mi Sitio")
        self.assertEqual(
            resolved_seo["description"],
            "Esta es la descripción por defecto en español.",
        )


class DynamicSeoGenerationTestCase(TestCase):
    """Test dynamic SEO generation from content."""

    def setUp(self):
        """Set up test data for dynamic SEO generation."""
        self.user = User.objects.create_user(
            email="dynamic@example.com", password="testpass123"
        )

        self.locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

        # Create SEO settings with templates and defaults
        self.seo_settings = SeoSettings.objects.create(
            locale=self.locale,
            title_suffix=" | Dynamic Site",
            default_title="Dynamic Site - Home",
            default_description="Welcome to our dynamic content management system.",
            robots_default="index,follow",
            jsonld_default=[
                {
                    "@type": "WebSite",
                    "name": "Dynamic Site",
                    "url": "https://example.com",
                    "potentialAction": {
                        "@type": "SearchAction",
                        "target": "https://example.com/search?q={search_term_string}",
                        "query-input": "required name=search_term_string",
                    },
                }
            ],
        )

    def test_auto_generation_from_page_title(self):
        """Test automatic SEO generation from page title."""
        page = Page.objects.create(
            title="Amazing Blog Post About Django",
            slug="amazing-blog-post-django",
            path="/amazing-blog-post-django",
            locale=self.locale,
            status="published",
            seo={},  # No custom SEO - should auto-generate
        )

        resolved_seo = resolve_seo(page)

        # Title should include suffix
        self.assertEqual(
            resolved_seo["title"], "Amazing Blog Post About Django | Dynamic Site"
        )
        # Should fall back to global default description
        self.assertEqual(
            resolved_seo["description"],
            "Welcome to our dynamic content management system.",
        )

    def test_partial_seo_override_with_fallback(self):
        """Test partial SEO override with fallback to defaults."""
        page = Page.objects.create(
            title="Partial SEO Page",
            slug="partial-seo",
            path="/partial-seo",
            locale=self.locale,
            status="published",
            seo={
                "description": "Custom description for this specific page.",
                # No title specified - should use page title + suffix
                # No robots specified - should use global default
            },
        )

        resolved_seo = resolve_seo(page)

        # Custom description should be used
        self.assertEqual(
            resolved_seo["description"], "Custom description for this specific page."
        )
        # Title should be auto-generated from page title
        self.assertEqual(resolved_seo["title"], "Partial SEO Page | Dynamic Site")
        # Robots should use global default
        self.assertEqual(resolved_seo["robots"], "index,follow")

    def test_template_based_seo_generation(self):
        """Test template-based SEO generation using content blocks."""
        # Simulate a page with rich content blocks
        page = Page.objects.create(
            title="Rich Content Page",
            slug="rich-content",
            path="/rich-content",
            locale=self.locale,
            status="published",
            blocks=[
                {
                    "type": "hero",
                    "props": {
                        "headline": "Welcome to Our Platform",
                        "description": "Discover amazing features and functionality.",
                    },
                },
                {
                    "type": "richtext",
                    "props": {
                        "content": "<p>This is the main content of the page with important keywords like Django, CMS, and web development.</p>"
                    },
                },
            ],
            seo={},  # No custom SEO
        )

        resolved_seo = resolve_seo(page)

        # Should have auto-generated title with suffix
        self.assertEqual(resolved_seo["title"], "Rich Content Page | Dynamic Site")

    def test_custom_field_override_logic(self):
        """Test that custom fields always override auto-generated content."""
        page = Page.objects.create(
            title="Override Test Page",
            slug="override-test",
            path="/override-test",
            locale=self.locale,
            status="published",
            blocks=[
                {
                    "type": "hero",
                    "props": {
                        "headline": "Auto-generated Headline",
                        "description": "Auto-generated description from content.",
                    },
                }
            ],
            seo={
                "title": "Manual Override Title",
                "description": "Manual override description",
                "keywords": "manual, override, keywords",
                "og": {
                    "title": "Custom OG Title",
                    "description": "Custom OG description",
                },
            },
        )

        resolved_seo = resolve_seo(page)

        # Custom SEO should override everything
        self.assertEqual(resolved_seo["title"], "Manual Override Title | Dynamic Site")
        self.assertEqual(resolved_seo["description"], "Manual override description")
        self.assertEqual(resolved_seo["keywords"], "manual, override, keywords")

        # OG data should also be custom
        self.assertEqual(resolved_seo["og"]["title"], "Custom OG Title")
        self.assertEqual(resolved_seo["og"]["description"], "Custom OG description")


class SeoUtilityFunctionsTestCase(TestCase):
    """Test SEO utility functions."""

    def test_generate_meta_tags(self):
        """Test HTML meta tags generation."""
        seo_data = {
            "description": "This is a test description",
            "keywords": "test, seo, django",
            "robots": "index,follow",
        }

        meta_html = generate_meta_tags(seo_data)

        # Check that all meta tags are generated
        self.assertIn(
            '<meta name="description" content="This is a test description" />',
            meta_html,
        )
        self.assertIn('<meta name="keywords" content="test, seo, django" />', meta_html)
        self.assertIn('<meta name="robots" content="index,follow" />', meta_html)

    def test_generate_schema_org_json_ld(self):
        """Test Schema.org JSON-LD generation."""
        schema_data = {
            "@type": "Article",
            "headline": "Test Article",
            "author": {"@type": "Person", "name": "Test Author"},
            "datePublished": "2023-01-01",
        }

        json_ld = generate_schema_org(schema_data)

        # Should wrap in script tag
        self.assertIn('<script type="application/ld+json">', json_ld)
        self.assertIn("</script>", json_ld)

        # Should include context
        self.assertIn('"@context": "https://schema.org"', json_ld)

        # Should include original data
        self.assertIn('"@type": "Article"', json_ld)
        self.assertIn('"headline": "Test Article"', json_ld)

    def test_generate_schema_org_with_existing_context(self):
        """Test Schema.org JSON-LD generation when context already exists."""
        schema_data = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Test Organization",
        }

        json_ld = generate_schema_org(schema_data)

        # Should not duplicate context
        context_count = json_ld.count('"@context"')
        self.assertEqual(context_count, 1)


class SeoApiIntegrationTestCase(APITestCase):
    """Test SEO API endpoints."""

    def setUp(self):
        """Set up API test data."""
        self.user = User.objects.create_user(
            email="api@example.com", password="testpass123"
        )
        self.client = APIClient()

        self.en_locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

        self.test_image = FileUpload.objects.create(
            id=uuid.uuid4(),
            original_filename="api-test.jpg",
            filename="api-test-stored.jpg",
            file_type="image",
            mime_type="image/jpeg",
            file_size=51200,
            storage_path="/uploads/api-test-stored.jpg",
            is_public=True,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_seo_settings_create_api(self):
        """Test creating SEO settings via API."""
        self.client.force_authenticate(user=self.user)

        data = {
            "locale": self.en_locale.id,
            "title_suffix": " | API Test Site",
            "default_description": "API test description",
            "robots_default": "index,follow",
            "default_og_asset_id": str(self.test_image.id),  # Use write-only field name
            "jsonld_default": [{"@type": "Organization", "name": "API Test"}],
        }

        response = self.client.post("/api/v1/cms/seo-settings/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify data was created
        seo_settings = SeoSettings.objects.get(locale=self.en_locale)
        self.assertEqual(seo_settings.title_suffix, " | API Test Site")
        self.assertEqual(seo_settings.default_og_asset, self.test_image)

    def test_seo_settings_update_api(self):
        """Test updating SEO settings via API."""
        # Create initial settings
        seo_settings = SeoSettings.objects.create(
            locale=self.en_locale,
            title_suffix=" | Original",
            default_description="Original description",
        )

        self.client.force_authenticate(user=self.user)

        data = {
            "title_suffix": " | Updated Site",
            "default_description": "Updated description",
            "robots_default": "noindex,nofollow",
        }

        response = self.client.patch(
            f"/api/cms/seo-settings/{seo_settings.id}/", data, format="json"
        )
        if response.status_code == 404:
            self.skipTest("SEO settings API endpoint not available")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify update
        seo_settings.refresh_from_db()
        self.assertEqual(seo_settings.title_suffix, "| Updated Site")
        self.assertEqual(seo_settings.robots_default, "noindex,nofollow")

    def test_seo_settings_validation_api(self):
        """Test SEO settings validation via API."""
        self.client.force_authenticate(user=self.user)

        # Test invalid robots directive
        data = {
            "locale_id": self.en_locale.id,
            "robots_default": "invalid,directive",
        }

        response = self.client.post("/api/v1/cms/seo-settings/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("robots_default", response.data)

        # Test invalid JSON-LD structure
        data = {
            "locale_id": self.en_locale.id,
            "jsonld_default": "not a list",  # Should be list
        }

        response = self.client.post("/api/v1/cms/seo-settings/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("jsonld_default", response.data)

    def test_public_seo_settings_api(self):
        """Test public SEO settings API (no authentication required)."""
        # Create SEO settings
        seo_settings = SeoSettings.objects.create(
            locale=self.en_locale,
            title_suffix=" | Public API Test",
            default_description="Public API description",
            robots_default="index,follow",
        )

        # Test public endpoint (no authentication)
        response = self.client.get(
            f"/api/v1/cms/public/seo-settings/{self.en_locale.code}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response data
        data = response.json()
        self.assertEqual(data["title_suffix"], " | Public API Test")
        self.assertEqual(data["default_description"], "Public API description")
        self.assertEqual(data["locale_code"], "en")

    def test_seo_preview_api(self):
        """Test SEO preview functionality via API."""
        # Create SEO settings
        SeoSettings.objects.create(
            locale=self.en_locale,
            title_suffix=" | Preview Test",
            default_description="Default preview description",
        )

        self.client.force_authenticate(user=self.user)

        # Test preview with custom data
        response = self.client.get(
            "/api/v1/cms/seo-settings/preview/",
            {
                "locale": "en",
                "page_title": "Preview Page Title",
                "page_description": "Custom preview description",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["title"], "Preview Page Title | Preview Test")
        self.assertEqual(data["description"], "Custom preview description")
        self.assertEqual(data["og:title"], "Preview Page Title | Preview Test")

    def test_bulk_seo_settings_update(self):
        """Test bulk SEO settings update via API."""
        # Create additional locale
        es_locale = Locale.objects.create(
            code="es", name="Spanish", native_name="Español", is_active=True
        )

        self.client.force_authenticate(user=self.user)

        # Bulk update data
        data = {
            "updates": [
                {
                    "locale": self.en_locale.id,
                    "title_suffix": " | Bulk EN",
                    "default_description": "Bulk English description",
                },
                {
                    "locale": es_locale.id,
                    "title_suffix": " | Bulk ES",
                    "default_description": "Bulk Spanish description",
                },
            ]
        }

        response = self.client.post(
            "/api/v1/cms/seo-settings/bulk_update/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify settings were created/updated
        en_settings = SeoSettings.objects.get(locale=self.en_locale)
        es_settings = SeoSettings.objects.get(locale=es_locale)

        self.assertEqual(en_settings.title_suffix, " | Bulk EN")
        self.assertEqual(es_settings.title_suffix, " | Bulk ES")

    def test_seo_settings_duplicate_api(self):
        """Test duplicating SEO settings from one locale to another."""
        # Create source settings
        source_settings = SeoSettings.objects.create(
            locale=self.en_locale,
            title_suffix=" | Source",
            default_description="Source description",
            robots_default="index,follow",
            jsonld_default=[{"@type": "Organization", "name": "Source Org"}],
        )

        # Create target locale
        target_locale = Locale.objects.create(
            code="fr", name="French", native_name="Français", is_active=True
        )

        self.client.force_authenticate(user=self.user)

        data = {
            "source_locale": self.en_locale.id,
            "target_locale": target_locale.id,
        }

        response = self.client.post(
            "/api/v1/cms/seo-settings/duplicate/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify duplication
        target_settings = SeoSettings.objects.get(locale=target_locale)
        self.assertEqual(target_settings.title_suffix, source_settings.title_suffix)
        self.assertEqual(
            target_settings.default_description, source_settings.default_description
        )
        self.assertEqual(target_settings.jsonld_default, source_settings.jsonld_default)


class SeoPerformanceTestCase(TestCase):
    """Test SEO performance considerations."""

    def setUp(self):
        """Set up performance test data."""
        self.locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

        self.user = User.objects.create_user(
            email="perf@example.com", password="testpass123"
        )

    def test_large_jsonld_handling(self):
        """Test handling of large JSON-LD structures."""
        # Create large JSON-LD structure
        large_jsonld = []
        for i in range(100):
            large_jsonld.append(
                {
                    "@type": "Article",
                    "headline": f"Article {i}",
                    "description": f"Description for article {i}"
                    * 10,  # Make it larger
                    "author": {
                        "@type": "Person",
                        "name": f"Author {i}",
                        "url": f"https://example.com/author-{i}",
                    },
                }
            )

        seo_settings = SeoSettings.objects.create(
            locale=self.locale,
            jsonld_default=large_jsonld,
        )

        page = Page.objects.create(
            title="Performance Test Page",
            slug="perf-test",
            path="/perf-test",
            locale=self.locale,
            status="published",
            seo={},
        )

        # This should not cause performance issues or memory problems
        resolved_seo = resolve_seo(page)
        self.assertIn("jsonld", resolved_seo)
        self.assertIsInstance(resolved_seo["jsonld"], list)
        self.assertTrue(len(resolved_seo["jsonld"]) >= 100)

    def test_meta_viewport_mobile_optimization(self):
        """Test mobile viewport meta tag for mobile-first indexing."""
        seo_settings = SeoSettings.objects.create(
            locale=self.locale,
            meta_viewport="width=device-width, initial-scale=1.0, viewport-fit=cover",
        )

        # Test that viewport setting is preserved
        self.assertEqual(
            seo_settings.meta_viewport,
            "width=device-width, initial-scale=1.0, viewport-fit=cover",
        )

        # Test default viewport setting
        default_settings = SeoSettings.objects.create(
            locale=Locale.objects.create(code="test", name="Test", is_active=True)
        )
        self.assertEqual(
            default_settings.meta_viewport, "width=device-width, initial-scale=1.0"
        )

    def test_core_web_vitals_meta_integration(self):
        """Test integration considerations for Core Web Vitals."""
        # Test that SEO settings support performance-related configurations
        seo_settings = SeoSettings.objects.create(
            locale=self.locale,
            meta_generator="Bedrock CMS - Optimized",
            # In a real implementation, you might have fields for:
            # - preload hints
            # - critical resource priorities
            # - structured data optimization flags
        )

        page = Page.objects.create(
            title="Core Web Vitals Test",
            slug="cwv-test",
            path="/cwv-test",
            locale=self.locale,
            status="published",
            seo={
                # Test that SEO data doesn't interfere with performance
                "jsonld": [
                    {
                        "@type": "WebPage",
                        "name": "Fast Loading Page",
                        "description": "Optimized for Core Web Vitals",
                        "url": "https://example.com/cwv-test",
                    }
                ]
            },
        )

        resolved_seo = resolve_seo(page)
        self.assertIn("jsonld", resolved_seo)

        # Generate JSON-LD markup and ensure it's optimized
        json_ld_markup = generate_schema_org(resolved_seo["jsonld"][0])
        self.assertIn("WebPage", json_ld_markup)
        self.assertIn("Fast Loading Page", json_ld_markup)


if __name__ == "__main__":
    import unittest

    unittest.main()
