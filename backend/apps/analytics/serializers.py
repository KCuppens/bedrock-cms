from django.contrib.auth import get_user_model

from rest_framework import serializers

from .models import (
    AnalyticsSummary,
    Assessment,
    ContentMetrics,
    PageView,
    Risk,
    Threat,
    UserActivity,
)

User = get_user_model()


class PageViewSerializer(serializers.ModelSerializer):
    """Serializer for PageView model"""

    page_title = serializers.CharField(source="page.title", read_only=True)

    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:

        model = PageView

        fields = [
            "id",
            "page",
            "page_title",
            "user",
            "user_email",
            "session_id",
            "ip_address",
            "user_agent",
            "url",
            "referrer",
            "title",
            "load_time",
            "time_on_page",
            "country",
            "city",
            "device_type",
            "browser",
            "os",
            "viewed_at",
        ]

        read_only_fields = ["id", "viewed_at", "page_title", "user_email"]


class PageViewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PageView records (minimal data)"""

    class Meta:

        model = PageView

        fields = [
            "page",
            "url",
            "referrer",
            "title",
            "load_time",
            "device_type",
            "browser",
            "os",
        ]

    def create(self, validated_data):  # noqa: C901

        # Extract additional data from request context

        request = self.context.get("request")

        if request:

            validated_data["ip_address"] = self.get_client_ip(request)

            validated_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")

            validated_data["session_id"] = request.session.session_key or ""

            if request.user.is_authenticated:

                validated_data["user"] = request.user

        return super().create(validated_data)

    def get_client_ip(self, request):  # noqa: C901
        """Get client IP address from request"""

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if x_forwarded_for:

            ip = x_forwarded_for.split(",")[0]

        else:

            ip = request.META.get("REMOTE_ADDR")

        return ip or "127.0.0.1"


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for UserActivity model"""

    user_email = serializers.CharField(source="user.email", read_only=True)

    action_display = serializers.CharField(source="get_action_display", read_only=True)

    content_object_name = serializers.SerializerMethodField()

    class Meta:

        model = UserActivity

        fields = [
            "id",
            "user",
            "user_email",
            "action",
            "action_display",
            "description",
            "content_type",
            "object_id",
            "content_object_name",
            "metadata",
            "ip_address",
            "user_agent",
            "session_id",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "user_email",
            "action_display",
            "content_object_name",
        ]

    def get_content_object_name(self, obj):  # noqa: C901
        """Get string representation of related object"""

        if obj.content_object:

            return str(obj.content_object)

        return None


class UserActivityCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating UserActivity records"""

    class Meta:

        model = UserActivity

        fields = ["action", "description", "content_type", "object_id", "metadata"]

    def create(self, validated_data):  # noqa: C901

        request = self.context.get("request")

        if request:

            validated_data["user"] = request.user

            validated_data["ip_address"] = self.get_client_ip(request)

            validated_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")

            validated_data["session_id"] = request.session.session_key or ""

        return super().create(validated_data)

    def get_client_ip(self, request):  # noqa: C901

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if x_forwarded_for:

            ip = x_forwarded_for.split(",")[0]

        else:

            ip = request.META.get("REMOTE_ADDR")

        return ip or "127.0.0.1"


class ContentMetricsSerializer(serializers.ModelSerializer):
    """Serializer for ContentMetrics model"""

    content_object_name = serializers.SerializerMethodField()

    content_type_name = serializers.CharField(
        source="content_type.name", read_only=True
    )

    class Meta:

        model = ContentMetrics

        fields = [
            "content_type",
            "content_type_name",
            "object_id",
            "content_object_name",
            "date",
            "content_category",
            "views",
            "unique_views",
            "avg_time_on_content",
            "bounce_rate",
            "shares",
            "comments",
            "downloads",
            "search_impressions",
            "search_clicks",
            "avg_position",
            "updated_at",
        ]

        read_only_fields = ["updated_at", "content_type_name", "content_object_name"]

    def get_content_object_name(self, obj):  # noqa: C901

        if obj.content_object:

            return str(obj.content_object)

        return None


class AssessmentSerializer(serializers.ModelSerializer):
    """Serializer for Assessment model"""

    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True
    )

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    assessment_type_display = serializers.CharField(
        source="get_assessment_type_display", read_only=True
    )

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    severity_display = serializers.CharField(
        source="get_severity_display", read_only=True
    )

    class Meta:

        model = Assessment

        fields = [
            "id",
            "title",
            "description",
            "assessment_type",
            "assessment_type_display",
            "status",
            "status_display",
            "target_url",
            "scope",
            "score",
            "severity",
            "severity_display",
            "findings",
            "recommendations",
            "assigned_to",
            "assigned_to_name",
            "created_by",
            "created_by_name",
            "scheduled_for",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "assigned_to_name",
            "created_by_name",
            "assessment_type_display",
            "status_display",
            "severity_display",
        ]


class AssessmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Assessment records"""

    class Meta:

        model = Assessment

        fields = [
            "title",
            "description",
            "assessment_type",
            "target_url",
            "scope",
            "assigned_to",
            "scheduled_for",
        ]

    def create(self, validated_data):  # noqa: C901

        request = self.context.get("request")

        if request and request.user:

            validated_data["created_by"] = request.user

        return super().create(validated_data)


class RiskSerializer(serializers.ModelSerializer):
    """Serializer for Risk model"""

    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)

    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True
    )

    assessment_title = serializers.CharField(source="assessment.title", read_only=True)

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    severity_display = serializers.CharField(
        source="get_severity_display", read_only=True
    )

    class Meta:

        model = Risk

        fields = [
            "id",
            "title",
            "description",
            "category",
            "category_display",
            "status",
            "status_display",
            "probability",
            "impact",
            "risk_score",
            "severity",
            "severity_display",
            "mitigation_plan",
            "mitigation_deadline",
            "mitigation_cost",
            "owner",
            "owner_name",
            "assigned_to",
            "assigned_to_name",
            "assessment",
            "assessment_title",
            "identified_at",
            "last_reviewed",
        ]

        read_only_fields = [
            "id",
            "risk_score",
            "severity",
            "identified_at",
            "last_reviewed",
            "owner_name",
            "assigned_to_name",
            "assessment_title",
            "category_display",
            "status_display",
            "severity_display",
        ]


class ThreatSerializer(serializers.ModelSerializer):
    """Serializer for Threat model"""

    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True
    )

    reported_by_name = serializers.CharField(
        source="reported_by.get_full_name", read_only=True
    )

    threat_type_display = serializers.CharField(
        source="get_threat_type_display", read_only=True
    )

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    severity_display = serializers.CharField(
        source="get_severity_display", read_only=True
    )

    class Meta:

        model = Threat

        fields = [
            "id",
            "title",
            "description",
            "threat_type",
            "threat_type_display",
            "status",
            "status_display",
            "severity",
            "severity_display",
            "source_ip",
            "target_url",
            "attack_vector",
            "indicators",
            "affected_systems",
            "data_compromised",
            "service_disrupted",
            "estimated_damage",
            "response_actions",
            "lessons_learned",
            "assigned_to",
            "assigned_to_name",
            "reported_by",
            "reported_by_name",
            "detected_at",
            "resolved_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "detected_at",
            "updated_at",
            "assigned_to_name",
            "reported_by_name",
            "threat_type_display",
            "status_display",
            "severity_display",
        ]


class ThreatCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Threat records"""

    class Meta:

        model = Threat

        fields = [
            "title",
            "description",
            "threat_type",
            "severity",
            "source_ip",
            "target_url",
            "attack_vector",
            "indicators",
            "affected_systems",
            "data_compromised",
            "service_disrupted",
            "estimated_damage",
            "assigned_to",
        ]

    def create(self, validated_data):  # noqa: C901

        request = self.context.get("request")

        if request and request.user:

            validated_data["reported_by"] = request.user

        return super().create(validated_data)


class AnalyticsSummarySerializer(serializers.ModelSerializer):
    """Serializer for AnalyticsSummary model"""

    period_type_display = serializers.CharField(
        source="get_period_type_display", read_only=True
    )

    class Meta:

        model = AnalyticsSummary

        fields = [
            "date",
            "period_type",
            "period_type_display",
            "total_views",
            "unique_visitors",
            "returning_visitors",
            "avg_session_duration",
            "bounce_rate",
            "new_users",
            "active_users",
            "user_actions",
            "pages_published",
            "files_uploaded",
            "content_updates",
            "threats_detected",
            "risks_identified",
            "assessments_completed",
            "avg_load_time",
            "uptime_percentage",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["created_at", "updated_at", "period_type_display"]


# Specialized serializers for analytics endpoints


class TrafficStatsSerializer(serializers.Serializer):
    """Serializer for traffic statistics"""

    date = serializers.DateField()

    views = serializers.IntegerField()

    unique_visitors = serializers.IntegerField()

    bounce_rate = serializers.DecimalField(max_digits=5, decimal_places=2)

    avg_session_duration = serializers.IntegerField()


class TopContentSerializer(serializers.Serializer):
    """Serializer for top performing content"""

    title = serializers.CharField()

    url = serializers.CharField()

    views = serializers.IntegerField()

    unique_views = serializers.IntegerField()

    avg_time_on_page = serializers.IntegerField()


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard summary statistics"""

    today_views = serializers.IntegerField()

    today_visitors = serializers.IntegerField()

    active_threats = serializers.IntegerField()

    open_risks = serializers.IntegerField()

    pending_assessments = serializers.IntegerField()

    avg_load_time = serializers.IntegerField()

    uptime_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)

    # Trend data

    views_trend = serializers.ListField(child=serializers.IntegerField())

    visitors_trend = serializers.ListField(child=serializers.IntegerField())

    threat_trend = serializers.ListField(child=serializers.IntegerField())


class RiskTimelineSerializer(serializers.Serializer):
    """Serializer for risk timeline data"""

    date = serializers.DateField()

    risks_identified = serializers.IntegerField()

    risks_mitigated = serializers.IntegerField()

    risk_score_avg = serializers.DecimalField(max_digits=5, decimal_places=2)


class ThreatStatsSerializer(serializers.Serializer):
    """Serializer for threat statistics"""

    threat_type = serializers.CharField()

    count = serializers.IntegerField()

    severity_breakdown = serializers.DictField()

    trend = serializers.ListField(child=serializers.IntegerField())
