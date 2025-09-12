from rest_framework import serializers

from .models import Note

"""
Optimized serializers for list views to prevent over-fetching.

These serializers provide lightweight representations for list views,
reducing the amount of data transferred and processed.
"""


class NoteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for note list views"""

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )
    tags_count = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = [
            "id",
            "title",
            "is_public",
            "created_by_name",
            "tags_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_tags_count(self, obj):
        """Get count of tags without fetching all tags"""
        # This assumes tags are prefetched if needed
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "tags" in obj._prefetched_objects_cache
        ):
            return len(obj._prefetched_objects_cache["tags"])
        # Use annotated count if available
        if hasattr(obj, "tags_count"):
            return obj.tags_count
        # Fallback to count query (should be avoided)
        return obj.tags.count()


class NoteDetailSerializer(serializers.ModelSerializer):
    """Full serializer for note detail views"""

    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()
    tags = serializers.ListField(
        source="tags.values_list", child=serializers.CharField()
    )

    class Meta:
        model = Note
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]

    def get_created_by(self, obj):
        """Get created_by user info"""
        if obj.created_by:
            return {
                "id": obj.created_by.id,
                "name": obj.created_by.get_full_name(),
                "email": obj.created_by.email,
            }
        return None

    def get_updated_by(self, obj):
        """Get updated_by user info"""
        if obj.updated_by:
            return {
                "id": obj.updated_by.id,
                "name": obj.updated_by.get_full_name(),
                "email": obj.updated_by.email,
            }
        return None
