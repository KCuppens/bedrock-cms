"""
Serializers for search functionality.
"""

from rest_framework import serializers

from .models import SearchIndex, SearchQuery, SearchSuggestion


class SearchResultSerializer(serializers.Serializer):
    """
    Serializer for search results.
    """

    id = serializers.CharField()
    title = serializers.CharField()
    excerpt = serializers.CharField()
    content_type = serializers.CharField()
    url = serializers.URLField(allow_blank=True)
    image_url = serializers.URLField(allow_blank=True)
    locale_code = serializers.CharField(allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    published_at = serializers.DateTimeField(allow_null=True)
    search_weight = serializers.FloatField()
    object_type = serializers.CharField()
    object_id = serializers.IntegerField()


class SearchRequestSerializer(serializers.Serializer):
    """
    Serializer for search requests.
    """

    query = serializers.CharField(required=True, max_length=500)
    category = serializers.CharField(required=False, allow_blank=True, max_length=50)
    locale = serializers.CharField(required=False, allow_blank=True, max_length=10)
    tags = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    date_from = serializers.DateTimeField(required=False, allow_null=True)
    date_to = serializers.DateTimeField(required=False, allow_null=True)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)


class SearchResponseSerializer(serializers.Serializer):
    """
    Serializer for search responses.
    """

    results = SearchResultSerializer(many=True)
    pagination = serializers.DictField()
    query = serializers.CharField()
    filters = serializers.DictField()
    execution_time_ms = serializers.IntegerField()
    suggestions = serializers.ListField(child=serializers.CharField())


class SearchSuggestionSerializer(serializers.ModelSerializer):
    """
    Serializer for search suggestions.
    """

    class Meta:
        model = SearchSuggestion
        fields = [
            "id",
            "suggestion_text",
            "search_count",
            "result_count",
            "click_through_rate",
            "categories",
            "locale_codes",
            "is_promoted",
        ]
        read_only_fields = ["id", "search_count", "result_count", "click_through_rate"]


class AutocompleteSerializer(serializers.Serializer):
    """
    Serializer for autocomplete requests.
    """

    query = serializers.CharField(required=True, min_length=2, max_length=200)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)


class SearchAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for search analytics.
    """

    period_days = serializers.IntegerField()
    total_queries = serializers.IntegerField()
    avg_results_per_query = serializers.FloatField()
    avg_execution_time_ms = serializers.FloatField()
    top_queries = serializers.ListField()
    zero_result_queries = serializers.ListField()


class SearchIndexSerializer(serializers.ModelSerializer):
    """
    Serializer for search index entries (admin use).
    """

    content_type_label = serializers.CharField(
        source="content_type.model", read_only=True
    )

    class Meta:
        model = SearchIndex
        fields = [
            "id",
            "content_type",
            "content_type_label",
            "object_id",
            "title",
            "content",
            "excerpt",
            "url",
            "image_url",
            "locale_code",
            "search_category",
            "search_tags",
            "is_published",
            "published_at",
            "search_weight",
            "indexed_at",
            "created_at",
        ]
        read_only_fields = ["id", "indexed_at", "created_at"]


class SearchQueryLogSerializer(serializers.ModelSerializer):
    """
    Serializer for search query logs (admin use).
    """

    user_email = serializers.CharField(
        source="user.email", read_only=True, allow_null=True
    )

    class Meta:
        model = SearchQuery
        fields = [
            "id",
            "query_text",
            "filters",
            "user",
            "user_email",
            "session_key",
            "ip_address",
            "result_count",
            "execution_time_ms",
            "clicked_result",
            "click_position",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BulkIndexSerializer(serializers.Serializer):
    """
    Serializer for bulk indexing operations.
    """

    model_label = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional model label to index (e.g., 'blog.blogpost')",
    )
    force_reindex = serializers.BooleanField(
        default=False, help_text="Whether to force re-indexing of existing entries"
    )
