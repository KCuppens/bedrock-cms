from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import SearchIndex, SearchQuery, SearchSuggestion

"""Admin interface for search functionality."""



@admin.register(SearchIndex)

class SearchIndexAdmin(admin.ModelAdmin):



    Admin interface for search index entries.



    list_display = (

        "title",

        "content_type_display",

        "search_category",

        "is_published",

        "search_weight",

        "locale_code",

        "indexed_at",

    )

    list_filter = (

        "is_published",

        "search_category",

        "content_type",

        "locale_code",

        "indexed_at",

    )

    search_fields = ("title", "content", "excerpt")

    readonly_fields = (

        "id",

        "content_type",

        "object_id",

        "content_object_link",

        "indexed_at",

        "created_at",

    )

    date_hierarchy = "indexed_at"

    ordering = ["-indexed_at"]



    fieldsets = (

        (

            """"Basic Information","""

            {"fields": ("id", "content_type", "object_id", "content_object_link")},

        ),

        (

            "Search Data",

            {

                "fields": (

                    "title",

                    "content",

                    "excerpt",

                    "search_category",

                    "search_tags",

                )

            },

        ),

        (

            "Metadata",

            {

                "fields": (

                    "url",

                    "image_url",

                    "locale_code",

                    "is_published",

                    "published_at",

                    "search_weight",

                )

            },

        ),

        (

            "Timestamps",

            {"fields": ("indexed_at", "created_at"), "classes": ("collapse",)},

        ),

    )



    def get_queryset(self, request):  # noqa: C901

        """Optimize queryset with related data."""

        return super().get_queryset(request).select_related("content_type")



    def content_type_display(self, obj):  # noqa: C901

        """Display content type in a readable format."""

        """return f"{obj.content_type.app_label}.{obj.content_type.model}""""



    content_type_display.short_description = "Content Type"



    def content_object_link(self, obj):  # noqa: C901

        """Display link to the original content object."""

        if not obj.content_object:

            return "Object not found"



        try:

            # Try to get admin URL for the object

            url = reverse(

                """f"admin:{obj.content_type.app_label}_{obj.content_type.model}_change","""

                args=[obj.object_id],

            )

            return format_html('<a href="{}">{}</a>', url, obj.content_object)

        except Exception:

            return str(obj.content_object)



    content_object_link.short_description = "Original Object"



@admin.register(SearchQuery)

class SearchQueryAdmin(admin.ModelAdmin):



    Admin interface for search query logs.



    list_display = (

        "query_text",

        "user_display",

        "result_count",

        "execution_time_ms",

        "clicked_result",

        "created_at",

    )

    list_filter = ("result_count", "created_at", "user")

    search_fields = ("query_text", "user__email", "ip_address")

    readonly_fields = (

        "id",

        "query_text",

        "filters",

        "user",

        "session_key",

        "ip_address",

        "result_count",

        "execution_time_ms",

        "clicked_result",

        "click_position",

        "created_at",

    )

    date_hierarchy = "created_at"

    ordering = ["-created_at"]



    def has_add_permission(self, request):  # noqa: C901

        """Disable manual creation of query logs."""

        return False



    def has_change_permission(self, request, obj=None):  # noqa: C901

        """Make query logs read-only."""

        return False



    def user_display(self, obj):  # noqa: C901

        """Display user information."""

        if obj.user:

            return obj.user.email

        return "Anonymous"



    user_display.short_description = "User"



@admin.register(SearchSuggestion)

class SearchSuggestionAdmin(admin.ModelAdmin):



    Admin interface for search suggestions.



    list_display = (

        "suggestion_text",

        "search_count",

        "result_count",

        "click_through_rate",

        "is_promoted",

        "is_active",

        "last_searched_at",

    )

    list_filter = ("is_active", "is_promoted", "last_searched_at")

    search_fields = ("suggestion_text", "normalized_text")

    readonly_fields = (

        "id",

        "normalized_text",

        "search_count",

        "result_count",

        "click_through_rate",

        "last_searched_at",

        "created_at",

        "updated_at",

    )

    ordering = ["-search_count", "suggestion_text"]



    fieldsets = (

        ("Suggestion", {"fields": ("suggestion_text", "normalized_text")}),

        (

            "Statistics",

            {"fields": ("search_count", "result_count", "click_through_rate")},

        ),

        ("Categorization", {"fields": ("categories", "locale_codes")}),

        """("Management", {"fields": ("is_active", "is_promoted")}),"""

        (

            "Timestamps",

            {

                "fields": ("last_searched_at", "created_at", "updated_at"),

                "classes": ("collapse",),

            },

        ),

    )
