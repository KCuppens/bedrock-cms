"""
Auto-generated serializers for registered content models.
"""

from typing import Any

from rest_framework import serializers

from .config import ContentConfig
from .registry import content_registry


class ContentSerializerFactory:
    """
    Factory for creating serializers for registered content models.
    """

    @classmethod
    def create_serializer(
        cls, config: ContentConfig
    ) -> type[serializers.ModelSerializer]:
        """
        Create a serializer class for a content configuration.

        Args:
            config: ContentConfig instance

        Returns:
            ModelSerializer class
        """
        model = config.model
        form_fields = list(config.get_effective_form_fields())
        custom_fields = cls._get_custom_fields(config)

        # Add custom field names to fields list
        for field_name in custom_fields.keys():
            if not field_name.startswith("get_"):
                form_fields.append(field_name)

        # Create the serializer class dynamically
        class Meta:
            model = config.model
            fields = form_fields

            # Add read-only fields
            read_only_fields = ["id", "created_at", "updated_at"]

            # If model has group_id, make it read-only
            if hasattr(model, "group_id"):
                read_only_fields.append("group_id")

        # Create the serializer class
        serializer_class = type(
            f"{model.__name__}Serializer",
            (serializers.ModelSerializer,),
            {"Meta": Meta, **custom_fields, **cls._get_custom_methods(config)},
        )

        return serializer_class

    @classmethod
    def _get_custom_fields(cls, config: ContentConfig) -> dict[str, Any]:
        """Get custom fields for the serializer."""
        custom_fields = {}

        # Add locale information if applicable
        if config.locale_field:
            custom_fields["locale_code"] = serializers.CharField(
                source=f"{config.locale_field}.code", read_only=True
            )
            custom_fields["locale_name"] = serializers.CharField(
                source=f"{config.locale_field}.name", read_only=True
            )

        # Add URL field if model has slug
        if config.slug_field and config.get_route_pattern():

            def get_url(self, obj):
                slug_value = getattr(obj, config.slug_field)
                if slug_value:
                    return config.get_route_pattern().format(slug=slug_value)
                return None

            custom_fields["url"] = serializers.SerializerMethodField()
            custom_fields["get_url"] = get_url

        # Add reading time for content with blocks
        if hasattr(config.model, "blocks") or "body_blocks" in config.searchable_fields:

            def get_reading_time(self, obj):
                # Estimate reading time from text content
                if hasattr(obj, "reading_time") and obj.reading_time:
                    return obj.reading_time

                # Calculate from blocks
                text_content = ""
                blocks_field = "blocks" if hasattr(obj, "blocks") else "body_blocks"

                if hasattr(obj, blocks_field):
                    blocks = getattr(obj, blocks_field) or []
                    for block in blocks:
                        if isinstance(block, dict) and "props" in block:
                            props = block["props"]
                            if "content" in props:
                                text_content += str(props["content"]) + " "
                            elif "text" in props:
                                text_content += str(props["text"]) + " "

                # Estimate reading time (average 250 words per minute)
                word_count = len(text_content.split())
                return max(1, word_count // 250)

            custom_fields["reading_time"] = serializers.SerializerMethodField()
            custom_fields["get_reading_time"] = get_reading_time

        return custom_fields

    @classmethod
    def _get_custom_methods(cls, config: ContentConfig) -> dict[str, Any]:
        """Get custom methods for the serializer."""
        methods = {}

        # Add validation for required fields
        def validate(self, attrs):
            # Custom validation logic can be added here
            return attrs

        methods["validate"] = validate

        return methods


class RegistrySerializer(serializers.Serializer):
    """Serializer for registry information."""

    model_label = serializers.CharField()
    kind = serializers.CharField()
    name = serializers.CharField()
    verbose_name = serializers.CharField()
    verbose_name_plural = serializers.CharField()
    slug_field = serializers.CharField(allow_null=True)
    locale_field = serializers.CharField(allow_null=True)
    translatable_fields = serializers.ListField(child=serializers.CharField())
    searchable_fields = serializers.ListField(child=serializers.CharField())
    seo_fields = serializers.ListField(child=serializers.CharField())
    route_pattern = serializers.CharField(allow_null=True)
    can_publish = serializers.BooleanField()
    allowed_block_types = serializers.ListField(
        child=serializers.CharField(), allow_null=True
    )
    form_fields = serializers.ListField(child=serializers.CharField(), allow_null=True)
    ordering = serializers.ListField(child=serializers.CharField())
    supports_publishing = serializers.BooleanField()
    supports_localization = serializers.BooleanField()


class RegistrySummarySerializer(serializers.Serializer):
    """Serializer for registry summary."""

    total_registered = serializers.IntegerField()
    by_kind = serializers.DictField()
    configs = serializers.DictField()


def get_serializer_for_model(model_label: str) -> type[serializers.ModelSerializer]:
    """
    Get or create a serializer for a registered model.

    Args:
        model_label: Model label (e.g., 'cms.page')

    Returns:
        ModelSerializer class

    Raises:
        ValueError: If model is not registered
    """
    config = content_registry.get_config(model_label)
    if not config:
        raise ValueError(f"Model {model_label} is not registered")

    return ContentSerializerFactory.create_serializer(config)


def get_serializer_for_config(
    config: ContentConfig,
) -> type[serializers.ModelSerializer]:
    """
    Get or create a serializer for a content configuration.

    Args:
        config: ContentConfig instance

    Returns:
        ModelSerializer class
    """
    return ContentSerializerFactory.create_serializer(config)
