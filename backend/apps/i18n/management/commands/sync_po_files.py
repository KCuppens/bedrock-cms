"""
Management command to sync .po files with database translations.
Imports Django's .po files into the database and exports database translations back to .po files.
"""

import os
import polib
from pathlib import Path
from typing import Dict, List, Tuple
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.translation import gettext
from django.apps import apps
from apps.i18n.models import UiMessage, UiMessageTranslation, Locale


class Command(BaseCommand):
    help = "Sync .po files with database translations (bidirectional)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--direction",
            type=str,
            choices=["import", "export", "sync"],
            default="sync",
            help="Direction of sync: import (po->db), export (db->po), sync (bidirectional)",
        )
        parser.add_argument(
            "--locale",
            type=str,
            help="Specific locale code to sync (e.g., es, fr). If not specified, syncs all active locales",
        )
        parser.add_argument(
            "--namespace",
            type=str,
            default="django",
            help="Namespace for imported messages (default: django)",
        )
        parser.add_argument(
            "--app", type=str, help="Specific Django app to sync translations for"
        )
        parser.add_argument(
            "--create-missing",
            action="store_true",
            help="Create .po files for locales that don't have them",
        )

    def handle(self, *args, **options):
        direction = options["direction"]
        locale_code = options.get("locale")
        namespace = options["namespace"]
        app_name = options.get("app")
        create_missing = options.get("create_missing", False)

        # Get locales to process
        if locale_code:
            locales = Locale.objects.filter(code=locale_code, is_active=True)
            if not locales.exists():
                self.stdout.write(
                    self.style.ERROR(f"Locale {locale_code} not found or not active")
                )
                return
        else:
            locales = Locale.objects.filter(is_active=True)

        # Get apps to process
        if app_name:
            if app_name not in [app.name for app in apps.get_app_configs()]:
                self.stdout.write(self.style.ERROR(f"App {app_name} not found"))
                return
            app_configs = [apps.get_app_config(app_name.split(".")[-1])]
        else:
            app_configs = apps.get_app_configs()

        if direction in ["import", "sync"]:
            self.import_from_po_files(locales, app_configs, namespace)

        if direction in ["export", "sync"]:
            self.export_to_po_files(locales, app_configs, namespace, create_missing)

    def import_from_po_files(self, locales, app_configs, namespace):
        """Import translations from .po files into database."""

        imported_count = 0
        updated_count = 0

        for app_config in app_configs:
            # Check for locale directory in app
            locale_dir = Path(app_config.path) / "locale"
            if not locale_dir.exists():
                continue

            self.stdout.write(f"Processing app: {app_config.name}")

            for locale in locales:
                # Look for .po files for this locale
                po_file_path = locale_dir / locale.code / "LC_MESSAGES" / "django.po"
                if not po_file_path.exists():
                    # Try language code without country (e.g., 'en' for 'en_US')
                    lang_code = locale.code.split("_")[0].split("-")[0]
                    po_file_path = locale_dir / lang_code / "LC_MESSAGES" / "django.po"
                    if not po_file_path.exists():
                        continue

                self.stdout.write(f"  Importing {locale.code} from {po_file_path}")

                # Parse .po file
                try:
                    po = polib.pofile(str(po_file_path))
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"    Failed to parse {po_file_path}: {e}")
                    )
                    continue

                # Import entries
                for entry in po:
                    if not entry.msgid:
                        continue

                    # Create message key from msgid
                    # Use app name and msgid to create unique key
                    message_key = f"{app_config.label}.{entry.msgid[:100]}"

                    # Get or create UiMessage
                    ui_message, created = UiMessage.objects.get_or_create(
                        key=message_key,
                        defaults={
                            "namespace": namespace,
                            "default_value": entry.msgid,
                            "description": f"Imported from {app_config.name}",
                        },
                    )

                    if created:
                        imported_count += 1

                    # Skip if no translation
                    if not entry.msgstr:
                        continue

                    # Create or update translation
                    translation, trans_created = (
                        UiMessageTranslation.objects.update_or_create(
                            message=ui_message,
                            locale=locale,
                            defaults={
                                "value": entry.msgstr,
                                "status": (
                                    "approved" if not entry.fuzzy else "needs_review"
                                ),
                            },
                        )
                    )

                    if not trans_created:
                        updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete: {imported_count} messages imported, "
                f"{updated_count} translations updated"
            )
        )

    def export_to_po_files(self, locales, app_configs, namespace, create_missing):
        """Export database translations to .po files."""

        exported_count = 0

        # Group messages by app
        messages_by_app = {}
        for ui_message in UiMessage.objects.filter(namespace=namespace):
            # Extract app name from key (format: app_label.msgid)
            parts = ui_message.key.split(".", 1)
            if len(parts) >= 2:
                app_label = parts[0]
                if app_label not in messages_by_app:
                    messages_by_app[app_label] = []
                messages_by_app[app_label].append(ui_message)

        for app_config in app_configs:
            app_label = app_config.label
            if app_label not in messages_by_app:
                continue

            # Ensure locale directory exists
            locale_dir = Path(app_config.path) / "locale"
            if not locale_dir.exists() and create_missing:
                locale_dir.mkdir(parents=True)
            elif not locale_dir.exists():
                continue

            self.stdout.write(f"Exporting translations for app: {app_config.name}")

            for locale in locales:
                # Skip default locale (usually 'en')
                if locale.is_default:
                    continue

                # Determine .po file path
                po_dir = locale_dir / locale.code / "LC_MESSAGES"
                po_file_path = po_dir / "django.po"

                # Create directory if needed
                if create_missing and not po_dir.exists():
                    po_dir.mkdir(parents=True)

                # Load existing .po file or create new one
                if po_file_path.exists():
                    po = polib.pofile(str(po_file_path))
                elif create_missing:
                    po = polib.POFile()
                    po.metadata = {
                        "Project-Id-Version": "1.0",
                        "Language": locale.code,
                        "Content-Type": "text/plain; charset=UTF-8",
                        "Content-Transfer-Encoding": "8bit",
                    }
                else:
                    continue

                self.stdout.write(f"  Exporting {locale.code} to {po_file_path}")

                # Export translations
                for ui_message in messages_by_app[app_label]:
                    # Get translation for this locale
                    try:
                        translation = UiMessageTranslation.objects.get(
                            message=ui_message, locale=locale
                        )
                    except UiMessageTranslation.DoesNotExist:
                        continue

                    # Extract msgid from key (remove app prefix)
                    msgid = (
                        ui_message.key.split(".", 1)[1]
                        if "." in ui_message.key
                        else ui_message.key
                    )

                    # Find or create entry in .po file
                    entry = po.find(msgid)
                    if entry:
                        entry.msgstr = translation.value
                        if translation.status == "needs_review":
                            entry.flags.append("fuzzy")
                    else:
                        entry = polib.POEntry(
                            msgid=msgid,
                            msgstr=translation.value,
                        )
                        if translation.status == "needs_review":
                            entry.flags = ["fuzzy"]
                        po.append(entry)

                    exported_count += 1

                # Save .po file
                po.save(str(po_file_path))

                # Compile to .mo file
                mo_file_path = po_dir / "django.mo"
                po.save_as_mofile(str(mo_file_path))

        self.stdout.write(
            self.style.SUCCESS(
                f"Export complete: {exported_count} translations exported"
            )
        )
