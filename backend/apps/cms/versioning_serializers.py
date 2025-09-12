from django.contrib.auth import get_user_model

from rest_framework import serializers

from .versioning import AuditEntry, PageRevision

"""Serializers for versioning and audit functionality."""



User = get_user_model()



class PageRevisionSerializer(serializers.ModelSerializer):

    """Serializer for PageRevision model."""



    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    created_by_name = serializers.CharField(

        source="created_by.get_full_name", read_only=True

    )

    block_count = serializers.SerializerMethodField()

    revision_type = serializers.SerializerMethodField()



    class Meta:

        model = PageRevision

        fields = [

            "id",

            "created_at",

            "created_by_email",

            "created_by_name",

            "is_published_snapshot",

            "is_autosave",

            "comment",

            "block_count",

            "revision_type",

        ]

        read_only_fields = ["id", "created_at"]



    def get_block_count(self, obj):  # noqa: C901

        """Get the number of blocks in this revision."""

        return obj.get_block_count()



    def get_revision_type(self, obj):  # noqa: C901

        """Get human-readable revision type."""

        if obj.is_published_snapshot:

            return "published"

        elif obj.is_autosave:

            return "autosave"

        else:

            return "manual"



class PageRevisionDetailSerializer(PageRevisionSerializer):

    """Detailed serializer including snapshot data."""



    class Meta(PageRevisionSerializer.Meta):

        fields = PageRevisionSerializer.Meta.fields + ["snapshot"]



class RevisionDiffSerializer(serializers.Serializer):

    """Serializer for revision diff data."""



    old_revision_id = serializers.UUIDField(read_only=True)

    new_revision_id = serializers.UUIDField(read_only=True)

    created_at = serializers.DateTimeField(read_only=True)

    has_changes = serializers.BooleanField(read_only=True)

    changes = serializers.JSONField(read_only=True)



class RevertRevisionSerializer(serializers.Serializer):

    """Serializer for revision revert operation."""



    comment = serializers.CharField(

        required=False,

        allow_blank=True,

        help_text="Optional comment about the revert operation",

    )



class AuditEntrySerializer(serializers.ModelSerializer):

    """Serializer for AuditEntry model."""



    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    actor_name = serializers.CharField(source="actor.get_full_name", read_only=True)

    object_name = serializers.SerializerMethodField()



    class Meta:

        model = AuditEntry

        fields = [

            "id",

            "actor_email",

            "actor_name",

            "action",

            "model_label",

            "object_id",

            "object_name",

            "created_at",

            "ip_address",

            "meta",

        ]

        read_only_fields = ["id", "created_at"]



    def get_object_name(self, obj):  # noqa: C901

        """Get human-readable name of the object."""

        try:

            if obj.content_object and hasattr(obj.content_object, "title"):

                return obj.content_object.title

            elif obj.content_object:

                return str(obj.content_object)

        except Exception:



        return f"{obj.model_label}#{obj.object_id}"



class AutosaveSerializer(serializers.Serializer):

    """Serializer for manual autosave creation."""



    comment = serializers.CharField(

        required=False, allow_blank=True, help_text="Optional comment for the autosave"

    )



    def validate(self, attrs):  # noqa: C901

        """Validate autosave creation."""

        page = self.context["page"]

        user = self.context["user"]



        if not PageRevision.should_create_autosave(page, user):

            raise serializers.ValidationError(

                "Autosave was created recently. Please wait before creating another autosave."

            )



        return attrs



class PublishPageSerializer(serializers.Serializer):

    """Serializer for page publishing."""



    published_at = serializers.DateTimeField(

        required=False, help_text="When to publish the page. Defaults to now."

    )

    comment = serializers.CharField(

        required=False,

        allow_blank=True,

        help_text="Optional comment about the publication",

    )



class UnpublishPageSerializer(serializers.Serializer):

    """Serializer for page unpublishing."""



    comment = serializers.CharField(

        required=False,

        allow_blank=True,

        help_text="Optional comment about unpublishing",

    )
