from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.i18n.models import Locale, TranslationUnit, UiMessage, UiMessageTranslation
from apps.i18n.translation import (
    Test,
    TranslationManager,
    TranslationResolver,
    UiMessageResolver,

    cases,

    translation,
    # utilities
)

User = get_user_model()

class TranslationResolverTest(TestCase):
    """Test cases for TranslationResolver."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@test.com", password="testpass123"
        )

        # Create locale chain: fr -> es -> en
        self.locale_en = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )
        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español", fallback=self.locale_en
        )
        self.locale_fr = Locale.objects.create(
            code="fr", name="French", native_name="Français", fallback=self.locale_es
        )

        # Create test object and translations
        self.content_type = ContentType.objects.get_for_model(User)

        # English translation (base)
        self.unit_en = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.user.id,
            field="first_name",
            source_locale=self.locale_en,
            target_locale=self.locale_en,
            source_text="John",
            target_text="John",
            status="approved",
            updated_by=self.user,
        )

        # Spanish translation
        self.unit_es = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.user.id,
            field="first_name",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="John",
            target_text="Juan",
            status="approved",
            updated_by=self.user,
        )

    def test_resolve_field_direct_translation(self):
        """Test resolving field with direct translation."""
        resolver = TranslationResolver(self.locale_es)
        result = resolver.resolve_field(self.user, "first_name")
        self.assertEqual(result, "Juan")

    def test_resolve_field_with_fallback(self):
        """Test resolving field using fallback locale."""
        # French has no translation, should fall back to Spanish
        resolver = TranslationResolver(self.locale_fr)
        result = resolver.resolve_field(self.user, "first_name")
        self.assertEqual(result, "Juan")

    def test_resolve_field_no_translation(self):
        """Test resolving field with no translation."""
        resolver = TranslationResolver(self.locale_fr)
        result = resolver.resolve_field(self.user, "last_name", "Default")
        self.assertEqual(result, "Default")

    def test_resolve_object_multiple_fields(self):
        """Test resolving multiple fields for an object."""
        # Add another field translation
        TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.user.id,
            field="last_name",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="Doe",
            target_text="García",
            status="approved",
            updated_by=self.user,
        )

        resolver = TranslationResolver(self.locale_es)
        result = resolver.resolve_object(self.user, ["first_name", "last_name"])

        self.assertEqual(result["first_name"], "Juan")
        self.assertEqual(result["last_name"], "García")

    def test_get_translation_status(self):
        """Test getting translation status for fields."""
        resolver = TranslationResolver(self.locale_es)
        status = resolver.get_translation_status(self.user, ["first_name", "last_name"])

        # First name has translation
        self.assertTrue(status["first_name"]["has_translation"])
        self.assertEqual(status["first_name"]["status"], "approved")

        # Last name has no translation
        self.assertFalse(status["last_name"]["has_translation"])
        self.assertEqual(status["last_name"]["status"], "missing")

    def test_fallback_chain_resolution(self):
        """Test complete fallback chain resolution."""
        # Create German locale with fallback to French
        locale_de = Locale.objects.create(
            code="de", name="German", native_name="Deutsch", fallback=self.locale_fr
        )

        # German -> French -> Spanish -> English
        resolver = TranslationResolver(locale_de)
        chain = resolver.fallback_chain

        self.assertEqual(len(chain), 4)
        self.assertEqual(chain[0], locale_de)
        self.assertEqual(chain[1], self.locale_fr)
        self.assertEqual(chain[2], self.locale_es)
        self.assertEqual(chain[3], self.locale_en)

class TranslationManagerTest(TestCase):
    """Test cases for TranslationManager."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@test.com", password="testpass123"
        )

        self.locale_en = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )
        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español"
        )

        self.manager = TranslationManager()

    def test_create_translation_unit(self):
        """Test creating a translation unit."""
        unit = self.manager.create_translation(
            obj=self.user,
            field="username",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="testuser",
            target_text="usuario_prueba",
            user=self.user,
        )

        self.assertIsNotNone(unit)
        self.assertEqual(unit.field, "username")
        self.assertEqual(unit.target_text, "usuario_prueba")

    def test_update_translation_unit(self):
        """Test updating a translation unit."""
        # Create initial unit
        unit = self.manager.create_translation(
            obj=self.user,
            field="email",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="test@test.com",
            target_text="prueba@prueba.com",
            user=self.user,
        )

        # Update it
        updated_unit = self.manager.update_translation(
            unit=unit, target_text="nuevo@prueba.com", status="approved", user=self.user
        )

        self.assertEqual(updated_unit.target_text, "nuevo@prueba.com")
        self.assertEqual(updated_unit.status, "approved")

    def test_get_translations_for_object(self):
        """Test getting all translations for an object."""
        # Create multiple translations
        self.manager.create_translation(
            obj=self.user,
            field="username",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="testuser",
            target_text="usuario_prueba",
            user=self.user,
        )

        self.manager.create_translation(
            obj=self.user,
            field="email",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="test@test.com",
            target_text="prueba@prueba.com",
            user=self.user,
        )

        translations = self.manager.get_translations_for_object(
            obj=self.user, target_locale=self.locale_es
        )

        self.assertEqual(len(translations), 2)

    def test_bulk_create_translations(self):
        """Test bulk creating translations."""
        translations_data = [
            {
                "obj": self.user,
                "field": "first_name",
                "source_text": "Test",
                "target_text": "Prueba",
            },
            {
                "obj": self.user,
                "field": "last_name",
                "source_text": "User",
                "target_text": "Usuario",
            },
        ]

        units = self.manager.bulk_create_translations(
            translations_data,
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            user=self.user,
        )

        self.assertEqual(len(units), 2)

    def test_get_translation_progress(self):
        """Test getting translation progress for an object."""
        # Create some translations
        self.manager.create_translation(
            obj=self.user,
            field="username",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="testuser",
            target_text="usuario_prueba",
            status="approved",
            user=self.user,
        )

        self.manager.create_translation(
            obj=self.user,
            field="email",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="test@test.com",
            target_text="",
            status="pending",
            user=self.user,
        )

        progress = self.manager.get_translation_progress(
            obj=self.user,
            target_locale=self.locale_es,
            fields=["username", "email", "first_name"],
        )

        self.assertEqual(progress["total_fields"], 3)
        self.assertEqual(progress["translated_fields"], 1)
        self.assertEqual(progress["pending_fields"], 1)
        self.assertEqual(progress["missing_fields"], 1)
        self.assertAlmostEqual(progress["completion_percentage"], 33.33, places=1)

class UiMessageResolverTest(TestCase):
    """Test cases for UiMessageResolver."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@test.com", password="testpass123"
        )

        # Create locale chain
        self.locale_en = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )
        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español", fallback=self.locale_en
        )
        self.locale_fr = Locale.objects.create(
            code="fr", name="French", native_name="Français", fallback=self.locale_es
        )

        # Create UI messages
        self.message_save = UiMessage.objects.create(
            namespace="common", key="buttons.save", default_value="Save"
        )
        self.message_cancel = UiMessage.objects.create(
            namespace="common", key="buttons.cancel", default_value="Cancel"
        )

        # Create translations
        UiMessageTranslation.objects.create(
            message=self.message_save,
            locale=self.locale_es,
            value="Guardar",
            status="approved",
            updated_by=self.user,
        )

    def test_resolve_message_direct(self):
        """Test resolving message with direct translation."""
        resolver = UiMessageResolver(self.locale_es)
        result = resolver.resolve("buttons.save")
        self.assertEqual(result, "Guardar")

    def test_resolve_message_fallback(self):
        """Test resolving message using fallback."""
        # French has no translation, should fall back to Spanish
        resolver = UiMessageResolver(self.locale_fr)
        result = resolver.resolve("buttons.save")
        self.assertEqual(result, "Guardar")

    def test_resolve_message_default(self):
        """Test resolving message with default value."""
        resolver = UiMessageResolver(self.locale_es)
        result = resolver.resolve("buttons.cancel")
        self.assertEqual(result, "Cancel")

    def test_resolve_message_not_found(self):
        """Test resolving non-existent message."""
        resolver = UiMessageResolver(self.locale_es)
        result = resolver.resolve("nonexistent.key", "Fallback")
        self.assertEqual(result, "Fallback")

    def test_resolve_with_parameters(self):
        """Test resolving message with parameters."""
        UiMessage.objects.create(
            namespace="validation",
            key="min_length",
            default_value="Minimum {min} characters required",
        )

        resolver = UiMessageResolver(self.locale_en)
        result = resolver.resolve("min_length", parameters={"min": 5})
        self.assertEqual(result, "Minimum 5 characters required")

    def test_get_all_messages(self):
        """Test getting all messages for a locale."""
        resolver = UiMessageResolver(self.locale_es)
        messages = resolver.get_all_messages()

        self.assertIn("buttons.save", messages)
        self.assertEqual(messages["buttons.save"], "Guardar")
        self.assertIn("buttons.cancel", messages)
        self.assertEqual(messages["buttons.cancel"], "Cancel")

    def test_get_namespace_messages(self):
        """Test getting messages for a specific namespace."""
        # Create message in different namespace
        UiMessage.objects.create(
            namespace="auth", key="login.title", default_value="Login"
        )

        resolver = UiMessageResolver(self.locale_en)
        messages = resolver.get_namespace_messages("common")

        self.assertIn("buttons.save", messages)
        self.assertIn("buttons.cancel", messages)
        self.assertNotIn("login.title", messages)
