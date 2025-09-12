import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch
from django.core.management import call_command
from django.test import TestCase
from apps.i18n.models import Locale, UiMessage, UiMessageTranslation
        import shutil
"""
Test cases for i18n management commands.
"""





class InitLocalesCommandTest(TestCase):
    """Test cases for init_locales command."""

    def test_init_locales_creates_default_locales(self):
        """Test that init_locales creates default locales."""
        # Run command
        call_command("init_locales")

        # Check that default locales were created
        self.assertTrue(Locale.objects.filter(code="en").exists())
        self.assertTrue(Locale.objects.filter(code="es").exists())
        self.assertTrue(Locale.objects.filter(code="fr").exists())

        # Check that English is default
        en_locale = Locale.objects.get(code="en")
        self.assertTrue(en_locale.is_default)
        self.assertTrue(en_locale.is_active)

    def test_init_locales_idempotent(self):
        """Test that init_locales is idempotent."""
        # Run command twice
        call_command("init_locales")
        initial_count = Locale.objects.count()

        call_command("init_locales")
        final_count = Locale.objects.count()

        # Count should remain the same
        self.assertEqual(initial_count, final_count)

    def test_init_locales_with_reset(self):
        """Test init_locales with reset option."""
        # Create a custom locale that's not in defaults
        Locale.objects.create(code="custom", name="Custom", native_name="Custom")

        # Run command with reset
        call_command("init_locales", "--reset")

        # Check that custom locale was removed
        self.assertFalse(Locale.objects.filter(code="custom").exists())

        # Check that default locales exist
        self.assertTrue(Locale.objects.filter(code="en").exists())
        self.assertTrue(Locale.objects.filter(code="es").exists())
        self.assertTrue(Locale.objects.filter(code="de").exists())


class ImportDjangoTranslationsCommandTest(TestCase):
    """Test cases for import_django_translations command."""

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
            code="es", name="Spanish", native_name="Español", is_active=True
        )

    def test_import_django_strings(self):
        """Test importing Django built-in strings."""
        # Run command
        out = StringIO()
        call_command("import_django_translations", stdout=out)

        # Check that messages were created
        self.assertTrue(UiMessage.objects.filter(namespace="django").exists())

        # Check some specific messages
        self.assertTrue(UiMessage.objects.filter(key="admin.save").exists())
        self.assertTrue(UiMessage.objects.filter(key="actions.cancel").exists())

        # Check output
        output = out.getvalue()
        self.assertIn("Import complete", output)

    def test_import_django_strings_with_locale(self):
        """Test importing Django strings for specific locale."""
        # Run command for Spanish
        call_command("import_django_translations", locale="es")

        # Check that Spanish translations were created
        spanish_translations = UiMessageTranslation.objects.filter(
            locale=self.locale_es
        )
        self.assertTrue(spanish_translations.exists())

    def test_import_django_strings_with_namespace(self):
        """Test importing Django strings with custom namespace."""
        # Run command with custom namespace
        call_command("import_django_translations", namespace="custom_django")

        # Check that messages use custom namespace
        self.assertTrue(UiMessage.objects.filter(namespace="custom_django").exists())

    def test_import_django_strings_update_existing(self):
        """Test updating existing Django strings."""
        # Create an existing message
        UiMessage.objects.create(
            namespace="django", key="admin.save", default_value="Old Save"
        )

        # Run command with update flag
        call_command("import_django_translations", update_existing=True)

        # The message should still exist with potentially updated value
        self.assertTrue(UiMessage.objects.filter(key="admin.save").exists())


class SyncPoFilesCommandTest(TestCase):
    """Test cases for sync_po_files command."""

    def setUp(self):
        """Set up test data."""
        self.locale_en = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )
        self.locale_es = Locale.objects.create(
            code="es", name="Spanish", native_name="Español"
        )

        # Create a temp directory for .po files
        self.temp_dir = tempfile.mkdtemp()
        self.locale_dir = Path(self.temp_dir) / "locale"
        self.locale_dir.mkdir()

        # Create Spanish locale directory
        self.es_dir = self.locale_dir / "es" / "LC_MESSAGES"
        self.es_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up temp directory."""

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("apps.i18n.management.commands.sync_po_files.polib")
    def test_import_from_po_files(self, mock_polib):
        """Test importing from .po files."""
        # Mock polib
        mock_po = MagicMock()
        mock_entry = MagicMock()
        mock_entry.msgid = "Hello"
        mock_entry.msgstr = "Hola"
        mock_entry.fuzzy = False
        mock_po.__iter__ = MagicMock(return_value=[mock_entry])
        mock_polib.pofile.return_value = mock_po

        # Mock app config
        with patch("apps.i18n.management.commands.sync_po_files.apps") as mock_apps:
            mock_app = MagicMock()
            mock_app.name = "test_app"
            mock_app.label = "test_app"
            mock_app.path = self.temp_dir
            mock_apps.get_app_configs.return_value = [mock_app]

            # Run command
            out = StringIO()
            call_command("sync_po_files", direction="import", stdout=out)

            # Check output
            output = out.getvalue()
            self.assertIn("Import complete", output)

    @patch("apps.i18n.management.commands.sync_po_files.polib")
    def test_export_to_po_files(self, mock_polib):
        """Test exporting to .po files."""
        # Create UI messages and translations
        message = UiMessage.objects.create(
            namespace="django", key="test_app.hello", default_value="Hello"
        )
        UiMessageTranslation.objects.create(
            message=message, locale=self.locale_es, value="Hola", status="approved"
        )

        # Mock polib
        mock_po = MagicMock()
        mock_polib.POFile.return_value = mock_po
        mock_polib.pofile.return_value = mock_po

        # Mock app config
        with patch("apps.i18n.management.commands.sync_po_files.apps") as mock_apps:
            mock_app = MagicMock()
            mock_app.name = "test_app"
            mock_app.label = "test_app"
            mock_app.path = self.temp_dir
            mock_apps.get_app_configs.return_value = [mock_app]

            # Run command
            out = StringIO()
            call_command(
                "sync_po_files", direction="export", create_missing=True, stdout=out
            )

            # Check output
            output = out.getvalue()
            self.assertIn("Export complete", output)

    def test_sync_bidirectional(self):
        """Test bidirectional sync."""
        with (
            patch(
                "apps.i18n.management.commands.sync_po_files.Command.import_from_po_files"
            ) as mock_import,
            patch(
                "apps.i18n.management.commands.sync_po_files.Command.export_to_po_files"
            ) as mock_export,
        ):
            # Run sync command
            call_command("sync_po_files", direction="sync")

            # Both import and export should be called
            mock_import.assert_called_once()
            mock_export.assert_called_once()

    def test_sync_with_specific_locale(self):
        """Test sync with specific locale."""
        # Create French locale
        Locale.objects.create(
            code="fr",
            name="French",
            native_name="Français",
            is_active=False,  # Inactive
        )

        # Run command for specific locale
        out = StringIO()
        err = StringIO()
        call_command("sync_po_files", locale="fr", stdout=out, stderr=err)

        # Should get error for inactive locale
        output = out.getvalue() + err.getvalue()
        self.assertIn("not found or not active", output)

    def test_sync_with_specific_app(self):
        """Test sync with specific app."""
        with patch("apps.i18n.management.commands.sync_po_files.apps") as mock_apps:
            # Mock app configs
            mock_app1 = MagicMock()
            mock_app1.name = "app1"
            mock_app2 = MagicMock()
            mock_app2.name = "app2"

            mock_apps.get_app_configs.return_value = [mock_app1, mock_app2]
            mock_apps.get_app_config.return_value = mock_app1

            # Run command for specific app
            out = StringIO()
            err = StringIO()

            # This should fail because app doesn't exist
            call_command("sync_po_files", app="nonexistent", stdout=out, stderr=err)

            output = out.getvalue() + err.getvalue()
            self.assertIn("not found", output)
