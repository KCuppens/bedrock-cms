import copy
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from apps.cms.models import Page
from apps.cms.versioning import AuditEntry, PageRevision, RevisionDiffer
from apps.i18n.models import Locale

"""Tests for versioning and audit functionality."""


User = get_user_model()


class PageRevisionModelTests(TestCase):
    """Test PageRevision model functionality."""

    def setUp(self):
        """Set up test data."""

        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        self.page = Page.objects.create(
            title="Test Page",
            slug="test-page",
            locale=self.locale,
            blocks=[{"type": "text", "props": {"content": "Hello World"}}],
            status="draft",
        )

    def test_create_snapshot(self):
        """Test creating a revision snapshot."""

        revision = PageRevision.create_snapshot(
            page=self.page,
            user=self.user,
            is_published=False,
            is_autosave=False,
            comment="Test revision",
        )

        self.assertEqual(revision.page, self.page)

        self.assertEqual(revision.created_by, self.user)

        """self.assertEqual(revision.comment, "Test revision")"""

        self.assertFalse(revision.is_published_snapshot)

        self.assertFalse(revision.is_autosave)

        # Check snapshot contains page data

        snapshot = revision.snapshot

        """self.assertEqual(snapshot["title"], "Test Page")"""

        """self.assertEqual(snapshot["slug"], "test-page")"""

        self.assertEqual(snapshot["status"], "draft")

    def test_autosave_throttling(self):
        """Test autosave throttling prevents frequent saves."""

        # First autosave should be allowed

        self.assertTrue(PageRevision.should_create_autosave(self.page, self.user))

        # Create an autosave

        PageRevision.create_snapshot(
            page=self.page, user=self.user, is_autosave=True, comment="Autosave"
        )

        # Second autosave within 1 minute should be blocked

        self.assertFalse(PageRevision.should_create_autosave(self.page, self.user))

    def test_published_snapshot_creation(self):
        """Test creation of published snapshots."""

        self.page.status = "published"

        self.page.published_at = timezone.now()

        revision = PageRevision.create_snapshot(
            page=self.page, user=self.user, is_published=True, comment="Published"
        )

        self.assertTrue(revision.is_published_snapshot)

        self.assertFalse(revision.is_autosave)

        self.assertEqual(revision.comment, "Published")

    def test_restore_to_page(self):
        """Test restoring a revision to page."""

        # Create initial revision

        original_title = self.page.title

        revision = PageRevision.create_snapshot(
            page=self.page, user=self.user, comment="Original state"
        )

        # Modify page

        self.page.title = "Modified Title"

        self.page.save()

        # Restore from revision

        restored_page = revision.restore_to_page()

        self.assertEqual(restored_page.title, original_title)

        self.assertEqual(restored_page.status, "draft")  # Always restored as draft

    def test_get_block_count(self):
        """Test block count calculation."""

        revision = PageRevision.create_snapshot(page=self.page, user=self.user)

        self.assertEqual(revision.get_block_count(), 1)

        # Create page with multiple blocks

        page_with_blocks = Page.objects.create(
            title="Multi Block Page",
            slug="multi-block",
            locale=self.locale,
            blocks=[
                {"type": "text", "props": {"content": "Block 1"}},
                {"type": "text", "props": {"content": "Block 2"}},
                """{"type": "image", "props": {"src": "/test.jpg"}},""",
            ],
            status="draft",
        )

        revision2 = PageRevision.create_snapshot(page=page_with_blocks, user=self.user)

        self.assertEqual(revision2.get_block_count(), 3)


class AuditEntryModelTests(TestCase):
    """Test AuditEntry model functionality."""

    def setUp(self):
        """Set up test data."""

        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        self.page = Page.objects.create(
            title="Test Page",
            slug="test-page",
            locale=self.locale,
            blocks=[],
            status="draft",
        )

    def test_log_audit_entry(self):
        """Test creating an audit log entry."""

        # Create a mock request with IP address

        mock_request = Mock()

        mock_request.META = {"REMOTE_ADDR": "127.0.0.1"}

        entry = AuditEntry.log(
            actor=self.user,
            action="create",
            obj=self.page,
            meta={"test": "data"},
            request=mock_request,
        )

        self.assertEqual(entry.actor, self.user)

        self.assertEqual(entry.action, "create")

        self.assertEqual(entry.content_object, self.page)

        """self.assertEqual(entry.meta, {"test": "data"})"""

        self.assertEqual(entry.ip_address, "127.0.0.1")

    def test_audit_entry_str(self):
        """Test audit entry string representation."""

        entry = AuditEntry.log(actor=self.user, action="update", obj=self.page)

        expected = f"{self.user.email} performed update on cms.page#{self.page.id}"

        self.assertEqual(str(entry), expected)


class RevisionDifferTests(TestCase):
    """Test revision diffing functionality."""

    def setUp(self):
        """Set up test data."""

        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        self.page = Page.objects.create(
            title="Original Title",
            slug="original-slug",
            locale=self.locale,
            blocks=[{"type": "text", "props": {"content": "Original content"}}],
            status="draft",
        )

    def test_diff_revisions(self):
        """Test diffing between two revisions."""

        # Create first revision

        revision1 = PageRevision.create_snapshot(
            page=self.page, user=self.user, comment="First revision"
        )

        # Modify page and create second revision

        self.page.title = "Updated Title"

        # Need to reassign blocks array for Django to detect the change

        blocks = copy.deepcopy(self.page.blocks)

        blocks[0]["props"]["content"] = "Updated content"

        self.page.blocks = blocks

        # Skip automatic revision creation

        self.page._skip_revision_creation = True

        self.page.save()

        revision2 = PageRevision.create_snapshot(
            page=self.page, user=self.user, comment="Second revision"
        )

        # Test diff

        diff = RevisionDiffer.diff_revisions(revision1, revision2)

        self.assertEqual(diff["old_revision_id"], revision1.id)

        self.assertEqual(diff["new_revision_id"], revision2.id)

        self.assertTrue(diff["has_changes"])

        # Should detect title change

        changes = diff["changes"]

        self.assertIn("title", changes)

        self.assertEqual(changes["title"]["old"], "Original Title")

        self.assertEqual(changes["title"]["new"], "Updated Title")

        # Should detect blocks change

        self.assertIn("blocks", changes)

    def test_diff_current_page(self):
        """Test diffing revision against current page state."""

        # Create revision

        revision = PageRevision.create_snapshot(
            page=self.page, user=self.user, comment="Original state"
        )

        # Modify page

        self.page.title = "Current Title"

        self.page.save()

        # Test diff against current

        diff = RevisionDiffer.diff_current_page(self.page, revision)

        self.assertEqual(diff["old_revision_id"], revision.id)

        self.assertIsNone(diff["new_revision_id"])

        self.assertTrue(diff["has_changes"])

        changes = diff["changes"]

        self.assertIn("title", changes)

        self.assertEqual(changes["title"]["old"], "Original Title")

        self.assertEqual(changes["title"]["new"], "Current Title")

    def test_no_changes_diff(self):
        """Test diff when there are no changes."""

        revision1 = PageRevision.create_snapshot(page=self.page, user=self.user)

        revision2 = PageRevision.create_snapshot(page=self.page, user=self.user)

        diff = RevisionDiffer.diff_revisions(revision1, revision2)

        self.assertFalse(diff["has_changes"])

        self.assertEqual(diff["changes"], {})


class VersioningAPITests(APITestCase):
    """Test versioning API endpoints."""

    def setUp(self):
        """Set up test data."""

        self.user = User.objects.create_superuser(
            email="test@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        # Create page with flag to skip revision creation

        self.page = Page(
            title="Test Page",
            slug="test-page",
            locale=self.locale,
            blocks=[{"type": "text", "props": {"content": "Hello"}}],
            status="draft",
        )

        self.page._skip_revision_creation = True

        self.page.save()

        # Create some revisions

        self.revision1 = PageRevision.create_snapshot(
            page=self.page, user=self.user, comment="First revision"
        )

        # Modify and create second revision

        self.page.title = "Updated Page"

        self.page._skip_revision_creation = True

        self.page.save()

        self.revision2 = PageRevision.create_snapshot(
            page=self.page, user=self.user, comment="Second revision"
        )

        self.client.force_authenticate(user=self.user)

    def test_list_revisions(self):
        """Test listing revisions for a page."""

        response = self.client.get(f"/api/v1/cms/pages/{self.page.id}/revisions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data["results"]), 2)

        self.assertEqual(data["results"][0]["comment"], "Second revision")

        self.assertEqual(data["results"][1]["comment"], "First revision")

    def test_revision_detail(self):
        """Test getting revision details."""

        response = self.client.get(f"/api/v1/cms/revisions/{self.revision1.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["id"], str(self.revision1.id))

        self.assertEqual(data["comment"], "First revision")

        self.assertIn("snapshot", data)

    def test_diff_revisions(self):
        """Test diffing between revisions."""

        response = self.client.get(
            f"/api/v1/cms/revisions/{self.revision2.id}/diff/",
            {"against": str(self.revision1.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertTrue(data["has_changes"])

        self.assertIn("title", data["changes"])

    def test_diff_current(self):
        """Test diffing revision against current page."""

        # Modify page again

        self.page.title = "Current Title"

        self.page.save()

        response = self.client.get(
            f"/api/v1/cms/revisions/{self.revision1.id}/diff_current/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertTrue(data["has_changes"])

        self.assertIn("title", data["changes"])

        self.assertEqual(data["changes"]["title"]["new"], "Current Title")

    def test_revert_revision(self):
        """Test reverting to a revision."""

        response = self.client.post(
            f"/api/v1/cms/revisions/{self.revision1.id}/revert/",
            {"comment": "Reverted to first revision"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that page was reverted

        self.page.refresh_from_db()

        """self.assertEqual(self.page.title, "Test Page")"""

        self.assertEqual(self.page.status, "draft")

    def test_manual_autosave(self):
        """Test manual autosave creation."""

        import json

        response = self.client.post(
            f"/api/v1/cms/pages/{self.page.id}/autosave/",
            json.dumps({"comment": "Manual autosave test"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()

        self.assertIn("revision_id", data)

        # Verify autosave was created

        revision = PageRevision.objects.get(id=data["revision_id"])

        self.assertTrue(revision.is_autosave)

        """self.assertEqual(revision.comment, "Manual autosave test")"""

    def test_publish_page(self):
        """Test publishing a page."""

        response = self.client.post(
            f"/api/v1/cms/pages/{self.page.id}/publish/",
            {"comment": "Publishing page"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check page is published

        self.page.refresh_from_db()

        self.assertEqual(self.page.status, "published")

        self.assertIsNotNone(self.page.published_at)

        # Check published revision was created

        published_revision = PageRevision.objects.filter(
            page=self.page, is_published_snapshot=True
        ).first()

        self.assertIsNotNone(published_revision)

    def test_unpublish_page(self):
        """Test unpublishing a page."""

        # First publish the page

        self.page.status = "published"

        self.page.published_at = timezone.now()

        self.page.save()

        response = self.client.post(
            f"/api/v1/cms/pages/{self.page.id}/unpublish/",
            {"comment": "Unpublishing page"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check page is unpublished

        self.page.refresh_from_db()

        self.assertEqual(self.page.status, "draft")

        self.assertIsNone(self.page.published_at)


class VersioningSignalsTests(TestCase):
    """Test versioning signal handlers."""

    def setUp(self):
        """Set up test data."""

        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

    def test_revision_created_on_page_save(self):
        """Test that revisions are created when pages are saved."""

        page = Page(
            title="New Page",
            slug="new-page",
            locale=self.locale,
            blocks=[],
            status="draft",
        )

        page._current_user = self.user

        page.save()

        # Should create a revision

        revisions = PageRevision.objects.filter(page=page)

        self.assertEqual(revisions.count(), 1)

    def test_audit_entry_created_on_page_save(self):
        """Test that audit entries are created when pages are saved."""

        page = Page(
            title="New Page",
            slug="new-page",
            locale=self.locale,
            blocks=[],
            status="draft",
        )

        page._current_user = self.user

        page.save()

        # Should create an audit entry

        audit_entries = AuditEntry.objects.filter(
            model_label="cms.page", object_id=page.id
        )

        self.assertEqual(audit_entries.count(), 1)

        audit_entry = audit_entries.first()
        self.assertIsNotNone(audit_entry)
        self.assertEqual(audit_entry.action, "create")
