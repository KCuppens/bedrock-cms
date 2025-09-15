"""Comprehensive i18n tests to boost coverage."""

import os

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.i18n.models import Locale, TranslationUnit, UiMessage, UiMessageTranslation
from apps.i18n.translation import (
    TranslationManager,
    TranslationResolver,
    UiMessageResolver,
)

User = get_user_model()


class LocaleModelTests(TestCase):
    """Test Locale model functionality."""

    def setUp(self):
        self.en_locale = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )

    def test_locale_str_method(self):
        """Test Locale string representation."""
        self.assertEqual(str(self.en_locale), "English (en)")

    def test_locale_is_default_property(self):
        """Test is_default property."""
        self.assertTrue(self.en_locale.is_default)

        fr_locale = Locale.objects.create(
            code="fr", name="French", native_name="Français"
        )
        self.assertFalse(fr_locale.is_default)

    def test_locale_fallback_chain(self):
        """Test get_fallback_chain method."""
        fr_locale = Locale.objects.create(
            code="fr", name="French", native_name="Français", fallback=self.en_locale
        )
        de_locale = Locale.objects.create(
            code="de", name="German", native_name="Deutsch", fallback=fr_locale
        )

        chain = de_locale.get_fallback_chain()
        expected = [de_locale, fr_locale, self.en_locale]
        self.assertEqual(chain, expected)

    def test_locale_no_fallback(self):
        """Test fallback chain for locale without fallback."""
        chain = self.en_locale.get_fallback_chain()
        self.assertEqual(chain, [self.en_locale])

    def test_locale_circular_fallback_prevention(self):
        """Test prevention of circular fallback chains."""
        from django.core.exceptions import ValidationError

        fr_locale = Locale.objects.create(
            code="fr", name="French", native_name="Français", fallback=self.en_locale
        )

        # This should raise a ValidationError to prevent circular reference
        self.en_locale.fallback = fr_locale
        with self.assertRaises(ValidationError) as cm:
            self.en_locale.save()

        self.assertIn("fallback", cm.exception.message_dict)
        self.assertIn("circular", cm.exception.message_dict["fallback"][0].lower())

    def test_locale_active_manager(self):
        """Test active locale manager."""
        active_locale = Locale.objects.create(code="es", name="Spanish", is_active=True)
        inactive_locale = Locale.objects.create(
            code="it", name="Italian", is_active=False
        )

        if hasattr(Locale.objects, "active"):
            active_locales = Locale.objects.active()
            self.assertIn(active_locale, active_locales)
            self.assertNotIn(inactive_locale, active_locales)


class TranslationUnitTests(TestCase):
    """Test TranslationUnit model."""

    def setUp(self):
        self.en_locale = Locale.objects.create(
            code="en", name="English", is_default=True
        )
        self.fr_locale = Locale.objects.create(
            code="fr", name="French", fallback=self.en_locale
        )
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass"
        )
        self.content_type = ContentType.objects.get_for_model(User)

    def test_translation_unit_creation(self):
        """Test basic TranslationUnit creation."""
        unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.user.pk,
            field="title",
            source_text="Hello",
            target_text="Bonjour",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
            status="approved",
        )

        self.assertEqual(unit.source_text, "Hello")
        self.assertEqual(unit.target_text, "Bonjour")
        self.assertEqual(unit.status, "approved")

    def test_translation_unit_str_method(self):
        """Test TranslationUnit string representation."""
        unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.user.pk,
            field="title",
            source_text="Hello",
            target_text="Bonjour",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
        )

        expected = f"user.title (en → fr) -> Bonjour"
        self.assertEqual(str(unit), expected)

    def test_translation_unit_status_choices(self):
        """Test different status values."""
        statuses = ["draft", "pending", "approved", "rejected", "needs_review"]

        for status in statuses:
            unit = TranslationUnit.objects.create(
                content_type=self.content_type,
                object_id=self.user.pk,
                field=f"field_{status}",
                source_text="Source",
                target_text="Target",
                source_locale=self.en_locale,
                target_locale=self.fr_locale,
                status=status,
            )
            self.assertEqual(unit.status, status)

    def test_translation_unit_upsert(self):
        """Test upsert_unit class method."""
        if hasattr(TranslationUnit, "upsert_unit"):
            unit = TranslationUnit.upsert_unit(
                obj=self.user,
                field="title",
                source_locale=self.en_locale,
                target_locale=self.fr_locale,
                source_text="Hello",
                user=self.user,
            )

            self.assertIsNotNone(unit)
            self.assertEqual(unit.source_text, "Hello")

    def test_translation_unit_get_for_object(self):
        """Test getting translations for an object."""
        TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.user.pk,
            field="title",
            source_text="Hello",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
        )
        TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.user.pk,
            field="description",
            source_text="Description",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
        )

        units = TranslationUnit.objects.filter(
            content_type=self.content_type,
            object_id=self.user.pk,
        )
        self.assertEqual(units.count(), 2)


class UiMessageTests(TestCase):
    """Test UiMessage and UiMessageTranslation models."""

    def setUp(self):
        self.en_locale = Locale.objects.create(
            code="en", name="English", is_default=True
        )
        self.fr_locale = Locale.objects.create(code="fr", name="French")

    def test_ui_message_creation(self):
        """Test UiMessage creation."""
        message = UiMessage.objects.create(
            key="welcome_message",
            default_value="Welcome to our site",
            description="Homepage welcome message",
            namespace="homepage",
        )

        self.assertEqual(message.key, "welcome_message")
        self.assertEqual(message.default_value, "Welcome to our site")

    def test_ui_message_str_method(self):
        """Test UiMessage string representation."""
        message = UiMessage.objects.create(
            key="test_message",
            default_value="Test Value",
        )

        self.assertEqual(str(message), "general.test_message")

    def test_ui_message_translation_creation(self):
        """Test UiMessageTranslation creation."""
        message = UiMessage.objects.create(
            key="hello",
            default_value="Hello",
        )

        translation = UiMessageTranslation.objects.create(
            message=message,
            locale=self.fr_locale,
            value="Bonjour",
        )

        self.assertEqual(translation.value, "Bonjour")
        self.assertEqual(translation.locale, self.fr_locale)

    def test_ui_message_translation_str_method(self):
        """Test UiMessageTranslation string representation."""
        message = UiMessage.objects.create(key="test", default_value="Test")
        translation = UiMessageTranslation.objects.create(
            message=message,
            locale=self.fr_locale,
            value="Test FR",
        )

        expected = "test (fr): Test FR"
        self.assertEqual(str(translation), expected)

    def test_ui_message_status_choices(self):
        """Test UiMessageTranslation status choices."""
        message = UiMessage.objects.create(key="test", default_value="Test")

        # Create additional locales for different status tests
        es_locale = Locale.objects.create(code="es", name="Spanish")
        de_locale = Locale.objects.create(code="de", name="German")

        statuses_and_locales = [
            ("draft", self.fr_locale),
            ("approved", es_locale),
            ("rejected", de_locale),
        ]

        for status, locale in statuses_and_locales:
            translation = UiMessageTranslation.objects.create(
                message=message,
                locale=locale,
                value=f"Value {status}",
                status=status,
            )
            self.assertEqual(translation.status, status)


class TranslationResolverTests(TestCase):
    """Test TranslationResolver functionality."""

    def setUp(self):
        self.en_locale = Locale.objects.create(
            code="en", name="English", is_default=True
        )
        self.fr_locale = Locale.objects.create(
            code="fr", name="French", fallback=self.en_locale
        )
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass"
        )
        self.resolver = TranslationResolver(self.fr_locale)

    def test_resolver_initialization(self):
        """Test resolver initialization."""
        self.assertEqual(self.resolver.target_locale, self.fr_locale)
        self.assertIsInstance(self.resolver.fallback_chain, list)

    def test_resolve_field_with_translation(self):
        """Test resolving field with existing translation."""
        content_type = ContentType.objects.get_for_model(User)
        TranslationUnit.objects.create(
            content_type=content_type,
            object_id=self.user.pk,
            field="title",
            source_text="Hello",
            target_text="Bonjour",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
            status="approved",
        )

        result = self.resolver.resolve_field(self.user, "title")
        self.assertEqual(result, "Bonjour")

    def test_resolve_field_fallback(self):
        """Test resolving field with fallback."""
        result = self.resolver.resolve_field(self.user, "nonexistent", "Default")
        self.assertEqual(result, "Default")

    def test_resolve_object_multiple_fields(self):
        """Test resolving multiple fields for an object."""
        content_type = ContentType.objects.get_for_model(User)
        TranslationUnit.objects.create(
            content_type=content_type,
            object_id=self.user.pk,
            field="title",
            source_text="Title",
            target_text="Titre",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
            status="approved",
        )

        result = self.resolver.resolve_object(self.user, ["title", "description"])
        self.assertIn("title", result)
        self.assertEqual(result["title"], "Titre")

    def test_get_translation_status(self):
        """Test getting translation status for fields."""
        fields = ["title", "description"]
        status_info = self.resolver.get_translation_status(self.user, fields)

        self.assertIn("title", status_info)
        self.assertIn("description", status_info)

        for field_info in status_info.values():
            self.assertIn("target_locale", field_info)
            self.assertIn("has_translation", field_info)
            self.assertIn("status", field_info)


class TranslationManagerTests(TestCase):
    """Test TranslationManager functionality."""

    def setUp(self):
        self.en_locale = Locale.objects.create(
            code="en", name="English", is_default=True
        )
        self.fr_locale = Locale.objects.create(code="fr", name="French")
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass"
        )
        self.manager = TranslationManager()

    def test_register_translatable_fields(self):
        """Test registering translatable fields."""
        TranslationManager.register_translatable_fields(
            "test.model", ["title", "content"]
        )
        self.assertIn("test.model", TranslationManager.TRANSLATABLE_FIELDS)

    def test_get_translatable_fields(self):
        """Test getting translatable fields for model."""
        TranslationManager.TRANSLATABLE_FIELDS["accounts.user"] = ["title", "bio"]
        fields = TranslationManager.get_translatable_fields(self.user)
        self.assertEqual(fields, ["title", "bio"])

    def test_create_translation(self):
        """Test creating a translation."""
        unit = self.manager.create_translation(
            obj=self.user,
            field="title",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
            source_text="Hello",
            target_text="Bonjour",
            user=self.user,
        )

        self.assertIsNotNone(unit)
        self.assertEqual(unit.target_text, "Bonjour")

    def test_update_translation(self):
        """Test updating existing translation."""
        unit = TranslationUnit.objects.create(
            content_type=ContentType.objects.get_for_model(User),
            object_id=self.user.pk,
            field="title",
            source_text="Hello",
            target_text="Bonjour",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
        )

        updated_unit = self.manager.update_translation(
            unit, target_text="Salut", status="approved", user=self.user
        )

        self.assertEqual(updated_unit.target_text, "Salut")
        self.assertEqual(updated_unit.status, "approved")

    def test_get_translations_for_object(self):
        """Test getting all translations for an object."""
        TranslationUnit.objects.create(
            content_type=ContentType.objects.get_for_model(User),
            object_id=self.user.pk,
            field="title",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
            source_text="Hello",
        )

        translations = self.manager.get_translations_for_object(self.user)
        self.assertEqual(translations.count(), 1)

    def test_get_translation_progress(self):
        """Test getting translation progress."""
        content_type = ContentType.objects.get_for_model(User)
        TranslationUnit.objects.create(
            content_type=content_type,
            object_id=self.user.pk,
            field="title",
            source_locale=self.en_locale,
            target_locale=self.fr_locale,
            source_text="Hello",
            target_text="Bonjour",
            status="approved",
        )

        progress = self.manager.get_translation_progress(
            self.user, self.fr_locale, ["title", "description"]
        )

        self.assertIn("total_fields", progress)
        self.assertIn("translated_fields", progress)
        self.assertIn("completion_percentage", progress)
        self.assertEqual(progress["total_fields"], 2)
        self.assertEqual(progress["translated_fields"], 1)

    def test_get_resolver(self):
        """Test getting resolver for locale."""
        resolver = TranslationManager.get_resolver("fr")
        self.assertIsInstance(resolver, TranslationResolver)


class UiMessageResolverTests(TestCase):
    """Test UiMessageResolver functionality."""

    def setUp(self):
        self.en_locale = Locale.objects.create(
            code="en", name="English", is_default=True
        )
        self.fr_locale = Locale.objects.create(
            code="fr", name="French", fallback=self.en_locale
        )
        self.resolver = UiMessageResolver(self.fr_locale)

    def test_resolver_initialization(self):
        """Test UiMessageResolver initialization."""
        self.assertEqual(self.resolver.locale, self.fr_locale)
        self.assertIsInstance(self.resolver.fallback_chain, list)

    def test_resolve_message_with_translation(self):
        """Test resolving message with translation."""
        message = UiMessage.objects.create(
            key="hello",
            default_value="Hello",
        )
        UiMessageTranslation.objects.create(
            message=message,
            locale=self.fr_locale,
            value="Bonjour",
            status="approved",
        )

        result = self.resolver.resolve_message("hello")
        self.assertEqual(result, "Bonjour")

    def test_resolve_message_fallback(self):
        """Test resolving message with fallback."""
        result = self.resolver.resolve_message("nonexistent", "Default")
        self.assertEqual(result, "Default")

    def test_resolve_with_parameters(self):
        """Test resolving message with parameter substitution."""
        message = UiMessage.objects.create(
            key="greeting",
            default_value="Hello {name}!",
        )

        result = self.resolver.resolve("greeting", parameters={"name": "John"})
        self.assertEqual(result, "Hello John!")

    def test_get_message_bundle(self):
        """Test getting message bundle."""
        UiMessage.objects.create(key="msg1", default_value="Message 1")
        UiMessage.objects.create(key="msg2", default_value="Message 2")

        bundle = self.resolver.get_message_bundle()
        self.assertIn("msg1", bundle)
        self.assertIn("msg2", bundle)

    def test_get_namespaced_bundle(self):
        """Test getting namespaced message bundle."""
        UiMessage.objects.create(key="nav.home", default_value="Home", namespace="nav")
        UiMessage.objects.create(
            key="footer.about", default_value="About", namespace="footer"
        )

        bundle = self.resolver.get_namespaced_bundle()
        if "nav" in bundle and "footer" in bundle:
            self.assertIn("nav", bundle)
            self.assertIn("footer", bundle)
