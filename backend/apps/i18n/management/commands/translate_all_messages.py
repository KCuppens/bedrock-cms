import time



from django.core.management.base import BaseCommand



from apps.i18n.models import Locale, UiMessage, UiMessageTranslation

from apps.i18n.services import DeepLTranslationService



Translate ALL UI messages to a target locale using DeepL.



class Command(BaseCommand):

    help = "Translate ALL UI messages to a target locale using DeepL"



    def add_arguments(self, parser):

        parser.add_argument(

            "--locale", type=str, default="fr", help="Target locale code (default: fr)"

        )

        parser.add_argument(

            "--source", type=str, default="en", help="Source locale code (default: en)"

        )

        parser.add_argument(

            "--force",

            action="store_true",

            help="Force re-translation of existing translations",

        )

        parser.add_argument(

            "--batch-size",

            type=int,

            default=10,

            help="Number of translations per batch (default: 10)",

        )

        parser.add_argument(

            "--delay",

            type=float,

            default=0.1,

            help="Delay between translations in seconds (default: 0.1)",

        )



    def handle(self, *args, **options):  # noqa: C901

        target_locale_code = options["locale"]

        source_locale_code = options["source"]

        force = options["force"]

        batch_size = options["batch_size"]

        delay = options["delay"]



        # Get locales

        try:

            target_locale = Locale.objects.get(code=target_locale_code, is_active=True)

            source_locale = Locale.objects.get(code=source_locale_code)

        except Locale.DoesNotExist as e:

            self.stdout.write(self.style.ERROR(f"Locale error: {e}"))



        self.stdout.write(

            f"Translating ALL UI messages from {source_locale.name} to {target_locale.name}"

        )

        self.stdout.write(f"Force re-translation: {force}")

        self.stdout.write("-" * 50)



        # Get messages to translate

        if force:

            # Translate all messages

            messages_to_translate = UiMessage.objects.all()

        else:

            # Only translate messages without existing translations

            messages_to_translate = UiMessage.objects.exclude(

                id__in=UiMessageTranslation.objects.filter(

                    locale=target_locale

                ).values_list("message_id", flat=True)

            )



        total_messages = messages_to_translate.count()

        self.stdout.write(f"Total messages to translate: {total_messages}")



        if total_messages == 0:

            self.stdout.write(self.style.SUCCESS("No messages need translation!"))



        # Initialize DeepL service

        deepl_service = DeepLTranslationService()



        translated_count = 0

        updated_count = 0

        skipped_count = 0

        error_count = 0



        # Process in batches

        for i in range(0, total_messages, batch_size):

            batch = list(messages_to_translate[i : i + batch_size])



            self.stdout.write(

                f"\nProcessing batch {i // batch_size + 1} ({i + 1}-{min(i + batch_size, total_messages)} of {total_messages})"

            )



            for message in batch:

                try:

                    # Skip if no default value

                    if not message.default_value or not message.default_value.strip():

                        self.stdout.write(

                            f"  [SKIP] {message.key}: empty default value"

                        )

                        skipped_count += 1



                    # Check if translation exists (for force mode)

                    existing_translation = None

                    if force:

                        try:

                            existing_translation = UiMessageTranslation.objects.get(

                                message=message, locale=target_locale

                            )

                        except UiMessageTranslation.DoesNotExist:



                    # Translate using DeepL

                    self.stdout.write(

                        f'  -> Translating: "{message.default_value[:50]}{"..." if len(message.default_value) > 50 else ""}"'

                    )



                    translated_text = deepl_service.translate(

                        text=message.default_value,

                        source_lang=source_locale.code,

                        target_lang=target_locale.code,

                    )



                    if translated_text and translated_text.strip():

                        if existing_translation:

                            # Update existing translation

                            existing_translation.value = translated_text

                            existing_translation.status = "draft"

                            existing_translation.save()

                            self.stdout.write(

                                f'    [OK] Updated: "{translated_text[:50]}{"..." if len(translated_text) > 50 else ""}"'

                            )

                            updated_count += 1

                        else:

                            # Create new translation

                            UiMessageTranslation.objects.create(

                                message=message,

                                locale=target_locale,

                                value=translated_text,

                                status="draft",

                            )

                            self.stdout.write(

                                f'    [OK] Created: "{translated_text[:50]}{"..." if len(translated_text) > 50 else ""}"'

                            )

                            translated_count += 1

                    else:

                        self.stdout.write("    [FAIL] No translation returned")

                        skipped_count += 1



                    # Add delay to avoid rate limiting

                    time.sleep(delay)



                except Exception as e:

                    self.stdout.write(self.style.ERROR(f"    [ERROR] {str(e)}"))

                    error_count += 1



        # Summary

        self.stdout.write("\n" + "=" * 50)

        self.stdout.write(self.style.SUCCESS("Translation Complete!"))

        self.stdout.write(f"Total processed: {total_messages}")

        self.stdout.write(f"New translations created: {translated_count}")

        self.stdout.write(f"Existing translations updated: {updated_count}")

        self.stdout.write(f"Skipped (empty/failed): {skipped_count}")

        self.stdout.write(f"Errors: {error_count}")



        # Show final statistics

        total_translations = UiMessageTranslation.objects.filter(

            locale=target_locale

        ).count()

        total_ui_messages = UiMessage.objects.count()

        coverage = (

            (total_translations / total_ui_messages * 100)

            if total_ui_messages > 0

            else 0

        )



        self.stdout.write(f"\nFinal translation coverage for {target_locale.name}:")

        self.stdout.write(

            f"{total_translations}/{total_ui_messages} messages ({coverage:.1f}%)"

        )

