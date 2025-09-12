import json



from django.contrib.auth import get_user_model

from django.test import TestCase, TransactionTestCase



from rest_framework import status



from apps.cms.models import Page

from apps.i18n.models import Locale, TranslationUnit, UiMessage, UiMessageTranslation

from apps.i18n.translation import (  # functionality

    APIClient,

    Tests,

    TranslationManager,

    TranslationResolver,

    UiMessageResolver,

    django.contrib.auth,

    get_user_model,

    rest_framework.test,

    translation,

)



User = get_user_model()



class LocaleModelTests(TestCase):

    """Test Locale model functionality."""



    def setUp(self):

        """Set up test data."""

        self.locale_en = Locale.objects.create(

            code="en",

            name="English",

            native_name="English",

            is_default=True,

            is_active=True,

        )

        self.locale_es = Locale.objects.create(

            code="es",

            name="Spanish",

            native_name="Español",

            fallback=self.locale_en,

            is_active=True,

        )

        self.locale_fr = Locale.objects.create(

            code="fr",

            name="French",

            native_name="Français",

            fallback=self.locale_en,

            is_active=True,

        )



    def test_fallback_chain(self):

        """Test fallback chain retrieval."""

        chain = self.locale_es.get_fallback_chain()



        self.assertEqual(len(chain), 2)

        self.assertEqual(chain[0], self.locale_es)

        self.assertEqual(chain[1], self.locale_en)



    def test_fallback_cycle_prevention(self):

        """Test prevention of fallback cycles."""

        # Try to create a cycle

        self.locale_en.fallback = self.locale_es



        with self.assertRaises(Exception):

            self.locale_en.save()



    def test_single_default_enforcement(self):

        """Test that only one locale can be default."""

        # Create another locale as default

        locale_de = Locale.objects.create(

            code="de",

            name="German",

            native_name="Deutsch",

            is_default=True,

            is_active=True,

        )



        # Check that the original default is no longer default

        self.locale_en.refresh_from_db()

        self.assertFalse(self.locale_en.is_default)

        self.assertTrue(locale_de.is_default)



class TranslationUnitModelTests(TestCase):

    """Test TranslationUnit model functionality."""



    def setUp(self):

        """Set up test data."""

        # Clean up any existing test data

        TranslationUnit.objects.all().delete()

        Locale.objects.all().delete()

        Page.objects.all().delete()

        User.objects.filter(email="test@example.com").delete()



        self.user = User.objects.create_user(

            email="test@example.com", password="testpass123"

        )

        self.locale_en = Locale.objects.create(

            code="en",

            name="English",

            native_name="English",

            is_default=True,

            is_active=True,

        )

        self.locale_es = Locale.objects.create(

            code="es",

            name="Spanish",

            native_name="Español",

            fallback=self.locale_en,

            is_active=True,

        )

        self.page = Page.objects.create(

            title="Test Page",

            slug="test-page",

            locale=self.locale_en,

            blocks=[{"type": "text", "props": {"content": "Hello World"}}],

            status="draft",

        )



    def tearDown(self):

        """Clean up after test."""



        User = get_user_model()



        TranslationUnit.objects.all().delete()

        Page.objects.all().delete()  # Delete pages before locales

        Locale.objects.all().delete()

        User.objects.filter(email="test@example.com").delete()



    def test_upsert_unit(self):

        """Test creating/updating translation units."""

        # Create unit

        unit = TranslationUnit.upsert_unit(

            obj=self.page,

            field="title",

            source_locale=self.locale_en,

            target_locale=self.locale_es,

            source_text="Test Page",

            user=self.user,

        )



        self.assertEqual(unit.source_text, "Test Page")

        self.assertEqual(unit.field, "title")

        self.assertEqual(unit.status, "missing")



        # Update same unit

        updated_unit = TranslationUnit.upsert_unit(

            obj=self.page,

            field="title",

            source_locale=self.locale_en,

            target_locale=self.locale_es,

            source_text="Updated Test Page",

            user=self.user,

        )



        # Should be same unit, but with updated source text

        self.assertEqual(updated_unit.id, unit.id)

        self.assertEqual(updated_unit.source_text, "Updated Test Page")



    def test_model_label_property(self):

        """Test model_label property."""

        unit = TranslationUnit.upsert_unit(

            obj=self.page,

            field="title",

            source_locale=self.locale_en,

            target_locale=self.locale_es,

            source_text="Test Page",

            user=self.user,

        )



        self.assertEqual(unit.model_label, "cms.page")



    def test_is_complete_property(self):

        """Test is_complete property."""

        unit = TranslationUnit.upsert_unit(

            obj=self.page,

            field="title",

            source_locale=self.locale_en,

            target_locale=self.locale_es,

            source_text="Test Page",

            user=self.user,

        )



        # Not complete initially

        self.assertFalse(unit.is_complete)



        # Add target text but not approved

        unit.target_text = "Página de Prueba"

        unit.status = "draft"

        unit.save()

        self.assertFalse(unit.is_complete)



        # Approve it

        unit.status = "approved"

        unit.save()

        self.assertTrue(unit.is_complete)



class TranslationManagerTests(TestCase):

    """Test TranslationManager functionality."""



    def setUp(self):

        """Set up test data."""

        # Clean up any existing test data

        TranslationUnit.objects.all().delete()

        Locale.objects.all().delete()

        Page.objects.all().delete()

        User.objects.filter(email="test@example.com").delete()



        self.user = User.objects.create_user(

            email="test@example.com", password="testpass123"

        )

        self.locale_en = Locale.objects.create(

            code="en",

            name="English",

            native_name="English",

            is_default=True,

            is_active=True,

        )

        self.locale_es = Locale.objects.create(

            code="es", name="Spanish", native_name="Español", is_active=True

        )

        self.page = Page.objects.create(

            title="Test Page",

            slug="test-page",

            locale=self.locale_en,

            blocks=[{"type": "text", "props": {"content": "Hello"}}],

            status="draft",

        )



    def tearDown(self):

        """Clean up after test."""



        User = get_user_model()



        TranslationUnit.objects.all().delete()

        Page.objects.all().delete()  # Delete pages before locales

        Locale.objects.all().delete()

        User.objects.filter(email="test@example.com").delete()



    def test_get_translatable_fields(self):

        """Test getting translatable fields for a model."""

        fields = TranslationManager.get_translatable_fields(self.page)

        self.assertEqual(set(fields), {"title", "blocks"})



    def test_extract_field_text(self):

        """Test text extraction from different field types."""

        # String field

        title_text = TranslationManager._extract_field_text(self.page, "title")

        self.assertEqual(title_text, "Test Page")



        # JSON field (blocks)

        blocks_text = TranslationManager._extract_field_text(self.page, "blocks")

        expected_json = json.dumps(

            [{"type": "text", "props": {"content": "Hello"}}], ensure_ascii=False

        )

        self.assertEqual(blocks_text, expected_json)



    def test_get_resolver(self):

        """Test getting a translation resolver."""

        resolver = TranslationManager.get_resolver("en")

        self.assertIsInstance(resolver, TranslationResolver)

        self.assertEqual(resolver.target_locale, self.locale_en)



        # Test fallback to default for invalid locale

        resolver = TranslationManager.get_resolver("invalid")

        self.assertEqual(

            resolver.target_locale, self.locale_en

        )  # Falls back to default



class TranslationResolverTests(TestCase):

    """Test TranslationResolver functionality."""



    def setUp(self):

        """Set up test data."""

        self.user = User.objects.create_user(

            email="test@example.com", password="testpass123"

        )

        self.locale_en = Locale.objects.create(

            code="en",

            name="English",

            native_name="English",

            is_default=True,

            is_active=True,

        )

        self.locale_es = Locale.objects.create(

            code="es",

            name="Spanish",

            native_name="Español",

            fallback=self.locale_en,

            is_active=True,

        )

        self.page = Page.objects.create(

            title="Test Page",

            slug="test-page",

            locale=self.locale_en,

            blocks=[{"type": "text", "props": {"content": "Hello"}}],

            status="draft",

        )



    def test_resolve_field_with_translation(self):

        """Test resolving a field with available translation."""

        # Create translation unit

        unit = TranslationUnit.upsert_unit(

            obj=self.page,

            field="title",

            source_locale=self.locale_en,

            target_locale=self.locale_es,

            source_text="Test Page",

            user=self.user,

        )

        unit.target_text = "Página de Prueba"

        unit.status = "approved"

        unit.save()



        # Resolve field

        resolver = TranslationResolver(self.locale_es)

        result = resolver.resolve_field(self.page, "title")



        self.assertEqual(result, "Página de Prueba")



    def test_resolve_field_with_fallback(self):

        """Test resolving a field using fallback chain."""

        resolver = TranslationResolver(self.locale_es)



        # No translation exists, should fall back to original value

        result = resolver.resolve_field(self.page, "title")

        self.assertEqual(result, "Test Page")



    def test_get_translation_status(self):

        """Test getting translation status."""

        # Create translation unit

        TranslationUnit.upsert_unit(

            obj=self.page,

            field="title",

            source_locale=self.locale_en,

            target_locale=self.locale_es,

            source_text="Test Page",

            user=self.user,

        )



        resolver = TranslationResolver(self.locale_es)

        status_info = resolver.get_translation_status(self.page, ["title"])



        self.assertIn("title", status_info)

        field_status = status_info["title"]

        self.assertTrue(field_status["has_translation"])

        self.assertEqual(field_status["status"], "missing")

        self.assertEqual(field_status["target_locale"], "es")



class UiMessageTests(TestCase):

    """Test UI message functionality."""



    def setUp(self):

        """Set up test data."""

        self.user = User.objects.create_user(

            email="test@example.com", password="testpass123"

        )

        self.locale_en = Locale.objects.create(

            code="en",

            name="English",

            native_name="English",

            is_default=True,

            is_active=True,

        )

        self.locale_es = Locale.objects.create(

            code="es",

            name="Spanish",

            native_name="Español",

            fallback=self.locale_en,

            is_active=True,

        )



        self.message = UiMessage.objects.create(

            key="auth.login.title",

            namespace="auth",

            description="Login page title",

            default_value="Sign In",

        )



    def test_ui_message_creation(self):

        """Test UI message creation."""

        self.assertEqual(str(self.message), "auth.auth.login.title")

        self.assertEqual(self.message.key, "auth.login.title")

        self.assertEqual(self.message.namespace, "auth")



    def test_ui_message_translation(self):

        """Test UI message translation."""

        translation = UiMessageTranslation.objects.create(

            message=self.message,

            locale=self.locale_es,

            value="Iniciar Sesión",

            status="approved",

            updated_by=self.user,

        )



        self.assertEqual(str(translation), "auth.login.title (es): Iniciar Sesión")

        self.assertEqual(translation.value, "Iniciar Sesión")



    def test_ui_message_resolver(self):

        """Test UI message resolution."""

        # Create translation

        UiMessageTranslation.objects.create(

            message=self.message,

            locale=self.locale_es,

            value="Iniciar Sesión",

            status="approved",

            updated_by=self.user,

        )



        # Resolve message

        resolver = UiMessageResolver(self.locale_es)

        result = resolver.resolve_message("auth.login.title")



        self.assertEqual(result, "Iniciar Sesión")



        # Test fallback

        result_fallback = resolver.resolve_message("nonexistent.key", "Default Value")

        self.assertEqual(result_fallback, "Default Value")



    def test_message_bundle(self):

        """Test message bundle generation."""

        # Create another message

        message2 = UiMessage.objects.create(

            key="auth.login.button", namespace="auth", default_value="Login"

        )



        # Create translations

        UiMessageTranslation.objects.create(

            message=self.message,

            locale=self.locale_es,

            value="Iniciar Sesión",

            status="approved",

            updated_by=self.user,

        )

        UiMessageTranslation.objects.create(

            message=message2,

            locale=self.locale_es,

            value="Entrar",

            status="approved",

            updated_by=self.user,

        )



        resolver = UiMessageResolver(self.locale_es)

        bundle = resolver.get_message_bundle("auth")



        self.assertIn("auth.login.title", bundle)

        self.assertIn("auth.login.button", bundle)

        self.assertEqual(bundle["auth.login.title"], "Iniciar Sesión")

        self.assertEqual(bundle["auth.login.button"], "Entrar")



class TranslationAPITests(TransactionTestCase):

    """Test translation API endpoints."""



    def setUp(self):

        """Set up test data."""

        # Ensure clean state for each test - delete in proper order



        TranslationUnit.objects.all().delete()

        Page.objects.all().delete()  # Delete pages before locales

        Locale.objects.all().delete()

        User = get_user_model()

        User.objects.filter(email="test@example.com").delete()



        # Set up test client for API requests



        self.client = APIClient()



        self.user = User.objects.create_user(

            email="test@example.com", password="testpass123"

        )

        self.locale_en = Locale.objects.create(

            code="en",

            name="English",

            native_name="English",

            is_default=True,

            is_active=True,

        )

        self.locale_es = Locale.objects.create(

            code="es",

            name="Spanish",

            native_name="Español",

            fallback=self.locale_en,

            is_active=True,

        )

        self.page = Page.objects.create(

            title="Test Page",

            slug="test-page",

            locale=self.locale_en,

            blocks=[{"type": "text", "props": {"content": "Hello"}}],

            status="draft",

        )



        # Create translation units

        self.unit = TranslationUnit.upsert_unit(

            obj=self.page,

            field="title",

            source_locale=self.locale_en,

            target_locale=self.locale_es,

            source_text="Test Page",

            user=self.user,

        )



        # Create translation unit for blocks field

        self.blocks_unit = TranslationUnit.upsert_unit(

            obj=self.page,

            field="blocks",

            source_locale=self.locale_en,

            target_locale=self.locale_es,

            source_text=str(self.page.blocks),

            user=self.user,

        )



        self.client.force_authenticate(user=self.user)



    def tearDown(self):

        """Clean up after test."""



        User = get_user_model()



        TranslationUnit.objects.all().delete()

        Page.objects.all().delete()  # Delete pages before locales

        Locale.objects.all().delete()

        User.objects.filter(email="test@example.com").delete()



    def test_list_locales(self):

        """Test listing locales."""

        response = self.client.get("/api/v1/i18n/locales/")



        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()



        # API returns paginated response

        self.assertIn("results", data)

        locales = data["results"]



        # Should have at least our 2 locales (might have others from fixtures/migrations)

        self.assertGreaterEqual(len(locales), 2)

        codes = [locale["code"] for locale in locales]

        self.assertIn("en", codes)

        self.assertIn("es", codes)



    def test_list_translation_units(self):

        """Test listing translation units."""

        response = self.client.get("/api/v1/i18n/translation-units/")



        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()



        # Should have 2 units: one for title and one for blocks (created by signal)

        self.assertEqual(len(data["results"]), 2)



        # Find the title unit

        title_unit = None

        blocks_unit = None

        for unit in data["results"]:

            if unit["field"] == "title":

                title_unit = unit

            elif unit["field"] == "blocks":

                blocks_unit = unit



        # Verify both units exist

        self.assertIsNotNone(title_unit, "Title translation unit should exist")

        self.assertIsNotNone(blocks_unit, "Blocks translation unit should exist")



        # Verify title unit content

        self.assertEqual(title_unit["source_text"], "Test Page")

        # target_locale is returned as locale ID, not code

        self.assertEqual(title_unit["target_locale"], self.locale_es.id)



    def test_get_units_for_object(self):

        """Test getting units for a specific object."""

        response = self.client.get(

            "/api/v1/i18n/translation-units/for_object/",

            {

                "model_label": "cms.page",

                "object_id": self.page.id,

                "target_locale": self.locale_es.code,

            },

        )



        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()



        # Should have 2 units: title and blocks

        self.assertEqual(len(data), 2)



        # Verify we have both expected fields

        fields = [unit["field"] for unit in data]

        self.assertIn("title", fields)

        self.assertIn("blocks", fields)



    def test_get_translation_status(self):

        """Test getting translation status for an object."""

        response = self.client.get(

            "/api/v1/i18n/translation-units/status_for_object/",

            {"model_label": "cms.page", "object_id": self.page.id},

        )



        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()



        # The status_for_object API returns a list of locale status objects

        self.assertIsInstance(data, list)

        self.assertEqual(len(data), 2)  # Should have status for 2 locales (en, es)



        # Check that each locale status has expected fields

        for locale_status in data:

            self.assertIn("locale", locale_status)

            self.assertIn("total_fields", locale_status)

            self.assertIn("completed_fields", locale_status)

            self.assertIn("completion_percentage", locale_status)



    def test_update_translation_unit(self):

        """Test updating a translation unit."""

        response = self.client.patch(

            f"/api/v1/i18n/translation-units/{self.unit.id}/",

            {"target_text": "Página de Prueba", "status": "draft"},

        )



        self.assertEqual(response.status_code, status.HTTP_200_OK)



        # Check that unit was updated

        self.unit.refresh_from_db()

        self.assertEqual(self.unit.target_text, "Página de Prueba")

        self.assertEqual(self.unit.status, "draft")



class TranslationSignalTests(TestCase):

    """Test translation signal handlers."""



    def setUp(self):

        """Set up test data."""

        # Clean up any existing test data

        TranslationUnit.objects.all().delete()

        Locale.objects.all().delete()

        Page.objects.all().delete()

        User.objects.filter(email="test@example.com").delete()



        self.user = User.objects.create_user(

            email="test@example.com", password="testpass123"

        )

        self.locale_en = Locale.objects.create(

            code="en",

            name="English",

            native_name="English",

            is_default=True,

            is_active=True,

        )

        self.locale_es = Locale.objects.create(

            code="es", name="Spanish", native_name="Español", is_active=True

        )



    def test_translation_units_created_on_page_save(self):

        """Test that translation units are created when pages are saved."""

        # Initially no units

        self.assertEqual(TranslationUnit.objects.count(), 0)



        # Create page with user context

        page = Page.objects.create(

            title="Test Page",

            slug="test-page",

            locale=self.locale_en,

            blocks=[{"type": "text", "props": {"content": "Hello"}}],

            status="draft",

        )

        page._current_user = self.user

        page.save()



        # Should create translation units

        units = TranslationUnit.objects.filter(

            content_type__app_label="cms", content_type__model="page", object_id=page.id

        )



        # Should have units for Spanish locale

        self.assertEqual(units.count(), 2)  # title and blocks



        # Check that units have correct source text

        title_unit = units.get(field="title")

        self.assertEqual(title_unit.source_text, "Test Page")

        self.assertEqual(title_unit.source_locale, self.locale_en)

        self.assertEqual(title_unit.target_locale, self.locale_es)

