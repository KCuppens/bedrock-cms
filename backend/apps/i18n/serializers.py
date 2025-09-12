from django.contrib.auth import get_user_model

from rest_framework import serializers

from .models import (
    Locale,
    Serializers,
    TranslationGlossary,
    TranslationHistory,
    TranslationQueue,
    TranslationUnit,
    UiMessage,
    UiMessageTranslation,
    ValidationError,

    django.core.exceptions,

    # models
    translation,
)

User = get_user_model()

class LocaleSerializer(serializers.ModelSerializer):
    """Serializer for Locale model."""

    fallback_code = serializers.CharField(source="fallback.code", read_only=True)
    fallback_name = serializers.CharField(source="fallback.name", read_only=True)

    class Meta:
        model = Locale
        fields = [
            "id",
            "code",
            "name",
            "native_name",
            "fallback",
            "fallback_code",
            "fallback_name",
            "rtl",
            "sort_order",
            "is_active",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

class TranslationUnitSerializer(serializers.ModelSerializer):
    """Serializer for TranslationUnit model."""

    model_label = serializers.CharField(read_only=True)
    source_locale_code = serializers.CharField(
        source="source_locale.code", read_only=True
    )
    target_locale_code = serializers.CharField(
        source="target_locale.code", read_only=True
    )
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True)
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = TranslationUnit
        fields = [
            "id",
            "model_label",
            "object_id",
            "field",
            "source_locale",
            "source_locale_code",
            "target_locale",
            "target_locale_code",
            "source_text",
            "target_text",
            "status",
            "updated_by",
            "updated_by_email",
            "is_complete",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "model_label",
            "object_id",
            "field",
            "source_locale",
            "source_locale_code",
            "source_text",
            "created_at",
        ]

class TranslationUnitUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating translation units."""

    class Meta:
        model = TranslationUnit
        fields = ["target_text", "status"]

    def validate_status(self, value):  # noqa: C901
        """Validate status transitions."""
        if self.instance:
            current_status = self.instance.status

            # Only allow certain transitions
            valid_transitions = {
                "missing": ["draft", "approved"],
                "draft": ["needs_review", "approved", "rejected", "missing"],
                "needs_review": ["approved", "rejected", "draft"],
                "approved": ["needs_review", "draft"],
                "rejected": ["draft", "needs_review"],
            }

            if value not in valid_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f"Cannot transition from {current_status} to {value}"
                )

        return value

class UiMessageSerializer(serializers.ModelSerializer):
    """Serializer for UiMessage model."""

    translation_count = serializers.SerializerMethodField()

    class Meta:
        model = UiMessage
        fields = [
            "id",
            "key",
            "namespace",
            "description",
            "default_value",
            "translation_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_translation_count(self, obj):  # noqa: C901
        """Get count of translations for this message."""
        return obj.translations.count()

class UiMessageTranslationSerializer(serializers.ModelSerializer):
    """Serializer for UiMessageTranslation model."""

    message_key = serializers.CharField(source="message.key", read_only=True)
    message_namespace = serializers.CharField(
        source="message.namespace", read_only=True
    )
    locale_code = serializers.CharField(source="locale.code", read_only=True)
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True)

    class Meta:
        model = UiMessageTranslation
        fields = [
            "id",
            "message",
            "message_key",
            "message_namespace",
            "locale",
            "locale_code",
            "value",
            "status",
            "updated_by",
            "updated_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "message_key",
            "message_namespace",
            "locale_code",
            "updated_by_email",
            "created_at",
            "updated_at",
        ]

class TranslationStatusSerializer(serializers.Serializer):
    """Serializer for translation status information."""

    target_locale = serializers.CharField()
    has_translation = serializers.BooleanField()
    status = serializers.CharField()
    fallback_locale = serializers.CharField(allow_null=True)
    needs_update = serializers.BooleanField()

class ObjectTranslationStatusSerializer(serializers.Serializer):
    """Serializer for object translation status."""

    object_id = serializers.IntegerField()
    model_label = serializers.CharField()
    fields = serializers.DictField(child=TranslationStatusSerializer())

class BulkTranslationUpdateSerializer(serializers.Serializer):
    """Serializer for bulk translation updates."""

    units = serializers.ListField(
        child=serializers.DictField(), help_text="List of translation unit updates"
    )

    def validate_units(self, value):  # noqa: C901
        """Validate bulk update data."""
        for unit_data in value:
            if "id" not in unit_data:
                raise serializers.ValidationError("Each unit must have an 'id' field")

            # Validate that at least one field is being updated
            updatable_fields = {"target_text", "status"}
            if not any(field in unit_data for field in updatable_fields):
                raise serializers.ValidationError(
                    "Each unit must update at least one of: target_text, status"
                )

        return value

class TranslationGlossarySerializer(serializers.ModelSerializer):
    """Serializer for TranslationGlossary model."""

    source_locale_code = serializers.CharField(
        source="source_locale.code", read_only=True
    )
    target_locale_code = serializers.CharField(
        source="target_locale.code", read_only=True
    )
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    updated_by_email = serializers.EmailField(source="updated_by.email", read_only=True)

    class Meta:
        model = TranslationGlossary
        fields = [
            "id",
            "term",
            "source_locale",
            "source_locale_code",
            "target_locale",
            "target_locale_code",
            "translation",
            "context",
            "category",
            "is_verified",
            "created_by",
            "created_by_email",
            "updated_by",
            "updated_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "source_locale_code",
            "target_locale_code",
            "created_by_email",
            "updated_by_email",
            "created_at",
            "updated_at",
        ]

class GlossarySearchSerializer(serializers.Serializer):
    """Serializer for glossary search requests."""

    term = serializers.CharField(required=False, help_text="Term to search for")
    source_locale = serializers.CharField(
        required=False, help_text="Source locale code"
    )
    target_locale = serializers.CharField(
        required=False, help_text="Target locale code"
    )
    category = serializers.CharField(required=False, help_text="Category to filter by")
    verified_only = serializers.BooleanField(
        default=False, help_text="Only return verified terms"
    )

class TranslationQueueSerializer(serializers.ModelSerializer):
    """Serializer for TranslationQueue model."""

    translation_unit_id = serializers.IntegerField(
        source="translation_unit.id", read_only=True
    )
    source_text = serializers.CharField(
        source="translation_unit.source_text", read_only=True
    )
    target_text = serializers.CharField(
        source="translation_unit.target_text", read_only=True
    )
    source_locale_code = serializers.CharField(
        source="translation_unit.source_locale.code", read_only=True
    )
    target_locale_code = serializers.CharField(
        source="translation_unit.target_locale.code", read_only=True
    )
    model_label = serializers.CharField(
        source="translation_unit.model_label", read_only=True
    )
    field_name = serializers.CharField(source="translation_unit.field", read_only=True)
    assigned_to_email = serializers.EmailField(
        source="assigned_to.email", read_only=True
    )
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = TranslationQueue
        fields = [
            "id",
            "translation_unit",
            "translation_unit_id",
            "source_text",
            "target_text",
            "source_locale_code",
            "target_locale_code",
            "model_label",
            "field_name",
            "status",
            "priority",
            "assigned_to",
            "assigned_to_email",
            "deadline",
            "notes",
            "machine_translation_suggestion",
            "mt_service",
            "word_count",
            "estimated_hours",
            "created_by",
            "created_by_email",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "translation_unit_id",
            "source_text",
            "target_text",
            "source_locale_code",
            "target_locale_code",
            "model_label",
            "field_name",
            "assigned_to_email",
            "created_by_email",
            "is_overdue",
            "word_count",
            "created_at",
            "updated_at",
        ]

class TranslationHistorySerializer(serializers.ModelSerializer):
    """Serializer for TranslationHistory model."""

    performed_by_email = serializers.EmailField(
        source="performed_by.email", read_only=True
    )
    translation_unit_id = serializers.IntegerField(
        source="translation_unit.id", read_only=True
    )

    class Meta:
        model = TranslationHistory
        fields = [
            "id",
            "translation_unit",
            "translation_unit_id",
            "action",
            "previous_status",
            "new_status",
            "previous_target_text",
            "new_target_text",
            "comment",
            "performed_by",
            "performed_by_email",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "translation_unit_id",
            "performed_by_email",
            "created_at",
        ]

class TranslationApprovalSerializer(serializers.Serializer):
    """Serializer for translation approval/rejection requests."""

    comment = serializers.CharField(
        required=False, help_text="Optional comment for the action"
    )

class MachineTranslationSuggestionSerializer(serializers.Serializer):
    """Serializer for machine translation suggestion requests."""

    text = serializers.CharField(required=True, help_text="Text to translate")
    source_locale = serializers.CharField(
        max_length=10, required=True, help_text="Source locale code"
    )
    target_locale = serializers.CharField(
        max_length=10, required=True, help_text="Target locale code for translation"
    )
    service = serializers.ChoiceField(
        choices=["google", "deepl", "azure", "auto"],
        default="auto",
        required=False,
        help_text="Machine translation service to use",
    )

class BulkUiMessageUpdateSerializer(serializers.Serializer):
    """Serializer for bulk UI message updates."""

    updates = serializers.ListField(
        child=serializers.DictField(), help_text="List of message translation updates"
    )

    def validate_updates(self, value):  # noqa: C901
        """Validate bulk update data."""
        for update_data in value:
            required_fields = {"message_id", "locale_id", "value"}
            if not all(field in update_data for field in required_fields):
                raise serializers.ValidationError(
                    "Each update must have message_id, locale_id, and value fields"
                )
        return value

class NamespaceSerializer(serializers.Serializer):
    """Serializer for UI message namespaces."""

    namespace = serializers.CharField()
    message_count = serializers.IntegerField()
    translation_progress = serializers.DictField(
        child=serializers.FloatField(),
        help_text="Translation progress per locale as percentage",
    )

class TranslationAssignmentSerializer(serializers.Serializer):
    """Serializer for assigning translations to users."""

    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        allow_null=True,
        required=False,
        help_text="User to assign the translation to (null to unassign)",
    )
    comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional comment for the assignment",
    )

class BulkAssignmentSerializer(serializers.Serializer):
    """Serializer for bulk assignment of translations."""

    translation_unit_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of translation unit IDs to assign",
    )
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        allow_null=True,
        required=False,
        help_text="User to assign the translations to (null to unassign)",
    )
    comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional comment for the assignment",
    )

    def validate_translation_unit_ids(self, value):  # noqa: C901
        """Validate that all translation unit IDs exist."""
        if not value:
            raise serializers.ValidationError(
                "At least one translation unit ID is required"
            )

        # Check if all IDs exist
        existing_ids = set(
            TranslationUnit.objects.filter(id__in=value).values_list("id", flat=True)
        )
        invalid_ids = set(value) - existing_ids

        if invalid_ids:
            raise serializers.ValidationError(
                f"Translation units with IDs {list(invalid_ids)} do not exist"
            )

        return value
