"""
Search API views.

Provides REST API endpoints for search functionality.
"""

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from apps.core.decorators import cache_response

from .models import SearchIndex, SearchQuery, SearchSuggestion
from .serializers import (
    AutocompleteSerializer,
    BulkIndexSerializer,
    SearchAnalyticsSerializer,
    SearchIndexSerializer,
    SearchQueryLogSerializer,
    SearchRequestSerializer,
    SearchResponseSerializer,
    SearchSuggestionSerializer,
)
from .services import search_service


class SearchThrottle(UserRateThrottle):
    """Custom throttle for search requests."""

    scope = "search"
    rate = "100/hour"


class SearchAPIView(generics.GenericAPIView):
    """
    Main search endpoint.

    Performs full-text search across all registered content types.
    """

    serializer_class = SearchRequestSerializer
    permission_classes = []  # Public endpoint
    throttle_classes = [SearchThrottle, AnonRateThrottle]

    def post(self, request):
        """Perform search."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract search parameters
        query = serializer.validated_data["query"]
        filters = {
            k: v
            for k, v in serializer.validated_data.items()
            if k not in ["query", "page", "page_size"] and v is not None
        }
        page = serializer.validated_data.get("page", 1)
        page_size = serializer.validated_data.get("page_size", 20)

        # Perform search
        results = search_service.search(
            query=query,
            filters=filters,
            page=page,
            page_size=page_size,
            user=request.user if request.user.is_authenticated else None,
            request=request,
        )

        # Serialize response
        response_serializer = SearchResponseSerializer(data=results)
        response_serializer.is_valid(raise_exception=True)

        return Response(response_serializer.data)


@api_view(["GET"])
@permission_classes([])
@cache_response(timeout=3600)  # Cache for 1 hour
def autocomplete_view(request):
    """
    Get search suggestions for autocomplete.
    """
    serializer = AutocompleteSerializer(data=request.GET)
    serializer.is_valid(raise_exception=True)

    query = serializer.validated_data["query"]
    limit = serializer.validated_data.get("limit", 10)

    suggestions = search_service.get_suggestions(query, limit)

    return Response({"query": query, "suggestions": suggestions})


class SearchSuggestionListCreateView(generics.ListCreateAPIView):
    """
    List and create search suggestions (admin only).
    """

    queryset = SearchSuggestion.objects.select_related("created_by").all()
    serializer_class = SearchSuggestionSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["is_active", "is_promoted"]
    ordering = ["-search_count", "suggestion_text"]


class SearchSuggestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a search suggestion (admin only).
    """

    queryset = SearchSuggestion.objects.select_related("created_by").all()
    serializer_class = SearchSuggestionSerializer
    permission_classes = [IsAdminUser]


@api_view(["GET"])
@permission_classes([IsAdminUser])
@cache_response(timeout=1800)  # Cache for 30 minutes
def search_analytics_view(request):
    """
    Get search analytics (admin only).
    """
    days = int(request.GET.get("days", 30))
    analytics = search_service.get_search_analytics(days)

    serializer = SearchAnalyticsSerializer(data=analytics)
    serializer.is_valid(raise_exception=True)

    return Response(serializer.data)


class SearchIndexListView(generics.ListAPIView):
    """
    List search index entries (admin only).
    """

    queryset = SearchIndex.objects.select_related("content_type").all()
    serializer_class = SearchIndexSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = [
        "content_type",
        "search_category",
        "is_published",
        "locale_code",
    ]
    ordering = ["-indexed_at"]


class SearchQueryLogListView(generics.ListAPIView):
    """
    List search query logs (admin only).
    """

    queryset = SearchQuery.objects.select_related("user").all()
    serializer_class = SearchQueryLogSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["user", "result_count"]
    ordering = ["-created_at"]


@api_view(["POST"])
@permission_classes([IsAdminUser])
def bulk_index_view(request):
    """
    Trigger bulk indexing of content (admin only).
    """
    serializer = BulkIndexSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    model_label = serializer.validated_data.get("model_label")

    try:
        indexed_count = search_service.reindex_all(model_label)

        return Response(
            {
                "success": True,
                "message": f"Successfully indexed {indexed_count} objects",
                "indexed_count": indexed_count,
                "model_label": model_label or "all",
            }
        )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["GET"])
@permission_classes([])
def search_categories_view(request):
    """
    Get available search categories.
    """
    categories = (
        SearchIndex.objects.values_list("search_category", flat=True)
        .distinct()
        .order_by("search_category")
    )

    return Response({"categories": list(categories)})
