from django.db.models import Count, Q
from django.utils import timezone

from celery import current_app
from celery.result import AsyncResult
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.cms.models import Page
from apps.cms.tasks import check_internal_links, check_single_page_links
from apps.i18n.models import Locale, TranslationUnit
from apps.i18n.tasks import seed_locale_translation_units

Reports API views for CMS background jobs and analytics.

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def broken_links_report(request):  # noqa: C901

    Get broken links report or trigger a new link check.

    GET /api/v1/reports/broken-links/ - Get cached results
    POST /api/v1/reports/broken-links/ - Trigger new check

    if request.method == "GET":
        # Get query parameters
        page_id = request.query_params.get("page_id")

        if page_id:
            try:
                page = Page.objects.get(id=page_id, status="published")
                # Check single page
                task = check_single_page_links.delay(page_id=int(page_id))
                return Response(
                    {
                        "task_id": task.id,
                        "status": "running",
                        "message": f"Checking links for page: {page.title}",
                    }
                )
            except Page.DoesNotExist:
                return Response(
                    {"error": "Page not found or not published"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Return information about recent checks
        return Response(
            {
                "message": "Use POST to trigger a new link check, or specify page_id parameter",
                "endpoints": {
                    "trigger_full_check": "POST /api/v1/reports/broken-links/",
                    "check_single_page": "GET /api/v1/reports/broken-links/?page_id=123",
                    "get_task_status": "GET /api/v1/reports/task-status/{task_id}/",
                },
            }
        )

    elif request.method == "POST":
        # Trigger new link check
        page_ids = request.data.get("page_ids")  # Optional list of page IDs

        if page_ids and not isinstance(page_ids, list):
            return Response(
                {"error": "page_ids must be a list of integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Start the task
        task = check_internal_links.delay(page_ids=page_ids)

        return Response(
            {
                "task_id": task.id,
                "status": "running",
                "message": f"Started link check for {'all pages' if not page_ids else f'{len(page_ids)} pages'}",
                "check_status_url": f"/api/v1/reports/task-status/{task.id}/",
            }
        )

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def translation_digest(request):  # noqa: C901

    Get missing translations digest per locale.

    GET /api/v1/reports/translation-digest/

    # Get all active locales
    locales = Locale.objects.filter(is_active=True).order_by("code")

    digest = {
        "generated_at": timezone.now(),
        "locales": [],
        "summary": {
            "total_locales": locales.count(),
            "total_units": 0,
            "total_missing": 0,
            "total_needs_review": 0,
            "total_approved": 0,
        },
    }

    for locale in locales:
        # Get translation unit statistics
        units = TranslationUnit.objects.filter(target_locale=locale)

        stats = units.aggregate(
            total=Count("id"),
            missing=Count("id", filter=Q(status="missing")),
            draft=Count("id", filter=Q(status="draft")),
            needs_review=Count("id", filter=Q(status="needs_review")),
            approved=Count("id", filter=Q(status="approved")),
        )

        # Calculate completion percentage
        total_units = stats["total"] or 1  # Avoid division by zero
        completion_pct = ((stats["approved"] or 0) / total_units) * 100

        locale_data = {
            "code": locale.code,
            "name": locale.name,
            "native_name": locale.native_name,
            "is_default": locale.is_default,
            "fallback_code": locale.fallback.code if locale.fallback else None,
            "statistics": stats,
            "completion_percentage": round(completion_pct, 1),
            "priority_areas": [],
        }

        # Identify priority areas (models with most missing translations)
        priority_query = (
            units.filter(status="missing")
            .values("content_type__app_label", "content_type__model")
            .annotate(missing_count=Count("id"))
            .order_by("-missing_count")[:5]
        )

        for item in priority_query:
            locale_data["priority_areas"].append(
                {
                    "model": f"{item['content_type__app_label']}.{item['content_type__model']}",
                    "missing_count": item["missing_count"],
                }
            )

        digest["locales"].append(locale_data)

        # Update summary
        digest["summary"]["total_units"] += stats["total"] or 0
        digest["summary"]["total_missing"] += stats["missing"] or 0
        digest["summary"]["total_needs_review"] += stats["needs_review"] or 0
        digest["summary"]["total_approved"] += stats["approved"] or 0

    return Response(digest)

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def task_status(request, task_id):  # noqa: C901

    Get status of a Celery task.

    GET /api/v1/reports/task-status/{task_id}/

    try:
        result = AsyncResult(task_id, app=current_app)

        response_data = {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "failed": result.failed() if result.ready() else None,
        }

        if result.ready():
            if result.successful():
                response_data["result"] = result.result
            elif result.failed():
                response_data["error"] = str(result.result)
        else:
            # Task is still running, get progress info
            if hasattr(result, "info") and result.info:
                response_data["progress"] = result.info

        return Response(response_data)

    except Exception as e:
        return Response(
            {"error": f"Failed to get task status: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def seed_locale(request):  # noqa: C901

    Trigger locale seeding task.

    POST /api/v1/reports/seed-locale/
    Body: {"locale_code": "es", "force_reseed": false}

    locale_code = request.data.get("locale_code")
    force_reseed = request.data.get("force_reseed", False)

    if not locale_code:
        return Response(
            {"error": "locale_code is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Validate locale exists
    try:
        locale = Locale.objects.get(code=locale_code)
        if not locale.is_active:
            return Response(
                {"error": f"Locale {locale_code} is not active"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except Locale.DoesNotExist:
        return Response(
            {"error": f"Locale {locale_code} not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Start seeding task
    task = seed_locale_translation_units.delay(
        locale_code=locale_code, force_reseed=force_reseed
    )

    return Response(
        {
            "task_id": task.id,
            "status": "running",
            "message": f"Started locale seeding for {locale_code}",
            "check_status_url": f"/api/v1/reports/task-status/{task.id}/",
        }
    )

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def reports_overview(request):  # noqa: C901

    Get overview of available reports and recent activity.

    GET /api/v1/reports/

    # Get some basic statistics
    total_pages = Page.objects.filter(status="published").count()
    total_locales = Locale.objects.filter(is_active=True).count()
    total_units = TranslationUnit.objects.count()
    pending_translations = TranslationUnit.objects.filter(
        status__in=["missing", "draft", "needs_review"]
    ).count()

    return Response(
        {
            "overview": {
                "total_published_pages": total_pages,
                "active_locales": total_locales,
                "translation_units": total_units,
                "pending_translations": pending_translations,
            },
            "available_reports": {
                "broken_links": {
                    "endpoint": "/api/v1/reports/broken-links/",
                    "description": "Check internal links in pages",
                    "methods": ["GET", "POST"],
                },
                "translation_digest": {
                    "endpoint": "/api/v1/reports/translation-digest/",
                    "description": "Missing translations summary per locale",
                    "methods": ["GET"],
                },
                "seed_locale": {
                    "endpoint": "/api/v1/reports/seed-locale/",
                    "description": "Seed translation units for a locale",
                    "methods": ["POST"],
                },
                "task_status": {
                    "endpoint": "/api/v1/reports/task-status/{task_id}/",
                    "description": "Get status of background task",
                    "methods": ["GET"],
                },
            },
            "generated_at": timezone.now(),
        }
    )
