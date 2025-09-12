from django.core.management.base import BaseCommand



from apps.i18n.models import Locale, UiMessage, UiMessageTranslation



Debug command to check UI messages that need translation.



class Command(BaseCommand):

    help = "Debug UI messages that need translation"



    def add_arguments(self, parser):

        parser.add_argument(

            "--locale", type=str, default="es", help="Target locale code (default: es)"

        )

        parser.add_argument(

            "--limit",

            type=int,

            default=10,

            help="Number of messages to show (default: 10)",

        )



    def handle(self, *args, **options):

        locale_code = options["locale"]

        limit = options["limit"]



        try:

            target_locale = Locale.objects.get(code=locale_code, is_active=True)

        except Locale.DoesNotExist:

            self.stdout.write(

                self.style.ERROR(f"Locale {locale_code} not found or not active")

            )



        # Get messages that need translation

        messages_query = UiMessage.objects.exclude(

            id__in=UiMessageTranslation.objects.filter(

                locale=target_locale

            ).values_list("message_id", flat=True)

        )



        total_count = messages_query.count()

        sample_messages = messages_query[:limit]



        self.stdout.write(f"Target locale: {target_locale.code}")

        self.stdout.write(f"Total messages needing translation: {total_count}")

        self.stdout.write(f"Showing first {limit} messages:")

        self.stdout.write("-" * 50)



        for i, message in enumerate(sample_messages, 1):

            self.stdout.write(f"{i}. Key: {message.key}")

            self.stdout.write(f"   Namespace: {message.namespace}")

            self.stdout.write(f'   Default value: "{message.default_value}"')

            self.stdout.write(f"   Description: {message.description or 'None'}")

            self.stdout.write(f"   Created: {message.created_at}")

            self.stdout.write("")



        # Check if messages have empty default values

        empty_default_count = (

            messages_query.filter(default_value__isnull=True).count()

            + messages_query.filter(default_value="").count()

        )



        self.stdout.write(f"Messages with empty default_value: {empty_default_count}")



        # Show sample of non-empty messages

        non_empty_messages = messages_query.exclude(default_value__isnull=True).exclude(

            default_value=""

        )[:5]



        if non_empty_messages:

            self.stdout.write("\nSample messages with non-empty default_value:")

            for msg in non_empty_messages:

                self.stdout.write(f'- {msg.key}: "{msg.default_value}"')

