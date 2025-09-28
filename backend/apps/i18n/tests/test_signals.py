from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.cms.models import Page
from apps.i18n.models import Locale, TranslationUnit
from apps.i18n.signals import (
    create_page_translation_units,
    create_translation_units_handler,
    register_model_for_translation,
    store_old_page_data,
)
from apps.i18n.translation import TranslationManager

User = get_user_model()


class PageSignalsTest(TestCase):
    """Test cases for Page model signal handlers."""

    def setUp(self):
        """Set up test data."""

        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale_en, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español", is_active=True
        )

        # Register translatable fields for Page

        TranslationManager.register_translatable_fields("cms.page", ["title", "blocks"])

    @patch("apps.i18n.signals.TranslationManager.create_translation_units")
    def test_create_page_translation_units_on_save(self, mock_create_units):
        """Test that translation units are created when a page is saved."""

        # Create page without triggering signals

        page = Page(
            title="Test Page",
            blocks=[{"type": "text", "value": "Hello World"}],
            locale=self.locale_en,
        )

        page._current_user = self.user

        # Simulate post_save signal directly

        create_page_translation_units(sender=Page, instance=page, created=True)

        # Verify create_translation_units was called once

        mock_create_units.assert_called_once_with(
            obj=page, source_locale=self.locale_en, user=self.user
        )

    def test_create_page_translation_units_skip_flag(self):
        """Test that translation units are skipped when _skip_translation_units flag is set."""

        page = Page.objects.create(
            title="Test Page", slug="test-page-skip-units", locale=self.locale_en
        )

        page._skip_translation_units = True

        with patch(
            "apps.i18n.signals.TranslationManager.create_translation_units"
        ) as mock_create_units:

            create_page_translation_units(sender=Page, instance=page, created=True)

            # Should not be called due to skip flag

            mock_create_units.assert_not_called()

    def test_create_page_translation_units_exception_handling(self):
        """Test that exceptions in translation unit creation don't break page saving."""

        page = Page.objects.create(
            title="Test Page",
            slug="test-page-exception-handling",
            locale=self.locale_en,
        )

        with patch(
            "apps.i18n.signals.TranslationManager.create_translation_units"
        ) as mock_create_units:

            mock_create_units.side_effect = Exception("Translation error")

            # Should not raise exception

            try:

                create_page_translation_units(sender=Page, instance=page, created=True)

            except Exception:

                self.fail("create_page_translation_units raised an exception")

    def test_store_old_page_data_new_page(self):
        """Test storing old page data for a new page."""

        page = Page(title="New Page", locale=self.locale_en)

        # Simulate pre_save signal for new page (pk is None)

        store_old_page_data(sender=Page, instance=page)

        # Should set old values to None for new pages

        self.assertIsNone(getattr(page, "_old_title", None))

        self.assertIsNone(getattr(page, "_old_blocks", None))

    def test_store_old_page_data_existing_page(self):
        """Test storing old page data for an existing page."""

        # Create initial page

        page = Page.objects.create(
            title="Original Title",
            slug="original-title-page",
            blocks=[{"type": "text", "value": "Original content"}],
            locale=self.locale_en,
        )

        # Modify page

        page.title = "Updated Title"

        page.blocks = [{"type": "text", "value": "Updated content"}]

        # Simulate pre_save signal

        store_old_page_data(sender=Page, instance=page)

        # Should store original values

        self.assertEqual(page._old_title, "Original Title")

        self.assertEqual(
            page._old_blocks, [{"type": "text", "value": "Original content"}]
        )


class GenericSignalsTest(TestCase):
    """Test cases for generic signal handlers."""

    def setUp(self):
        """Set up test data."""

        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale_en, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español", is_active=True
        )

    @patch("apps.i18n.signals.TranslationManager.create_translation_units")
    def test_create_translation_units_handler_with_locale(self, mock_create_units):
        """Test generic handler with a model that has a locale field."""

        # Create page without triggering signals

        page = Page(title="Test Page", locale=self.locale_en)

        page._current_user = self.user

        # Call generic handler directly

        create_translation_units_handler(sender=Page, instance=page, created=True)

        # Verify create_translation_units was called with correct locale

        mock_create_units.assert_called_once_with(
            obj=page, source_locale=self.locale_en, user=self.user
        )

    @patch("apps.i18n.signals.TranslationManager.create_translation_units")
    def test_create_translation_units_handler_without_locale(self, mock_create_units):
        """Test generic handler with a model that doesn't have a locale field."""

        # Create a mock object without locale field

        mock_instance = MagicMock()

        mock_instance.locale = None

        # Remove locale attribute to simulate model without locale

        del mock_instance.locale

        mock_instance._current_user = self.user

        # Call generic handler

        create_translation_units_handler(
            sender=type(mock_instance), instance=mock_instance, created=True
        )

        # Should use default locale

        mock_create_units.assert_called_once_with(
            obj=mock_instance,
            source_locale=self.locale_en,  # Default locale
            user=self.user,
        )

    def test_create_translation_units_handler_exception_handling(self):
        """Test that exceptions in generic handler don't break saving."""

        page = Page.objects.create(
            title="Test Page", slug="test-page-generic-handler", locale=self.locale_en
        )

        with patch(
            "apps.i18n.signals.TranslationManager.create_translation_units"
        ) as mock_create_units:

            mock_create_units.side_effect = Exception("Translation error")

            # Should not raise exception

            try:

                create_translation_units_handler(
                    sender=Page, instance=page, created=True
                )

            except Exception:

                self.fail("create_translation_units_handler raised an exception")

    def test_register_model_for_translation(self):
        """Test registering a model for automatic translation."""

        # Create a mock model class

        class MockModel:
            pass

        fields = ["title", "content"]

        with (
            patch("apps.i18n.signals.ContentType.objects.get_for_model") as mock_get_ct,
            patch(
                "apps.i18n.signals.TranslationManager.register_translatable_fields"
            ) as mock_register,
            patch("apps.i18n.signals.post_save.connect") as mock_connect,
        ):

            # Mock ContentType

            mock_ct = MagicMock()

            mock_ct.app_label = "test_app"

            mock_ct.model = "mockmodel"

            mock_get_ct.return_value = mock_ct

            # Call register function

            register_model_for_translation(MockModel, fields)

            # Verify translatable fields were registered

            mock_register.assert_called_once_with("test_app.mockmodel", fields)

            # Verify signal was connected

            mock_connect.assert_called_once_with(
                create_translation_units_handler, sender=MockModel, weak=False
            )

    def test_register_model_for_translation_without_fields(self):
        """Test registering a model without specifying fields."""

        class MockModel:
            pass

        with (
            patch(
                "apps.i18n.signals.TranslationManager.register_translatable_fields"
            ) as mock_register,
            patch("apps.i18n.signals.post_save.connect") as mock_connect,
        ):

            # Call register function without fields

            register_model_for_translation(MockModel)

            # Fields registration should not be called

            mock_register.assert_not_called()

            # Signal should still be connected

            mock_connect.assert_called_once_with(
                create_translation_units_handler, sender=MockModel, weak=False
            )


class SignalIntegrationTest(TestCase):
    """Integration tests for signal handlers working together."""

    def setUp(self):
        """Set up test data."""

        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale_en, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español", is_active=True
        )

        # Register translatable fields for Page

        TranslationManager.register_translatable_fields("cms.page", ["title", "blocks"])

    def test_page_save_creates_translation_units(self):
        """Test that saving a page creates translation units."""

        # Create a page

        page = Page.objects.create(
            title="Test Page",
            slug="test-page-integration",
            blocks=[{"type": "text", "value": "Hello World"}],
            locale=self.locale_en,
        )

        # Check that translation units were created

        units = TranslationUnit.objects.filter(
            content_type=ContentType.objects.get_for_model(Page), object_id=page.id
        )

        # Should have units for each target locale (excluding source)

        expected_count = (
            Locale.objects.filter(is_active=True).exclude(id=self.locale_en.id).count()
            * 2
        )  # 2 fields

        self.assertEqual(units.count(), expected_count)

        # Check specific translation units exist

        self.assertTrue(
            units.filter(field="title", target_locale=self.locale_es).exists()
        )

        self.assertTrue(
            units.filter(field="blocks", target_locale=self.locale_es).exists()
        )
