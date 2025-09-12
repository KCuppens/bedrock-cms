"""
Translation services for auto-suggestions and machine translation.
"""

import logging

from django.conf import settings

import requests

logger = logging.getLogger(__name__)


class DeepLTranslationService:
    """
    DeepL API integration for machine translation suggestions.

    Provides simple, high-quality translation suggestions using DeepL API.
    """

    def __init__(self):
        self.api_key = getattr(settings, "DEEPL_API_KEY", None)
        if not self.api_key:
            logger.warning(
                "DEEPL_API_KEY not configured - translations will use fallback"
            )
        else:
            logger.info(f"DEEPL_API_KEY configured: {self.api_key[:10]}...")

        # Always use free API endpoint for now
        # The endpoint detection based on key suffix isn't reliable
        self.base_url = "https://api-free.deepl.com/v2"
        logger.info("Using DeepL Free API")

    def translate(self, text, source_lang, target_lang):
        """
        Translate text from source language to target language.

        Args:
            text (str): Text to translate
            source_lang (str): Source language code (e.g., 'en', 'es')
            target_lang (str): Target language code (e.g., 'es', 'fr')

        Returns:
            str: Translated text or None if translation failed
        """
        if not text or not text.strip():
            return None

        # If no API key, use simple fallback translations
        if not self.api_key:
            return self._fallback_translate(text, source_lang, target_lang)

        # Map common locale codes to DeepL language codes
        lang_mapping = {
            "en": "EN",
            "es": "ES",
            "fr": "FR",
            "de": "DE",
            "it": "IT",
            "pt": "PT",
            "ru": "RU",
            "ja": "JA",
            "zh": "ZH",
            "ko": "KO",
            "nl": "NL",
            "pl": "PL",
            "sv": "SV",
            "da": "DA",
            "fi": "FI",
            "no": "NB",  # Norwegian
            "cs": "CS",  # Czech
            "hu": "HU",  # Hungarian
            "et": "ET",  # Estonian
            "lv": "LV",  # Latvian
            "lt": "LT",  # Lithuanian
            "sk": "SK",  # Slovak
            "sl": "SL",  # Slovenian
            "bg": "BG",  # Bulgarian
            "ro": "RO",  # Romanian
            "el": "EL",  # Greek
            "tr": "TR",  # Turkish
            "uk": "UK",  # Ukrainian
        }

        source_code = lang_mapping.get(source_lang.lower(), source_lang.upper())
        target_code = lang_mapping.get(target_lang.lower(), target_lang.upper())

        logger.info(
            f"DeepL translate request: '{text}' from {source_lang}({source_code}) to {target_lang}({target_code})"
        )

        try:
            logger.info(f"Making DeepL API request to: {self.base_url}/translate")
            logger.info(
                f"Request data: text='{text}', source_lang={source_code}, target_lang={target_code}"
            )

            response = requests.post(
                f"{self.base_url}/translate",
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                data={
                    "text": text,
                    "source_lang": source_code,
                    "target_lang": target_code,
                    "preserve_formatting": "1",
                },
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("translations"):
                    translated_text = result["translations"][0]["text"]
                    logger.info(
                        f"DeepL translation successful: '{text}' -> '{translated_text}' ({source_lang}->{target_lang})"
                    )
                    return translated_text
                else:
                    logger.warning("DeepL response missing translations array")
            else:
                logger.error(f"DeepL API error {response.status_code}: {response.text}")

        except requests.RequestException as e:
            logger.error(f"DeepL API request failed: {e}")
        except Exception as e:
            logger.error(f"DeepL translation error: {e}")

        logger.warning(
            f"DeepL translation returned None for: '{text}' ({source_lang}->{target_lang})"
        )
        return None

    def get_supported_languages(self):
        """
        Get list of supported languages from DeepL API.

        Returns:
            dict: Dictionary with 'source' and 'target' language lists
        """
        try:
            response = requests.get(
                f"{self.base_url}/languages",
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                params={"type": "source"},
                timeout=10,
            )

            source_languages = []
            if response.status_code == 200:
                source_languages = response.json()

            response = requests.get(
                f"{self.base_url}/languages",
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                params={"type": "target"},
                timeout=10,
            )

            target_languages = []
            if response.status_code == 200:
                target_languages = response.json()

            return {"source": source_languages, "target": target_languages}

        except Exception as e:
            logger.error(f"Failed to get DeepL supported languages: {e}")
            return {"source": [], "target": []}

    def _fallback_translate(self, text, source_lang, target_lang):
        """
        Simple fallback translation when DeepL is not available.
        Provides basic translations for common UI terms.
        """
        # Basic translation dictionary for common UI terms
        translations = {
            "en": {
                "es": {
                    "home": "inicio",
                    "about": "acerca de",
                    "contact": "contacto",
                    "products": "productos",
                    "services": "servicios",
                    "login": "iniciar sesión",
                    "logout": "cerrar sesión",
                    "register": "registrarse",
                    "search": "buscar",
                    "menu": "menú",
                    "settings": "configuración",
                    "profile": "perfil",
                    "dashboard": "tablero",
                    "welcome": "bienvenido",
                },
                "fr": {
                    "home": "accueil",
                    "about": "à propos",
                    "contact": "contact",
                    "products": "produits",
                    "services": "services",
                    "login": "connexion",
                    "logout": "déconnexion",
                    "register": "s'inscrire",
                    "search": "rechercher",
                    "menu": "menu",
                    "settings": "paramètres",
                    "profile": "profil",
                    "dashboard": "tableau de bord",
                    "welcome": "bienvenue",
                },
                "de": {
                    "home": "startseite",
                    "about": "über",
                    "contact": "kontakt",
                    "products": "produkte",
                    "services": "dienstleistungen",
                    "login": "anmelden",
                    "logout": "abmelden",
                    "register": "registrieren",
                    "search": "suchen",
                    "menu": "menü",
                    "settings": "einstellungen",
                    "profile": "profil",
                    "dashboard": "dashboard",
                    "welcome": "willkommen",
                },
            }
        }

        # Try to find a basic translation
        text_lower = text.lower().strip()
        if source_lang in translations and target_lang in translations[source_lang]:
            if text_lower in translations[source_lang][target_lang]:
                # Preserve capitalization
                translated = translations[source_lang][target_lang][text_lower]
                if text[0].isupper():
                    translated = translated.capitalize()
                if text.isupper():
                    translated = translated.upper()
                return translated

        # If no translation found, return a placeholder indicating translation needed
        logger.info(
            f"No fallback translation for '{text}' from {source_lang} to {target_lang}"
        )

        # For Spanish, provide basic word-by-word translation for "Home"
        if source_lang == "en" and target_lang == "es":
            if text_lower == "home":
                return "Inicio"

        # Return None if no translation available
        # This will cause the translation to be skipped
        return None

    def check_usage(self):
        """
        Check current API usage and limits.

        Returns:
            dict: Usage information or None if failed
        """
        try:
            response = requests.get(
                f"{self.base_url}/usage",
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                timeout=10,
            )

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.error(f"Failed to check DeepL usage: {e}")

        return None
