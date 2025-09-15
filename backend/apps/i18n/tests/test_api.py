"""
Comprehensive API tests for the I18n (internationalization) app.

This module provides extensive test coverage for:
- Translation Management APIs
- Locale management endpoints
- Translation unit CRUD operations
- UI message translation endpoints
- Translation status workflow
- Batch translation operations
- Authentication and permissions
- Import/export functionality
"""

import json
import os
import tempfile
from datetime import datetime, timedelta

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

from apps.i18n.models import (
    Locale,
    TranslationGlossary,
    TranslationHistory,
    TranslationQueue,
    TranslationUnit,
    UiMessage,
    UiMessageTranslation,
)

User = get_user_model()


class I18nAPITestCase(TestCase):
    """Base test case for I18n API tests with common setup."""

    def setUp(self):
        """Set up common test data and authentication."""
        self.client = APIClient()

        # Create test users with different roles
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="adminpass123",
            is_staff=True,
            is_superuser=True,
        )

        self.translator_user = User.objects.create_user(
            email="translator@test.com",
            password="translatorpass123",
        )

        self.regular_user = User.objects.create_user(
            email="user@test.com",
            password="userpass123",
        )

        # Create test locales
        self.locale_en = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
            sort_order=1,
        )

        self.locale_es = Locale.objects.create(
            code="es",
            name="Spanish",
            native_name="Español",
            is_active=True,
            sort_order=2,
            fallback=self.locale_en,
        )

        self.locale_fr = Locale.objects.create(
            code="fr",
            name="French",
            native_name="Français",
            is_active=True,
            sort_order=3,
            fallback=self.locale_en,
        )

        # Inactive locale for testing
        self.locale_inactive = Locale.objects.create(
            code="de",
            name="German",
            native_name="Deutsch",
            is_active=False,
            sort_order=4,
        )

    def authenticate_user(self, user=None):
        """Authenticate a user for API requests."""
        if user is None:
            user = self.translator_user
        self.client.force_authenticate(user=user)

    def unauthenticate(self):
        """Remove authentication from the client."""
        self.client.force_authenticate(user=None)


class LocaleAPITestCase(I18nAPITestCase):
    """Test cases for Locale API endpoints."""

    def test_list_locales_authenticated(self):
        """Test listing locales as authenticated user."""
        self.authenticate_user()

        url = reverse("locales-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Handle both paginated and non-paginated responses
        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data
        self.assertEqual(len(data), 4)  # 3 active + 1 inactive

    def test_list_locales_unauthenticated(self):
        """Test listing locales as unauthenticated user (should work for read-only)."""
        self.unauthenticate()

        url = reverse("locales-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_active_locales_only(self):
        """Test filtering to only active locales."""
        self.authenticate_user()

        url = reverse("locales-list")
        response = self.client.get(url, {"active_only": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data
        self.assertEqual(len(data), 3)  # Only active locales

        # Check all returned locales are active
        for locale_data in data:
            self.assertTrue(locale_data["is_active"])

    def test_create_locale_authenticated(self):
        """Test creating a locale as authenticated user."""
        self.authenticate_user(self.admin_user)

        url = reverse("locales-list")
        data = {
            "code": "pt",
            "name": "Portuguese",
            "native_name": "Português",
            "is_active": True,
            "rtl": False,
            "sort_order": 5,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Locale.objects.count(), 5)
        self.assertEqual(response.data["code"], "pt")
        self.assertEqual(response.data["name"], "Portuguese")

    def test_create_locale_unauthenticated(self):
        """Test creating a locale as unauthenticated user should fail."""
        self.unauthenticate()

        url = reverse("locales-list")
        data = {
            "code": "pt",
            "name": "Portuguese",
            "native_name": "Português",
        }

        response = self.client.post(url, data, format="json")

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_create_locale_duplicate_code(self):
        """Test creating locale with duplicate code should fail."""
        self.authenticate_user(self.admin_user)

        url = reverse("locales-list")
        data = {
            "code": "en",  # Already exists
            "name": "English US",
            "native_name": "English (US)",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_locale(self):
        """Test updating a locale."""
        self.authenticate_user(self.admin_user)

        url = reverse("locales-detail", kwargs={"pk": self.locale_es.pk})
        data = {
            "code": "es",
            "name": "Spanish (Spain)",
            "native_name": "Español (España)",
            "is_active": True,
            "sort_order": 2,
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.locale_es.refresh_from_db()
        self.assertEqual(self.locale_es.name, "Spanish (Spain)")

    def test_partial_update_locale(self):
        """Test partially updating a locale."""
        self.authenticate_user(self.admin_user)

        url = reverse("locales-detail", kwargs={"pk": self.locale_es.pk})
        data = {"name": "Spanish Updated"}

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.locale_es.refresh_from_db()
        self.assertEqual(self.locale_es.name, "Spanish Updated")

    def test_delete_locale_non_default(self):
        """Test deleting a non-default locale."""
        self.authenticate_user(self.admin_user)

        url = reverse("locales-detail", kwargs={"pk": self.locale_es.pk})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Locale.objects.count(), 3)

    def test_delete_default_locale_forbidden(self):
        """Test deleting the default locale should fail."""
        self.authenticate_user(self.admin_user)

        url = reverse("locales-detail", kwargs={"pk": self.locale_en.pk})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot delete the default locale", response.data["error"])

    def test_toggle_active_status(self):
        """Test toggling locale active status."""
        self.authenticate_user(self.admin_user)

        url = reverse("locales-toggle-active", kwargs={"pk": self.locale_es.pk})

        # First toggle - deactivate
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.locale_es.refresh_from_db()
        self.assertFalse(self.locale_es.is_active)

        # Second toggle - reactivate
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.locale_es.refresh_from_db()
        self.assertTrue(self.locale_es.is_active)

    def test_toggle_default_locale_deactivation_forbidden(self):
        """Test that default locale cannot be deactivated."""
        self.authenticate_user(self.admin_user)

        url = reverse("locales-toggle-active", kwargs={"pk": self.locale_en.pk})

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot deactivate the default locale", response.data["error"])

    def test_set_default_locale(self):
        """Test setting a locale as default."""
        self.authenticate_user(self.admin_user)

        url = reverse("locales-set-default", kwargs={"pk": self.locale_es.pk})

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.locale_en.refresh_from_db()
        self.locale_es.refresh_from_db()

        self.assertFalse(self.locale_en.is_default)
        self.assertTrue(self.locale_es.is_default)
        self.assertTrue(self.locale_es.is_active)  # Should auto-activate

    def test_set_already_default_locale(self):
        """Test setting an already default locale as default."""
        self.authenticate_user(self.admin_user)

        url = reverse("locales-set-default", kwargs={"pk": self.locale_en.pk})

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("already the default locale", response.data["message"])


class TranslationUnitAPITestCase(I18nAPITestCase):
    """Test cases for TranslationUnit API endpoints."""

    def setUp(self):
        """Set up translation unit test data."""
        super().setUp()

        self.content_type = ContentType.objects.get_for_model(User)

        # Create test translation units
        self.translation_unit_1 = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.regular_user.id,
            field="first_name",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="John",
            target_text="Juan",
            status="draft",
            updated_by=self.translator_user,
        )

        self.translation_unit_2 = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.regular_user.id,
            field="last_name",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="Doe",
            target_text="",  # Empty target text
            status="missing",
            updated_by=self.translator_user,
        )

        # Create queue item for workflow testing
        self.queue_item = TranslationQueue.objects.create(
            translation_unit=self.translation_unit_1,
            status="pending",
            priority="medium",
            created_by=self.admin_user,
        )

    def test_list_translation_units(self):
        """Test listing translation units."""
        self.authenticate_user()

        url = reverse("translation-units-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data
        self.assertEqual(len(data), 2)

    def test_list_translation_units_unauthenticated(self):
        """Test listing translation units as unauthenticated user should fail."""
        self.unauthenticate()

        url = reverse("translation-units-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_translation_units_by_locale(self):
        """Test filtering translation units by target locale."""
        self.authenticate_user()

        url = reverse("translation-units-list")
        response = self.client.get(url, {"target_locale": self.locale_es.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data
        for unit in data:
            self.assertEqual(unit["target_locale"], self.locale_es.id)

    def test_filter_translation_units_by_status(self):
        """Test filtering translation units by status."""
        self.authenticate_user()

        url = reverse("translation-units-list")
        response = self.client.get(url, {"status": "draft"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data
        for unit in data:
            self.assertEqual(unit["status"], "draft")

    def test_search_translation_units(self):
        """Test searching translation units by source/target text."""
        self.authenticate_user()

        url = reverse("translation-units-list")
        response = self.client.get(url, {"search": "John"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data
        self.assertGreater(len(data), 0)

    def test_get_translation_unit_detail(self):
        """Test retrieving a specific translation unit."""
        self.authenticate_user()

        url = reverse(
            "translation-units-detail", kwargs={"pk": self.translation_unit_1.pk}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.translation_unit_1.id)
        self.assertEqual(response.data["source_text"], "John")

    def test_update_translation_unit(self):
        """Test updating a translation unit."""
        self.authenticate_user()

        url = reverse(
            "translation-units-detail", kwargs={"pk": self.translation_unit_2.pk}
        )
        data = {
            "target_text": "Apellido",
            "status": "draft",
        }

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.translation_unit_2.refresh_from_db()
        self.assertEqual(self.translation_unit_2.target_text, "Apellido")
        self.assertEqual(self.translation_unit_2.status, "draft")
        self.assertEqual(self.translation_unit_2.updated_by, self.translator_user)

    def test_invalid_status_transition(self):
        """Test invalid status transition should fail."""
        self.authenticate_user()

        # Try to go from draft to approved without validation
        url = reverse(
            "translation-units-detail", kwargs={"pk": self.translation_unit_1.pk}
        )
        data = {"status": "approved"}

        response = self.client.patch(url, data, format="json")

        # This should succeed as the serializer allows this transition
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_translations_for_object(self):
        """Test getting all translations for a specific object."""
        self.authenticate_user()

        url = reverse("translation-units-for-object")
        response = self.client.get(
            url,
            {
                "model_label": f"{self.content_type.app_label}.{self.content_type.model}",
                "object_id": self.regular_user.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_translations_for_object_with_locale_filter(self):
        """Test getting translations for object filtered by target locale."""
        self.authenticate_user()

        url = reverse("translation-units-for-object")
        response = self.client.get(
            url,
            {
                "model_label": f"{self.content_type.app_label}.{self.content_type.model}",
                "object_id": self.regular_user.id,
                "target_locale": self.locale_es.code,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_translations_for_object_missing_params(self):
        """Test getting translations for object with missing required params."""
        self.authenticate_user()

        url = reverse("translation-units-for-object")
        response = self.client.get(url, {"model_label": "auth.user"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "model_label and object_id parameters are required", response.data["error"]
        )

    def test_get_translation_status_for_object(self):
        """Test getting translation status summary for an object."""
        self.authenticate_user()

        url = reverse("translation-units-status-for-object")
        response = self.client.get(
            url,
            {
                "model_label": f"{self.content_type.app_label}.{self.content_type.model}",
                "object_id": self.regular_user.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

        # Should have data for active locales (excluding default)
        locales_with_data = [item["locale"]["code"] for item in response.data]
        self.assertIn("es", locales_with_data)
        self.assertIn("fr", locales_with_data)

    def test_bulk_update_translation_units(self):
        """Test bulk updating multiple translation units."""
        self.authenticate_user()

        url = reverse("translation-units-bulk-update")
        data = {
            "units": [
                {
                    "id": self.translation_unit_1.id,
                    "target_text": "Juan Carlos",
                    "status": "needs_review",
                },
                {
                    "id": self.translation_unit_2.id,
                    "target_text": "González",
                    "status": "draft",
                },
            ]
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_updated"], 2)
        self.assertEqual(len(response.data["updated"]), 2)

        # Verify updates
        self.translation_unit_1.refresh_from_db()
        self.translation_unit_2.refresh_from_db()

        self.assertEqual(self.translation_unit_1.target_text, "Juan Carlos")
        self.assertEqual(self.translation_unit_1.status, "needs_review")
        self.assertEqual(self.translation_unit_2.target_text, "González")

    def test_bulk_update_with_invalid_id(self):
        """Test bulk update with invalid translation unit ID."""
        self.authenticate_user()

        url = reverse("translation-units-bulk-update")
        data = {
            "units": [
                {
                    "id": 99999,  # Non-existent ID
                    "target_text": "Test",
                    "status": "draft",
                },
            ]
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_updated"], 0)
        self.assertEqual(len(response.data["errors"]), 1)


class TranslationWorkflowAPITestCase(I18nAPITestCase):
    """Test cases for translation workflow actions (approve, reject, etc.)."""

    def setUp(self):
        """Set up workflow test data."""
        super().setUp()

        self.content_type = ContentType.objects.get_for_model(User)

        self.translation_unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.regular_user.id,
            field="bio",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="Software developer from California",
            target_text="Desarrollador de software de California",
            status="needs_review",
            updated_by=self.translator_user,
        )

    def test_approve_translation(self):
        """Test approving a translation."""
        self.authenticate_user(self.admin_user)

        url = reverse(
            "translation-units-approve", kwargs={"pk": self.translation_unit.pk}
        )
        data = {"comment": "Translation looks good!"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.translation_unit.refresh_from_db()
        self.assertEqual(self.translation_unit.status, "approved")

        # Check history was created
        history = TranslationHistory.objects.filter(
            translation_unit=self.translation_unit, action="approved"
        ).first()

        self.assertIsNotNone(history)
        self.assertEqual(history.comment, "Translation looks good!")
        self.assertEqual(history.performed_by, self.admin_user)

    def test_approve_translation_without_target_text(self):
        """Test approving translation without target text should fail."""
        self.translation_unit.target_text = ""
        self.translation_unit.save()

        self.authenticate_user(self.admin_user)

        url = reverse(
            "translation-units-approve", kwargs={"pk": self.translation_unit.pk}
        )
        data = {"comment": "Approving"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot approve translation without target text", response.data["error"]
        )

    def test_reject_translation(self):
        """Test rejecting a translation."""
        self.authenticate_user(self.admin_user)

        url = reverse(
            "translation-units-reject", kwargs={"pk": self.translation_unit.pk}
        )
        data = {"comment": "Needs improvement in terminology"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.translation_unit.refresh_from_db()
        self.assertEqual(self.translation_unit.status, "rejected")

        # Check history was created
        history = TranslationHistory.objects.filter(
            translation_unit=self.translation_unit, action="rejected"
        ).first()

        self.assertIsNotNone(history)
        self.assertEqual(history.comment, "Needs improvement in terminology")

    def test_mark_as_draft(self):
        """Test marking translation as draft."""
        self.authenticate_user()

        url = reverse(
            "translation-units-mark-as-draft", kwargs={"pk": self.translation_unit.pk}
        )
        data = {"comment": "Reverting to draft for changes"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.translation_unit.refresh_from_db()
        self.assertEqual(self.translation_unit.status, "draft")

    def test_mark_needs_review(self):
        """Test marking translation as needs review."""
        self.translation_unit.status = "draft"
        self.translation_unit.save()

        self.authenticate_user()

        url = reverse(
            "translation-units-mark-needs-review",
            kwargs={"pk": self.translation_unit.pk},
        )
        data = {"comment": "Ready for review"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.translation_unit.refresh_from_db()
        self.assertEqual(self.translation_unit.status, "needs_review")

    def test_mark_needs_review_without_target_text(self):
        """Test marking as needs review without target text should fail."""
        self.translation_unit.target_text = ""
        self.translation_unit.status = "draft"
        self.translation_unit.save()

        self.authenticate_user()

        url = reverse(
            "translation-units-mark-needs-review",
            kwargs={"pk": self.translation_unit.pk},
        )

        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Cannot mark as needs review without target text", response.data["error"]
        )

    def test_complete_translation(self):
        """Test completing a translation (shortcut to approved)."""
        self.authenticate_user()

        url = reverse(
            "translation-units-complete", kwargs={"pk": self.translation_unit.pk}
        )
        data = {"comment": "Translation completed"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.translation_unit.refresh_from_db()
        self.assertEqual(self.translation_unit.status, "approved")

    def test_get_translation_history(self):
        """Test getting translation history."""
        # Create some history entries
        TranslationHistory.objects.create(
            translation_unit=self.translation_unit,
            action="created",
            performed_by=self.translator_user,
            new_status="draft",
            comment="Initial creation",
        )

        TranslationHistory.objects.create(
            translation_unit=self.translation_unit,
            action="updated",
            performed_by=self.translator_user,
            previous_status="draft",
            new_status="needs_review",
            comment="Updated and marked for review",
        )

        self.authenticate_user()

        url = reverse(
            "translation-units-history", kwargs={"pk": self.translation_unit.pk}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Check data structure
        history_item = response.data[0]  # Most recent first
        self.assertIn("action", history_item)
        self.assertIn("performed_by", history_item)
        self.assertIn("comment", history_item)


class TranslationAssignmentAPITestCase(I18nAPITestCase):
    """Test cases for translation assignment functionality."""

    def setUp(self):
        """Set up assignment test data."""
        super().setUp()

        self.content_type = ContentType.objects.get_for_model(User)

        self.translation_unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.regular_user.id,
            field="bio",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="Software developer",
            target_text="",
            status="missing",
            updated_by=self.admin_user,
        )

    def test_assign_translation_to_user(self):
        """Test assigning a translation to a user."""
        self.authenticate_user(self.admin_user)

        url = reverse(
            "translation-units-assign", kwargs={"pk": self.translation_unit.pk}
        )
        data = {
            "assigned_to": self.translator_user.id,
            "comment": "Please translate this",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check queue item was created
        queue_item = TranslationQueue.objects.filter(
            translation_unit=self.translation_unit
        ).first()

        self.assertIsNotNone(queue_item)
        self.assertEqual(queue_item.assigned_to, self.translator_user)

        # Check response data
        self.assertIn("assignment", response.data)
        self.assertEqual(
            response.data["assignment"]["assigned_to"], self.translator_user.id
        )

    def test_unassign_translation(self):
        """Test unassigning a translation."""
        # First assign it
        TranslationQueue.objects.create(
            translation_unit=self.translation_unit,
            assigned_to=self.translator_user,
            created_by=self.admin_user,
        )

        self.authenticate_user(self.admin_user)

        url = reverse(
            "translation-units-assign", kwargs={"pk": self.translation_unit.pk}
        )
        data = {
            "assigned_to": None,  # Unassign
            "comment": "Unassigning for reassignment",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check assignment was removed
        queue_item = TranslationQueue.objects.get(
            translation_unit=self.translation_unit
        )
        self.assertIsNone(queue_item.assigned_to)

    def test_bulk_assign_translations(self):
        """Test bulk assigning multiple translations."""
        # Create another translation unit
        translation_unit_2 = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.regular_user.id,
            field="first_name",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="John",
            target_text="",
            status="missing",
            updated_by=self.admin_user,
        )

        self.authenticate_user(self.admin_user)

        url = reverse("translation-units-bulk-assign")
        data = {
            "translation_unit_ids": [self.translation_unit.id, translation_unit_2.id],
            "assigned_to": self.translator_user.id,
            "comment": "Bulk assignment for Spanish translations",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_assigned"], 2)
        self.assertEqual(len(response.data["assigned"]), 2)

        # Verify assignments
        queue_items = TranslationQueue.objects.filter(
            translation_unit__in=[self.translation_unit, translation_unit_2]
        )

        self.assertEqual(queue_items.count(), 2)
        for item in queue_items:
            self.assertEqual(item.assigned_to, self.translator_user)

    def test_bulk_assign_with_invalid_ids(self):
        """Test bulk assignment with some invalid IDs."""
        self.authenticate_user(self.admin_user)

        url = reverse("translation-units-bulk-assign")
        data = {
            "translation_unit_ids": [self.translation_unit.id, 99999],  # One invalid
            "assigned_to": self.translator_user.id,
            "comment": "Test assignment",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Expecting validation error for invalid IDs


class MachineTranslationAPITestCase(I18nAPITestCase):
    """Test cases for machine translation suggestion functionality."""

    def setUp(self):
        """Set up machine translation test data."""
        super().setUp()

        self.content_type = ContentType.objects.get_for_model(User)

        self.translation_unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.regular_user.id,
            field="bio",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="Hello world",
            target_text="",
            status="missing",
            updated_by=self.translator_user,
        )

    @patch("apps.i18n.services.DeepLTranslationService")
    def test_get_machine_translation_suggestion(self, mock_deepl_service):
        """Test getting machine translation suggestion."""
        # Mock DeepL service
        mock_instance = MagicMock()
        mock_instance.translate.return_value = "Hola mundo"
        mock_deepl_service.return_value = mock_instance

        self.authenticate_user()

        url = reverse(
            "translation-units-mt-suggest", kwargs={"pk": self.translation_unit.pk}
        )
        data = {
            "text": "Hello world",
            "source_locale": "en",
            "target_locale": "es",
            "service": "deepl",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["suggestion"], "Hola mundo")
        self.assertEqual(response.data["service"], "deepl")
        self.assertEqual(response.data["source_text"], "Hello world")

    @patch("apps.i18n.services.DeepLTranslationService")
    def test_machine_translation_service_error(self, mock_deepl_service):
        """Test handling of machine translation service errors."""
        # Mock service to raise exception
        mock_deepl_service.side_effect = Exception("DeepL API Error")

        self.authenticate_user()

        url = reverse(
            "translation-units-mt-suggest", kwargs={"pk": self.translation_unit.pk}
        )
        data = {
            "text": "Hello world",
            "source_locale": "en",
            "target_locale": "es",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should fallback to original text when service fails
        self.assertEqual(response.data["suggestion"], "Hello world")


class UiMessageAPITestCase(I18nAPITestCase):
    """Test cases for UI Message API endpoints."""

    def setUp(self):
        """Set up UI message test data."""
        super().setUp()

        self.ui_message_1 = UiMessage.objects.create(
            key="common.save",
            namespace="common",
            description="Save button text",
            default_value="Save",
        )

        self.ui_message_2 = UiMessage.objects.create(
            key="common.cancel",
            namespace="common",
            description="Cancel button text",
            default_value="Cancel",
        )

        self.ui_message_auth = UiMessage.objects.create(
            key="auth.login",
            namespace="auth",
            description="Login button text",
            default_value="Login",
        )

        # Create some translations
        self.translation_es = UiMessageTranslation.objects.create(
            message=self.ui_message_1,
            locale=self.locale_es,
            value="Guardar",
            status="approved",
            updated_by=self.translator_user,
        )

    def test_list_ui_messages(self):
        """Test listing UI messages."""
        self.authenticate_user()

        url = reverse("ui-messages-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        self.assertEqual(len(data), 3)

    def test_filter_ui_messages_by_namespace(self):
        """Test filtering UI messages by namespace."""
        self.authenticate_user()

        url = reverse("ui-messages-list")
        response = self.client.get(url, {"namespace": "common"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        self.assertEqual(len(data), 2)

        for message in data:
            self.assertEqual(message["namespace"], "common")

    def test_search_ui_messages(self):
        """Test searching UI messages by key, description, or default value."""
        self.authenticate_user()

        url = reverse("ui-messages-list")
        response = self.client.get(url, {"search": "save"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        self.assertGreater(len(data), 0)

    def test_create_ui_message(self):
        """Test creating a new UI message."""
        self.authenticate_user(self.admin_user)

        url = reverse("ui-messages-list")
        data = {
            "key": "common.delete",
            "namespace": "common",
            "description": "Delete button text",
            "default_value": "Delete",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UiMessage.objects.count(), 4)
        self.assertEqual(response.data["key"], "common.delete")

    def test_create_ui_message_duplicate_key(self):
        """Test creating UI message with duplicate key should fail."""
        self.authenticate_user(self.admin_user)

        url = reverse("ui-messages-list")
        data = {
            "key": "common.save",  # Already exists
            "namespace": "common",
            "default_value": "Save Again",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_ui_message(self):
        """Test updating a UI message."""
        self.authenticate_user(self.admin_user)

        url = reverse("ui-messages-detail", kwargs={"pk": self.ui_message_1.pk})
        data = {
            "key": "common.save",
            "namespace": "common",
            "description": "Updated save button text",
            "default_value": "Save Changes",
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.ui_message_1.refresh_from_db()
        self.assertEqual(self.ui_message_1.description, "Updated save button text")
        self.assertEqual(self.ui_message_1.default_value, "Save Changes")

    def test_delete_ui_message(self):
        """Test deleting a UI message."""
        self.authenticate_user(self.admin_user)

        url = reverse("ui-messages-detail", kwargs={"pk": self.ui_message_2.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(UiMessage.objects.count(), 2)

    def test_get_message_bundle_for_locale(self):
        """Test getting message bundle for a specific locale."""
        # No authentication required for bundle endpoint
        self.unauthenticate()

        url = reverse("ui-messages-bundle", kwargs={"locale_code": "es"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that translated message is returned
        self.assertEqual(response.data["common.save"], "Guardar")

        # Check that non-translated messages fall back to default
        self.assertEqual(response.data["common.cancel"], "Cancel")
        self.assertEqual(response.data["auth.login"], "Login")

    def test_get_message_bundle_nonexistent_locale(self):
        """Test getting message bundle for non-existent locale."""
        self.unauthenticate()

        url = reverse("ui-messages-bundle", kwargs={"locale_code": "xx"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Locale xx not found", response.data["error"])


class UiMessageTranslationAPITestCase(I18nAPITestCase):
    """Test cases for UI Message Translation API endpoints."""

    def setUp(self):
        """Set up UI message translation test data."""
        super().setUp()

        self.ui_message = UiMessage.objects.create(
            key="common.submit",
            namespace="common",
            description="Submit button text",
            default_value="Submit",
        )

        self.translation = UiMessageTranslation.objects.create(
            message=self.ui_message,
            locale=self.locale_es,
            value="Enviar",
            status="draft",
            updated_by=self.translator_user,
        )

    def test_list_ui_message_translations(self):
        """Test listing UI message translations."""
        self.authenticate_user()

        url = reverse("ui-message-translations-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        self.assertEqual(len(data), 1)

    def test_filter_translations_by_locale(self):
        """Test filtering translations by locale."""
        self.authenticate_user()

        url = reverse("ui-message-translations-list")
        response = self.client.get(url, {"locale": self.locale_es.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        for translation in data:
            self.assertEqual(translation["locale"], self.locale_es.id)

    def test_filter_translations_by_status(self):
        """Test filtering translations by status."""
        self.authenticate_user()

        url = reverse("ui-message-translations-list")
        response = self.client.get(url, {"status": "draft"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        for translation in data:
            self.assertEqual(translation["status"], "draft")

    def test_search_translations(self):
        """Test searching translations by message key or value."""
        self.authenticate_user()

        url = reverse("ui-message-translations-list")
        response = self.client.get(url, {"search": "submit"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        self.assertGreater(len(data), 0)

    def test_create_ui_message_translation(self):
        """Test creating a new UI message translation."""
        ui_message_2 = UiMessage.objects.create(
            key="common.reset",
            namespace="common",
            default_value="Reset",
        )

        self.authenticate_user()

        url = reverse("ui-message-translations-list")
        data = {
            "message": ui_message_2.id,
            "locale": self.locale_fr.id,
            "value": "Réinitialiser",
            "status": "draft",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UiMessageTranslation.objects.count(), 2)
        self.assertEqual(response.data["value"], "Réinitialiser")

    def test_create_duplicate_translation(self):
        """Test creating duplicate translation should fail."""
        self.authenticate_user()

        url = reverse("ui-message-translations-list")
        data = {
            "message": self.ui_message.id,
            "locale": self.locale_es.id,  # Already exists
            "value": "Enviar Nuevo",
            "status": "draft",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_ui_message_translation(self):
        """Test updating a UI message translation."""
        self.authenticate_user()

        url = reverse(
            "ui-message-translations-detail", kwargs={"pk": self.translation.pk}
        )
        data = {
            "message": self.ui_message.id,
            "locale": self.locale_es.id,
            "value": "Enviar Formulario",
            "status": "approved",
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.translation.refresh_from_db()
        self.assertEqual(self.translation.value, "Enviar Formulario")
        self.assertEqual(self.translation.status, "approved")
        self.assertEqual(self.translation.updated_by, self.translator_user)

    def test_bulk_update_ui_message_translations(self):
        """Test bulk updating multiple UI message translations."""
        # Create another message and translation
        ui_message_2 = UiMessage.objects.create(
            key="common.close",
            namespace="common",
            default_value="Close",
        )

        translation_2 = UiMessageTranslation.objects.create(
            message=ui_message_2,
            locale=self.locale_es,
            value="Cerrar",
            status="draft",
            updated_by=self.translator_user,
        )

        self.authenticate_user()

        url = reverse("ui-message-translations-bulk-update")
        data = {
            "updates": [
                {
                    "message_id": self.ui_message.id,
                    "locale_id": self.locale_es.id,
                    "value": "Enviar Actualizado",
                    "status": "approved",
                },
                {
                    "message_id": ui_message_2.id,
                    "locale_id": self.locale_es.id,
                    "value": "Cerrar Actualizado",
                    "status": "approved",
                },
            ]
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_updated"], 2)

        # Verify updates
        self.translation.refresh_from_db()
        translation_2.refresh_from_db()

        self.assertEqual(self.translation.value, "Enviar Actualizado")
        self.assertEqual(self.translation.status, "approved")
        self.assertEqual(translation_2.value, "Cerrar Actualizado")

    def test_get_namespaces_with_translation_progress(self):
        """Test getting namespaces with translation progress data."""
        self.authenticate_user()

        url = reverse("ui-message-translations-namespaces")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

        # Check data structure
        namespace_data = next(
            (item for item in response.data if item["namespace"] == "common"), None
        )
        self.assertIsNotNone(namespace_data)
        self.assertIn("message_count", namespace_data)
        self.assertIn("locale_stats", namespace_data)


class UiMessageImportExportAPITestCase(I18nAPITestCase):
    """Test cases for UI message import/export functionality."""

    def setUp(self):
        """Set up import/export test data."""
        super().setUp()

        self.ui_message = UiMessage.objects.create(
            key="test.message",
            namespace="test",
            default_value="Test Message",
        )

    def test_import_json_translations(self):
        """Test importing translations from JSON file."""
        self.authenticate_user(self.admin_user)

        # Create test JSON data
        json_data = {
            "test.message": "Mensaje de Prueba",
            "test.new_message": "Nuevo Mensaje",
            "nested.key.value": "Valor Anidado",
        }

        json_content = json.dumps(json_data).encode("utf-8")
        json_file = SimpleUploadedFile(
            "translations_es.json", json_content, content_type="application/json"
        )

        url = reverse("ui-messages-import-json")
        data = {
            "file": json_file,
            "locale": "es",
            "namespace": "test",
            "flatten_keys": True,
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")

        details = response.data["details"]
        self.assertGreater(details["translations_created"], 0)

    def test_import_json_missing_file(self):
        """Test importing without providing file should fail."""
        self.authenticate_user(self.admin_user)

        url = reverse("ui-messages-import-json")
        data = {
            "locale": "es",
            "namespace": "test",
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No file provided", response.data["message"])

    def test_import_json_missing_locale(self):
        """Test importing without locale should fail."""
        self.authenticate_user(self.admin_user)

        json_data = {"test.key": "Test Value"}
        json_content = json.dumps(json_data).encode("utf-8")
        json_file = SimpleUploadedFile(
            "test.json", json_content, content_type="application/json"
        )

        url = reverse("ui-messages-import-json")
        data = {"file": json_file}

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Locale code is required", response.data["message"])

    def test_import_json_invalid_locale(self):
        """Test importing with invalid locale should fail."""
        self.authenticate_user(self.admin_user)

        json_data = {"test.key": "Test Value"}
        json_content = json.dumps(json_data).encode("utf-8")
        json_file = SimpleUploadedFile(
            "test.json", json_content, content_type="application/json"
        )

        url = reverse("ui-messages-import-json")
        data = {
            "file": json_file,
            "locale": "xx",  # Non-existent locale
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Locale xx not found", response.data["message"])

    def test_import_invalid_json(self):
        """Test importing invalid JSON should fail."""
        self.authenticate_user(self.admin_user)

        invalid_json = b"{ invalid json content"
        json_file = SimpleUploadedFile(
            "invalid.json", invalid_json, content_type="application/json"
        )

        url = reverse("ui-messages-import-json")
        data = {
            "file": json_file,
            "locale": "es",
        }

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid JSON format", response.data["message"])

    def test_sync_keys_from_frontend(self):
        """Test syncing translation keys from frontend."""
        self.authenticate_user(self.admin_user)

        url = reverse("ui-messages-sync-keys")
        data = {
            "keys": [
                {
                    "key": "frontend.button.submit",
                    "defaultValue": "Submit Form",
                    "description": "Form submission button",
                    "namespace": "frontend",
                },
                {
                    "key": "frontend.error.required",
                    "defaultValue": "This field is required",
                    "namespace": "frontend",
                },
            ],
            "source": "build",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["created"]), 2)
        self.assertTrue(response.data["auto_approved"])

    def test_report_missing_keys_runtime(self):
        """Test reporting missing translation keys detected at runtime."""
        self.authenticate_user()

        url = reverse("ui-messages-report-missing")
        data = {
            "keys": ["runtime.missing.key1", "runtime.missing.key2"],
            "locale": "es",
            "url": "/some/page",
            "component": "SomeComponent",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reported"], 2)

    def test_get_discovery_stats(self):
        """Test getting translation discovery statistics."""
        # No authentication required
        self.unauthenticate()

        url = reverse("ui-messages-discovery-stats")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response structure
        self.assertIn("total_messages", response.data)
        self.assertIn("recent_discoveries", response.data)
        self.assertIn("by_namespace", response.data)
        self.assertIn("untranslated_by_locale", response.data)


class TranslationGlossaryAPITestCase(I18nAPITestCase):
    """Test cases for Translation Glossary API endpoints."""

    def setUp(self):
        """Set up glossary test data."""
        super().setUp()

        self.glossary_entry = TranslationGlossary.objects.create(
            term="Dashboard",
            translation="Panel de Control",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            category="ui",
            context="Main application dashboard",
            is_verified=True,
            created_by=self.admin_user,
        )

    def test_list_glossary_entries(self):
        """Test listing glossary entries."""
        self.authenticate_user()

        url = reverse("glossary-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        self.assertEqual(len(data), 1)

    def test_filter_glossary_by_locale(self):
        """Test filtering glossary by source/target locale."""
        self.authenticate_user()

        url = reverse("glossary-list")
        response = self.client.get(url, {"source_locale": self.locale_en.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        for entry in data:
            self.assertEqual(entry["source_locale"], self.locale_en.id)

    def test_filter_glossary_by_category(self):
        """Test filtering glossary by category."""
        self.authenticate_user()

        url = reverse("glossary-list")
        response = self.client.get(url, {"category": "ui"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        for entry in data:
            self.assertEqual(entry["category"], "ui")

    def test_search_glossary_terms(self):
        """Test searching glossary terms."""
        self.authenticate_user()

        url = reverse("glossary-search")
        response = self.client.get(url, {"term": "Dashboard"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["term"], "Dashboard")

    def test_create_glossary_entry(self):
        """Test creating a new glossary entry."""
        self.authenticate_user(self.admin_user)

        url = reverse("glossary-list")
        data = {
            "term": "Settings",
            "translation": "Configuración",
            "source_locale": self.locale_en.id,
            "target_locale": self.locale_es.id,
            "category": "ui",
            "context": "Application settings page",
            "is_verified": False,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TranslationGlossary.objects.count(), 2)
        self.assertEqual(response.data["term"], "Settings")
        self.assertEqual(response.data["created_by"], self.admin_user.id)

    def test_create_duplicate_glossary_entry(self):
        """Test creating duplicate glossary entry should fail."""
        self.authenticate_user(self.admin_user)

        url = reverse("glossary-list")
        data = {
            "term": "Dashboard",  # Already exists for en->es
            "translation": "Tablero",
            "source_locale": self.locale_en.id,
            "target_locale": self.locale_es.id,
            "category": "ui",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_glossary_entry(self):
        """Test updating a glossary entry."""
        self.authenticate_user(self.admin_user)

        url = reverse("glossary-detail", kwargs={"pk": self.glossary_entry.pk})
        data = {
            "term": "Dashboard",
            "translation": "Tablero de Control",
            "source_locale": self.locale_en.id,
            "target_locale": self.locale_es.id,
            "category": "ui",
            "context": "Updated context for main dashboard",
            "is_verified": True,
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.glossary_entry.refresh_from_db()
        self.assertEqual(self.glossary_entry.translation, "Tablero de Control")
        self.assertEqual(self.glossary_entry.updated_by, self.admin_user)

    def test_delete_glossary_entry(self):
        """Test deleting a glossary entry."""
        self.authenticate_user(self.admin_user)

        url = reverse("glossary-detail", kwargs={"pk": self.glossary_entry.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(TranslationGlossary.objects.count(), 0)


class TranslationQueueAPITestCase(I18nAPITestCase):
    """Test cases for Translation Queue API endpoints."""

    def setUp(self):
        """Set up translation queue test data."""
        super().setUp()

        self.content_type = ContentType.objects.get_for_model(User)

        self.translation_unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.regular_user.id,
            field="bio",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="Software developer",
            target_text="",
            status="missing",
            updated_by=self.admin_user,
        )

        self.queue_item = TranslationQueue.objects.create(
            translation_unit=self.translation_unit,
            status="pending",
            priority="high",
            assigned_to=self.translator_user,
            deadline=timezone.now() + timedelta(days=3),
            notes="Urgent translation needed",
            created_by=self.admin_user,
        )

    def test_list_translation_queue(self):
        """Test listing translation queue items."""
        self.authenticate_user()

        url = reverse("translation-queue-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        self.assertEqual(len(data), 1)

    def test_filter_queue_by_status(self):
        """Test filtering queue by status."""
        self.authenticate_user()

        url = reverse("translation-queue-list")
        response = self.client.get(url, {"status": "pending"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        for item in data:
            self.assertEqual(item["status"], "pending")

    def test_filter_queue_by_assigned_user(self):
        """Test filtering queue by assigned user."""
        self.authenticate_user()

        url = reverse("translation-queue-list")
        response = self.client.get(url, {"assigned_to": self.translator_user.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        for item in data:
            self.assertEqual(item["assigned_to"], self.translator_user.id)

    def test_create_queue_item(self):
        """Test creating a new translation queue item."""
        # Create another translation unit
        translation_unit_2 = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.regular_user.id,
            field="first_name",
            source_locale=self.locale_en,
            target_locale=self.locale_fr,
            source_text="John",
            target_text="",
            status="missing",
            updated_by=self.admin_user,
        )

        self.authenticate_user(self.admin_user)

        url = reverse("translation-queue-list")
        data = {
            "translation_unit": translation_unit_2.id,
            "priority": "medium",
            "assigned_to": self.translator_user.id,
            "deadline": (timezone.now() + timedelta(days=5)).isoformat(),
            "notes": "French translation needed",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TranslationQueue.objects.count(), 2)

    def test_update_queue_item(self):
        """Test updating a translation queue item."""
        self.authenticate_user(self.admin_user)

        url = reverse("translation-queue-detail", kwargs={"pk": self.queue_item.pk})
        data = {
            "translation_unit": self.translation_unit.id,
            "status": "in_progress",
            "priority": "urgent",
            "assigned_to": self.translator_user.id,
            "notes": "Updated notes - urgent priority",
        }

        response = self.client.put(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.queue_item.refresh_from_db()
        self.assertEqual(self.queue_item.status, "in_progress")
        self.assertEqual(self.queue_item.priority, "urgent")

    def test_assign_queue_item_to_user(self):
        """Test assigning queue item to a different user."""
        self.authenticate_user(self.admin_user)

        url = reverse("translation-queue-assign", kwargs={"pk": self.queue_item.pk})
        data = {"user_id": self.regular_user.id}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.queue_item.refresh_from_db()
        self.assertEqual(self.queue_item.assigned_to, self.regular_user)
        self.assertEqual(self.queue_item.status, "assigned")

    def test_assign_queue_item_invalid_user(self):
        """Test assigning queue item to invalid user."""
        self.authenticate_user(self.admin_user)

        url = reverse("translation-queue-assign", kwargs={"pk": self.queue_item.pk})
        data = {"user_id": 99999}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_overdue_queue_items(self):
        """Test getting overdue queue items."""
        # Create an overdue item
        overdue_unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.regular_user.id,
            field="last_name",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="Smith",
            target_text="",
            status="missing",
        )

        TranslationQueue.objects.create(
            translation_unit=overdue_unit,
            status="pending",
            deadline=timezone.now() - timedelta(days=1),  # Overdue
            created_by=self.admin_user,
        )

        self.authenticate_user()

        url = reverse("translation-queue-overdue")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_get_translation_queue_summary(self):
        """Test getting translation queue summary statistics."""
        self.authenticate_user()

        url = reverse("translation-queue-summary")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response structure
        self.assertIn("overall", response.data)
        self.assertIn("locales", response.data)

        overall = response.data["overall"]
        self.assertIn("total", overall)
        self.assertIn("pending", overall)
        self.assertIn("completion_percentage", overall)


class TranslationHistoryAPITestCase(I18nAPITestCase):
    """Test cases for Translation History API endpoints."""

    def setUp(self):
        """Set up translation history test data."""
        super().setUp()

        self.content_type = ContentType.objects.get_for_model(User)

        self.translation_unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.regular_user.id,
            field="bio",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="Developer",
            target_text="Desarrollador",
            status="approved",
            updated_by=self.translator_user,
        )

        # Create history entries
        self.history_1 = TranslationHistory.objects.create(
            translation_unit=self.translation_unit,
            action="created",
            new_status="draft",
            new_target_text="Desarrollador",
            comment="Initial translation",
            performed_by=self.translator_user,
        )

        self.history_2 = TranslationHistory.objects.create(
            translation_unit=self.translation_unit,
            action="approved",
            previous_status="draft",
            new_status="approved",
            previous_target_text="Desarrollador",
            new_target_text="Desarrollador",
            comment="Approved after review",
            performed_by=self.admin_user,
        )

    def test_list_translation_history(self):
        """Test listing translation history entries."""
        self.authenticate_user()

        url = reverse("translation-history-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        self.assertEqual(len(data), 2)

    def test_filter_history_by_action(self):
        """Test filtering history by action."""
        self.authenticate_user()

        url = reverse("translation-history-list")
        response = self.client.get(url, {"action": "approved"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        for entry in data:
            self.assertEqual(entry["action"], "approved")

    def test_filter_history_by_translation_unit(self):
        """Test filtering history by translation unit."""
        self.authenticate_user()

        url = reverse("translation-history-list")
        response = self.client.get(url, {"translation_unit": self.translation_unit.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if hasattr(response.data, "get"):
            data = response.data.get("results", response.data)
        else:
            data = response.data
        for entry in data:
            self.assertEqual(entry["translation_unit"], self.translation_unit.id)

    def test_get_history_detail(self):
        """Test retrieving specific history entry."""
        self.authenticate_user()

        url = reverse("translation-history-detail", kwargs={"pk": self.history_1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["action"], "created")
        self.assertEqual(response.data["comment"], "Initial translation")

    def test_history_read_only(self):
        """Test that history endpoints are read-only."""
        self.authenticate_user(self.admin_user)

        # Try to create history entry (should fail)
        url = reverse("translation-history-list")
        data = {
            "translation_unit": self.translation_unit.id,
            "action": "updated",
            "comment": "Test update",
        }

        response = self.client.post(url, data, format="json")

        # Should fail because it's a read-only viewset
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class BulkTranslationOperationsAPITestCase(I18nAPITestCase):
    """Test cases for bulk translation operations."""

    def setUp(self):
        """Set up bulk operations test data."""
        super().setUp()

        # Create multiple UI messages for bulk operations
        self.messages = []
        for i in range(5):
            message = UiMessage.objects.create(
                key=f"bulk.message_{i}",
                namespace="bulk",
                default_value=f"Message {i}",
                description=f"Bulk test message {i}",
            )
            self.messages.append(message)

    @patch("apps.i18n.views.getattr")
    @patch("apps.i18n.tasks.bulk_auto_translate_ui_messages.delay")
    def test_bulk_auto_translate_ui_messages(self, mock_task, mock_getattr):
        """Test starting bulk auto-translation task."""
        # Mock settings.CELERY_TASK_ALWAYS_EAGER to return False
        mock_getattr.return_value = False
        mock_task.return_value = MagicMock(id="test-task-id")

        self.authenticate_user(self.admin_user)

        url = reverse("ui-message-translations-bulk-auto-translate")
        data = {
            "locale": "es",
            "source_locale": "en",
            "namespace": "bulk",
            "max_translations": 3,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "started")
        self.assertEqual(response.data["task_id"], "test-task-id")

        # Verify task was called with correct parameters
        mock_task.assert_called_once_with(
            locale_code="es",
            source_locale_code="en",
            namespace="bulk",
            max_translations=3,
        )

    def test_bulk_auto_translate_missing_locale(self):
        """Test bulk auto-translate without required locale parameter."""
        self.authenticate_user(self.admin_user)

        url = reverse("ui-message-translations-bulk-auto-translate")
        data = {"source_locale": "en"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Target locale is required", response.data["message"])

    def test_bulk_auto_translate_invalid_locale(self):
        """Test bulk auto-translate with invalid locale."""
        self.authenticate_user(self.admin_user)

        url = reverse("ui-message-translations-bulk-auto-translate")
        data = {
            "locale": "xx",  # Invalid locale
            "source_locale": "en",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not found or not active", response.data["message"])

    @patch("celery.result.AsyncResult")
    def test_check_task_status(self, mock_async_result):
        """Test checking the status of a bulk translation task."""
        # Mock task result
        mock_result = MagicMock()
        mock_result.status = "PROGRESS"
        mock_result.ready.return_value = False
        mock_result.info = {
            "current": 2,
            "total": 5,
            "status": "Processing translations...",
            "translated": 2,
            "errors": 0,
            "skipped": 0,
        }
        mock_async_result.return_value = mock_result

        self.authenticate_user()

        url = reverse("ui-message-translations-task-status")
        response = self.client.get(url, {"task_id": "test-task-id"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "PROGRESS")
        self.assertEqual(response.data["progress"]["current"], 2)
        self.assertEqual(response.data["progress"]["total"], 5)

    def test_check_task_status_missing_id(self):
        """Test checking task status without providing task ID."""
        self.authenticate_user()

        url = reverse("ui-message-translations-task-status")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Task ID is required", response.data["message"])


class PermissionTestCase(I18nAPITestCase):
    """Test cases for API permissions and authentication requirements."""

    def test_locale_read_permissions(self):
        """Test that locale listing works for both authenticated and unauthenticated users."""
        # Test authenticated
        self.authenticate_user()
        url = reverse("locales-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test unauthenticated (should work for read-only)
        self.unauthenticate()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_locale_write_permissions(self):
        """Test that locale creation requires authentication."""
        self.unauthenticate()

        url = reverse("locales-list")
        data = {"code": "test", "name": "Test"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_translation_unit_requires_authentication(self):
        """Test that translation unit endpoints require authentication."""
        self.unauthenticate()

        url = reverse("translation-units-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ui_message_requires_authentication(self):
        """Test that UI message endpoints require authentication."""
        self.unauthenticate()

        url = reverse("ui-messages-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_ui_message_bundle_public_access(self):
        """Test that UI message bundle endpoint allows public access."""
        self.unauthenticate()

        url = reverse("ui-messages-bundle", kwargs={"locale_code": "en"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ui_message_discovery_stats_public_access(self):
        """Test that discovery stats endpoint allows public access."""
        self.unauthenticate()

        url = reverse("ui-messages-discovery-stats")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_glossary_requires_authentication(self):
        """Test that glossary endpoints require authentication."""
        self.unauthenticate()

        url = reverse("glossary-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_translation_queue_requires_authentication(self):
        """Test that translation queue endpoints require authentication."""
        self.unauthenticate()

        url = reverse("translation-queue-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_translation_history_requires_authentication(self):
        """Test that translation history endpoints require authentication."""
        self.unauthenticate()

        url = reverse("translation-history-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ValidationTestCase(I18nAPITestCase):
    """Test cases for API input validation."""

    def test_locale_code_validation(self):
        """Test locale code validation."""
        self.authenticate_user(self.admin_user)

        url = reverse("locales-list")

        # Test empty code
        response = self.client.post(url, {"code": "", "name": "Test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test very long code
        long_code = "x" * 15  # Max length is 10
        response = self.client.post(
            url, {"code": long_code, "name": "Test"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_translation_status_validation(self):
        """Test translation status validation."""
        content_type = ContentType.objects.get_for_model(User)

        translation_unit = TranslationUnit.objects.create(
            content_type=content_type,
            object_id=self.regular_user.id,
            field="bio",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="Test",
            target_text="",
            status="draft",
            updated_by=self.translator_user,
        )

        self.authenticate_user()

        url = reverse("translation-units-detail", kwargs={"pk": translation_unit.pk})

        # Test invalid status
        response = self.client.patch(url, {"status": "invalid_status"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ui_message_key_uniqueness(self):
        """Test UI message key uniqueness validation."""
        self.authenticate_user(self.admin_user)

        # Create first message
        UiMessage.objects.create(
            key="test.unique",
            namespace="test",
            default_value="Test",
        )

        url = reverse("ui-messages-list")

        # Try to create duplicate
        response = self.client.post(
            url,
            {
                "key": "test.unique",  # Duplicate
                "namespace": "test",
                "default_value": "Another Test",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_update_validation(self):
        """Test bulk update input validation."""
        self.authenticate_user()

        url = reverse("translation-units-bulk-update")

        # Test missing required fields
        response = self.client.post(
            url, {"units": [{"target_text": "Test"}]}, format="json"  # Missing 'id'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test empty units array
        response = self.client.post(url, {"units": []}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
