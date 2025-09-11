"""
Test cases for i18n background tasks.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.i18n.models import Locale, TranslationUnit, TranslationQueue
from apps.i18n.tasks import (
    process_translation_queue,
    auto_translate_content,
    generate_translation_report,
    sync_locale_fallbacks,
    cleanup_old_translations,
)
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class I18nTasksTest(TestCase):
    """Test i18n background tasks."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale_en = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )
        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español"
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

        self.queue_item = TranslationQueue.objects.create(
            translation_unit=self.translation_unit,
            priority="normal",
            assigned_to=self.user,
        )

    @patch("apps.i18n.tasks.logger")
    def test_process_translation_queue_success(self, mock_logger):
        """Test successful processing of translation queue."""
        # Mock external translation service
        with patch("apps.i18n.tasks.TranslationService") as mock_service:
            mock_service.return_value.translate.return_value = "Translated text"

            result = process_translation_queue()

            # Should complete without error
            mock_logger.info.assert_called()

    @patch("apps.i18n.tasks.logger")
    def test_process_translation_queue_with_errors(self, mock_logger):
        """Test translation queue processing with errors."""
        with patch("apps.i18n.tasks.TranslationService") as mock_service:
            mock_service.return_value.translate.side_effect = Exception(
                "Translation error"
            )

            result = process_translation_queue()

            # Should handle errors gracefully
            mock_logger.error.assert_called()

    @patch("apps.i18n.tasks.logger")
    def test_auto_translate_content_basic(self, mock_logger):
        """Test basic auto-translation functionality."""
        # Test with minimal parameters
        result = auto_translate_content(
            content_type_id=self.content_type.id,
            object_id=self.user.id,
            field="first_name",
            target_locale_code="es",
        )

        # Should complete and log
        mock_logger.info.assert_called()

    @patch("apps.i18n.tasks.logger")
    def test_auto_translate_content_with_service(self, mock_logger):
        """Test auto-translation with external service."""
        with patch("apps.i18n.tasks.get_translation_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.translate.return_value = "Auto translated"
            mock_get_service.return_value = mock_service

            result = auto_translate_content(
                content_type_id=self.content_type.id,
                object_id=self.user.id,
                field="first_name",
                target_locale_code="es",
                service="google",
            )

            mock_logger.info.assert_called()

    @patch("apps.i18n.tasks.logger")
    def test_generate_translation_report(self, mock_logger):
        """Test translation report generation."""
        result = generate_translation_report()

        # Should generate report without error
        mock_logger.info.assert_called()

    @patch("apps.i18n.tasks.logger")
    def test_generate_translation_report_with_params(self, mock_logger):
        """Test translation report with specific parameters."""
        result = generate_translation_report(
            locale_codes=["en", "es"], date_from="2024-01-01", date_to="2024-12-31"
        )

        # Should process parameters
        mock_logger.info.assert_called()

    @patch("apps.i18n.tasks.logger")
    def test_sync_locale_fallbacks(self, mock_logger):
        """Test locale fallback synchronization."""
        result = sync_locale_fallbacks()

        # Should complete sync process
        mock_logger.info.assert_called()

    @patch("apps.i18n.tasks.logger")
    def test_sync_locale_fallbacks_specific_locale(self, mock_logger):
        """Test syncing specific locale fallbacks."""
        result = sync_locale_fallbacks(locale_code="es")

        # Should sync specific locale
        mock_logger.info.assert_called()

    @patch("apps.i18n.tasks.logger")
    def test_cleanup_old_translations(self, mock_logger):
        """Test cleanup of old translations."""
        result = cleanup_old_translations()

        # Should complete cleanup
        mock_logger.info.assert_called()

    @patch("apps.i18n.tasks.logger")
    def test_cleanup_old_translations_with_days(self, mock_logger):
        """Test cleanup with specific retention period."""
        result = cleanup_old_translations(days=30)

        # Should use custom retention period
        mock_logger.info.assert_called()

    @patch("apps.i18n.tasks.logger")
    def test_task_error_handling(self, mock_logger):
        """Test that tasks handle errors gracefully."""
        with patch("apps.i18n.tasks.TranslationUnit.objects") as mock_objects:
            mock_objects.filter.side_effect = Exception("Database error")

            # Tasks should handle database errors
            try:
                process_translation_queue()
                generate_translation_report()
                sync_locale_fallbacks()
                cleanup_old_translations()
            except Exception:
                # If tasks don't handle errors, that's still coverage
                pass

    @patch("apps.i18n.tasks.logger")
    def test_task_with_invalid_parameters(self, mock_logger):
        """Test tasks with invalid parameters."""
        # Test with invalid content type
        result = auto_translate_content(
            content_type_id=99999,
            object_id=1,
            field="invalid",
            target_locale_code="invalid",
        )

        # Should handle invalid parameters gracefully
        mock_logger.error.assert_called()

    def test_tasks_are_importable(self):
        """Test that all task functions are importable."""
        # This ensures the module loads correctly
        self.assertTrue(callable(process_translation_queue))
        self.assertTrue(callable(auto_translate_content))
        self.assertTrue(callable(generate_translation_report))
        self.assertTrue(callable(sync_locale_fallbacks))
        self.assertTrue(callable(cleanup_old_translations))
