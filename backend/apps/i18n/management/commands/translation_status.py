from django.core.management.base import BaseCommand



from apps.i18n.models import Locale, UiMessage, UiMessageTranslation



"""Show translation status for a locale."""



class Command(BaseCommand):

    help = "Show translation status for a locale"



    def add_arguments(self, parser):

        parser.add_argument(

            "--locale",

            type=str,

            default="fr",

            help="Locale code to check (default: fr)",

        )



    def handle(self, *args, **options):

        locale_code = options["locale"]



        try:

            locale = Locale.objects.get(code=locale_code)

        except Locale.DoesNotExist:

            self.stdout.write(self.style.ERROR(f"Locale {locale_code} not found"))



        self.stdout.write(f"Translation status for: {locale.name} ({locale.code})")

        self.stdout.write(f"Active: {locale.is_active}")

        self.stdout.write("-" * 50)



        # Total UI messages

        total_messages = UiMessage.objects.count()

        self.stdout.write(f"Total UI messages: {total_messages}")



        # Messages with translations for this locale

        translated_messages = UiMessage.objects.filter(

            id__in=UiMessageTranslation.objects.filter(locale=locale).values_list(

                "message_id", flat=True

            )

        ).count()

        self.stdout.write(

            f"Messages with {locale.code} translations: {translated_messages}"

        )



        # Messages WITHOUT translations for this locale

        untranslated_messages = UiMessage.objects.exclude(

            id__in=UiMessageTranslation.objects.filter(locale=locale).values_list(

                "message_id", flat=True

            )

        ).count()

        self.stdout.write(

            f"Messages WITHOUT {locale.code} translations: {untranslated_messages}"

        )



        # Calculate percentage

        if total_messages > 0:

            percentage = (translated_messages / total_messages) * 100

            """self.stdout.write(f"Translation coverage: {percentage:.1f}%")"""



        # Show breakdown by namespace

        self.stdout.write("\nBreakdown by namespace:")

        namespaces = (

            UiMessage.objects.values("namespace").distinct().order_by("namespace")

        )



        for ns in namespaces:

            namespace = ns["namespace"]

            ns_total = UiMessage.objects.filter(namespace=namespace).count()

            ns_translated = UiMessage.objects.filter(

                namespace=namespace,

                id__in=UiMessageTranslation.objects.filter(locale=locale).values_list(

                    "message_id", flat=True

                ),

            ).count()

            ns_percentage = (ns_translated / ns_total * 100) if ns_total > 0 else 0



            self.stdout.write(

                f"  {namespace}: {ns_translated}/{ns_total} ({ns_percentage:.1f}%)"

            )



        # Show recent translations

        self.stdout.write("\nRecent translations:")

        recent_translations = (

            UiMessageTranslation.objects.filter(locale=locale)

            .select_related("message")

            .order_by("-created_at")[:5]

        )



        if recent_translations:

            for trans in recent_translations:

                self.stdout.write(f'  - {trans.message.key}: "{trans.value}"')

        else:

            self.stdout.write("  No translations found.")

