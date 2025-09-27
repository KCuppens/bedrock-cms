"""Tests for i18n translation functionality."""

import os

# Configure Django settings before any imports
from unittest.mock import Mock, patch

import django
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.i18n.models import Locale, TranslationUnit, UiMessage, UiMessageTranslation
from apps.i18n.translation import TranslationResolver


class TranslationResolverTestCase(TestCase):
    """Test translation resolver functionality."""

    def setUp(self):
        """Set up test data."""
        # Create test locales
        self.en_locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={"name": "English", "native_name": "English", "is_default": True},
        )
        self.fr_locale = Locale.objects.create(
            code="fr",
            name="French",
            native_name="Français",
            fallback=self.en_locale,
        )
        self.es_locale = Locale.objects.create(
            code="es",
            name="Spanish",
            native_name="Español",
            fallback=self.en_locale,
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
        # Use real User instance for proper Django ORM compatibility
        from django.contrib.auth import get_user_model
        from django.contrib.contenttypes.models import ContentType

        User = get_user_model()
        test_user = User.objects.create_user(
            email="test_translation@example.com", password="testpass123"
        )
        content_type = ContentType.objects.get_for_model(User)

        # Create translation unit
        unit = TranslationUnit.objects.create(
            content_type=content_type,
            object_id=test_user.pk,
            field="title",
            source_text="Hello",
            target_text="Bonjour",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
            status="approved",
        )

        # Test resolving field
        result = self.resolver.resolve_field(test_user, "title")
        self.assertEqual(result, "Bonjour")

    def test_resolve_field_fallback_to_default(self):
        """Test resolving field falls back to default locale."""
        # Use a real User instance instead of Mock
        from django.contrib.auth import get_user_model

        User = get_user_model()

        test_user = User.objects.create_user(
            email="test2@example.com", password="testpass123"
        )

        # Use real ContentType instead of Mock
        user_ct = ContentType.objects.get_for_model(User)

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = user_ct

            # Create only English translation (fallback)
            unit = TranslationUnit.objects.create(
                content_type=user_ct,
                object_id=test_user.pk,
                field="title",
                source_text="Hello",
                target_text="Hello",
                source_locale=self.en_locale,
                target_locale=self.en_locale,
                status="approved",
            )

            # Mock fallback chain
            with patch.object(
                self.resolver, "fallback_chain", [self.fr_locale, self.en_locale]
            ):
                result = self.resolver.resolve_field(test_user, "title")
                self.assertEqual(result, "Hello")

    def test_resolve_field_with_default_value(self):
        """Test resolving field returns default when no translation exists."""
        # Use a real User instance instead of Mock for proper Django ORM compatibility
        from django.contrib.auth import get_user_model

        User = get_user_model()

        test_user = User.objects.create_user(
            email="test3@example.com", password="testpass123"
        )

        # Use real ContentType instead of Mock
        from django.contrib.contenttypes.models import ContentType

        user_ct = ContentType.objects.get_for_model(User)

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = user_ct

            # No translation exists - should return default value
            result = self.resolver.resolve_field(test_user, "title", "Default Title")
            self.assertEqual(result, "Default Title")

    def test_resolve_field_empty_translation(self):
        """Test resolving field skips empty translations."""
        # Use a real User instance instead of Mock
        from django.contrib.auth import get_user_model

        User = get_user_model()

        test_user = User.objects.create_user(
            email="test4@example.com", password="testpass123"
        )

        # Use real ContentType instead of Mock
        user_ct = ContentType.objects.get_for_model(User)

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = user_ct

            # Create empty translation in French
            TranslationUnit.objects.create(
                content_type=user_ct,
                object_id=test_user.pk,
                field="title",
                source_text="Hello",
                target_text="",  # Empty translation
                source_locale=self.en_locale,
                target_locale=self.fr_locale,
                status="approved",
            )

            # Create fallback translation in English
            TranslationUnit.objects.create(
                content_type=user_ct,
                object_id=test_user.pk,
                field="title",
                source_text="Hello",
                target_text="Hello",
                source_locale=self.en_locale,
                target_locale=self.en_locale,
                status="approved",
            )

            # Mock fallback chain
            with patch.object(
                self.resolver, "fallback_chain", [self.fr_locale, self.en_locale]
            ):
                result = self.resolver.resolve_field(test_user, "title")
                self.assertEqual(result, "Hello")

    def test_resolve_field_non_approved_status(self):
        """Test resolving field skips non-approved translations."""
        # Use a real User instance instead of Mock
        from django.contrib.auth import get_user_model

        User = get_user_model()

        test_user = User.objects.create_user(
            email="test5@example.com", password="testpass123"
        )

        # Use real ContentType instead of Mock
        user_ct = ContentType.objects.get_for_model(User)

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.return_value = user_ct

            # Create draft translation (not approved)
            TranslationUnit.objects.create(
                content_type=user_ct,
                object_id=test_user.pk,
                field="title",
                source_text="Hello",
                target_text="Bonjour Draft",
                source_locale=self.en_locale,
                target_locale=self.fr_locale,
                status="draft",  # Not approved
            )

            # Create approved fallback
            TranslationUnit.objects.create(
                content_type=user_ct,
                object_id=test_user.pk,
                field="title",
                source_text="Hello",
                target_text="Hello",
                source_locale=self.en_locale,
                target_locale=self.en_locale,
                status="approved",
            )

            # Mock fallback chain
            with patch.object(
                self.resolver, "fallback_chain", [self.fr_locale, self.en_locale]
            ):
                result = self.resolver.resolve_field(test_user, "title")
                self.assertEqual(result, "Hello")  # Should use approved fallback

    def test_resolve_multiple_fields(self):
        """Test resolving multiple fields for same object."""
        # Use real User instance for proper Django ORM compatibility
        from django.contrib.auth import get_user_model
        from django.contrib.contenttypes.models import ContentType

        User = get_user_model()
        test_user = User.objects.create_user(
            email="test_multiple@example.com", password="testpass123"
        )
        content_type = ContentType.objects.get_for_model(User)

        # Create translations for multiple fields
        TranslationUnit.objects.create(
            content_type=content_type,
            object_id=test_user.pk,
            field="title",
            source_text="Hello",
            target_text="Bonjour",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
            status="approved",
        )

        TranslationUnit.objects.create(
            content_type=content_type,
            object_id=test_user.pk,
            field="description",
            source_text="Description",
            target_text="Description Fr",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
            status="approved",
        )

        # Test both fields
        title_result = self.resolver.resolve_field(test_user, "title")
        desc_result = self.resolver.resolve_field(test_user, "description")

        self.assertEqual(title_result, "Bonjour")
        self.assertEqual(desc_result, "Description Fr")


class TranslationUtilitiesTestCase(TestCase):
    """Test additional translation utilities."""

    def setUp(self):
        """Set up test data."""
        self.en_locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={"name": "English", "native_name": "English", "is_default": True},
        )
        self.fr_locale = Locale.objects.create(
            code="fr",
            name="French",
            native_name="Français",
            fallback=self.en_locale,
        )

    def test_ui_message_translation(self):
        """Test UI message translation functionality."""
        # Create UI message
        message = UiMessage.objects.create(
            key="welcome_message",
            default_value="Welcome to our site",
            description="homepage",
        )

        # Create translation
        translation = UiMessageTranslation.objects.create(
            message=message,
            locale=self.fr_locale,
            value="Bienvenue sur notre site",
        )

        # Test retrieval
        self.assertEqual(translation.value, "Bienvenue sur notre site")
        self.assertEqual(translation.locale, self.fr_locale)
        self.assertEqual(translation.message, message)

    def test_translation_unit_status_choices(self):
        """Test translation unit status choices."""
        from django.contrib.auth import get_user_model
        from django.contrib.contenttypes.models import ContentType

        # Create real test object
        User = get_user_model()
        test_user = User.objects.create_user(
            email="status_test@example.com", password="testpass123"
        )
        content_type = ContentType.objects.get_for_model(User)

        # Test different status values
        statuses = ["draft", "pending", "approved", "rejected"]

        for status in statuses:
            unit = TranslationUnit.objects.create(
                content_type=content_type,
                object_id=test_user.pk,
                field=f"field_{status}",
                source_text="Source",
                target_text=f"Target {status}",
                source_locale=self.en_locale,
                target_locale=self.fr_locale,
                status=status,
            )

            self.assertEqual(unit.status, status)

    def test_locale_fallback_chain(self):
        """Test locale fallback chain functionality."""
        # Create chain: es -> fr -> en
        es_locale = Locale.objects.create(
            code="es",
            name="Spanish",
            native_name="Español",
            fallback=self.fr_locale,
        )

        # Test fallback chain
        chain = es_locale.get_fallback_chain()
        expected = [es_locale, self.fr_locale, self.en_locale]
        self.assertEqual(chain, expected)

    def test_content_type_functionality(self):
        """Test that content type resolution works properly."""
        # Use a real User instance for proper Django ORM compatibility
        from django.contrib.auth import get_user_model

        User = get_user_model()

        test_user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        resolver = TranslationResolver(self.fr_locale)

        # Test multiple resolve_field calls - should work without errors
        result1 = resolver.resolve_field(test_user, "field1", "default1")
        result2 = resolver.resolve_field(test_user, "field2", "default2")

        # Should return defaults since no translations exist
        self.assertEqual(result1, "default1")
        self.assertEqual(result2, "default2")


class TranslationIntegrationTestCase(TestCase):
    """Integration tests for translation functionality."""

    def setUp(self):
        """Set up integration test data."""
        self.en_locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={"name": "English", "native_name": "English", "is_default": True},
        )
        self.fr_locale = Locale.objects.create(
            code="fr",
            name="French",
            native_name="Français",
            fallback=self.en_locale,
        )

    def test_translation_workflow(self):
        """Test complete translation workflow."""
        from django.contrib.auth import get_user_model
        from django.contrib.contenttypes.models import ContentType

        # Use a real model for testing - User model
        User = get_user_model()
        content_type = ContentType.objects.get_for_model(User)

        # Create test user object
        test_user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        # 1. Create source content translation
        source_unit = TranslationUnit.objects.create(
            content_type=content_type,
            object_id=test_user.pk,
            field="title",
            source_text="Original Title",
            target_text="Original Title",
            source_locale=self.en_locale,
            target_locale=self.en_locale,
            status="approved",
        )

        # 2. Create target translation in draft
        target_unit = TranslationUnit.objects.create(
            content_type=content_type,
            object_id=test_user.pk,
            field="title",
            source_text="Original Title",
            target_text="Titre Original",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
            status="draft",
        )

        # 3. Resolver should use English fallback (draft not approved)
        resolver = TranslationResolver(self.fr_locale)
        with patch.object(resolver, "fallback_chain", [self.fr_locale, self.en_locale]):
            result = resolver.resolve_field(test_user, "title")
            self.assertEqual(result, "Original Title")

        # 4. Approve French translation
        target_unit.status = "approved"
        target_unit.save()

        # 5. Now should use French translation
        result = resolver.resolve_field(test_user, "title")
        self.assertEqual(result, "Titre Original")

    def test_multilingual_content_resolution(self):
        """Test resolving content in multiple languages."""
        from django.contrib.auth import get_user_model
        from django.contrib.contenttypes.models import ContentType

        # Use a real model for testing - User model
        User = get_user_model()
        content_type = ContentType.objects.get_for_model(User)

        # Create test user object
        test_user = User.objects.create_user(
            email="test2@example.com", password="testpass123"
        )

        # Create German locale
        de_locale = Locale.objects.create(
            code="de",
            name="German",
            native_name="Deutsch",
            fallback=self.en_locale,
        )

        # Create translations in multiple languages
        languages = [
            (self.en_locale, "English Title"),
            (self.fr_locale, "Titre Français"),
            (de_locale, "Deutscher Titel"),
        ]

        for locale, text in languages:
            TranslationUnit.objects.create(
                content_type=content_type,
                object_id=test_user.pk,
                field="title",
                source_text="Original Title",
                target_text=text,
                source_locale=self.en_locale,
                target_locale=locale,
                status="approved",
            )

        # Test resolution for each language
        for locale, expected_text in languages:
            resolver = TranslationResolver(locale)
            with patch.object(resolver, "fallback_chain", [locale, self.en_locale]):
                result = resolver.resolve_field(test_user, "title")
                self.assertEqual(result, expected_text)
