from rest_framework import serializers
from apps.cms.models import Redirect
from django.contrib.auth import get_user_model

User = get_user_model()


class RedirectSerializer(serializers.ModelSerializer):
    """Serializer for Redirect model"""

    class Meta:
        model = Redirect
        fields = [
            "id",
            "from_path",
            "to_path",
            "status",
            "is_active",
            "notes",
            "hits",
            "locale",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "hits"]
        extra_kwargs = {
            "locale": {"required": False, "allow_null": True},
            "notes": {"required": False, "allow_blank": True},
            "is_active": {"required": False, "default": True},
        }

    def validate(self, data):
        """Validate redirect configuration"""
        from_path = data.get("from_path")
        to_path = data.get("to_path")

        # Basic validation
        if from_path and to_path and from_path == to_path:
            raise serializers.ValidationError(
                "from_path and to_path cannot be the same"
            )

        return data

    def create(self, validated_data):
        """Create redirect instance"""
        return Redirect.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Update redirect instance"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
