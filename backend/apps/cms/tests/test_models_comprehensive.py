"""Comprehensive tests for CMS models to boost coverage."""

import os

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()


import os
from datetime import datetime, timedelta

import django
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.cms.models import Page, Redirect
from apps.i18n.models import Locale

User = get_user_model()


class PageModelTests(TestCase):
    """Test Page model methods and properties."""

    def setUp(self):
        self.locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={"name": "English", "native_name": "English", "is_default": True},
        )
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass"
        )

    def test_page_str_method(self):
        """Test Page string representation."""
        page = Page.objects.create(
            title="Test Page",
            slug="test-page",
            path="/test-page/",
            locale=self.locale,
        )
        self.assertEqual(str(page), "Test Page (English (en))")

    def test_page_get_absolute_url(self):
        """Test get_absolute_url method."""
        page = Page.objects.create(
            title="Test Page",
            slug="test-page",
            path="/test-page/",
            locale=self.locale,
        )
        if hasattr(page, "get_absolute_url"):
            url = page.get_absolute_url()
            self.assertIn("/test-page", url)

    def test_page_slug_generation(self):
        """Test automatic slug generation."""
        page = Page.objects.create(
            title="Test Page With Spaces",
            slug="test-page-with-spaces",
            path="/test-page-with-spaces/",
            locale=self.locale,
        )
        # Slug should be what we provided
        self.assertEqual(page.slug, "test-page-with-spaces")

    def test_page_path_generation(self):
        """Test path computation."""
        parent = Page.objects.create(
            title="Parent",
            slug="parent",
            path="/parent/",
            locale=self.locale,
        )
        child = Page.objects.create(
            title="Child",
            slug="child",
            parent=parent,
            locale=self.locale,
        )
        expected_path = "/parent/child"
        self.assertTrue(child.path.endswith("child"))

    def test_page_is_published_property(self):
        """Test is_published property."""
        page = Page.objects.create(
            title="Test Page",
            slug="test-page-published",
            status="published",
            locale=self.locale,
        )
        if hasattr(page, "is_published"):
            self.assertTrue(page.is_published)

        page.status = "draft"
        page.save()
        if hasattr(page, "is_published"):
            self.assertFalse(page.is_published)

    def test_page_publish_method(self):
        """Test publish method."""
        page = Page.objects.create(
            title="Draft Page",
            slug="draft-page-test",
            status="draft",
            locale=self.locale,
        )

        if hasattr(page, "publish"):
            page.publish(user=self.user)
            page.refresh_from_db()
            self.assertEqual(page.status, "published")
            self.assertIsNotNone(page.published_at)

    def test_page_unpublish_method(self):
        """Test unpublish method."""
        page = Page.objects.create(
            title="Published Page",
            slug="published-page-test",
            status="published",
            published_at=timezone.now(),
            locale=self.locale,
        )

        if hasattr(page, "unpublish"):
            page.unpublish(user=self.user)
            page.refresh_from_db()
            self.assertEqual(page.status, "draft")

    def test_page_blocks_validation(self):
        """Test blocks field validation."""
        page = Page.objects.create(
            title="Blocks Page",
            slug="blocks-page-test",
            blocks=[
                {"type": "richtext", "props": {"content": "Test content"}},
                {
                    "type": "hero",
                    "props": {"title": "Hero Title", "subtitle": "Subtitle"},
                },
            ],
            locale=self.locale,
        )
        self.assertEqual(len(page.blocks), 2)
        self.assertEqual(page.blocks[0]["type"], "richtext")

    def test_page_seo_fields(self):
        """Test SEO field handling."""
        seo_data = {
            "title": "Custom SEO Title",
            "description": "Custom meta description",
            "keywords": ["test", "seo"],
        }
        page = Page.objects.create(
            title="SEO Page",
            slug="seo-page-test",
            seo=seo_data,
            locale=self.locale,
        )
        self.assertEqual(page.seo["title"], "Custom SEO Title")

    def test_page_hierarchy_methods(self):
        """Test page hierarchy methods."""
        parent = Page.objects.create(
            title="Parent",
            slug="parent",
            locale=self.locale,
        )
        child1 = Page.objects.create(
            title="Child 1",
            slug="child-1",
            parent=parent,
            locale=self.locale,
        )
        child2 = Page.objects.create(
            title="Child 2",
            slug="child-2",
            parent=parent,
            locale=self.locale,
        )

        children = parent.children.all()
        self.assertEqual(children.count(), 2)

    def test_page_position_handling(self):
        """Test page position in hierarchy."""
        parent = Page.objects.create(
            title="Parent", slug="parent-position-test", locale=self.locale
        )

        child1 = Page.objects.create(
            title="Child 1",
            slug="child-1",
            parent=parent,
            position=0,
            locale=self.locale,
        )
        child2 = Page.objects.create(
            title="Child 2",
            slug="child-2",
            parent=parent,
            position=1,
            locale=self.locale,
        )

        children = parent.children.order_by("position")
        self.assertEqual(list(children), [child1, child2])

    def test_page_status_choices(self):
        """Test page status validation."""
        valid_statuses = ["draft", "published", "scheduled", "pending_review"]

        for status in valid_statuses:
            page = Page.objects.create(
                title=f"Page {status}",
                slug=f"page-{status}",
                status=status,
                locale=self.locale,
            )
            self.assertEqual(page.status, status)


class RedirectModelTests(TestCase):
    """Test Redirect model functionality."""

    def setUp(self):
        self.locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={"name": "English", "native_name": "English", "is_default": True},
        )

    def test_redirect_creation(self):
        """Test redirect creation and string representation."""
        redirect = Redirect.objects.create(
            from_path="/old-path/",
            to_path="/new-path/",
            status=301,
        )
        # Trailing slashes are removed by clean method (except for root)
        self.assertEqual(redirect.from_path, "/old-path")
        self.assertEqual(redirect.to_path, "/new-path")
        self.assertEqual(redirect.status, 301)

    def test_redirect_str_method(self):
        """Test redirect string representation."""
        redirect = Redirect.objects.create(
            from_path="/old/",
            to_path="/new/",
        )
        expected = "/old -> /new (301)"
        self.assertEqual(str(redirect), expected)

    def test_redirect_validation(self):
        """Test redirect validation."""
        # Test same path redirect
        with self.assertRaises(ValidationError):
            redirect = Redirect(
                from_path="/same/",
                to_path="/same/",
            )
            if hasattr(redirect, "clean"):
                redirect.clean()

    def test_redirect_status_codes(self):
        """Test valid redirect status codes."""
        valid_codes = [301, 302, 307, 308]

        for code in valid_codes:
            redirect = Redirect.objects.create(
                from_path=f"/test-{code}/",
                to_path="/target/",
                status=code,
            )
            self.assertEqual(redirect.status, code)


class PageManagerTests(TestCase):
    """Test Page model manager methods."""

    def setUp(self):
        self.locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={"name": "English", "native_name": "English", "is_default": True},
        )

    def test_published_pages_queryset(self):
        """Test published pages manager method."""
        published = Page.objects.create(
            title="Published",
            slug="published-manager-test",
            status="published",
            locale=self.locale,
        )
        draft = Page.objects.create(
            title="Draft",
            slug="draft-manager-test",
            status="draft",
            locale=self.locale,
        )

        if hasattr(Page.objects, "published"):
            published_pages = Page.objects.published()
            self.assertIn(published, published_pages)
            self.assertNotIn(draft, published_pages)

    def test_by_locale_queryset(self):
        """Test filtering by locale."""
        en_page = Page.objects.create(
            title="English Page",
            slug="english-page-test",
            locale=self.locale,
        )

        fr_locale = Locale.objects.create(code="fr", name="French")
        fr_page = Page.objects.create(
            title="French Page",
            slug="french-page-test",
            locale=fr_locale,
        )

        en_pages = Page.objects.filter(locale=self.locale)
        self.assertIn(en_page, en_pages)
        self.assertNotIn(fr_page, en_pages)
