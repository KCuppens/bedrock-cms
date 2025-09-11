"""
Simple CMS Views tests to start building coverage.

Basic tests for CMS views without complex factory dependencies.
"""

import json
from datetime import datetime, timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.cms.models import Page
from apps.cms.views import PagesViewSet
from apps.i18n.models import Locale

User = get_user_model()


class PagesViewSetBasicTestCase(APITestCase):
    """Basic tests for PagesViewSet core functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create locale
        self.locale_en = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        # Create users
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )

        self.regular_user = User.objects.create_user(
            email="user@example.com", password="testpass123"
        )

        # Create test pages
        self.published_page = Page.objects.create(
            title="Published Page",
            slug="published-page",
            path="/published-page/",
            locale=self.locale_en,
            status="published",
            blocks=[{"type": "text", "props": {"content": "Test content"}}],
        )

        self.draft_page = Page.objects.create(
            title="Draft Page",
            slug="draft-page",
            path="/draft-page/",
            locale=self.locale_en,
            status="draft",
            blocks=[{"type": "text", "props": {"content": "Draft content"}}],
        )

    def test_get_queryset_optimization(self):
        """Test that queryset is properly optimized."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/cms/api/pages/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("results", data)
        self.assertGreater(len(data["results"]), 0)

    def test_get_serializer_class_selection(self):
        """Test serializer class selection based on action."""
        viewset = PagesViewSet()

        # Read actions should use PageReadSerializer
        viewset.action = "list"
        serializer_class = viewset.get_serializer_class()
        self.assertEqual(serializer_class.__name__, "PageReadSerializer")

        # Write actions should use PageWriteSerializer
        viewset.action = "create"
        serializer_class = viewset.get_serializer_class()
        self.assertEqual(serializer_class.__name__, "PageWriteSerializer")

    def test_get_by_path_success(self):
        """Test successful page retrieval by path."""
        response = self.client.get(
            "/api/v1/cms/api/pages/get_by_path/",
            {"path": "/published-page/", "locale": "en"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["title"], "Published Page")
        self.assertEqual(data["slug"], "published-page")

    def test_get_by_path_missing_path_parameter(self):
        """Test error when path parameter is missing."""
        response = self.client.get(
            "/api/v1/cms/api/pages/get_by_path/", {"locale": "en"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["error"], "Path parameter is required")

    def test_get_by_path_invalid_locale(self):
        """Test error with invalid locale."""
        response = self.client.get(
            "/api/v1/cms/api/pages/get_by_path/",
            {"path": "/published-page/", "locale": "invalid"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["error"], "Invalid locale")

    def test_get_by_path_page_not_found(self):
        """Test error when page doesn't exist."""
        response = self.client.get(
            "/api/v1/cms/api/pages/get_by_path/",
            {"path": "/nonexistent-page/", "locale": "en"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertEqual(data["error"], "Page not found")

    def test_get_by_path_draft_without_permission(self):
        """Test accessing draft page without permission."""
        response = self.client.get(
            "/api/v1/cms/api/pages/get_by_path/",
            {"path": "/draft-page/", "locale": "en"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertEqual(data["error"], "Permission denied")

    def test_get_by_path_draft_with_permission(self):
        """Test accessing draft page with proper permission."""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(
            "/api/v1/cms/api/pages/get_by_path/",
            {"path": "/draft-page/", "locale": "en"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["title"], "Draft Page")

    def test_children_endpoint(self):
        """Test children endpoint."""
        # Create child page
        child_page = Page.objects.create(
            title="Child Page",
            slug="child-page",
            path="/published-page/child/",
            locale=self.locale_en,
            status="published",
            parent=self.published_page,
            blocks=[{"type": "text", "props": {"content": "Child content"}}],
        )

        response = self.client.get(
            f"/api/v1/cms/api/pages/{self.published_page.id}/children/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["title"], "Child Page")

    def test_tree_endpoint(self):
        """Test tree endpoint returns hierarchical structure."""
        response = self.client.get("/api/v1/cms/api/pages/tree/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Should return tree structure
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_retrieve_page(self):
        """Test page retrieval."""
        response = self.client.get(f"/api/v1/cms/api/pages/{self.published_page.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["id"], self.published_page.id)
        self.assertEqual(data["title"], self.published_page.title)

    def test_create_page_success(self):
        """Test successful page creation."""
        self.client.force_authenticate(user=self.admin_user)

        page_data = {
            "title": "New Page",
            "slug": "new-page",
            "locale": self.locale_en.id,
            "status": "draft",
            "blocks": [{"type": "text", "props": {"content": "Test content"}}],
        }

        response = self.client.post("/api/v1/cms/api/pages/", page_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["title"], "New Page")
        self.assertEqual(data["slug"], "new-page")

        # Verify page was created in database
        self.assertTrue(Page.objects.filter(slug="new-page").exists())

    def test_create_page_without_permission(self):
        """Test page creation without permission fails."""
        self.client.force_authenticate(user=self.regular_user)

        page_data = {
            "title": "New Page",
            "slug": "new-page",
            "locale": self.locale_en.id,
            "status": "draft",
        }

        response = self.client.post("/api/v1/cms/api/pages/", page_data, format="json")

        # Should require permissions
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_page_success(self):
        """Test successful page update."""
        self.client.force_authenticate(user=self.admin_user)

        update_data = {
            "title": "Updated Title",
            "blocks": [
                {"type": "heading", "props": {"text": "Updated Heading", "level": 2}}
            ],
        }

        response = self.client.patch(
            f"/api/v1/cms/api/pages/{self.draft_page.id}/", update_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["title"], "Updated Title")

        # Verify database was updated
        self.draft_page.refresh_from_db()
        self.assertEqual(self.draft_page.title, "Updated Title")

    def test_delete_page(self):
        """Test page deletion."""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.delete(f"/api/v1/cms/api/pages/{self.draft_page.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify page was deleted
        self.assertFalse(Page.objects.filter(id=self.draft_page.id).exists())


class PagePublishingTestCase(APITestCase):
    """Test page publishing operations."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.locale_en = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )

        self.draft_page = Page.objects.create(
            title="Draft Page",
            slug="draft-page",
            path="/draft-page/",
            locale=self.locale_en,
            status="draft",
            blocks=[{"type": "text", "props": {"content": "Draft content"}}],
        )

        self.published_page = Page.objects.create(
            title="Published Page",
            slug="published-page",
            path="/published-page/",
            locale=self.locale_en,
            status="published",
            published_at=timezone.now(),
            blocks=[{"type": "text", "props": {"content": "Published content"}}],
        )

    def test_publish_page_success(self):
        """Test successful page publishing."""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.draft_page.id}/publish/",
            {"comment": "Publishing for launch"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Page published successfully")

        # Verify page status changed
        self.draft_page.refresh_from_db()
        self.assertEqual(self.draft_page.status, "published")
        self.assertIsNotNone(self.draft_page.published_at)

    def test_publish_page_without_permission(self):
        """Test publishing without proper permissions."""
        # Regular user without publish permission
        regular_user = User.objects.create_user(
            email="user@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=regular_user)

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.draft_page.id}/publish/"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unpublish_page_success(self):
        """Test successful page unpublishing."""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.published_page.id}/unpublish/",
            {"comment": "Unpublishing for updates"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Page unpublished successfully")

        # Verify page status changed
        self.published_page.refresh_from_db()
        self.assertEqual(self.published_page.status, "draft")
        self.assertIsNone(self.published_page.published_at)

    def test_schedule_page_success(self):
        """Test successful page scheduling."""
        self.client.force_authenticate(user=self.admin_user)

        # Schedule for 1 hour from now
        scheduled_time = timezone.now() + timedelta(hours=1)

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.draft_page.id}/schedule/",
            {"scheduled_at": scheduled_time.isoformat(), "comment": "Scheduled launch"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("Page scheduled successfully", data["message"])

        # Verify scheduling
        self.draft_page.refresh_from_db()
        self.assertEqual(self.draft_page.status, "scheduled")
        self.assertIsNotNone(self.draft_page.scheduled_at)

    def test_schedule_page_past_time_error(self):
        """Test error when scheduling in the past."""
        self.client.force_authenticate(user=self.admin_user)

        # Try to schedule in the past
        past_time = timezone.now() - timedelta(hours=1)

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.draft_page.id}/schedule/",
            {"scheduled_at": past_time.isoformat(), "comment": "Invalid schedule"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["error"], "Cannot schedule content in the past")

    def test_scheduled_content_list(self):
        """Test listing scheduled content."""
        # Create scheduled page
        scheduled_time = timezone.now() + timedelta(hours=1)

        scheduled_page = Page.objects.create(
            title="Scheduled Page",
            slug="scheduled-page",
            path="/scheduled-page/",
            locale=self.locale_en,
            status="scheduled",
            scheduled_at=scheduled_time,
            blocks=[{"type": "text", "props": {"content": "Scheduled content"}}],
        )

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get("/api/v1/cms/api/pages/scheduled_content/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Should return scheduled pages
        self.assertGreater(len(data["results"]), 0)
        scheduled_titles = [page["title"] for page in data["results"]]
        self.assertIn("Scheduled Page", scheduled_titles)
