from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg
from django.utils.safestring import mark_safe
import json

from .models import (
    PageView,
    UserActivity,
    ContentMetrics,
    Assessment,
    Risk,
    Threat,
    AnalyticsSummary,
)


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    """Admin interface for PageView model"""

    list_display = [
        "id",
        "page_title_link",
        "user_link",
        "device_type",
        "ip_address",
        "viewed_at",
        "time_on_page",
    ]
    list_filter = [
        "device_type",
        "viewed_at",
        "browser",
        "os",
        "page__status",
        "country",
    ]
    search_fields = [
        "url",
        "title",
        "page__title",
        "user__email",
        "ip_address",
        "session_id",
    ]
    readonly_fields = [
        "id",
        "viewed_at",
        "session_id",
        "ip_address",
        "user_agent",
        "browser",
        "os",
    ]
    date_hierarchy = "viewed_at"
    ordering = ["-viewed_at"]
    list_per_page = 50

    fieldsets = (
        ("Basic Information", {"fields": ("page", "user", "url", "title", "referrer")}),
        (
            "Visitor Information",
            {"fields": ("session_id", "ip_address", "user_agent", "country", "city")},
        ),
        ("Device & Browser", {"fields": ("device_type", "browser", "os")}),
        ("Performance Metrics", {"fields": ("load_time", "time_on_page", "viewed_at")}),
    )

    def page_title_link(self, obj):
        """Display page title as link to page admin"""
        if obj.page:
            url = reverse("admin:cms_page_change", args=[obj.page.pk])
            return format_html('<a href="{}">{}</a>', url, obj.page.title)
        return obj.title or obj.url

    page_title_link.short_description = "Page"
    page_title_link.admin_order_field = "page__title"

    def user_link(self, obj):
        """Display user as link to user admin"""
        if obj.user:
            url = reverse("admin:accounts_user_change", args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return "Anonymous"

    user_link.short_description = "User"
    user_link.admin_order_field = "user__email"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("page", "user")


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Admin interface for UserActivity model"""

    list_display = [
        "user_link",
        "action",
        "description",
        "content_object_link",
        "ip_address",
        "created_at",
    ]
    list_filter = ["action", "created_at", "content_type"]
    search_fields = ["user__email", "description", "ip_address", "session_id"]
    readonly_fields = ["id", "created_at", "session_id", "ip_address", "user_agent"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    list_per_page = 50

    fieldsets = (
        ("Activity Information", {"fields": ("user", "action", "description")}),
        ("Related Object", {"fields": ("content_type", "object_id", "content_object")}),
        ("Context", {"fields": ("metadata", "ip_address", "user_agent", "session_id")}),
        ("Timestamp", {"fields": ("created_at",)}),
    )

    def user_link(self, obj):
        """Display user as link to user admin"""
        url = reverse("admin:accounts_user_change", args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)

    user_link.short_description = "User"
    user_link.admin_order_field = "user__email"

    def content_object_link(self, obj):
        """Display content object as link if possible"""
        if obj.content_object:
            try:
                url = reverse(
                    f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                    args=[obj.object_id],
                )
                return format_html('<a href="{}">{}</a>', url, str(obj.content_object))
            except:
                return str(obj.content_object)
        return "-"

    content_object_link.short_description = "Related Object"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user", "content_type")
            .prefetch_related("content_object")
        )


@admin.register(ContentMetrics)
class ContentMetricsAdmin(admin.ModelAdmin):
    """Admin interface for ContentMetrics model"""

    list_display = [
        "content_object_link",
        "date",
        "content_category",
        "views",
        "unique_views",
        "bounce_rate",
        "updated_at",
    ]
    list_filter = ["content_category", "date", "content_type"]
    search_fields = ["content_type__model", "object_id"]
    readonly_fields = ["updated_at"]
    date_hierarchy = "date"
    ordering = ["-date", "-views"]
    list_per_page = 50

    fieldsets = (
        (
            "Content Information",
            {"fields": ("content_type", "object_id", "content_category", "date")},
        ),
        (
            "Traffic Metrics",
            {"fields": ("views", "unique_views", "avg_time_on_content", "bounce_rate")},
        ),
        ("Engagement Metrics", {"fields": ("shares", "comments", "downloads")}),
        (
            "SEO Metrics",
            {"fields": ("search_impressions", "search_clicks", "avg_position")},
        ),
        ("Metadata", {"fields": ("updated_at",)}),
    )

    def content_object_link(self, obj):
        """Display content object as link"""
        if obj.content_object:
            try:
                url = reverse(
                    f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change",
                    args=[obj.object_id],
                )
                return format_html('<a href="{}">{}</a>', url, str(obj.content_object))
            except:
                return str(obj.content_object)
        return f"{obj.content_type.model} #{obj.object_id}"

    content_object_link.short_description = "Content"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("content_type")


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    """Admin interface for Assessment model"""

    list_display = [
        "title",
        "assessment_type",
        "status",
        "severity",
        "score",
        "assigned_to_link",
        "created_at",
    ]
    list_filter = [
        "assessment_type",
        "status",
        "severity",
        "created_at",
        "scheduled_for",
        "completed_at",
    ]
    search_fields = [
        "title",
        "description",
        "target_url",
        "assigned_to__email",
        "created_by__email",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    list_per_page = 50

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "description", "assessment_type", "status")},
        ),
        (
            "Assessment Details",
            {"fields": ("target_url", "scope", "score", "severity")},
        ),
        ("Results", {"fields": ("findings", "recommendations")}),
        ("Assignment", {"fields": ("assigned_to", "created_by")}),
        ("Timeline", {"fields": ("scheduled_for", "started_at", "completed_at")}),
        ("Metadata", {"fields": ("id", "created_at", "updated_at")}),
    )

    def assigned_to_link(self, obj):
        """Display assigned user as link"""
        if obj.assigned_to:
            url = reverse("admin:accounts_user_change", args=[obj.assigned_to.pk])
            return format_html(
                '<a href="{}">{}</a>', url, obj.assigned_to.get_full_name()
            )
        return "Unassigned"

    assigned_to_link.short_description = "Assigned To"
    assigned_to_link.admin_order_field = "assigned_to__name"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("assigned_to", "created_by")


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    """Admin interface for Risk model"""

    list_display = [
        "title",
        "category",
        "status",
        "severity",
        "risk_score",
        "owner_link",
        "identified_at",
    ]
    list_filter = [
        "category",
        "status",
        "severity",
        "identified_at",
        "mitigation_deadline",
    ]
    search_fields = [
        "title",
        "description",
        "mitigation_plan",
        "owner__email",
        "assigned_to__email",
    ]
    readonly_fields = ["id", "risk_score", "severity", "identified_at", "last_reviewed"]
    date_hierarchy = "identified_at"
    ordering = ["-risk_score", "-identified_at"]
    list_per_page = 50

    fieldsets = (
        (
            "Risk Information",
            {"fields": ("title", "description", "category", "status")},
        ),
        (
            "Risk Assessment",
            {"fields": ("probability", "impact", "risk_score", "severity")},
        ),
        (
            "Mitigation",
            {"fields": ("mitigation_plan", "mitigation_deadline", "mitigation_cost")},
        ),
        ("Assignment", {"fields": ("owner", "assigned_to", "assessment")}),
        ("Timeline", {"fields": ("identified_at", "last_reviewed")}),
    )

    def owner_link(self, obj):
        """Display owner as link"""
        if obj.owner:
            url = reverse("admin:accounts_user_change", args=[obj.owner.pk])
            return format_html('<a href="{}">{}</a>', url, obj.owner.get_full_name())
        return "Unassigned"

    owner_link.short_description = "Owner"
    owner_link.admin_order_field = "owner__name"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("owner", "assigned_to", "assessment")
        )


@admin.register(Threat)
class ThreatAdmin(admin.ModelAdmin):
    """Admin interface for Threat model"""

    list_display = [
        "title",
        "threat_type",
        "status",
        "severity",
        "source_ip",
        "assigned_to_link",
        "detected_at",
    ]
    list_filter = [
        "threat_type",
        "status",
        "severity",
        "detected_at",
        "data_compromised",
        "service_disrupted",
    ]
    search_fields = [
        "title",
        "description",
        "source_ip",
        "target_url",
        "attack_vector",
        "assigned_to__email",
        "reported_by__email",
    ]
    readonly_fields = ["id", "detected_at", "updated_at"]
    date_hierarchy = "detected_at"
    ordering = ["-detected_at"]
    list_per_page = 50

    fieldsets = (
        (
            "Threat Information",
            {"fields": ("title", "description", "threat_type", "status", "severity")},
        ),
        (
            "Attack Details",
            {"fields": ("source_ip", "target_url", "attack_vector", "indicators")},
        ),
        (
            "Impact Assessment",
            {
                "fields": (
                    "affected_systems",
                    "data_compromised",
                    "service_disrupted",
                    "estimated_damage",
                )
            },
        ),
        ("Response", {"fields": ("response_actions", "lessons_learned")}),
        ("Assignment", {"fields": ("assigned_to", "reported_by")}),
        ("Timeline", {"fields": ("detected_at", "resolved_at", "updated_at")}),
    )

    def assigned_to_link(self, obj):
        """Display assigned user as link"""
        if obj.assigned_to:
            url = reverse("admin:accounts_user_change", args=[obj.assigned_to.pk])
            return format_html(
                '<a href="{}">{}</a>', url, obj.assigned_to.get_full_name()
            )
        return "Unassigned"

    assigned_to_link.short_description = "Assigned To"
    assigned_to_link.admin_order_field = "assigned_to__name"

    def get_queryset(self, request):
        return (
            super().get_queryset(request).select_related("assigned_to", "reported_by")
        )


@admin.register(AnalyticsSummary)
class AnalyticsSummaryAdmin(admin.ModelAdmin):
    """Admin interface for AnalyticsSummary model"""

    list_display = [
        "date",
        "period_type",
        "total_views",
        "unique_visitors",
        "active_users",
        "threats_detected",
        "uptime_percentage",
    ]
    list_filter = ["period_type", "date"]
    search_fields = ["date"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "date"
    ordering = ["-date"]
    list_per_page = 50

    fieldsets = (
        ("Period Information", {"fields": ("date", "period_type")}),
        (
            "Traffic Metrics",
            {
                "fields": (
                    "total_views",
                    "unique_visitors",
                    "returning_visitors",
                    "avg_session_duration",
                    "bounce_rate",
                )
            },
        ),
        ("User Metrics", {"fields": ("new_users", "active_users", "user_actions")}),
        (
            "Content Metrics",
            {"fields": ("pages_published", "files_uploaded", "content_updates")},
        ),
        (
            "Security Metrics",
            {
                "fields": (
                    "threats_detected",
                    "risks_identified",
                    "assessments_completed",
                )
            },
        ),
        ("Performance Metrics", {"fields": ("avg_load_time", "uptime_percentage")}),
        ("Metadata", {"fields": ("created_at", "updated_at")}),
    )


# Custom admin site configuration
admin.site.site_header = "Bedrock CMS Analytics"
admin.site.site_title = "Analytics Admin"
admin.site.index_title = "Analytics Administration"
