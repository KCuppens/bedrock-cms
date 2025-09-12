from django.core.management.base import BaseCommand

from apps.i18n.services import DeepLTranslationService

"""
Test DeepL translation service.
"""


class Command(BaseCommand):
    help = "Test DeepL translation service"

    def handle(self, *args, **options):
        service = DeepLTranslationService()

        # Test translation
        test_text = "Hello world"
        source_lang = "en"
        target_lang = "fr"

        self.stdout.write("Testing DeepL translation:")
        self.stdout.write(f'Text: "{test_text}"')
        self.stdout.write(f"From: {source_lang}")
        self.stdout.write(f"To: {target_lang}")
        self.stdout.write("-" * 30)

        result = service.translate(test_text, source_lang, target_lang)

        if result:
            self.stdout.write(self.style.SUCCESS(f'Translation: "{result}"'))
        else:
            self.stdout.write(self.style.ERROR("Translation failed"))

        # Test with actual UI message content
        self.stdout.write("\nTesting actual UI message content:")
        ui_texts = ["15 min ago", "Add Locale", "Blog Post: Q4 Updates", "Broken Links"]

        for text in ui_texts:
            result = service.translate(text, "en", "fr")
            if result:
                self.stdout.write(f'✓ "{text}" → "{result}"')
            else:
                self.stdout.write(self.style.ERROR(f'✗ "{text}" → FAILED'))
