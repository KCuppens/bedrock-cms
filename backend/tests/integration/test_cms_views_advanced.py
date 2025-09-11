"""
Advanced CMS Views tests for publishing, moderation, and complex operations.

Tests publishing workflows, moderation system, scheduled content,
block operations, and all remaining CMS view functionality.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.cms.models import Page
from apps.i18n.models import Locale
from tests.fixtures.sample_data import *
from tests.factories import *

User = get_user_model()


class PagePublishingTestCase(APITestCase):
    """Test page publishing and workflow operations."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.locale_en = LocaleFactory(code="en", is_default=True)
        self.admin_user = AdminUserFactory()
        self.editor_user = EditorUserFactory()

        self.draft_page = DraftPageFactory(
            title="Draft Page",
            slug="draft-page",
            path="/draft-page/",
            locale=self.locale_en,
            status="draft",
        )

        self.published_page = PublishedPageFactory(
            title="Published Page",
            slug="published-page",
            path="/published-page/",
            locale=self.locale_en,
            status="published",
            published_at=timezone.now(),
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
        regular_user = UserFactory()
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

    def test_unschedule_page_success(self):
        """Test successful page unscheduling."""
        # First schedule the page
        scheduled_time = timezone.now() + timedelta(hours=1)
        self.draft_page.scheduled_at = scheduled_time
        self.draft_page.status = "scheduled"
        self.draft_page.save()

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.draft_page.id}/unschedule/",
            {"comment": "Cancelling schedule"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Page unscheduled successfully")

        # Verify unscheduling
        self.draft_page.refresh_from_db()
        self.assertEqual(self.draft_page.status, "draft")
        self.assertIsNone(self.draft_page.scheduled_at)

    def test_scheduled_content_list(self):
        """Test listing scheduled content."""
        # Create scheduled pages
        scheduled_time1 = timezone.now() + timedelta(hours=1)
        scheduled_time2 = timezone.now() + timedelta(hours=2)

        page1 = PageFactory(
            title="Scheduled Page 1",
            status="scheduled",
            scheduled_at=scheduled_time1,
            locale=self.locale_en,
        )

        page2 = PageFactory(
            title="Scheduled Page 2",
            status="scheduled",
            scheduled_at=scheduled_time2,
            locale=self.locale_en,
        )

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get("/api/v1/cms/api/pages/scheduled_content/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Should return scheduled pages ordered by scheduled_at
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["title"], "Scheduled Page 1")
        self.assertEqual(data["results"][1]["title"], "Scheduled Page 2")


class PageModerationTestCase(APITestCase):
    """Test page moderation workflow."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.locale_en = LocaleFactory(code="en", is_default=True)
        self.admin_user = AdminUserFactory()
        self.editor_user = EditorUserFactory()
        self.contributor_user = UserFactory()

        self.draft_page = DraftPageFactory(
            title="Content for Review",
            slug="content-review",
            path="/content-review/",
            locale=self.locale_en,
            status="draft",
        )

    def test_submit_for_review_success(self):
        """Test successful submission for review."""
        self.client.force_authenticate(user=self.contributor_user)

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.draft_page.id}/submit_for_review/",
            {"review_notes": "Ready for review"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Page submitted for review")

        # Verify status change
        self.draft_page.refresh_from_db()
        self.assertEqual(self.draft_page.status, "under_review")

    def test_approve_page_success(self):
        """Test successful page approval."""
        # Set page to under_review status
        self.draft_page.status = "under_review"
        self.draft_page.save()

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.draft_page.id}/approve/",
            {"review_comment": "Approved, looks good", "publish_immediately": True},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Page approved and published")

        # Verify approval and publishing
        self.draft_page.refresh_from_db()
        self.assertEqual(self.draft_page.status, "published")
        self.assertIsNotNone(self.draft_page.published_at)

    def test_reject_page_success(self):
        """Test successful page rejection."""
        # Set page to under_review status
        self.draft_page.status = "under_review"
        self.draft_page.save()

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.draft_page.id}/reject/",
            {
                "review_comment": "Needs more work on content",
                "rejection_reason": "content_quality",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Page rejected and returned to draft")

        # Verify rejection
        self.draft_page.refresh_from_db()
        self.assertEqual(self.draft_page.status, "draft")

    def test_moderation_queue_list(self):
        """Test moderation queue listing."""
        # Create pages in different review states
        review_page1 = PageFactory(
            title="Review Page 1", status="under_review", locale=self.locale_en
        )

        review_page2 = PageFactory(
            title="Review Page 2", status="under_review", locale=self.locale_en
        )

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get("/api/v1/cms/api/pages/moderation_queue/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Should return pages under review
        self.assertEqual(len(data["results"]), 2)
        review_titles = [page["title"] for page in data["results"]]
        self.assertIn("Review Page 1", review_titles)
        self.assertIn("Review Page 2", review_titles)

    def test_moderation_stats(self):
        """Test moderation statistics."""
        # Create pages in various states for stats
        PageFactory.create_batch(3, status="under_review", locale=self.locale_en)
        PageFactory.create_batch(2, status="published", locale=self.locale_en)
        PageFactory.create_batch(1, status="draft", locale=self.locale_en)

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get("/api/v1/cms/api/pages/moderation_stats/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Should return statistics
        self.assertIn("pending_review", data)
        self.assertIn("published_today", data)
        self.assertIn("total_drafts", data)
        self.assertEqual(data["pending_review"], 3)


class PageBlockOperationsTestCase(APITestCase):
    """Test block-level operations on pages."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.locale_en = LocaleFactory(code="en", is_default=True)
        self.admin_user = AdminUserFactory()

        self.test_page = DraftPageFactory(
            title="Block Test Page",
            slug="block-test",
            path="/block-test/",
            locale=self.locale_en,
            blocks=[
                {"type": "text", "props": {"content": "First block content"}},
                {
                    "type": "heading",
                    "props": {"text": "Second block heading", "level": 2},
                },
            ],
        )

    def test_update_block_success(self):
        """Test successful block update."""
        self.client.force_authenticate(user=self.admin_user)

        updated_block = {"type": "text", "props": {"content": "Updated block content"}}

        response = self.client.patch(
            f"/api/v1/cms/api/pages/{self.test_page.id}/blocks/0/",
            updated_block,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Block updated successfully")

        # Verify block was updated
        self.test_page.refresh_from_db()
        self.assertEqual(
            self.test_page.blocks[0]["props"]["content"], "Updated block content"
        )

    def test_update_block_invalid_index(self):
        """Test error with invalid block index."""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.patch(
            f"/api/v1/cms/api/pages/{self.test_page.id}/blocks/999/",
            {"type": "text", "props": {"content": "test"}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertEqual(data["error"], "Invalid block index")

    def test_insert_block_success(self):
        """Test successful block insertion."""
        self.client.force_authenticate(user=self.admin_user)

        new_block = {
            "block": {
                "type": "image",
                "props": {"src": "https://example.com/image.jpg", "alt": "Test image"},
            },
            "position": 1,
        }

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.test_page.id}/blocks/insert/",
            new_block,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Block inserted successfully")

        # Verify block was inserted
        self.test_page.refresh_from_db()
        self.assertEqual(len(self.test_page.blocks), 3)
        self.assertEqual(self.test_page.blocks[1]["type"], "image")

    def test_reorder_blocks_success(self):
        """Test successful block reordering."""
        self.client.force_authenticate(user=self.admin_user)

        # Reverse the order of blocks
        reorder_data = {"new_order": [1, 0]}  # Second block first, first block second

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.test_page.id}/blocks/reorder/",
            reorder_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Blocks reordered successfully")

        # Verify reordering
        self.test_page.refresh_from_db()
        self.assertEqual(self.test_page.blocks[0]["type"], "heading")
        self.assertEqual(self.test_page.blocks[1]["type"], "text")

    def test_delete_block_success(self):
        """Test successful block deletion."""
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.delete(
            f"/api/v1/cms/api/pages/{self.test_page.id}/blocks/0/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Block deleted successfully")

        # Verify block was deleted
        self.test_page.refresh_from_db()
        self.assertEqual(len(self.test_page.blocks), 1)
        self.assertEqual(self.test_page.blocks[0]["type"], "heading")


class PageMoveOperationsTestCase(APITestCase):
    """Test page movement and hierarchy operations."""

    def setUp(self):
        """Set up hierarchical test data."""
        self.client = APIClient()
        self.locale_en = LocaleFactory(code="en", is_default=True)
        self.admin_user = AdminUserFactory()

        # Create hierarchical structure
        self.parent1 = PublishedPageFactory(
            title="Parent 1", slug="parent1", path="/parent1/", locale=self.locale_en
        )

        self.parent2 = PublishedPageFactory(
            title="Parent 2", slug="parent2", path="/parent2/", locale=self.locale_en
        )

        self.child = PublishedPageFactory(
            title="Child Page",
            slug="child",
            path="/parent1/child/",
            locale=self.locale_en,
            parent=self.parent1,
        )

        self.sibling1 = PublishedPageFactory(
            title="Sibling 1",
            slug="sibling1",
            path="/parent1/sibling1/",
            locale=self.locale_en,
            parent=self.parent1,
        )

        self.sibling2 = PublishedPageFactory(
            title="Sibling 2",
            slug="sibling2",
            path="/parent1/sibling2/",
            locale=self.locale_en,
            parent=self.parent1,
        )

    def test_move_page_to_new_parent(self):
        """Test moving page to new parent."""
        self.client.force_authenticate(user=self.admin_user)

        move_data = {"new_parent_id": self.parent2.id, "position": 0}

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.child.id}/move/", move_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Page moved successfully")

        # Verify move
        self.child.refresh_from_db()
        self.assertEqual(self.child.parent.id, self.parent2.id)
        self.assertEqual(self.child.path, "/parent2/child/")

    def test_reorder_children_success(self):
        """Test successful children reordering."""
        self.client.force_authenticate(user=self.admin_user)

        # Reverse order of children
        reorder_data = {
            "child_order": [self.sibling2.id, self.sibling1.id, self.child.id]
        }

        response = self.client.post(
            f"/api/v1/cms/api/pages/{self.parent1.id}/reorder_children/",
            reorder_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "Children reordered successfully")

        # Verify reordering (checking menu_order or similar field)
        children = Page.objects.filter(parent=self.parent1).order_by("menu_order")
        self.assertEqual(
            list(children.values_list("id", flat=True)),
            [self.sibling2.id, self.sibling1.id, self.child.id],
        )


class SitemapViewTestCase(APITestCase):
    """Test sitemap generation."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.locale_en = LocaleFactory(code="en", is_default=True)

        # Create published pages
        PublishedPageFactory.create_batch(5, locale=self.locale_en, status="published")

    def test_sitemap_generation(self):
        """Test sitemap XML generation."""
        response = self.client.get("/sitemap/en.xml")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/xml")

        # Verify XML structure
        content = response.content.decode()
        self.assertIn('<?xml version="1.0"', content)
        self.assertIn("<urlset", content)
        self.assertIn("<url>", content)
        self.assertIn("<loc>", content)

    def test_sitemap_invalid_locale(self):
        """Test sitemap with invalid locale."""
        response = self.client.get("/sitemap/invalid.xml")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
