"""Search services for CMS content.

Provides search functionality including indexing, querying, and analytics.
"""

import logging
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union

from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Q
from django.utils import timezone

from apps.registry.registry import content_registry

# PostgreSQL search functionality (optional)

try:
    from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

    HAS_POSTGRES_SEARCH = True

except ImportError:

    HAS_POSTGRES_SEARCH = False
    SearchQuery = None  # type: ignore[assignment,misc]
    SearchRank = None  # type: ignore[assignment,misc]
    SearchVector = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


class SearchService:
    """Core search service for CMS content.

    Handles search indexing, querying, ranking, and analytics.
    """

    def __init__(self):
        self._index_model = None
        self._query_log_model = None
        self._suggestion_model = None

    @property
    def index_model(self):
        if self._index_model is None:
            from .models import SearchIndex

            self._index_model = SearchIndex
        return self._index_model

    @property
    def query_log_model(self):
        if self._query_log_model is None:
            from .models import SearchQuery as SearchQueryLog

            self._query_log_model = SearchQueryLog
        return self._query_log_model

    @property
    def suggestion_model(self):
        if self._suggestion_model is None:
            from .models import SearchSuggestion

            self._suggestion_model = SearchSuggestion
        return self._suggestion_model

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20,
        user=None,
        request=None,
    ) -> Dict[str, Any]:
        """Perform a search across all indexed content.

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

    def _build_search_queryset(self, query: str, filters: Dict[str, Any]):
        """Build search queryset with query and filters."""
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

    def _serialize_search_result(self, result) -> Dict[str, Any]:
        """Serialize a search result for API response."""
        # Get content type info safely

        object_type = ""

        if result.content_type:

            object_type = f"{result.content_type.app_label}.{result.content_type.model}"

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
        filters: Dict[str, Any],
        result_count: int,
        execution_time_ms: int,
        user=None,
        request=None,
    ):
        """Log search query for analytics."""
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
        """Update search suggestions based on query."""
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

    def get_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """Get search suggestions for autocomplete.

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
        """Index or re-index a single object.

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
        """Remove an object from the search index.

        Args:
            obj: Django model instance to remove
        """
        content_type = ContentType.objects.get_for_model(obj)

        self.index_model.objects.filter(
            content_type=content_type, object_id=obj.pk
        ).delete()

    def reindex_all(self, model_label: Optional[str] = None, batch_size: int = 1000):
        """Re-index all registered content types or a specific model with bulk operations.

        Args:
            model_label: Optional model label to index (e.g., 'blog.blogpost')
            batch_size: Number of objects to process in each batch for memory efficiency
        """
        from django.db import transaction

        configs = content_registry.get_all_configs()

        if model_label:
            configs = [c for c in configs if c.model_label == model_label]

        indexed_count = 0

        for config in configs:
            model = config.model
            content_type = ContentType.objects.get_for_model(model)

            # Get all objects for this model
            queryset = model.objects.all()

            # Apply additional filters if needed
            if hasattr(model, "is_published"):
                # Only index published content
                queryset = queryset.filter(is_published=True)
            elif hasattr(model, "status"):
                # Only index published content
                queryset = queryset.filter(status="published")

            # Get total count for progress tracking
            total_objects = queryset.count()
            logger.info(
                f"Starting bulk reindexing of {total_objects} {model.__name__} objects"
            )

            # Process in batches for better memory usage
            for offset in range(0, total_objects, batch_size):
                batch_queryset = queryset[offset : offset + batch_size]
                search_indexes_to_create = []
                search_indexes_to_update = []

                # Prefetch existing search indexes for this batch
                object_ids = list(batch_queryset.values_list("pk", flat=True))
                existing_indexes = {
                    idx.object_id: idx
                    for idx in self.index_model.objects.filter(
                        content_type=content_type, object_id__in=object_ids
                    )
                }

                # Prepare bulk operations
                for obj in batch_queryset:
                    try:
                        if obj.pk in existing_indexes:
                            # Update existing index
                            search_index = existing_indexes[obj.pk]
                            search_index.update_from_object(obj)
                            search_indexes_to_update.append(search_index)
                        else:
                            # Create new index
                            search_index = self.index_model(
                                content_type=content_type,
                                object_id=obj.pk,
                                title=str(obj),
                            )
                            search_index.update_from_object(obj)
                            search_indexes_to_create.append(search_index)

                        indexed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to prepare index for object {obj}: {e}")

                # Perform bulk operations in a transaction
                with transaction.atomic():
                    if search_indexes_to_create:
                        self.index_model.objects.bulk_create(search_indexes_to_create)

                    if search_indexes_to_update:
                        # Bulk update - update all fields that might have changed
                        self.index_model.objects.bulk_update(
                            search_indexes_to_update,
                            fields=[
                                "title",
                                "content",
                                "excerpt",
                                "url",
                                "image_url",
                                "search_category",
                                "search_tags",
                                "search_weight",
                                "locale_code",
                                "is_published",
                                "published_at",
                            ],
                        )

                logger.info(
                    f"Processed batch {offset//batch_size + 1}/{(total_objects-1)//batch_size + 1} for {model.__name__}"
                )

        logger.info(
            f"Bulk reindexing completed. Indexed {indexed_count} objects total."
        )
        return indexed_count

    def get_search_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get search analytics for the last N days.

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


# Global search service instance - lazy initialization
_search_service = None


def get_search_service():
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
