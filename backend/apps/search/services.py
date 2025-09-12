import time
from typing import Any
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.utils import timezone
    from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from apps.registry.registry import content_registry
from .models import SearchIndex
from .models import SearchQuery as SearchQueryLog
from .models import SearchSuggestion
        from datetime import timedelta
        from django.db.models import Avg, Count
"""
Search services for CMS content.

Provides search functionality including indexing, querying, and analytics.
"""



# PostgreSQL search functionality (optional)
try:

    HAS_POSTGRES_SEARCH = True
except ImportError:
    HAS_POSTGRES_SEARCH = False




class SearchService:
    """
    Core search service for CMS content.

    Handles search indexing, querying, ranking, and analytics.
    """

    def __init__(self):
        self.index_model = SearchIndex
        self.query_log_model = SearchQueryLog
        self.suggestion_model = SearchSuggestion

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
        user=None,
        request=None,
    ) -> dict[str, Any]:
        """
        Perform a search across all indexed content.

        Args:
            query: Search query string
            filters: Additional filters (category, locale, etc.)
            page: Page number (1-based)
            page_size: Results per page
            user: User performing the search
            request: HTTP request object for analytics

        Returns:
            Dictionary with search results, pagination info, and metadata
        """
        start_time = time.time()
        filters = filters or {}

        # Build base queryset
        queryset = self._build_search_queryset(query, filters)

        # Get total count before pagination
        total_results = queryset.count()

        # Apply pagination
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        # Calculate execution time
        execution_time = int((time.time() - start_time) * 1000)

        # Log the search query
        self._log_search_query(
            query=query,
            filters=filters,
            result_count=total_results,
            execution_time_ms=execution_time,
            user=user,
            request=request,
        )

        # Update search suggestions
        self._update_suggestions(query, total_results)

        return {
            "results": [
                self._serialize_search_result(result) for result in page_obj.object_list
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "total_results": total_results,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
            "query": query,
            "filters": filters,
            "execution_time_ms": execution_time,
            "suggestions": self.get_suggestions(query)[:5],  # Top 5 suggestions
        }

    def _build_search_queryset(self, query: str, filters: dict[str, Any]):
        """
        Build search queryset with query and filters.
        """
        queryset = self.index_model.objects.filter(is_published=True)

        # Apply text search
        if query:
            if HAS_POSTGRES_SEARCH:
                # Use PostgreSQL full-text search
                search_query = SearchQuery(query)
                queryset = (
                    queryset.annotate(
                        search_rank=SearchRank(F("search_vector"), search_query)
                    )
                    .filter(search_vector=search_query)
                    .order_by("-search_rank", "-search_weight", "-published_at")
                )
            else:
                # Fallback to basic text search
                search_terms = query.split()
                q_objects = Q()

                for term in search_terms:
                    q_objects |= (
                        Q(title__icontains=term)
                        | Q(content__icontains=term)
                        | Q(excerpt__icontains=term)
                    )

                queryset = queryset.filter(q_objects).order_by(
                    "-search_weight", "-published_at"
                )
        else:
            # No query, just order by relevance
            queryset = queryset.order_by("-search_weight", "-published_at")

        # Apply filters
        if "category" in filters and filters["category"]:
            queryset = queryset.filter(search_category=filters["category"])

        if "locale" in filters and filters["locale"]:
            queryset = queryset.filter(locale_code=filters["locale"])

        if "tags" in filters and filters["tags"]:
            # Filter by tags (JSON field contains)
            for tag in filters["tags"]:
                queryset = queryset.filter(search_tags__contains=[tag])

        if "date_from" in filters and filters["date_from"]:
            queryset = queryset.filter(published_at__gte=filters["date_from"])

        if "date_to" in filters and filters["date_to"]:
            queryset = queryset.filter(published_at__lte=filters["date_to"])

        return queryset

    def _serialize_search_result(self, result: SearchIndex) -> dict[str, Any]:
        """
        Serialize a search result for API response.
        """
        # Get content type info safely
        object_type = ""
        if result.content_type:
            object_type = f"{result.content_type.app_label}.{result.content_type.model}"  # type: ignore[attr-defined]

        return {
            "id": str(result.id),
            "title": result.title,
            "excerpt": result.excerpt or result.content[:200] + "...",
            "content_type": result.search_category,
            "url": result.url,
            "image_url": result.image_url,
            "locale_code": result.locale_code,
            "tags": result.search_tags,
            "published_at": result.published_at,
            "search_weight": result.search_weight,
            "object_type": object_type,
            "object_id": result.object_id,
        }

    def _log_search_query(
        self,
        query: str,
        filters: dict[str, Any],
        result_count: int,
        execution_time_ms: int,
        user=None,
        request=None,
    ):
        """
        Log search query for analytics.
        """
        log_data = {
            "query_text": query,
            "filters": filters,
            "result_count": result_count,
            "execution_time_ms": execution_time_ms,
        }

        if user and user.is_authenticated:
            log_data["user"] = user

        if request:
            log_data["session_key"] = request.session.session_key or ""
            # Get IP address from request
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                log_data["ip_address"] = x_forwarded_for.split(",")[0].strip()
            else:
                log_data["ip_address"] = request.META.get("REMOTE_ADDR")

        self.query_log_model.objects.create(**log_data)

    def _update_suggestions(self, query: str, result_count: int):
        """
        Update search suggestions based on query.
        """
        if not query or len(query) < 2:
            return

        # Clean and normalize query
        normalized_query = query.lower().strip()

        # Get or create suggestion
        suggestion, created = self.suggestion_model.objects.get_or_create(
            normalized_text=normalized_query,
            defaults={"suggestion_text": query, "normalized_text": normalized_query},
        )

        # Update search count and stats
        suggestion.increment_search_count(result_count)

    def get_suggestions(self, query: str, limit: int = 10) -> list[str]:
        """
        Get search suggestions for autocomplete.

        Args:
            query: Partial query string
            limit: Maximum number of suggestions

        Returns:
            List of suggestion strings
        """
        if not query or len(query) < 2:
            return []

        normalized_query = query.lower().strip()

        suggestions = self.suggestion_model.objects.filter(
            normalized_text__startswith=normalized_query, is_active=True
        ).order_by("-is_promoted", "-search_count")[:limit]

        return [s.suggestion_text for s in suggestions]

    def index_object(self, obj):
        """
        Index or re-index a single object.

        Args:
            obj: Django model instance to index
        """
        # Get content type
        content_type = ContentType.objects.get_for_model(obj)

        # Get or create search index entry
        search_index, created = self.index_model.objects.get_or_create(
            content_type=content_type, object_id=obj.pk, defaults={"title": str(obj)}
        )

        # Update search data
        search_index.update_from_object(obj)
        search_index.save()

        return search_index

    def remove_from_index(self, obj):
        """
        Remove an object from the search index.

        Args:
            obj: Django model instance to remove
        """
        content_type = ContentType.objects.get_for_model(obj)

        self.index_model.objects.filter(
            content_type=content_type, object_id=obj.pk
        ).delete()

    def reindex_all(self, model_label: str | None = None):
        """
        Re-index all registered content types or a specific model.

        Args:
            model_label: Optional model label to index (e.g., 'blog.blogpost')
        """
        configs = content_registry.get_all_configs()

        if model_label:
            configs = [c for c in configs if c.model_label == model_label]

        indexed_count = 0

        for config in configs:
            model = config.model

            # Get all objects for this model
            queryset = model.objects.all()

            # Apply additional filters if needed
            if hasattr(model, "is_published"):
                # Only index published content
                queryset = queryset.filter(is_published=True)
            elif hasattr(model, "status"):
                # Only index published content
                queryset = queryset.filter(status="published")

            # Index each object
            for obj in queryset.iterator():
                try:
                    self.index_object(obj)
                    indexed_count += 1
                except Exception:
                    pass

        return indexed_count

    def get_search_analytics(self, days: int = 30) -> dict[str, Any]:
        """
        Get search analytics for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with analytics data
        """


        start_date = timezone.now() - timedelta(days=days)

        # Get search queries from the period
        queries = self.query_log_model.objects.filter(created_at__gte=start_date)

        # Basic stats
        total_queries = queries.count()
        avg_results = (
            queries.aggregate(avg_results=Avg("result_count"))["avg_results"] or 0
        )
        avg_execution_time = (
            queries.aggregate(avg_time=Avg("execution_time_ms"))["avg_time"] or 0
        )

        # Top queries
        top_queries = (
            queries.values("query_text")
            .annotate(count=Count("query_text"))
            .order_by("-count")[:10]
        )

        # Zero result queries
        zero_result_queries = (
            queries.filter(result_count=0)
            .values("query_text")
            .annotate(count=Count("query_text"))
            .order_by("-count")[:10]
        )

        return {
            "period_days": days,
            "total_queries": total_queries,
            "avg_results_per_query": round(avg_results, 2),
            "avg_execution_time_ms": round(avg_execution_time, 2),
            "top_queries": list(top_queries),
            "zero_result_queries": list(zero_result_queries),
        }


# Global search service instance
search_service = SearchService()
