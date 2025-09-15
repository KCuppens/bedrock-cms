"""Background tasks for search app."""

from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.utils import timezone

from celery import shared_task

from .models import SearchIndex, SearchQuery, SearchSuggestion
from .services import SearchService


@shared_task(bind=True, max_retries=3)
def reindex_content(
    self, content_type_id: Optional[int] = None, object_ids: Optional[List[int]] = None
):
    """
    Reindex content for search.

    Args:
        content_type_id: Specific content type to reindex
        object_ids: Specific object IDs to reindex
    """
    try:
        search_service = SearchService()

        if content_type_id:
            content_type = ContentType.objects.get(id=content_type_id)
            model_class = content_type.model_class()

            if object_ids:
                objects = model_class.objects.filter(id__in=object_ids)
            else:
                objects = model_class.objects.all()

            for obj in objects:
                search_service.index_object(obj)
        else:
            # Reindex all registered content types
            search_service.reindex_all()

        return {"status": "success", "message": "Content reindexed successfully"}

    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@shared_task
def cleanup_search_logs(days_to_keep: int = 30):
    """
    Clean up old search logs.

    Args:
        days_to_keep: Number of days of logs to keep
    """
    cutoff_date = timezone.now() - timedelta(days=days_to_keep)

    # Delete old search queries
    deleted_queries = SearchQuery.objects.filter(created_at__lt=cutoff_date).delete()

    return {"status": "success", "deleted_queries": deleted_queries[0]}


@shared_task
def update_search_suggestions():
    """Update search suggestions based on recent queries."""
    # Get popular searches from the last 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)

    popular_queries = (
        SearchQuery.objects.filter(created_at__gte=seven_days_ago)
        .values("query_text")
        .annotate(count=Count("id"))
        .filter(count__gte=5)
        .order_by("-count")[:100]
    )

    for query_data in popular_queries:
        query_text = query_data["query_text"]
        count = query_data["count"]

        # Calculate average result count and click-through rate
        queries = SearchQuery.objects.filter(
            query_text=query_text, created_at__gte=seven_days_ago
        )

        avg_results = queries.aggregate(avg=models.Avg("result_count"))["avg"] or 0

        clicks = queries.exclude(clicked_result=None).count()
        ctr = clicks / count if count > 0 else 0

        # Update or create suggestion
        SearchSuggestion.objects.update_or_create(
            normalized_text=query_text.lower().strip(),
            defaults={
                "suggestion_text": query_text,
                "search_count": count,
                "result_count": int(avg_results),
                "click_through_rate": ctr,
                "last_searched_at": timezone.now(),
                "is_active": True,
            },
        )

    # Deactivate old suggestions
    SearchSuggestion.objects.filter(last_searched_at__lt=seven_days_ago).update(
        is_active=False
    )

    return {"status": "success", "suggestions_updated": popular_queries.count()}


@shared_task
def process_search_analytics():
    """Process search analytics for reporting."""
    # This would typically aggregate search data for analytics
    # For now, just a placeholder
    return {"status": "success", "message": "Analytics processed"}


@shared_task(bind=True, max_retries=2)
def sync_search_index(self, model_name: str, object_id: int, action: str = "update"):
    """
    Sync search index for a specific object.

    Args:
        model_name: Name of the model
        object_id: ID of the object
        action: 'update' or 'delete'
    """
    try:
        from django.apps import apps

        model = apps.get_model(model_name)

        if action == "delete":
            content_type = ContentType.objects.get_for_model(model)
            SearchIndex.objects.filter(
                content_type=content_type, object_id=object_id
            ).delete()
        else:
            obj = model.objects.get(pk=object_id)
            search_service = SearchService()
            search_service.index_object(obj)

        return {"status": "success", "action": action}

    except Exception as exc:
        self.retry(exc=exc, countdown=30)
