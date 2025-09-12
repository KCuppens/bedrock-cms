from django.core.management.base import BaseCommand

from django.utils import translation

from django.utils.translation import gettext_lazy as _



from apps.i18n.models import Locale, UiMessage, UiMessageTranslation



Import Django's built-in translation strings into the database.

This includes admin interface strings, form validation messages, etc.



class Command(BaseCommand):

    help = "Import Django built-in translation strings into database"



    # Common Django translation strings to import

    DJANGO_STRINGS = {

        # Admin interface

        "admin.site_title": _("Django site admin"),

        "admin.site_header": _("Django administration"),

        "admin.index_title": _("Site administration"),

        "admin.add": _("Add"),

        "admin.change": _("Change"),

        "admin.delete": _("Delete"),

        "admin.save": _("Save"),

        "admin.save_continue": _("Save and continue editing"),

        "admin.save_add_another": _("Save and add another"),

        "admin.delete_selected": _("Delete selected"),

        "admin.change_password": _("Change password"),

        "admin.logout": _("Log out"),

        "admin.view_site": _("View site"),

        "admin.filter": _("Filter"),

        "admin.clear_filters": _("Clear all filters"),

        "admin.search": _("Search"),

        "admin.show_all": _("Show all"),

        # Form validation

        "validation.required": _("This field is required."),

        "validation.invalid": _("Enter a valid value."),

        "validation.email_invalid": _("Enter a valid email address."),

        "validation.url_invalid": _("Enter a valid URL."),

        "validation.min_length": _(

            "Ensure this value has at least %(limit_value)d character (it has %(show_value)d)."

        ),

        "validation.max_length": _(

            "Ensure this value has at most %(limit_value)d character (it has %(show_value)d)."

        ),

        "validation.min_value": _(

            "Ensure this value is greater than or equal to %(limit_value)s."

        ),

        "validation.max_value": _(

            "Ensure this value is less than or equal to %(limit_value)s."

        ),

        # Authentication

        "auth.login": _("Log in"),

        "auth.logout": _("Log out"),

        "auth.password": _("Password"),

        "auth.username": _("Username"),

        "auth.email": _("Email address"),

        "auth.forgot_password": _("Forgotten your password?"),

        "auth.reset_password": _("Reset password"),

        "auth.change_password": _("Change password"),

        "auth.password_reset_sent": _(

            "We've emailed you instructions for setting your password."

        ),

        "auth.invalid_login": _("Please enter a correct %(username)s and password."),

        # Permissions

        "perms.add": _("Can add %(verbose_name)s"),

        "perms.change": _("Can change %(verbose_name)s"),

        "perms.delete": _("Can delete %(verbose_name)s"),

        "perms.view": _("Can view %(verbose_name)s"),

        # Dates and times

        "datetime.today": _("Today"),

        "datetime.tomorrow": _("Tomorrow"),

        "datetime.yesterday": _("Yesterday"),

        "datetime.now": _("Now"),

        "datetime.am": _("a.m."),

        "datetime.pm": _("p.m."),

        "datetime.midnight": _("Midnight"),

        "datetime.noon": _("Noon"),

        # Pagination

        "pagination.previous": _("Previous"),

        "pagination.next": _("Next"),

        "pagination.first": _("First"),

        "pagination.last": _("Last"),

        "pagination.page": _("Page"),

        "pagination.of": _("of"),

        # Common actions

        "actions.yes": _("Yes"),

        "actions.no": _("No"),

        "actions.save": _("Save"),

        "actions.cancel": _("Cancel"),

        "actions.delete": _("Delete"),

        "actions.edit": _("Edit"),

        "actions.view": _("View"),

        "actions.download": _("Download"),

        "actions.upload": _("Upload"),

        "actions.submit": _("Submit"),

        "actions.confirm": _("Confirm"),

        "actions.close": _("Close"),

        "actions.back": _("Back"),

        "actions.continue": _("Continue"),

        "actions.retry": _("Retry"),

        "actions.refresh": _("Refresh"),

        # Status messages

        "status.success": _("Success"),

        "status.error": _("Error"),

        "status.warning": _("Warning"),

        "status.info": _("Information"),

        "status.loading": _("Loading..."),

        "status.saving": _("Saving..."),

        "status.deleting": _("Deleting..."),

        "status.processing": _("Processing..."),

        # File upload

        "files.choose_file": _("Choose file"),

        "files.no_file_chosen": _("No file chosen"),

        "files.upload": _("Upload"),

        "files.drop_files": _("Drop files here"),

        "files.browse": _("Browse"),

        "files.size_error": _("File size exceeds limit"),

        "files.type_error": _("Invalid file type"),

    }



    def add_arguments(self, parser):

        parser.add_argument(

            "--locale", type=str, help="Specific locale to import translations for"

        )

        parser.add_argument(

            "--namespace",

            type=str,

            default="django",

            help="Namespace for imported messages",

        )

        parser.add_argument(

            "--update-existing",

            action="store_true",

            help="Update existing translations",

        )



    def handle(self, *args, **options):  # noqa: C901

        locale_code = options.get("locale")

        namespace = options["namespace"]

        update_existing = options.get("update_existing", False)



        # Get locales to process

        if locale_code:

            locales = Locale.objects.filter(code=locale_code, is_active=True)

        else:

            locales = Locale.objects.filter(is_active=True)



        if not locales.exists():

            self.stdout.write(self.style.ERROR("No active locales found"))



        created_messages = 0

        created_translations = 0

        updated_translations = 0



        # Get default locale

        default_locale = Locale.objects.filter(is_default=True).first()

        if not default_locale:

            self.stdout.write(self.style.ERROR("No default locale set"))



        # Import each string

        for key, lazy_string in self.DJANGO_STRINGS.items():

            # Get default value (in default locale)

            with translation.override(default_locale.code):

                default_value = str(lazy_string)



            # Create or get UiMessage

            ui_message, created = UiMessage.objects.get_or_create(

                key=key,

                defaults={

                    "namespace": namespace,

                    "default_value": default_value,

                    "description": f"Django built-in: {key.replace('.', ' ').title()}",

                },

            )



            if created:

                created_messages += 1

                self.stdout.write(f"Created message: {key}")



            # Create translations for each locale

            for locale in locales:

                # Skip if same as default and not forced

                if locale.id == default_locale.id and not update_existing:



                # Get translated value

                with translation.override(locale.code):

                    translated_value = str(lazy_string)



                # Skip if translation is same as default (not actually translated)

                if translated_value == default_value and locale.id != default_locale.id:



                # Create or update translation

                if update_existing:

                    translation_obj, trans_created = (

                        UiMessageTranslation.objects.update_or_create(

                            message=ui_message,

                            locale=locale,

                            defaults={"value": translated_value, "status": "approved"},

                        )

                    )

                    if not trans_created:

                        updated_translations += 1

                else:

                    translation_obj, trans_created = (

                        UiMessageTranslation.objects.get_or_create(

                            message=ui_message,

                            locale=locale,

                            defaults={"value": translated_value, "status": "approved"},

                        )

                    )



                if trans_created:

                    created_translations += 1



        self.stdout.write(

            self.style.SUCCESS(

                f"Import complete:\n"

                f"  - {created_messages} messages created\n"

                f"  - {created_translations} translations created\n"

                f"  - {updated_translations} translations updated"

            )

        )



        # Show statistics per locale

        self.stdout.write("\nTranslation coverage by locale:")

        for locale in locales:

            total_messages = UiMessage.objects.filter(namespace=namespace).count()

            translated = UiMessageTranslation.objects.filter(

                message__namespace=namespace, locale=locale

            ).count()

            percentage = (

                (translated / total_messages * 100) if total_messages > 0 else 0

            )

            self.stdout.write(

                f"  {locale.code}: {translated}/{total_messages} ({percentage:.1f}%)"

            )

