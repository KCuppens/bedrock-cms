"""Tests for i18n translation functionality."""

from unittest.mock import Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.i18n.models import Locale, TranslationUnit, UiMessage, UiMessageTranslation
from apps.i18n.translation import TranslationResolver


class TranslationResolverTestCase(TestCase):
    """Test translation resolver functionality."""

    def setUp(self):
        """Set up test data."""
        # Create test locales
        self.en_locale = Locale.objects.create(
            code="en", name="English", is_default=True
        )
        self.fr_locale = Locale.objects.create(
            code="fr", name="French", fallback_locale=self.en_locale
        )
        self.es_locale = Locale.objects.create(
            code="es", name="Spanish", fallback_locale=self.en_locale
        )

        # Create resolver
        self.resolver = TranslationResolver(self.fr_locale)

    def test_resolver_initialization(self):
        """Test resolver initialization."""
        self.assertEqual(self.resolver.target_locale, self.fr_locale)

        # Should get fallback chain from locale
        with patch.object(self.fr_locale, "get_fallback_chain") as mock_chain:
            mock_chain.return_value = [self.fr_locale, self.en_locale]
            resolver = TranslationResolver(self.fr_locale)
            mock_chain.assert_called_once()

    def test_resolve_field_with_translation(self):
        """Test resolving field with existing translation."""
        # Create test object
        mock_obj = Mock()
        mock_obj.pk = 1

        # Mock content type
        mock_ct = Mock()
        mock_ct.pk = 1

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = mock_ct

            # Create translation unit
            unit = TranslationUnit.objects.create(
                content_type=mock_ct,
                object_id=1,
                field="title",
                source_text="Hello",
                target_text="Bonjour",
                target_locale=self.fr_locale,
                status="approved",
            )

            # Test resolving field
            result = self.resolver.resolve_field(mock_obj, "title")
            self.assertEqual(result, "Bonjour")

    def test_resolve_field_fallback_to_default(self):
        """Test resolving field falls back to default locale."""
        # Create test object
        mock_obj = Mock()
        mock_obj.pk = 2

        # Mock content type
        mock_ct = Mock()
        mock_ct.pk = 1

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = mock_ct

            # Create only English translation (fallback)
            unit = TranslationUnit.objects.create(
                content_type=mock_ct,
                object_id=2,
                field="title",
                source_text="Hello",
                target_text="Hello",
                target_locale=self.en_locale,
                status="approved",
            )

            # Mock fallback chain
            with patch.object(
                self.resolver, "fallback_chain", [self.fr_locale, self.en_locale]
            ):
                result = self.resolver.resolve_field(mock_obj, "title")
                self.assertEqual(result, "Hello")

    def test_resolve_field_with_default_value(self):
        """Test resolving field returns default when no translation exists."""
        # Create test object
        mock_obj = Mock()
        mock_obj.pk = 3

        # Mock content type
        mock_ct = Mock()
        mock_ct.pk = 1

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = mock_ct

            # No translation exists
            result = self.resolver.resolve_field(mock_obj, "title", "Default Title")
            self.assertEqual(result, "Default Title")

    def test_resolve_field_empty_translation(self):
        """Test resolving field skips empty translations."""
        # Create test object
        mock_obj = Mock()
        mock_obj.pk = 4

        # Mock content type
        mock_ct = Mock()
        mock_ct.pk = 1

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = mock_ct

            # Create empty translation in French
            TranslationUnit.objects.create(
                content_type=mock_ct,
                object_id=4,
                field="title",
                source_text="Hello",
                target_text="",  # Empty translation
                target_locale=self.fr_locale,
                status="approved",
            )

            # Create fallback translation in English
            TranslationUnit.objects.create(
                content_type=mock_ct,
                object_id=4,
                field="title",
                source_text="Hello",
                target_text="Hello",
                target_locale=self.en_locale,
                status="approved",
            )

            # Mock fallback chain
            with patch.object(
                self.resolver, "fallback_chain", [self.fr_locale, self.en_locale]
            ):
                result = self.resolver.resolve_field(mock_obj, "title")
                self.assertEqual(result, "Hello")

    def test_resolve_field_non_approved_status(self):
        """Test resolving field skips non-approved translations."""
        # Create test object
        mock_obj = Mock()
        mock_obj.pk = 5

        # Mock content type
        mock_ct = Mock()
        mock_ct.pk = 1

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = mock_ct

            # Create draft translation (not approved)
            TranslationUnit.objects.create(
                content_type=mock_ct,
                object_id=5,
                field="title",
                source_text="Hello",
                target_text="Bonjour Draft",
                target_locale=self.fr_locale,
                status="draft",  # Not approved
            )

            # Create approved fallback
            TranslationUnit.objects.create(
                content_type=mock_ct,
                object_id=5,
                field="title",
                source_text="Hello",
                target_text="Hello",
                target_locale=self.en_locale,
                status="approved",
            )

            # Mock fallback chain
            with patch.object(
                self.resolver, "fallback_chain", [self.fr_locale, self.en_locale]
            ):
                result = self.resolver.resolve_field(mock_obj, "title")
                self.assertEqual(result, "Hello")  # Should use approved fallback

    def test_resolve_multiple_fields(self):
        """Test resolving multiple fields for same object."""
        # Create test object
        mock_obj = Mock()
        mock_obj.pk = 6

        # Mock content type
        mock_ct = Mock()
        mock_ct.pk = 1

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = mock_ct

            # Create translations for multiple fields
            TranslationUnit.objects.create(
                content_type=mock_ct,
                object_id=6,
                field="title",
                source_text="Hello",
                target_text="Bonjour",
                target_locale=self.fr_locale,
                status="approved",
            )

            TranslationUnit.objects.create(
                content_type=mock_ct,
                object_id=6,
                field="description",
                source_text="Description",
                target_text="Description Fr",
                target_locale=self.fr_locale,
                status="approved",
            )

            # Test both fields
            title_result = self.resolver.resolve_field(mock_obj, "title")
            desc_result = self.resolver.resolve_field(mock_obj, "description")

            self.assertEqual(title_result, "Bonjour")
            self.assertEqual(desc_result, "Description Fr")


class TranslationUtilitiesTestCase(TestCase):
    """Test additional translation utilities."""

    def setUp(self):
        """Set up test data."""
        self.en_locale = Locale.objects.create(
            code="en", name="English", is_default=True
        )
        self.fr_locale = Locale.objects.create(
            code="fr", name="French", fallback_locale=self.en_locale
        )

    def test_ui_message_translation(self):
        """Test UI message translation functionality."""
        # Create UI message
        message = UiMessage.objects.create(
            key="welcome_message",
            default_text="Welcome to our site",
            context="homepage",
        )

        # Create translation
        translation = UiMessageTranslation.objects.create(
            message=message,
            locale=self.fr_locale,
            translated_text="Bienvenue sur notre site",
        )

        # Test retrieval
        self.assertEqual(translation.translated_text, "Bienvenue sur notre site")
        self.assertEqual(translation.locale, self.fr_locale)
        self.assertEqual(translation.message, message)

    def test_translation_unit_status_choices(self):
        """Test translation unit status choices."""
        # Create test object
        mock_obj = Mock()
        mock_obj.pk = 1

        # Mock content type
        mock_ct = Mock()
        mock_ct.pk = 1

        # Test different status values
        statuses = ["draft", "pending", "approved", "rejected"]

        for status in statuses:
            unit = TranslationUnit.objects.create(
                content_type=mock_ct,
                object_id=1,
                field=f"field_{status}",
                source_text="Source",
                target_text=f"Target {status}",
                target_locale=self.fr_locale,
                status=status,
            )

            self.assertEqual(unit.status, status)

    def test_locale_fallback_chain(self):
        """Test locale fallback chain functionality."""
        # Create chain: es -> fr -> en
        es_locale = Locale.objects.create(
            code="es", name="Spanish", fallback_locale=self.fr_locale
        )

        # Test fallback chain
        chain = es_locale.get_fallback_chain()
        expected = [es_locale, self.fr_locale, self.en_locale]
        self.assertEqual(chain, expected)

    def test_content_type_caching(self):
        """Test that content type lookups are efficient."""
        # Create test object
        mock_obj = Mock()
        mock_obj.pk = 1

        resolver = TranslationResolver(self.fr_locale)

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_ct = Mock()
            mock_ct.pk = 1
            mock_get_ct.return_value = mock_ct

            # Multiple calls should use the same content type
            resolver.resolve_field(mock_obj, "field1", "default")
            resolver.resolve_field(mock_obj, "field2", "default")

            # Should be called for each resolve_field call
            self.assertEqual(mock_get_ct.call_count, 2)


class TranslationIntegrationTestCase(TestCase):
    """Integration tests for translation functionality."""

    def setUp(self):
        """Set up integration test data."""
        self.en_locale = Locale.objects.create(
            code="en", name="English", is_default=True
        )
        self.fr_locale = Locale.objects.create(
            code="fr", name="French", fallback_locale=self.en_locale
        )

    def test_translation_workflow(self):
        """Test complete translation workflow."""
        # Create test object
        mock_obj = Mock()
        mock_obj.pk = 1

        # Mock content type
        mock_ct = Mock()
        mock_ct.pk = 1

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = mock_ct

            # 1. Create source content translation
            source_unit = TranslationUnit.objects.create(
                content_type=mock_ct,
                object_id=1,
                field="title",
                source_text="Original Title",
                target_text="Original Title",
                target_locale=self.en_locale,
                status="approved",
            )

            # 2. Create target translation in draft
            target_unit = TranslationUnit.objects.create(
                content_type=mock_ct,
                object_id=1,
                field="title",
                source_text="Original Title",
                target_text="Titre Original",
                target_locale=self.fr_locale,
                status="draft",
            )

            # 3. Resolver should use English fallback (draft not approved)
            resolver = TranslationResolver(self.fr_locale)
            with patch.object(
                resolver, "fallback_chain", [self.fr_locale, self.en_locale]
            ):
                result = resolver.resolve_field(mock_obj, "title")
                self.assertEqual(result, "Original Title")

            # 4. Approve French translation
            target_unit.status = "approved"
            target_unit.save()

            # 5. Now should use French translation
            result = resolver.resolve_field(mock_obj, "title")
            self.assertEqual(result, "Titre Original")

    def test_multilingual_content_resolution(self):
        """Test resolving content in multiple languages."""
        # Create test object
        mock_obj = Mock()
        mock_obj.pk = 2

        # Mock content type
        mock_ct = Mock()
        mock_ct.pk = 1

        # Create German locale
        de_locale = Locale.objects.create(
            code="de", name="German", fallback_locale=self.en_locale
        )

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = mock_ct

            # Create translations in multiple languages
            languages = [
                (self.en_locale, "English Title"),
                (self.fr_locale, "Titre Français"),
                (de_locale, "Deutscher Titel"),
            ]

            for locale, text in languages:
                TranslationUnit.objects.create(
                    content_type=mock_ct,
                    object_id=2,
                    field="title",
                    source_text="Original Title",
                    target_text=text,
                    target_locale=locale,
                    status="approved",
                )

            # Test resolution for each language
            for locale, expected_text in languages:
                resolver = TranslationResolver(locale)
                with patch.object(resolver, "fallback_chain", [locale, self.en_locale]):
                    result = resolver.resolve_field(mock_obj, "title")
                    self.assertEqual(result, expected_text)
