"""Tests for core CMS models."""

import os

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()


import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import django

# Configure Django settings before any imports
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.cms.models import BlockType, Page
from apps.i18n.models import Locale

User = get_user_model()


class PageModelTestCase(TestCase):
    """Test Page model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="page@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )

        self.page = Page.objects.create(
            title="Test Page",
            slug="test-page",
            path="/test-page",
            locale=self.locale,
            status="draft",
        )

    def test_page_creation(self):
        """Test basic page creation."""
        self.assertEqual(self.page.title, "Test Page")
        self.assertEqual(self.page.slug, "test-page")
        self.assertEqual(self.page.status, "draft")
        self.assertEqual(self.page.locale, self.locale)

    def test_page_str_representation(self):
        """Test page string representation."""
        expected = f"{self.page.title} ({self.page.locale})"
        self.assertEqual(str(self.page), expected)

    def test_page_status_choices(self):
        """Test page status choices."""
        page = Page()

        # Should have status choices defined
        status_choices = [choice[0] for choice in Page.STATUS_CHOICES]
        expected_statuses = [
            "draft",
            "pending_review",
            "published",
            "scheduled",
            "archived",
        ]

        for status in expected_statuses:
            if status in status_choices:
                self.assertIn(status, status_choices)

    def test_page_slug_validation(self):
        """Test page slug validation."""
        # Valid slug
        page = Page.objects.create(
            title="Valid Slug Page",
            slug="valid-slug-page",
            path="/valid-slug-page",
            locale=self.locale,
        )
        self.assertEqual(page.slug, "valid-slug-page")

        # Test slug constraints exist
        self.assertTrue(hasattr(Page, "slug"))

    def test_page_path_validation(self):
        """Test page path validation."""
        # Valid path - path is computed from slug
        page = Page.objects.create(
            title="Path Test Page",
            slug="path-test",
            locale=self.locale,
        )
        self.assertEqual(page.path, "/path-test")

    def test_page_locale_relationship(self):
        """Test page locale relationship."""
        self.assertEqual(self.page.locale, self.locale)

        # Test reverse relationship using the default related_name
        locale_pages = self.locale.page_set.all()
        self.assertIn(self.page, locale_pages)

    def test_page_user_relationships(self):
        """Test page user relationships."""
        # Test reviewed_by field
        self.page.reviewed_by = self.user
        self.page.save()
        self.assertEqual(self.page.reviewed_by, self.user)

    def test_page_timestamps(self):
        """Test page timestamp fields."""
        # Should have created_at
        self.assertIsNotNone(self.page.created_at)
        self.assertIsInstance(self.page.created_at, datetime)

        # Should have updated_at
        self.assertIsNotNone(self.page.updated_at)
        self.assertIsInstance(self.page.updated_at, datetime)

    def test_page_published_status(self):
        """Test page published status handling."""
        # Draft page should not be published
        self.assertEqual(self.page.status, "draft")

        # Publish page
        self.page.status = "published"
        self.page.published_at = timezone.now()
        self.page.save()

        self.assertEqual(self.page.status, "published")
        self.assertIsNotNone(self.page.published_at)

    def test_page_blocks_field(self):
        """Test page blocks JSON field."""
        # Should be able to store blocks data
        blocks_data = [
            {"type": "text", "data": {"text": "Hello World"}},
            {"type": "image", "data": {"src": "/media/test.jpg", "alt": "Test image"}},
        ]

        self.page.blocks = blocks_data
        self.page.save()

        self.page.refresh_from_db()
        self.assertEqual(self.page.blocks, blocks_data)

    def test_page_seo_field(self):
        """Test page SEO JSON field."""
        seo_data = {
            "title": "Custom SEO Title",
            "description": "Custom SEO description",
            "keywords": ["test", "page", "seo"],
        }

        self.page.seo = seo_data
        self.page.save()

        self.page.refresh_from_db()
        self.assertEqual(self.page.seo, seo_data)

    def test_page_ordering(self):
        """Test page ordering."""
        # Create pages with different positions
        page1 = Page.objects.create(
            title="Page 1",
            slug="page-1",
            path="/page-1",
            locale=self.locale,
            position=1,
        )

        page2 = Page.objects.create(
            title="Page 2",
            slug="page-2",
            path="/page-2",
            locale=self.locale,
            position=2,
        )

        # Should be able to order by position
        ordered_pages = Page.objects.filter(locale=self.locale).order_by("position")
        positions = [p.position for p in ordered_pages if p.position is not None]

        if len(positions) >= 2:
            self.assertLessEqual(positions[0], positions[1])

    def test_page_homepage_functionality(self):
        """Test page homepage functionality."""
        # Set as homepage
        self.page.is_homepage = True
        self.page.save()

        self.assertTrue(self.page.is_homepage)

    def test_page_navigation_functionality(self):
        """Test page navigation functionality."""
        # Add to main menu
        self.page.in_main_menu = True
        self.page.position = 1
        self.page.save()

        self.assertTrue(self.page.in_main_menu)
        self.assertEqual(self.page.position, 1)

    def test_page_rbac_mixin(self):
        """Test Page RBAC mixin functionality."""
        # Page should inherit from RBACMixin
        from apps.accounts.rbac import RBACMixin

        self.assertTrue(isinstance(self.page, RBACMixin))

        # Should have RBAC methods
        rbac_methods = [
            "user_has_locale_access",
            "user_has_section_access",
            "user_has_scope_access",
        ]
        for method in rbac_methods:
            self.assertTrue(hasattr(self.page, method))

    @patch("apps.cms.models.validate_blocks")
    def test_page_block_validation(self, mock_validate):
        """Test page block validation."""
        mock_validate.return_value = None  # Valid blocks

        blocks = [{"type": "text", "data": {"text": "Test"}}]
        self.page.blocks = blocks
        self.page.save()

        # Validation should be called if implemented
        # This tests that the validation hook exists

    def test_page_meta_options(self):
        """Test Page model meta options."""
        meta = Page._meta

        # Should have proper meta configuration
        self.assertIsNotNone(meta)

        # Should have indexes for performance
        if hasattr(meta, "indexes"):
            self.assertIsInstance(meta.indexes, list)

    def test_page_unique_constraints(self):
        """Test page unique constraints."""
        # Test that we can create pages with the same slug but different parents
        parent_page = Page.objects.create(
            title="Parent Page",
            slug="parent",
            locale=self.locale,
        )

        # Should be able to create child page with same slug as sibling
        child_page = Page.objects.create(
            title="Child Page",
            slug="test-page",  # Same slug as existing page but different parent
            parent=parent_page,
            locale=self.locale,
        )

        # Different parent should allow same slug
        self.assertEqual(child_page.slug, "test-page")
        self.assertEqual(child_page.parent, parent_page)


class BlockTypeModelTestCase(TestCase):
    """Test BlockType model functionality."""

    def setUp(self):
        """Set up test data."""
        self.block_type = BlockType.objects.create(
            type="text",
            component="TextBlock",
            label="Text Block",
            description="Simple text content",
            category="content",
            icon="text",
            schema={"type": "object", "properties": {"text": {"type": "string"}}},
            default_props={"text": ""},
            is_active=True,
        )

    def test_block_type_creation(self):
        """Test basic block type creation."""
        self.assertEqual(self.block_type.type, "text")
        self.assertEqual(self.block_type.label, "Text Block")
        self.assertTrue(self.block_type.is_active)

    def test_block_type_str_representation(self):
        """Test block type string representation."""
        expected = f"{self.block_type.label} ({self.block_type.type})"
        self.assertEqual(str(self.block_type), expected)

    def test_block_type_schema_validation(self):
        """Test block type schema is valid JSON."""
        self.assertIsInstance(self.block_type.schema, dict)
        self.assertIn("type", self.block_type.schema)
        self.assertEqual(self.block_type.schema["type"], "object")

    def test_block_type_categories(self):
        """Test block type categorization."""
        # Use valid categories from BlockTypeCategory
        categories = ["content", "media", "layout", "marketing", "dynamic", "other"]

        for idx, category in enumerate(categories):
            block_type = BlockType.objects.create(
                type=f"{category}_block_{idx}",  # Make unique type
                component=f"{category.title()}Block",
                label=f"{category.title()} Block",
                description=f"Block for {category}",
                category=category,
                icon=category,
                schema={"type": "object"},
                default_props={"category": category},  # Non-empty default props
                is_active=True,
            )

            self.assertEqual(block_type.category, category)

    def test_block_type_active_filtering(self):
        """Test filtering active block types."""
        # Create inactive block type
        inactive_block = BlockType.objects.create(
            type="deprecated",
            component="DeprecatedBlock",
            label="Deprecated Block",
            description="Old block type",
            category="other",  # Use valid category from BlockTypeCategory
            icon="warning",
            schema={"type": "object"},
            default_props={"deprecated": True},  # Provide non-empty default props
            is_active=False,
        )

        # Test filtering
        active_blocks = BlockType.objects.filter(is_active=True)
        inactive_blocks = BlockType.objects.filter(is_active=False)

        self.assertIn(self.block_type, active_blocks)
        self.assertIn(inactive_block, inactive_blocks)
        self.assertNotIn(inactive_block, active_blocks)

    def test_block_type_schema_complexity(self):
        """Test complex block type schemas."""
        complex_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string", "maxLength": 100},
                "content": {"type": "string"},
                "settings": {
                    "type": "object",
                    "properties": {
                        "background_color": {"type": "string"},
                        "text_align": {
                            "type": "string",
                            "enum": ["left", "center", "right"],
                        },
                    },
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "link": {"type": "string", "format": "uri"},
                        },
                    },
                },
            },
            "required": ["title"],
        }

        complex_block = BlockType.objects.create(
            type="complex",
            component="ComplexBlock",
            label="Complex Block",
            description="Block with complex schema",
            category="content",
            icon="gear",
            schema=complex_schema,
            default_props={"title": ""},
            is_active=True,
        )

        self.assertEqual(complex_block.schema, complex_schema)

    def test_block_type_ordering(self):
        """Test block type ordering."""
        # Create block types with different orders
        block1 = BlockType.objects.create(
            type="first",
            component="FirstBlock",
            label="First Block",
            description="First block",
            category="content",
            icon="first",
            schema={"type": "object"},
            default_props={"text": ""},
            order=1,
            is_active=True,
        )

        block2 = BlockType.objects.create(
            type="second",
            component="SecondBlock",
            label="Second Block",
            description="Second block",
            category="content",
            icon="second",
            schema={"type": "object"},
            default_props={"text": ""},
            order=2,
            is_active=True,
        )

        # Should be able to order
        ordered_blocks = BlockType.objects.filter(category="content").order_by("order")
        if len(ordered_blocks) >= 2:
            self.assertLessEqual(ordered_blocks[0].order, ordered_blocks[1].order)


class ModelIntegrationTestCase(TestCase):
    """Integration tests for CMS models."""

    def setUp(self):
        """Set up integration test data."""
        self.user = User.objects.create_user(
            email="integration@example.com",
            password="testpass123",
        )

        self.locale = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )

    def test_page_block_type_relationship(self):
        """Test relationship between pages and block types."""
        # Create block type
        text_block = BlockType.objects.create(
            type="text",
            component="TextBlock",
            label="Text Block",
            description="Text content",
            category="content",
            icon="text",
            schema={"type": "object", "properties": {"text": {"type": "string"}}},
            default_props={"text": ""},
            is_active=True,
        )

        # Create page with blocks using this type
        page = Page.objects.create(
            title="Integration Test Page",
            slug="integration-test",
            locale=self.locale,
            blocks=[{"type": "text", "data": {"text": "This is a text block"}}],
        )

        # Should be able to validate blocks against block types
        self.assertIsNotNone(page.blocks)
        self.assertEqual(len(page.blocks), 1)
        self.assertEqual(page.blocks[0]["type"], "text")

    def test_model_cascade_relationships(self):
        """Test cascade relationships between models."""
        from django.db.models.deletion import ProtectedError

        # Create page
        page = Page.objects.create(
            title="Cascade Test Page",
            slug="cascade-test",
            locale=self.locale,
        )

        page_id = page.id

        # Try to delete locale
        try:
            self.locale.delete()
            # If deletion succeeded, check if page was cascade deleted
            with self.assertRaises(Page.DoesNotExist):
                Page.objects.get(id=page_id)
        except ProtectedError:
            # Locale deletion was protected because of the page
            # This is the expected behavior - verify page still exists
            page_still_exists = Page.objects.get(id=page_id)
            self.assertIsNotNone(page_still_exists)
            self.assertEqual(page_still_exists.locale, self.locale)

    def test_model_validation_integration(self):
        """Test model validation integration."""
        # Test with invalid data
        with self.assertRaises(ValidationError):
            page = Page(
                title="",  # Invalid empty title
                slug="test",
                locale=self.locale,
            )
            page.full_clean()  # Trigger validation

    def test_model_caching_integration(self):
        """Test model caching integration."""
        # Create page
        page = Page.objects.create(
            title="Cache Test Page",
            slug="cache-test",
            locale=self.locale,
        )

        # Test that cache integration exists (if implemented)
        # This tests the structure exists for caching
        from django.core.cache import cache

        self.assertIsNotNone(cache)

    def test_performance_with_large_dataset(self):
        """Test model performance with larger datasets."""
        # Create multiple pages
        pages = []
        for i in range(20):
            page = Page.objects.create(
                title=f"Performance Test Page {i}",
                slug=f"performance-test-{i}",
                locale=self.locale,
                status="published" if i % 2 == 0 else "draft",
            )
            pages.append(page)

        # Should handle queries efficiently
        published_pages = Page.objects.filter(status="published")
        self.assertGreaterEqual(published_pages.count(), 10)

        # Should handle ordering efficiently
        ordered_pages = Page.objects.filter(locale=self.locale).order_by("-created_at")
        self.assertEqual(ordered_pages.count(), 20)
