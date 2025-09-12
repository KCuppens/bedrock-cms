from rest_framework import serializers


from apps.blog.models import Category, Tag

from apps.cms.model_parts.category import Collection


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""

    post_count = serializers.IntegerField(read_only=True)

    class Meta:

        model = Category

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "color",
            "is_active",
            "post_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["slug", "created_at", "updated_at", "post_count"]

    def create(self, validated_data):
        """Create a new category, ensuring read-only fields are excluded"""

        # Remove any read-only fields that might have been included

        validated_data.pop("post_count", None)

        # Remove created_by as Blog Category model doesn't have this field

        validated_data.pop("created_by", None)

        return super().create(validated_data)


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model"""

    post_count = serializers.IntegerField(read_only=True)

    class Meta:

        model = Tag

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "post_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["slug", "created_at", "updated_at", "post_count"]

    def create(self, validated_data):
        """Create a new tag, ensuring read-only fields are excluded"""

        # Remove any read-only fields that might have been included

        validated_data.pop("post_count", None)

        # Remove created_by as Blog Tag model doesn't have this field

        validated_data.pop("created_by", None)

        return super().create(validated_data)


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for Collection model"""

    categories = CategorySerializer(many=True, read_only=True)

    category_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    tags = TagSerializer(many=True, read_only=True)

    tag_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    item_count = serializers.IntegerField(read_only=True)

    class Meta:

        model = Collection

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "cover_image",
            "status",
            "categories",
            "category_ids",
            "tags",
            "tag_ids",
            "meta_title",
            "meta_description",
            "item_count",
            "created_at",
            "updated_at",
            "published_at",
        ]

        read_only_fields = ["slug", "created_at", "updated_at", "published_at"]

    def create(self, validated_data):

        category_ids = validated_data.pop("category_ids", [])

        tag_ids = validated_data.pop("tag_ids", [])

        collection = Collection.objects.create(**validated_data)

        if category_ids:

            collection.categories.set(category_ids)

        if tag_ids:

            collection.tags.set(tag_ids)

        return collection

    def update(self, instance, validated_data):

        category_ids = validated_data.pop("category_ids", None)

        tag_ids = validated_data.pop("tag_ids", None)

        for attr, value in validated_data.items():

            setattr(instance, attr, value)

        instance.save()

        if category_ids is not None:

            instance.categories.set(category_ids)

        if tag_ids is not None:

            instance.tags.set(tag_ids)

        return instance
