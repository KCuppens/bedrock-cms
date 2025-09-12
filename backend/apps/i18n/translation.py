import json
from typing import Any, Optional

from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet

from .models import Locale, TranslationUnit, UiMessage, UiMessageTranslation

"""Translation utilities for content fallback and resolution."""



class TranslationResolver:
    """Utility for resolving translated content with fallback support."""



    def __init__(self, target_locale: Locale):

        """Initialize resolver with target locale."""

        self.target_locale = target_locale

        self.fallback_chain = target_locale.get_fallback_chain()



    def resolve_field(self, obj, field: str, default_value: str = "") -> str:



        """Resolve a translated field with fallback.

        Args:
            obj: Object to get translation for
            field: Field name to translate
            default_value: Default if no translation found

        Returns:
            Translated text or fallback
        """



        content_type = ContentType.objects.get_for_model(obj)



        # Try each locale in the fallback chain

        for locale in self.fallback_chain:

            try:

                unit = TranslationUnit.objects.get(

                    content_type=content_type,

                    object_id=obj.pk,

                    field=field,

                    target_locale=locale,

                    status="approved",

                )

                if unit.target_text:

                    return unit.target_text

            except TranslationUnit.DoesNotExist:
                pass



        # If no approved translation found, try source text from any unit

        try:

            unit = TranslationUnit.objects.filter(

                content_type=content_type, object_id=obj.pk, field=field

            ).first()



            if unit is not None and unit.source_text:

                return unit.source_text

        except TranslationUnit.DoesNotExist:
            pass



        # Fall back to current field value or default

        try:

            current_value = getattr(obj, field, None)

            if current_value is not None and str(current_value).strip():

                return str(current_value)

            else:

                return default_value

        except AttributeError:

            return default_value



    def resolve_object(self, obj, fields: list[str]) -> dict[str, str]:



        """Resolve multiple fields for an object.

        Args:
            obj: Object to translate
            fields: List of field names to translate

        Returns:
            Dict mapping field names to translated values
        """



        result = {}

        for field in fields:

            result[field] = self.resolve_field(obj, field)

        return result



    def get_translation_status(

        self, obj, fields: list[str]

    ) -> dict[str, dict[str, Any]]:



        """Get translation status for multiple fields.

        Args:
            obj: Object to check
            fields: List of field names

        Returns:
            Dict with translation status info for each field
        """



        content_type = ContentType.objects.get_for_model(obj)

        result = {}



        for field in fields:

            field_info = {

                "target_locale": self.target_locale.code,

                "has_translation": False,

                "status": "missing",

                "fallback_locale": None,

                "needs_update": False,

            }



            # Check for translation in target locale

            try:

                unit = TranslationUnit.objects.get(

                    content_type=content_type,

                    object_id=obj.pk,

                    field=field,

                    target_locale=self.target_locale,

                )

                field_info["has_translation"] = True

                field_info["status"] = unit.status

                field_info["needs_update"] = unit.status == "needs_review"



            except TranslationUnit.DoesNotExist:

                # Check fallback chain

                for locale in self.fallback_chain[1:]:  # Skip target locale

                    try:

                        fallback_unit = TranslationUnit.objects.get(

                            content_type=content_type,

                            object_id=obj.pk,

                            field=field,

                            target_locale=locale,

                            status="approved",

                        )

                        if fallback_unit.target_text:

                            field_info["fallback_locale"] = locale.code



                    except TranslationUnit.DoesNotExist:
                        pass



            result[field] = field_info



        return result



class TranslationManager:



    """Manager for handling content translation operations."""



    # Configuration for translatable fields per model

    TRANSLATABLE_FIELDS = {

        "cms.page": ["title", "blocks"],  # Will be expanded as needed

    }



    def __init__(self):

        """Initialize translation manager."""



    @classmethod

    def register_translatable_fields(cls, model_label: str, fields: list[str]):

        """Register translatable fields for a model."""

        cls.TRANSLATABLE_FIELDS[model_label] = fields



    @classmethod

    def get_translatable_fields(cls, obj) -> list[str]:

        """Get list of translatable fields for an object."""

        content_type = ContentType.objects.get_for_model(obj)

        model_label = f"{content_type.app_label}.{content_type.model}"

        return cls.TRANSLATABLE_FIELDS.get(model_label, [])



    @classmethod

    def create_translation_units(cls, obj, source_locale: Locale, user=None):



        """Create translation units for an object's translatable fields."""



        Args:

            obj: Object to create units for

            source_locale: Source locale of the content

            user: User creating the units



        translatable_fields = cls.get_translatable_fields(obj)

        if not translatable_fields:



        # Get all active target locales except source

        target_locales = Locale.objects.filter(is_active=True).exclude(

            pk=source_locale.pk

        )



        for field in translatable_fields:

            # Extract source text

            source_text = cls._extract_field_text(obj, field)

            if not source_text:



            # Create units for each target locale

            for target_locale in target_locales:

                TranslationUnit.upsert_unit(

                    obj=obj,

                    field=field,

                    source_locale=source_locale,

                    target_locale=target_locale,

                    source_text=source_text,

                    user=user,

                )



    @classmethod

    def _extract_field_text(cls, obj, field: str) -> str:



        Extract text content from a field for translation.



        Args:

            obj: Object to extract from

            field: Field name



        Returns:

            Text content as string



        try:

            value = getattr(obj, field)

            if isinstance(value, str):

                return value

            elif isinstance(value, list):

                # For blocks or other JSON fields, serialize to JSON

                return json.dumps(value, ensure_ascii=False)

            elif isinstance(value, dict):

                return json.dumps(value, ensure_ascii=False)

            else:

                return str(value) if value is not None else ""



        except AttributeError:

            return ""



    def create_translation(

        self,

        obj,

        field: str,

        source_locale: Locale,

        target_locale: Locale,

        source_text: str,

        target_text: str = "",

        status: str = "draft",

        user=None,

    ) -> TranslationUnit:



        Create a new translation unit.



        Args:

            obj: Object to translate

            field: Field name

            source_locale: Source locale

            target_locale: Target locale

            source_text: Source text

            target_text: Translated text

            status: Translation status

            user: User creating the translation



        Returns:

            Created TranslationUnit



        content_type = ContentType.objects.get_for_model(obj)



        unit, created = TranslationUnit.objects.update_or_create(

            content_type=content_type,

            object_id=obj.pk,

            field=field,

            source_locale=source_locale,

            target_locale=target_locale,

            defaults={

                "source_text": source_text,

                "target_text": target_text,

                "status": status,

                "updated_by": user,

            },

        )

        return unit



    def update_translation(

        self,

        unit: TranslationUnit,

        target_text: str | None = None,

        status: str | None = None,

        user=None,

    ) -> TranslationUnit:



        Update an existing translation unit.



        Args:

            unit: TranslationUnit to update

            target_text: New translated text

            status: New status

            user: User updating the translation



        Returns:

            Updated TranslationUnit



        if target_text is not None:

            unit.target_text = target_text

        if status is not None:

            unit.status = status

        if user is not None:

            unit.updated_by = user

        unit.save()

        return unit



    def get_translations_for_object(

        self, obj, target_locale: Optional["Locale"] = None

    ) -> "QuerySet[TranslationUnit]":



        Get all translations for an object.



        Args:

            obj: Object to get translations for

            target_locale: Optional locale filter



        Returns:

            QuerySet of TranslationUnit objects



        content_type = ContentType.objects.get_for_model(obj)



        units = TranslationUnit.objects.filter(

            content_type=content_type, object_id=obj.pk

        )



        if target_locale:

            units = units.filter(target_locale=target_locale)



        return units



    def bulk_create_translations(

        self,

        translations_data: list[dict[str, Any]],

        source_locale: Locale,

        target_locale: Locale,

        user=None,

    ) -> list[TranslationUnit]:



        Bulk create multiple translations.



        Args:

            translations_data: List of dicts with obj,

                field,

                source_text,

                target_text

            source_locale: Source locale for all translations

            target_locale: Target locale for all translations

            user: User creating the translations



        Returns:

            List of created TranslationUnit objects



        units = []

        for data in translations_data:

            unit = self.create_translation(

                obj=data["obj"],

                field=data["field"],

                source_locale=source_locale,

                target_locale=target_locale,

                source_text=data["source_text"],

                target_text=data.get("target_text", ""),

                status=data.get("status", "draft"),

                user=user,

            )

            """units.append(unit)"""

        return units



    def get_translation_progress(

        self, obj, target_locale: Locale, fields: list[str]

    ) -> dict[str, Any]:



        Get translation progress for an object.



        Args:

            obj: Object to check

            target_locale: Target locale

            fields: List of fields to check



        Returns:

            Dict with progress statistics



        content_type = ContentType.objects.get_for_model(obj)



        total_fields = len(fields)

        translated_fields = 0

        pending_fields = 0

        missing_fields = 0



        for field in fields:

            try:

                unit = TranslationUnit.objects.get(

                    content_type=content_type,

                    object_id=obj.pk,

                    field=field,

                    target_locale=target_locale,

                )



                if unit.status == "approved" and unit.target_text:

                    translated_fields += 1

                elif unit.status in ["draft", "pending", "needs_review"]:

                    pending_fields += 1

                else:

                    missing_fields += 1



            except TranslationUnit.DoesNotExist:

                missing_fields += 1



        completion_percentage = (

            (translated_fields / total_fields * 100) if total_fields > 0 else 0

        )



        return {

            "total_fields": total_fields,

            "translated_fields": translated_fields,

            "pending_fields": pending_fields,

            "missing_fields": missing_fields,

            "completion_percentage": completion_percentage,

        }



    @classmethod

    def get_resolver(cls, locale_code: str) -> TranslationResolver:



        Get a translation resolver for a locale.



        Args:

            locale_code: Target locale code



        Returns:

            TranslationResolver instance



        try:

            locale = Locale.objects.get(code=locale_code, is_active=True)

            return TranslationResolver(locale)

        except Locale.DoesNotExist:

            # Fall back to default locale

            default_locale = Locale.objects.get(is_default=True, is_active=True)

            return TranslationResolver(default_locale)



class UiMessageResolver:



    Resolver for UI message translations.



    def __init__(self, locale: Locale):

        """Initialize with target locale."""

        self.locale = locale

        self.fallback_chain = locale.get_fallback_chain()



    def resolve_message(self, key: str, default: str = "") -> str:



        Resolve a UI message with fallback.



        Args:

            key: Message key

            default: Default value if not found



        Returns:

            Translated message text



        try:

            message = UiMessage.objects.get(key=key)



            # Try each locale in fallback chain

            for locale in self.fallback_chain:

                try:

                    translation = UiMessageTranslation.objects.get(

                        message=message, locale=locale, status="approved"

                    )

                    return translation.value

                except UiMessageTranslation.DoesNotExist:
                    pass



            # Fall back to default value

            return message.default_value if message.default_value else default



        except UiMessage.DoesNotExist:

            return default



    def resolve(

        self,

        key: str,

        default: str | None = None,

        parameters: dict[str, Any] | None = None,

    ) -> str:



        Resolve a UI message with fallback and parameter substitution.

        Alias for resolve_message with parameter support.



        Args:

            key: Message key

            default: Default value if not found

            parameters: Optional dict of parameters to substitute



        Returns:

            Translated message text with parameters substituted



        if default is None:

            default = key



        message = self.resolve_message(key, default)

        # Apply parameter substitution if provided

        if parameters:

            try:

                # Use Python string formatting

                message = message.format(**parameters)

            except (KeyError, ValueError):

                # If formatting fails, return message as-is



        return message



    def get_message_bundle(self, namespace: str | None = None) -> dict[str, str]:



        Get all messages for a namespace as a dict.



        Args:

            namespace: Optional namespace filter



        Returns:

            """Dict mapping message keys to translated values"""



        messages = UiMessage.objects.all()

        if namespace:

            messages = messages.filter(namespace=namespace)



        result = {}

        for message in messages:

            result[message.key] = self.resolve_message(message.key)



        return result



    def get_namespaced_bundle(self) -> dict[str, dict[str, str]]:



        Get all messages organized by namespace.



        Returns:

            """Dict mapping namespaces to message dicts"""



        # Get all namespaces

        namespaces = UiMessage.objects.values_list("namespace", flat=True).distinct()



        result = {}

        for namespace in namespaces:

            result[namespace] = self.get_message_bundle(namespace)



        return result



    def get_all_messages(self) -> dict[str, str]:



        Get all messages as a flat dictionary.

        Alias for get_message_bundle with no namespace filter.



        Returns:

            """Dict mapping message keys to translated values"""



        return self.get_message_bundle()



    def get_namespace_messages(self, namespace: str) -> dict[str, str]:



        Get all messages for a specific namespace.

        Alias for get_message_bundle with namespace filter.



        Args:

            namespace: Namespace to filter by



        Returns:

            """Dict mapping message keys to translated values"""



        return self.get_message_bundle(namespace)
