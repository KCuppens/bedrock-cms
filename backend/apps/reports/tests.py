"""Comprehensive tests for reports app to boost coverage."""

import json
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

from apps.cms.models import Page
from apps.i18n.models import Locale, TranslationUnit

User = get_user_model()


class ReportsAPITestCase(TestCase):
    """Test reports API endpoints comprehensively."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create admin user
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
            is_superuser=True,
        )

        # Create regular user
        self.regular_user = User.objects.create_user(
            email="user@example.com", password="userpass123"
        )

        # Create test locale
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        # Create test page
        self.page = Page.objects.create(
            title="Test Page",
            slug="test-page",
            content="Test content with [link](internal-link)",
            status="published",
            locale=self.locale,
            created_by=self.admin_user,
        )

    def test_reports_overview_admin_access(self):
        """Test reports overview endpoint with admin access."""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:overview")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Check overview structure
        self.assertIn("overview", data)
        self.assertIn("available_reports", data)
        self.assertIn("generated_at", data)

        # Check overview statistics
        overview = data["overview"]
        self.assertIn("total_published_pages", overview)
        self.assertIn("active_locales", overview)
        self.assertIn("translation_units", overview)
        self.assertIn("pending_translations", overview)

        # Verify counts match test data
        self.assertEqual(overview["total_published_pages"], 1)
        self.assertEqual(overview["active_locales"], 1)

        # Check available reports structure
        reports = data["available_reports"]
        expected_reports = [
            "broken_links",
            "translation_digest",
            "seed_locale",
            "task_status",
        ]

        for report_name in expected_reports:
            self.assertIn(report_name, reports)
            report_info = reports[report_name]
            self.assertIn("endpoint", report_info)
            self.assertIn("description", report_info)
            self.assertIn("methods", report_info)

    def test_reports_overview_permission_denied(self):
        """Test reports overview with regular user (should be denied)."""
        self.client.force_authenticate(user=self.regular_user)

        url = reverse("reports:overview")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reports_overview_unauthenticated(self):
        """Test reports overview without authentication."""
        url = reverse("reports:overview")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("apps.reports.views.check_single_page_links")
    def test_broken_links_report_single_page(self, mock_task):
        """Test broken links report for single page."""
        mock_task.delay.return_value = Mock(id="test-task-id-123")

        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:broken-links")
        response = self.client.get(url, {"page_id": self.page.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("task_id", data)
        self.assertIn("status", data)
        self.assertIn("message", data)

        self.assertEqual(data["task_id"], "test-task-id-123")
        self.assertEqual(data["status"], "running")

        # Verify task was called with correct parameters
        mock_task.delay.assert_called_once_with(page_id=self.page.id)

    def test_broken_links_report_page_not_found(self):
        """Test broken links report with non-existent page."""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:broken-links")
        response = self.client.get(url, {"page_id": 99999})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Page not found or not published")

    def test_broken_links_report_get_info(self):
        """Test broken links report GET without page_id (info endpoint)."""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:broken-links")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("message", data)
        self.assertIn("endpoints", data)

        endpoints = data["endpoints"]
        self.assertIn("trigger_full_check", endpoints)
        self.assertIn("check_single_page", endpoints)
        self.assertIn("get_task_status", endpoints)

    @patch("apps.reports.views.check_internal_links")
    def test_broken_links_report_post_full_check(self, mock_task):
        """Test triggering full broken links check."""
        mock_task.delay.return_value = Mock(id="full-check-task-id")

        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:broken-links")
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("task_id", data)
        self.assertIn("status", data)
        self.assertIn("message", data)
        self.assertIn("check_status_url", data)

        self.assertEqual(data["task_id"], "full-check-task-id")
        self.assertEqual(data["status"], "running")

        # Verify task was called with no page_ids (full check)
        mock_task.delay.assert_called_once_with(page_ids=None)

    @patch("apps.reports.views.check_internal_links")
    def test_broken_links_report_post_specific_pages(self, mock_task):
        """Test triggering broken links check for specific pages."""
        mock_task.delay.return_value = Mock(id="specific-pages-task-id")

        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:broken-links")
        page_ids = [self.page.id]
        response = self.client.post(url, {"page_ids": page_ids}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(data["task_id"], "specific-pages-task-id")
        self.assertIn("1 pages", data["message"])

        # Verify task was called with specific page_ids
        mock_task.delay.assert_called_once_with(page_ids=page_ids)

    def test_broken_links_report_post_invalid_page_ids(self):
        """Test broken links report with invalid page_ids format."""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:broken-links")
        response = self.client.post(url, {"page_ids": "not_a_list"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "page_ids must be a list of integers")

    def test_translation_digest_basic(self):
        """Test basic translation digest functionality."""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:translation-digest")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Check digest structure
        self.assertIn("generated_at", data)
        self.assertIn("locales", data)
        self.assertIn("summary", data)

        # Check summary structure
        summary = data["summary"]
        expected_summary_keys = [
            "total_locales",
            "total_units",
            "total_missing",
            "total_needs_review",
            "total_approved",
        ]

        for key in expected_summary_keys:
            self.assertIn(key, summary)
            self.assertIsInstance(summary[key], int)

        # Check locales structure
        self.assertIsInstance(data["locales"], list)
        self.assertEqual(len(data["locales"]), 1)  # We have one test locale

        if data["locales"]:
            locale_data = data["locales"][0]
            expected_locale_keys = [
                "code",
                "name",
                "native_name",
                "is_default",
                "fallback_code",
                "statistics",
                "completion_percentage",
                "priority_areas",
            ]

            for key in expected_locale_keys:
                self.assertIn(key, locale_data)

            # Verify locale data matches our test locale
            self.assertEqual(locale_data["code"], "en")
            self.assertEqual(locale_data["name"], "English")
            self.assertTrue(locale_data["is_default"])

    def test_translation_digest_with_translation_units(self):
        """Test translation digest with actual translation units."""
        from django.contrib.contenttypes.models import ContentType

        # Create some translation units
        content_type = ContentType.objects.get_for_model(Page)

        translation_units = [
            {"status": "missing", "key": "title.missing"},
            {"status": "draft", "key": "content.draft"},
            {"status": "needs_review", "key": "meta.review"},
            {"status": "approved", "key": "slug.approved"},
        ]

        for unit_data in translation_units:
            TranslationUnit.objects.create(
                content_type=content_type,
                object_id=self.page.id,
                field_name="title",
                key=unit_data["key"],
                source_text="Test source text",
                target_text=(
                    "Test target text" if unit_data["status"] != "missing" else ""
                ),
                target_locale=self.locale,
                status=unit_data["status"],
            )

        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:translation-digest")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Verify summary reflects the created translation units
        summary = data["summary"]
        self.assertEqual(summary["total_units"], 4)
        self.assertEqual(summary["total_missing"], 1)
        self.assertEqual(summary["total_approved"], 1)

        # Verify locale completion percentage calculation
        locale_data = data["locales"][0]
        self.assertEqual(
            locale_data["completion_percentage"], 25.0
        )  # 1 approved out of 4

    @patch("apps.reports.views.AsyncResult")
    def test_task_status_successful(self, mock_async_result):
        """Test task status endpoint with successful task."""
        # Mock successful task result
        mock_result = Mock()
        mock_result.status = "SUCCESS"
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.failed.return_value = False
        mock_result.result = {"completed": True, "broken_links": []}

        mock_async_result.return_value = mock_result

        self.client.force_authenticate(user=self.admin_user)

        task_id = "test-task-123"
        url = reverse("reports:task-status", args=[task_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        expected_keys = ["task_id", "status", "ready", "successful", "failed", "result"]

        for key in expected_keys:
            self.assertIn(key, data)

        self.assertEqual(data["task_id"], task_id)
        self.assertEqual(data["status"], "SUCCESS")
        self.assertTrue(data["ready"])
        self.assertTrue(data["successful"])
        self.assertFalse(data["failed"])
        self.assertIsInstance(data["result"], dict)

    @patch("apps.reports.views.AsyncResult")
    def test_task_status_failed(self, mock_async_result):
        """Test task status endpoint with failed task."""
        # Mock failed task result
        mock_result = Mock()
        mock_result.status = "FAILURE"
        mock_result.ready.return_value = True
        mock_result.successful.return_value = False
        mock_result.failed.return_value = True
        mock_result.result = Exception("Task failed with error")

        mock_async_result.return_value = mock_result

        self.client.force_authenticate(user=self.admin_user)

        task_id = "failed-task-456"
        url = reverse("reports:task-status", args=[task_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["task_id"], task_id)
        self.assertEqual(data["status"], "FAILURE")
        self.assertTrue(data["ready"])
        self.assertFalse(data["successful"])
        self.assertTrue(data["failed"])
        self.assertIn("error", data)

    @patch("apps.reports.views.AsyncResult")
    def test_task_status_pending(self, mock_async_result):
        """Test task status endpoint with pending task."""
        # Mock pending task result
        mock_result = Mock()
        mock_result.status = "PENDING"
        mock_result.ready.return_value = False
        mock_result.info = {"current": 5, "total": 10, "status": "Processing..."}

        mock_async_result.return_value = mock_result

        self.client.force_authenticate(user=self.admin_user)

        task_id = "pending-task-789"
        url = reverse("reports:task-status", args=[task_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["task_id"], task_id)
        self.assertEqual(data["status"], "PENDING")
        self.assertFalse(data["ready"])
        self.assertIsNone(data["successful"])
        self.assertIsNone(data["failed"])
        self.assertIn("progress", data)
        self.assertEqual(data["progress"]["current"], 5)

    @patch("apps.reports.views.AsyncResult")
    def test_task_status_exception(self, mock_async_result):
        """Test task status endpoint with exception."""
        mock_async_result.side_effect = Exception("Invalid task ID")

        self.client.force_authenticate(user=self.admin_user)

        task_id = "invalid-task"
        url = reverse("reports:task-status", args=[task_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn("error", data)
        self.assertIn("Failed to get task status", data["error"])

    @patch("apps.reports.views.seed_locale_translation_units")
    def test_seed_locale_success(self, mock_task):
        """Test successful locale seeding."""
        mock_task.delay.return_value = Mock(id="seed-task-123")

        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:seed-locale")
        data = {"locale_code": "en", "force_reseed": False}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertIn("task_id", response_data)
        self.assertIn("status", response_data)
        self.assertIn("message", response_data)
        self.assertIn("check_status_url", response_data)

        self.assertEqual(response_data["task_id"], "seed-task-123")
        self.assertEqual(response_data["status"], "running")
        self.assertIn("en", response_data["message"])

        # Verify task was called with correct parameters
        mock_task.delay.assert_called_once_with(locale_code="en", force_reseed=False)

    def test_seed_locale_missing_code(self):
        """Test locale seeding without locale_code."""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:seed-locale")
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "locale_code is required")

    def test_seed_locale_not_found(self):
        """Test locale seeding with non-existent locale."""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:seed-locale")
        data = {"locale_code": "nonexistent"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response_data = response.json()
        self.assertIn("error", response_data)
        self.assertEqual(response_data["error"], "Locale nonexistent not found")

    def test_seed_locale_inactive(self):
        """Test locale seeding with inactive locale."""
        # Create inactive locale
        inactive_locale = Locale.objects.create(
            code="fr", name="French", native_name="Français", is_active=False
        )

        self.client.force_authenticate(user=self.admin_user)

        url = reverse("reports:seed-locale")
        data = {"locale_code": "fr"}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response_data = response.json()
        self.assertIn("error", response_data)
        self.assertEqual(response_data["error"], "Locale fr is not active")


class ReportsIntegrationTestCase(TestCase):
    """Integration tests for reports functionality."""

    def setUp(self):
        """Set up integration test data."""
        self.admin_user = User.objects.create_user(
            email="integration@example.com",
            password="integrationpass123",
            is_staff=True,
            is_superuser=True,
        )

        # Create multiple locales for comprehensive testing
        self.en_locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        self.es_locale = Locale.objects.create(
            code="es",
            name="Spanish",
            native_name="Español",
            is_active=True,
            fallback=self.en_locale,
        )

        # Create multiple pages
        self.pages = []
        for i in range(3):
            page = Page.objects.create(
                title=f"Test Page {i+1}",
                slug=f"test-page-{i+1}",
                content=f"Test content for page {i+1}",
                status="published",
                locale=self.en_locale,
                created_by=self.admin_user,
            )
            self.pages.append(page)

    def test_reports_workflow_integration(self):
        """Test complete reports workflow integration."""
        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        # 1. Get reports overview
        overview_url = reverse("reports:overview")
        overview_response = client.get(overview_url)

        self.assertEqual(overview_response.status_code, status.HTTP_200_OK)

        overview_data = overview_response.json()
        self.assertEqual(overview_data["overview"]["total_published_pages"], 3)
        self.assertEqual(overview_data["overview"]["active_locales"], 2)

        # 2. Get translation digest
        digest_url = reverse("reports:translation-digest")
        digest_response = client.get(digest_url)

        self.assertEqual(digest_response.status_code, status.HTTP_200_OK)

        digest_data = digest_response.json()
        self.assertEqual(len(digest_data["locales"]), 2)

        # Verify both locales are present
        locale_codes = [locale["code"] for locale in digest_data["locales"]]
        self.assertIn("en", locale_codes)
        self.assertIn("es", locale_codes)

        # 3. Test broken links report info endpoint
        links_url = reverse("reports:broken-links")
        links_response = client.get(links_url)

        self.assertEqual(links_response.status_code, status.HTTP_200_OK)

        links_data = links_response.json()
        self.assertIn("endpoints", links_data)

        # Verify all expected endpoints are documented
        endpoints = links_data["endpoints"]
        self.assertIn("trigger_full_check", endpoints)
        self.assertIn("check_single_page", endpoints)
        self.assertIn("get_task_status", endpoints)

    def test_multiple_locales_translation_digest(self):
        """Test translation digest with multiple locales."""
        from django.contrib.contenttypes.models import ContentType

        # Create translation units for both locales
        content_type = ContentType.objects.get_for_model(Page)

        # English locale units (default)
        TranslationUnit.objects.create(
            content_type=content_type,
            object_id=self.pages[0].id,
            field_name="title",
            key="page1.title",
            source_text="Test Page 1",
            target_text="Test Page 1",
            target_locale=self.en_locale,
            status="approved",
        )

        # Spanish locale units (with various statuses)
        spanish_units = [
            {"status": "missing", "target_text": ""},
            {"status": "needs_review", "target_text": "Página de Prueba 1"},
            {"status": "approved", "target_text": "Página de Prueba 2"},
        ]

        for i, unit_data in enumerate(spanish_units):
            TranslationUnit.objects.create(
                content_type=content_type,
                object_id=self.pages[i].id,
                field_name="title",
                key=f"page{i+1}.title.es",
                source_text=f"Test Page {i+1}",
                target_text=unit_data["target_text"],
                target_locale=self.es_locale,
                status=unit_data["status"],
            )

        client = APIClient()
        client.force_authenticate(user=self.admin_user)

        url = reverse("reports:translation-digest")
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Verify summary aggregates from both locales
        summary = data["summary"]
        self.assertEqual(summary["total_units"], 4)  # 1 EN + 3 ES
        self.assertEqual(summary["total_missing"], 1)
        self.assertEqual(summary["total_needs_review"], 1)
        self.assertEqual(summary["total_approved"], 2)

        # Find Spanish locale data
        es_locale_data = next(
            (loc for loc in data["locales"] if loc["code"] == "es"), None
        )

        self.assertIsNotNone(es_locale_data)
        self.assertEqual(es_locale_data["fallback_code"], "en")
        self.assertFalse(es_locale_data["is_default"])

        # Verify Spanish completion percentage
        # 1 approved out of 3 = 33.3%
        self.assertAlmostEqual(es_locale_data["completion_percentage"], 33.3, places=1)
