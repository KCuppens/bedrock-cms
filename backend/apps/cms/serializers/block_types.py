from rest_framework import serializers

from apps.cms.models import BlockType, BlockTypeCategory


class BlockTypeSerializer(serializers.ModelSerializer):
    """Serializer for BlockType model with full CRUD support."""

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    updated_by_name = serializers.CharField(
        source="updated_by.get_full_name", read_only=True
    )

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )

    class Meta:

        model = BlockType

        fields = [
            "id",
            "type",
            "component",
            "label",
            "description",
            "category",
            "category_display",
            "icon",
            "is_active",
            "preload",
            "editing_mode",
            "schema",
            "default_props",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def validate_type(self, value):
        """Validate block type identifier."""

        if not value.islower():

            raise serializers.ValidationError("Block type must be lowercase")

        if not value.replace("_", "").isalnum():

            raise serializers.ValidationError(
                "Block type can only contain lowercase letters, numbers, and underscores"
            )

        return value

    def validate_component(self, value):
        """Validate component name follows naming convention."""

        if not value.endswith("Block"):

            raise serializers.ValidationError("Component name should end with 'Block'")

        if not value.replace("Block", "").isalpha():

            raise serializers.ValidationError(
                "Component name should only contain letters followed by 'Block'"
            )

        return value

    def validate_icon(self, value):
        """Validate icon name is a valid identifier."""

        if value and not value.replace("-", "").replace("_", "").isalnum():

            raise serializers.ValidationError(
                "Icon name should only contain letters, numbers, hyphens, and underscores"
            )

        return value

    def validate_schema(self, value):
        """Validate that schema is a valid JSON schema object."""

        if not isinstance(value, dict):

            raise serializers.ValidationError("Schema must be a valid JSON object")

        # Basic JSON schema validation

        if "type" in value and value["type"] not in [
            "object",
            "array",
            "string",
            "number",
            "boolean",
        ]:

            raise serializers.ValidationError("Invalid schema type specified")

        return value

    def validate_default_props(self, value):
        """Validate that default_props is a valid JSON object."""

        if not isinstance(value, dict):

            raise serializers.ValidationError(
                "Default props must be a valid JSON object"
            )

        return value


class BlockTypeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )

    class Meta:

        model = BlockType

        fields = [
            "id",
            "type",
            "component",
            "label",
            "description",
            "category",
            "category_display",
            "icon",
            "is_active",
            "preload",
            "updated_at",
        ]


class BlockTypeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new block types."""

    class Meta:

        model = BlockType

        fields = [
            "type",
            "component",
            "label",
            "description",
            "category",
            "icon",
            "is_active",
            "preload",
            "editing_mode",
            "schema",
            "default_props",
        ]

    def create(self, validated_data):
        """Create new block type with current user as creator."""

        user = self.context["request"].user

        validated_data["created_by"] = user

        validated_data["updated_by"] = user

        return super().create(validated_data)


class BlockTypeUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating block types."""

    class Meta:

        model = BlockType

        fields = [
            "component",
            "label",
            "description",
            "category",
            "icon",
            "is_active",
            "preload",
            "editing_mode",
            "schema",
            "default_props",
        ]

        # Don't allow changing type after creation

    def update(self, instance, validated_data):
        """Update block type with current user as updater."""

        user = self.context["request"].user

        validated_data["updated_by"] = user

        return super().update(instance, validated_data)


class BlockTypeCategorySerializer(serializers.Serializer):
    """Serializer for block type categories."""

    value = serializers.CharField()

    label = serializers.CharField()

    @classmethod
    def get_categories(cls):
        """Get all available categories."""

        return [
            {"value": choice[0], "label": choice[1]}
            for choice in BlockTypeCategory.choices
        ]
