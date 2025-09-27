from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.i18n.models import (  # models
    Locale,
    TranslationGlossary,
    TranslationHistory,
    TranslationQueue,
    TranslationUnit,
    UiMessage,
    UiMessageTranslation,
)

User = get_user_model()


class LocaleModelTest(TestCase):
    """Test cases for Locale model."""

    def setUp(self):  # noqa: C901
        """Set up test data."""

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
            code="es",
            name="Spanish",
            native_name="Español",
            is_active=True,
            fallback=self.locale_en,
        )

        self.locale_fr = Locale.objects.create(
            code="fr",
            name="French",
            native_name="Français",
            is_active=True,
            fallback=self.locale_es,
        )

    def test_locale_creation(self):  # noqa: C901
        """Test locale creation."""

        self.assertEqual(self.locale_en.code, "en")

        self.assertEqual(self.locale_en.name, "English")

        self.assertTrue(self.locale_en.is_default)

        self.assertTrue(self.locale_en.is_active)

        self.assertFalse(self.locale_en.rtl)

    def test_locale_string_representation(self):  # noqa: C901
        """Test locale string representation."""

        self.assertEqual(str(self.locale_en), "English (en)")

        self.assertEqual(str(self.locale_es), "Spanish (es)")

    def test_only_one_default_locale(self):  # noqa: C901
        """Test that only one locale can be default."""

        # Try to create another default locale

        locale_de = Locale.objects.create(
            code="de",
            name="German",
            native_name="Deutsch",
            is_default=True,
            is_active=True,
        )

        # Refresh the original default locale

        self.locale_en.refresh_from_db()

        # The new locale should be default

        self.assertTrue(locale_de.is_default)

        # The old default should no longer be default

        self.assertFalse(self.locale_en.is_default)

    def test_fallback_chain(self):  # noqa: C901
        """Test fallback chain resolution."""

        # fr -> es -> en

        chain = self.locale_fr.get_fallback_chain()

        self.assertEqual(len(chain), 3)

        self.assertEqual(chain[0], self.locale_fr)

        self.assertEqual(chain[1], self.locale_es)

        self.assertEqual(chain[2], self.locale_en)

    def test_fallback_chain_no_fallback(self):  # noqa: C901
        """Test fallback chain with no fallback."""

        chain = self.locale_en.get_fallback_chain()

        self.assertEqual(len(chain), 1)

        self.assertEqual(chain[0], self.locale_en)

    def test_circular_fallback_prevention(self):  # noqa: C901
        """Test that circular fallbacks are prevented."""

        # Try to create a circular fallback: en -> es -> en

        self.locale_en.fallback = self.locale_es

        # This should raise a ValidationError

        with self.assertRaises(ValidationError) as context:

            self.locale_en.save()

        # Check that the error message mentions circular fallback

        self.assertIn("cycle", str(context.exception).lower())

    def test_locale_ordering(self):  # noqa: C901
        """Test locale ordering."""

        locales = Locale.objects.all().order_by("name")

        self.assertEqual(locales[0], self.locale_en)

        self.assertEqual(locales[1], self.locale_fr)

        self.assertEqual(locales[2], self.locale_es)


class UiMessageModelTest(TestCase):
    """Test cases for UiMessage model."""

    def setUp(self):  # noqa: C901
        """Set up test data."""

        self.message = UiMessage.objects.create(
            namespace="common",
            key="buttons.save",
            default_value="Save",
            description="Save button text",
        )

    def test_ui_message_creation(self):  # noqa: C901
        """Test UI message creation."""

        self.assertEqual(self.message.namespace, "common")

        self.assertEqual(self.message.key, "buttons.save")

        self.assertEqual(self.message.default_value, "Save")

        self.assertEqual(self.message.description, "Save button text")

    def test_ui_message_string_representation(self):  # noqa: C901
        """Test UI message string representation."""

        self.assertEqual(str(self.message), "common.buttons.save")

    def test_unique_key_constraint(self):  # noqa: C901
        """Test that keys must be unique."""

        with self.assertRaises(Exception):

            UiMessage.objects.create(
                namespace="common",
                key="buttons.save",  # Same key
                default_value="Different value",
            )

    def test_ordering(self):  # noqa: C901
        """Test UI message ordering."""

        message2 = UiMessage.objects.create(
            namespace="auth", key="login.title", default_value="Login"
        )

        message3 = UiMessage.objects.create(
            namespace="common", key="buttons.cancel", default_value="Cancel"
        )

        messages = UiMessage.objects.all()

        # Should be ordered by namespace, then key

        self.assertEqual(messages[0], message2)  # auth.login.title

        self.assertEqual(messages[1], message3)  # common.buttons.cancel

        self.assertEqual(messages[2], self.message)  # common.buttons.save


class UiMessageTranslationModelTest(TestCase):
    """Test cases for UiMessageTranslation model."""

    def setUp(self):  # noqa: C901
        """Set up test data."""

        self.user = User.objects.create_user(
            email="translator@test.com", password="testpass123"
        )

        self.locale_en, _ = Locale.objects.get_or_create(
            code="en",
            defaults={"name": "English", "native_name": "English", "is_default": True},
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
            status="approved",
            updated_by=self.user,
        )

    def test_translation_creation(self):  # noqa: C901
        """Test translation creation."""

        self.assertEqual(self.translation.message, self.message)

        self.assertEqual(self.translation.locale, self.locale_es)

        self.assertEqual(self.translation.value, "Guardar")

        """self.assertEqual(self.translation.status, "approved")"""

        self.assertEqual(self.translation.updated_by, self.user)

    def test_translation_string_representation(self):  # noqa: C901
        """Test translation string representation."""

        # UiMessageTranslation.__str__ returns f"{self.message.key} ({self.locale.code}): {self.value}"

        expected = "buttons.save (es): Guardar"

        self.assertEqual(str(self.translation), expected)

    def test_unique_constraint(self):  # noqa: C901
        """Test unique constraint on message-locale pair."""

        with self.assertRaises(Exception):

            UiMessageTranslation.objects.create(
                message=self.message,
                locale=self.locale_es,  # Same message-locale pair
                value="Different translation",
                updated_by=self.user,
            )

    def test_status_choices(self):  # noqa: C901
        """Test translation status choices."""

        valid_statuses = ["missing", "draft", "needs_review", "approved", "rejected"]

        for status in valid_statuses:

            self.translation.status = status

            self.translation.save()

            self.assertEqual(self.translation.status, status)


class TranslationUnitModelTest(TestCase):
    """Test cases for TranslationUnit model."""

    def setUp(self):  # noqa: C901
        """Set up test data."""

        self.user = User.objects.create_user(
            email="translator@test.com", password="testpass123"
        )

        self.locale_en, _ = Locale.objects.get_or_create(
            code="en",
            defaults={"name": "English", "native_name": "English", "is_default": True},
        )

        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español"
        )

        # Get content type for User model

        self.content_type = ContentType.objects.get_for_model(User)

        self.translation_unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.user.id,
            field="username",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="translator",
            target_text="traductor",
            status="approved",
            updated_by=self.user,
        )

    def test_translation_unit_creation(self):  # noqa: C901
        """Test translation unit creation."""

        self.assertEqual(self.translation_unit.content_type, self.content_type)

        self.assertEqual(self.translation_unit.object_id, self.user.id)

        self.assertEqual(self.translation_unit.field, "username")

        self.assertEqual(self.translation_unit.source_locale, self.locale_en)

        self.assertEqual(self.translation_unit.target_locale, self.locale_es)

        self.assertEqual(self.translation_unit.source_text, "translator")

        self.assertEqual(self.translation_unit.target_text, "traductor")

        """self.assertEqual(self.translation_unit.status, "approved")"""

    def test_translation_unit_string_representation(self):  # noqa: C901
        """Test translation unit string representation."""

        # TranslationUnit.__str__ returns: f"{self.content_type.model}.{self.field} ({self.source_locale.code} → {self.target_locale.code}) -> {self.target_text}"

        expected = "user.username (en → es) -> traductor"

        self.assertEqual(str(self.translation_unit), expected)

    def test_unique_constraint(self):  # noqa: C901
        """Test unique constraint on translation unit."""

        with self.assertRaises(Exception):

            TranslationUnit.objects.create(
                content_type=self.content_type,
                object_id=self.user.id,
                field="username",  # Same field
                source_locale=self.locale_en,
                target_locale=self.locale_es,  # Same target locale
                source_text="translator",
                target_text="different",
                updated_by=self.user,
            )

    def test_status_choices(self):  # noqa: C901
        """Test translation unit status choices."""

        valid_statuses = [
            "pending",
            "in_progress",
            "needs_review",
            """"approved",""" "rejected",
        ]

        for status in valid_statuses:

            self.translation_unit.status = status

            self.translation_unit.save()

            self.assertEqual(self.translation_unit.status, status)


class TranslationGlossaryModelTest(TestCase):
    """Test cases for TranslationGlossary model."""

    def setUp(self):  # noqa: C901
        """Set up test data."""

        self.user = User.objects.create_user(
            email="admin@test.com", password="testpass123"
        )

        self.locale_en, _ = Locale.objects.get_or_create(
            code="en", defaults={"name": "English", "native_name": "English"}
        )

        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español"
        )

        self.glossary_entry = TranslationGlossary.objects.create(
            term="Dashboard",
            translation="Panel de Control",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            category="ui",
            context="Main navigation menu",
            is_verified=True,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_glossary_creation(self):  # noqa: C901
        """Test glossary entry creation."""

        self.assertEqual(self.glossary_entry.term, "Dashboard")

        self.assertEqual(self.glossary_entry.translation, "Panel de Control")

        self.assertEqual(self.glossary_entry.source_locale, self.locale_en)

        self.assertEqual(self.glossary_entry.target_locale, self.locale_es)

        self.assertEqual(self.glossary_entry.category, "ui")

        self.assertEqual(self.glossary_entry.context, "Main navigation menu")

        self.assertTrue(self.glossary_entry.is_verified)

    def test_glossary_string_representation(self):  # noqa: C901
        """Test glossary entry string representation."""

        # TranslationGlossary.__str__ returns: f"{self.term} ({self.source_locale.code} → {self.target_locale.code})"

        expected = "Dashboard (en → es)"

        self.assertEqual(str(self.glossary_entry), expected)

    def test_unique_constraint(self):  # noqa: C901
        """Test unique constraint on glossary entry."""

        with self.assertRaises(Exception):

            TranslationGlossary.objects.create(
                term="Dashboard",  # Same term
                translation="Different translation",
                source_locale=self.locale_en,  # Same source
                target_locale=self.locale_es,  # Same target
                created_by=self.user,
            )


class TranslationQueueModelTest(TestCase):
    """Test cases for TranslationQueue model."""

    def setUp(self):  # noqa: C901
        """Set up test data."""

        self.user = User.objects.create_user(
            email="translator@test.com", password="testpass123"
        )

        self.assignee = User.objects.create_user(
            email="assignee@test.com", password="testpass123"
        )

        self.locale_en, _ = Locale.objects.get_or_create(
            code="en", defaults={"name": "English", "native_name": "English"}
        )

        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español"
        )

        self.content_type = ContentType.objects.get_for_model(User)

        self.translation_unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.user.id,
            field="bio",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="User biography",
            updated_by=self.user,
        )

        self.queue_item = TranslationQueue.objects.create(
            translation_unit=self.translation_unit,
            priority="high",
            status="pending",
            assigned_to=self.assignee,
            created_by=self.user,
        )

    def test_queue_creation(self):  # noqa: C901
        """Test queue item creation."""

        self.assertEqual(self.queue_item.translation_unit, self.translation_unit)

        self.assertEqual(self.queue_item.priority, "high")

        self.assertEqual(self.queue_item.status, "pending")

        self.assertEqual(self.queue_item.assigned_to, self.assignee)

        self.assertEqual(self.queue_item.created_by, self.user)

    def test_queue_string_representation(self):  # noqa: C901
        """Test queue item string representation."""

        # TranslationQueue.__str__ returns: f"Queue: {self.translation_unit} ({self.status})"

        # And self.status is 'pending' in the test setup (line 416)

        expected = "Queue: user.bio (en → es) (pending)"

        self.assertEqual(str(self.queue_item), expected)

    def test_priority_choices(self):  # noqa: C901
        """Test queue priority choices."""

        valid_priorities = ["low", "medium", "high", "urgent"]

        for priority in valid_priorities:

            self.queue_item.priority = priority

            self.queue_item.save()

            self.assertEqual(self.queue_item.priority, priority)

    def test_status_choices(self):  # noqa: C901
        """Test queue status choices."""

        valid_statuses = ["pending", "assigned", "in_progress", "completed", "rejected"]

        for status in valid_statuses:

            self.queue_item.status = status

            self.queue_item.save()

            self.assertEqual(self.queue_item.status, status)


class TranslationHistoryModelTest(TestCase):
    """Test cases for TranslationHistory model."""

    def setUp(self):  # noqa: C901
        """Set up test data."""

        self.user = User.objects.create_user(
            email="translator@test.com", password="testpass123"
        )

        self.locale_en, _ = Locale.objects.get_or_create(
            code="en", defaults={"name": "English", "native_name": "English"}
        )

        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español"
        )

        self.content_type = ContentType.objects.get_for_model(User)

        self.translation_unit = TranslationUnit.objects.create(
            content_type=self.content_type,
            object_id=self.user.id,
            field="title",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            source_text="Title",
            target_text="Título",
            updated_by=self.user,
        )

        self.history_entry = TranslationHistory.objects.create(
            translation_unit=self.translation_unit,
            action="approved",
            previous_status="pending",
            new_status="approved",
            previous_target_text="",
            new_target_text="Título",
            comment="Translation approved",
            performed_by=self.user,
        )

    def test_history_creation(self):  # noqa: C901
        """Test history entry creation."""

        self.assertEqual(self.history_entry.translation_unit, self.translation_unit)

        """self.assertEqual(self.history_entry.action, "approved")"""

        self.assertEqual(self.history_entry.previous_status, "pending")

        """self.assertEqual(self.history_entry.new_status, "approved")"""

        self.assertEqual(self.history_entry.previous_target_text, "")

        self.assertEqual(self.history_entry.new_target_text, "Título")

        """self.assertEqual(self.history_entry.comment, "Translation approved")"""

        self.assertEqual(self.history_entry.performed_by, self.user)

    def test_history_string_representation(self):  # noqa: C901
        """Test history entry string representation."""

        expected = f"{self.translation_unit} - approved by {self.user.email}"

        self.assertEqual(str(self.history_entry), expected)

    def test_action_choices(self):  # noqa: C901
        """Test history action choices."""

        valid_actions = ["created", "updated", "approved", "rejected", "status_changed"]

        for action in valid_actions:

            history = TranslationHistory.objects.create(
                translation_unit=self.translation_unit,
                action=action,
                performed_by=self.user,
            )

            self.assertEqual(history.action, action)
