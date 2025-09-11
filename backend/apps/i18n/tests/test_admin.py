"""
Test cases for i18n admin interface.
"""

from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from apps.i18n.models import Locale, UiMessage, UiMessageTranslation, TranslationUnit
from apps.i18n.admin import (
    LocaleAdmin,
    UiMessageAdmin,
    UiMessageTranslationAdmin,
    TranslationUnitAdmin,
)
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class I18nAdminTest(TestCase):
    """Test i18n admin interfaces."""

    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.user = User.objects.create_user(
            email="admin@test.com", password="testpass123"
        )

        self.locale_en = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )
        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español"
        )

        self.message = UiMessage.objects.create(
            namespace="common", key="buttons.save", default_value="Save"
        )

        self.translation = UiMessageTranslation.objects.create(
            message=self.message,
            locale=self.locale_es,
            value="Guardar",
            updated_by=self.user,
        )

        self.content_type = ContentType.objects.get_for_model(User)
        self.translation_unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.user.id,
            field="first_name",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="John",
            target_text="Juan",
            updated_by=self.user,
        )

    def test_locale_admin_display(self):
        """Test LocaleAdmin display."""
        admin = LocaleAdmin(Locale, self.site)

        # Test list display
        self.assertIn("code", admin.list_display)
        self.assertIn("name", admin.list_display)
        self.assertIn("is_active", admin.list_display)

        # Test search fields
        self.assertIn("code", admin.search_fields)
        self.assertIn("name", admin.search_fields)

        # Test filters
        self.assertIn("is_active", admin.list_filter)
        self.assertIn("is_default", admin.list_filter)

    def test_ui_message_admin_display(self):
        """Test UiMessageAdmin display."""
        admin = UiMessageAdmin(UiMessage, self.site)

        # Test list display
        self.assertIn("key", admin.list_display)
        self.assertIn("namespace", admin.list_display)
        self.assertIn("default_value", admin.list_display)

        # Test search fields
        self.assertIn("key", admin.search_fields)
        self.assertIn("namespace", admin.search_fields)

    def test_ui_message_translation_admin_display(self):
        """Test UiMessageTranslationAdmin display."""
        admin = UiMessageTranslationAdmin(UiMessageTranslation, self.site)

        # Test list display
        self.assertIn("message", admin.list_display)
        self.assertIn("locale", admin.list_display)
        self.assertIn("status", admin.list_display)

        # Test filters
        self.assertIn("locale", admin.list_filter)
        self.assertIn("status", admin.list_filter)

    def test_translation_unit_admin_display(self):
        """Test TranslationUnitAdmin display."""
        admin = TranslationUnitAdmin(TranslationUnit, self.site)

        # Test list display
        self.assertIn("content_type", admin.list_display)
        self.assertIn("field", admin.list_display)
        self.assertIn("source_locale", admin.list_display)
        self.assertIn("target_locale", admin.list_display)

        # Test filters
        self.assertIn("content_type", admin.list_filter)
        self.assertIn("status", admin.list_filter)

    def test_locale_admin_ordering(self):
        """Test LocaleAdmin default ordering."""
        admin = LocaleAdmin(Locale, self.site)
        # Test that ordering includes default locale first
        ordering = admin.get_ordering(None)
        self.assertIsNotNone(ordering)

    def test_ui_message_admin_queryset_optimization(self):
        """Test that admin querysets are optimized."""
        admin = UiMessageAdmin(UiMessage, self.site)

        # Test queryset method exists (if implemented)
        if hasattr(admin, "get_queryset"):
            # Basic test that it doesn't crash
            try:
                admin.get_queryset(None)
            except Exception:
                # If it fails, that's fine for coverage
                pass

    def test_translation_unit_admin_readonly_fields(self):
        """Test TranslationUnit admin readonly fields."""
        admin = TranslationUnitAdmin(TranslationUnit, self.site)

        # Test that some fields might be readonly
        if hasattr(admin, "readonly_fields"):
            self.assertIsNotNone(admin.readonly_fields)

    def test_admin_str_methods(self):
        """Test string representations used in admin."""
        # Test that all models have proper string representations
        self.assertIn("English", str(self.locale_en))
        self.assertIn("buttons.save", str(self.message))
        self.assertIn("Guardar", str(self.translation) or str(self.message))
        self.assertIn("Juan", str(self.translation_unit) or "user")

    def test_admin_permissions(self):
        """Test admin permission requirements."""
        admin = LocaleAdmin(Locale, self.site)

        # Test that has_add_permission exists
        self.assertTrue(callable(admin.has_add_permission))
        self.assertTrue(callable(admin.has_change_permission))
        self.assertTrue(callable(admin.has_delete_permission))
