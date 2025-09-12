from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Prefetch, Q, Value, When
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.cache import cache_page

from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.blog.models import BlogPost, BlogSettings
from apps.blog.serializers import BlogPostSerializer
from apps.core.decorators import cache_method_response
from apps.core.throttling import (
    BurstWriteThrottle,
    PublishOperationThrottle,
    WriteOperationThrottle,
)
from apps.i18n.models import Locale

from .models import Page
from .seo_utils import generate_hreflang_alternates
from .serializers import PageReadSerializer, PageTreeItemSerializer, PageWriteSerializer
from .services.scheduling import SchedulingService
from .versioning_views import VersioningMixin


class PagesViewSet(VersioningMixin, viewsets.ModelViewSet):

    """API endpoints for managing pages."""



    throttle_classes = [

        UserRateThrottle,

        WriteOperationThrottle,

        BurstWriteThrottle,

        PublishOperationThrottle,

    ]



    def get_queryset(self):  # noqa: C901



        queryset = (

            Page.objects.select_related("locale", "parent", "reviewed_by")

            .prefetch_related(

                Prefetch(

                    "children",

                    queryset=Page.objects.only("id", "title", "slug", "status"),

                )

            )

            .annotate(_children_count=Count("children"))

        )



        # Only load full blocks for detail views

        if self.action != "retrieve":

            queryset = queryset.defer("blocks", "seo")



        return queryset



    def get_serializer_class(self):  # noqa: C901

        if self.action in ["create", "update", "partial_update"]:

            return PageWriteSerializer

        return PageReadSerializer



    def get_permissions(self):  # noqa: C901

        """Set permissions based on action."""

        if self.action in ["list", "retrieve", "get_by_path", "children", "tree"]:

            # Read operations

            return [permissions.AllowAny()]

        elif self.action in ["publish", "unpublish", "schedule", "unschedule"]:

            # Publishing operations require special permission

            return [permissions.IsAuthenticated(), permissions.DjangoModelPermissions()]

        elif self.action in [

            """"approve","""

            "reject",

            "moderation_queue",

            "moderation_stats",

        ]:

            # Moderation operations require special permission

            return [permissions.IsAuthenticated(), permissions.DjangoModelPermissions()]

        elif self.action in ["submit_for_review"]:

            # Content creators can submit for review

            return [permissions.IsAuthenticated()]

        else:

            # Write operations require change permission

            return [permissions.IsAuthenticated(), permissions.DjangoModelPermissions()]



    @extend_schema(

        parameters=[

            OpenApiParameter("path", str, description="Page path"),

            OpenApiParameter("locale", str, description="Locale code"),

            OpenApiParameter("preview", str, description="Preview token UUID"),

            OpenApiParameter(

                "with_seo", str, description="Include resolved SEO data (1 to enable)"

            ),

        ]

    )

    @action(detail=False, methods=["get"])

    @cache_method_response(timeout=600, vary_on_headers=["Accept-Language"])

    def get_by_path(self, request):  # noqa: C901

        """Get page by path and locale."""

        path = request.query_params.get("path")

        locale_code = request.query_params.get("locale", "en")

        preview_token = request.query_params.get("preview")



        if not path:

            return Response(

                {"error": "Path parameter is required"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        try:

            locale = Locale.objects.get(code=locale_code)

        except Locale.DoesNotExist:

            return Response(

                {"error": "Invalid locale"}, status=status.HTTP_400_BAD_REQUEST

            )



        # Get page by path and locale

        try:

            page = Page.objects.get(path=path, locale=locale)

        except Page.DoesNotExist:

            return Response(

                {"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND

            )



        # Check permissions for draft content

        if page.status == "draft":

            if preview_token:

                # Validate preview token but don't allow state changes

                if str(page.preview_token) != preview_token:

                    return Response(

                        {"error": "Invalid preview token"},

                        status=status.HTTP_403_FORBIDDEN,

                    )

            else:

                # Check if user has view permission

                if not request.user.has_perm("cms.view_page"):

                    return Response(

                        {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN

                    )



        serializer = self.get_serializer(page)

        return Response(serializer.data)



    @extend_schema(

        parameters=[

            OpenApiParameter("locale", str, description="Locale code"),

            OpenApiParameter("depth", int, description="Tree depth (1 or 2)"),

        ]

    )

    @action(detail=True, methods=["get"])

    def children(self, request, pk=None):  # noqa: C901

        """Get children of a page."""

        page = self.get_object()

        locale_code = request.query_params.get("locale")

        depth = int(request.query_params.get("depth", 1))



        queryset = page.children.filter(status="published").order_by("position")



        if locale_code:

            try:

                locale = Locale.objects.get(code=locale_code)

                queryset = queryset.filter(locale=locale)

            except Locale.DoesNotExist:

                return Response(

                    {"error": "Invalid locale"}, status=status.HTTP_400_BAD_REQUEST

                )



        if depth == 2:

            # Prefetch grandchildren for nested tree

            queryset = queryset.prefetch_related("children")



        serializer = PageTreeItemSerializer(queryset, many=True)

        return Response(serializer.data)



    @extend_schema(

        parameters=[

            OpenApiParameter("locale", str, description="Locale code"),

            OpenApiParameter("root", int, description="Root page ID"),

            OpenApiParameter("depth", int, description="Tree depth"),

        ]

    )

    @action(detail=False, methods=["get"])

    def tree(self, request):  # noqa: C901

        """Get navigation tree."""

        locale_code = request.query_params.get("locale", "en")

        root_id = request.query_params.get("root")

        depth = int(request.query_params.get("depth", 2))



        try:

            locale = Locale.objects.get(code=locale_code)

        except Locale.DoesNotExist:

            return Response(

                {"error": "Invalid locale"}, status=status.HTTP_400_BAD_REQUEST

            )



        # Build tree query

        queryset = Page.objects.filter(locale=locale, status="published")



        if root_id:

            try:

                root_page = Page.objects.get(id=root_id, locale=locale)

                queryset = queryset.filter(parent=root_page)

            except Page.DoesNotExist:

                return Response(

                    {"error": "Root page not found"}, status=status.HTTP_404_NOT_FOUND

                )

        else:

            queryset = queryset.filter(parent=None)



        queryset = queryset.order_by("position")



        if depth >= 2:

            queryset = queryset.prefetch_related("children")



        serializer = PageTreeItemSerializer(queryset, many=True)

        return Response(serializer.data)



    @extend_schema(

        parameters=[

            OpenApiParameter(

                "with_seo", str, description="Include resolved SEO data (1 to enable)"

            ),

        ]

    )

    def retrieve(self, request, *args, **kwargs):  # noqa: C901

        """Get a single page by ID with optional SEO data."""

        return super().retrieve(request, *args, **kwargs)



    def create(self, request, *args, **kwargs):  # noqa: C901

        """Create a new page."""

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)



        # Set position at end of siblings

        parent = serializer.validated_data.get("parent")

        last_position = Page.objects.filter(parent=parent).count()



        with transaction.atomic():

            page = serializer.save(position=last_position)



        return Response(PageReadSerializer(page).data, status=status.HTTP_201_CREATED)



    @action(detail=True, methods=["post"])

    def move(self, request, pk=None):  # noqa: C901

        """Move a page to a new parent and position."""

        page = self.get_object()

        new_parent_id = request.data.get("new_parent_id")

        new_position = request.data.get("position", 0)



        with transaction.atomic():

            # Update parent

            if new_parent_id:

                try:

                    new_parent = Page.objects.get(id=new_parent_id, locale=page.locale)

                    page.parent = new_parent

                except Page.DoesNotExist:

                    return Response(

                        {"error": "Invalid parent"}, status=status.HTTP_400_BAD_REQUEST

                    )

            else:

                page.parent = None



            page.position = new_position

            page.save()



            # Resequence siblings in both old and new parent groups

            Page.siblings_resequence(page.parent_id)



        return Response(PageReadSerializer(page).data)



    @action(detail=True, methods=["post"])

    def reorder_children(self, request, pk=None):  # noqa: C901

        """Reorder children of a page."""

        page = self.get_object()

        child_ids = request.data.get("ids", [])



        if not isinstance(child_ids, list):

            return Response(

                {"error": "ids must be a list"}, status=status.HTTP_400_BAD_REQUEST

            )



        with transaction.atomic():

            # Validate all child IDs first

            valid_children = Page.objects.filter(

                id__in=child_ids, parent=page

            ).values_list("id", flat=True)



            if len(valid_children) != len(child_ids):

                invalid_ids = set(child_ids) - set(valid_children)

                return Response(

                    {"error": f"Invalid child IDs: {invalid_ids}"},

                    status=status.HTTP_400_BAD_REQUEST,

                )



            # Bulk update using CASE statement for efficiency



            cases = [

                When(id=child_id, then=Value(position))

                for position, child_id in enumerate(child_ids)

            ]



            Page.objects.filter(id__in=child_ids).update(

                position=Case(*cases, output_field=IntegerField())

            )



        return Response({"success": True})



    def perform_create(self, serializer):  # noqa: C901

        """Set user context when creating pages."""

        page = serializer.save()

        page._current_user = self.request.user

        page._current_request = self.request

        page.save()



        # Add revision_id to response if available

        revision_id = getattr(page, "_revision_id", None)

        if revision_id:

            serializer.instance._revision_id = revision_id



    def perform_update(self, serializer):  # noqa: C901

        """Set user context when updating pages."""

        page = serializer.save()

        page._current_user = self.request.user

        page._current_request = self.request

        page.save()



        # Add revision_id to response if available

        revision_id = getattr(page, "_revision_id", None)

        if revision_id:

            serializer.instance._revision_id = revision_id



    # Publishing and scheduling endpoints

    @action(detail=True, methods=["post"])

    def publish(self, request, pk=None):  # noqa: C901

        """Publish a page immediately."""

        page = self.get_object()



        with transaction.atomic():

            page.status = "published"

            page.published_at = datetime.now()

            page._current_user = self.request.user

            page._current_request = self.request

            page.save(update_fields=["status", "published_at"])



        return Response(

            {

                "status": "published",

                "published_at": page.published_at,

                "message": "Page published successfully",

            }

        )



    @action(detail=True, methods=["post"])

    def unpublish(self, request, pk=None):  # noqa: C901

        """Unpublish a page."""

        page = self.get_object()



        with transaction.atomic():

            page.status = "draft"

            page._current_user = self.request.user

            page._current_request = self.request

            page.save(update_fields=["status"])



        return Response({"status": "draft", "message": "Page unpublished successfully"})



    @action(detail=True, methods=["post"])

    def schedule(self, request, pk=None):  # noqa: C901

        """Schedule a page for future publishing."""



        page = self.get_object()

        publish_at_str = request.data.get("publish_at")

        unpublish_at_str = request.data.get("unpublish_at")



        if not publish_at_str:

            return Response(

                {"error": "publish_at is required"}, status=status.HTTP_400_BAD_REQUEST

            )



        try:

            # Parse the datetime strings

            publish_at = parse_datetime(publish_at_str)

            if not publish_at:

                return Response(

                    {"error": "Invalid publish_at format. Use ISO format."},

                    status=status.HTTP_400_BAD_REQUEST,

                )



            unpublish_at = None

            if unpublish_at_str:

                unpublish_at = parse_datetime(unpublish_at_str)

                if not unpublish_at:

                    return Response(

                        {"error": "Invalid unpublish_at format. Use ISO format."},

                        status=status.HTTP_400_BAD_REQUEST,

                    )



            # Schedule using the service

            publish_task, unpublish_task = SchedulingService.schedule_publish(

                content_object=page,

                publish_at=publish_at,

                unpublish_at=unpublish_at,

                user=self.request.user,

            )



            # Update page metadata for tracking

            page._current_user = self.request.user

            page._current_request = self.request



            return Response(

                {

                    "status": "scheduled",

                    "scheduled_publish_at": page.scheduled_publish_at,

                    "scheduled_unpublish_at": page.scheduled_unpublish_at,

                    "scheduled_task_id": publish_task.id,

                    "message": "Page scheduled successfully",

                }

            )



        except ValidationError as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:

            return Response(

                {"error": f"Failed to schedule page: {str(e)}"},

                status=status.HTTP_400_BAD_REQUEST,

            )



    @action(detail=True, methods=["post"])

    def unschedule(self, request, pk=None):  # noqa: C901

        """Remove scheduling from a page."""



        page = self.get_object()



        try:

            SchedulingService.cancel_scheduling(page)



            # Update page metadata for tracking

            page._current_user = self.request.user

            page._current_request = self.request



            return Response(

                {"status": page.status, "message": "Page unscheduled successfully"}

            )

        except Exception as e:

            return Response(

                {"error": f"Failed to unschedule page: {str(e)}"},

                status=status.HTTP_400_BAD_REQUEST,

            )



    @action(detail=True, methods=["post"], url_path="schedule-unpublish")

    def schedule_unpublish(self, request, pk=None):  # noqa: C901

        """Schedule a published page to be unpublished at a future time."""



        page = self.get_object()

        unpublish_at_str = request.data.get("unpublish_at")



        if not unpublish_at_str:

            return Response(

                {"error": "unpublish_at is required"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        try:

            # Parse the datetime string

            unpublish_at = parse_datetime(unpublish_at_str)

            if not unpublish_at:

                return Response(

                    {"error": "Invalid datetime format. Use ISO format."},

                    status=status.HTTP_400_BAD_REQUEST,

                )



            # Schedule unpublishing using the service

            unpublish_task = SchedulingService.schedule_unpublish(

                content_object=page, unpublish_at=unpublish_at, user=self.request.user

            )



            # Update page metadata for tracking

            page._current_user = self.request.user

            page._current_request = self.request



            return Response(

                {

                    "status": page.status,

                    "scheduled_unpublish_at": page.scheduled_unpublish_at,

                    "scheduled_task_id": unpublish_task.id,

                    "message": "Page scheduled for unpublishing",

                }

            )



        except ValidationError as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:

            return Response(

                {"error": f"Failed to schedule unpublishing: {str(e)}"},

                status=status.HTTP_400_BAD_REQUEST,

            )



    @action(detail=False, methods=["get"])

    def scheduled_content(self, request):  # noqa: C901

        """Get all scheduled content."""



        scheduled_pages = (

            self.get_queryset()

            .filter(status="scheduled", published_at__isnull=False)

            .order_by("published_at")

        )



        # Optional date range filtering

        start_date = request.query_params.get("start_date")

        end_date = request.query_params.get("end_date")



        if start_date:

            try:



                start_dt = parse_datetime(start_date)

                if start_dt:

                    scheduled_pages = scheduled_pages.filter(published_at__gte=start_dt)

            except ValueError:
                pass



        if end_date:

            try:



                end_dt = parse_datetime(end_date)

                if end_dt:

                    scheduled_pages = scheduled_pages.filter(published_at__lte=end_dt)

            except ValueError:
                pass



        serializer = PageReadSerializer(scheduled_pages, many=True)

        return Response(serializer.data)



    @action(detail=False, methods=["get"], url_path="scheduled-tasks")

    def scheduled_tasks(self, request):  # noqa: C901

        """Get all scheduled tasks for pages."""



        # Get query parameters

        status = request.query_params.get("status", "pending")

        from_date = request.query_params.get("from_date")

        to_date = request.query_params.get("to_date")



        # Parse dates if provided



        if from_date:

            from_date = parse_datetime(from_date)

        if to_date:

            to_date = parse_datetime(to_date)



        # Get scheduled tasks for pages

        page_content_type = ContentType.objects.get_for_model(Page)

        tasks = SchedulingService.get_scheduled_tasks(

            content_type=page_content_type,

            status=status,

            from_date=from_date,

            to_date=to_date,

        )



        # Serialize the tasks

        task_data = []

        for task in tasks:

            page = task.content_object

            """task_data.append("""

                {

                    "id": task.id,

                    "content_type": "page",

                    "content_id": task.object_id,

                    "content_title": page.title if page else "Unknown",

                    "task_type": task.task_type,

                    "scheduled_for": task.scheduled_for,

                    "status": task.status,

                    "attempts": task.attempts,

                    "created_by": task.created_by.email if task.created_by else None,

                    "created_at": task.created_at,

                    "error_message": task.error_message if task.error_message else None,

                }

            )



        return Response({"count": len(task_data), "results": task_data})



    # Moderation workflow endpoints

    @action(detail=True, methods=["post"])

    def submit_for_review(self, request, pk=None):  # noqa: C901

        """Submit a page for moderation review."""

        page = self.get_object()



        if not page.can_be_submitted_for_review():

            return Response(

                {

                    "error": f"Page cannot be submitted for review from status: {page.status}"

                },

                status=status.HTTP_400_BAD_REQUEST,

            )



        try:

            with transaction.atomic():

                page._current_user = request.user

                page._current_request = request

                page.submit_for_review()



            return Response(

                {

                    "status": "pending_review",

                    "submitted_for_review_at": page.submitted_for_review_at,

                    "message": "Page submitted for review successfully",

                }

            )



        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



    @action(detail=True, methods=["post"])

    def approve(self, request, pk=None):  # noqa: C901

        """Approve a page (moderator only)."""

        page = self.get_object()

        notes = request.data.get("notes", "")



        """if not page.can_be_approved():"""

            return Response(

                {"error": f"Page cannot be approved from status: {page.status}"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        try:

            with transaction.atomic():

                page.approve(reviewer=request.user, notes=notes)



            return Response(

                {

                    """"status": "approved","""

                    "reviewed_by": page.reviewed_by.email if page.reviewed_by else None,

                    "review_notes": page.review_notes,

                    """"message": "Page approved successfully","""

                }

            )



        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



    @action(detail=True, methods=["post"])

    def reject(self, request, pk=None):  # noqa: C901

        """Reject a page with review comments."""

        page = self.get_object()

        notes = request.data.get("notes", "")



        if not notes.strip():

            return Response(

                {"error": "Review notes are required when rejecting content"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        if not page.can_be_rejected():

            return Response(

                {"error": f"Page cannot be rejected from status: {page.status}"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        try:

            with transaction.atomic():

                page.reject(reviewer=request.user, notes=notes)



            return Response(

                {

                    "status": "rejected",

                    "reviewed_by": page.reviewed_by.email if page.reviewed_by else None,

                    "review_notes": page.review_notes,

                    "message": "Page rejected successfully",

                }

            )



        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



    @action(detail=False, methods=["get"])

    def moderation_queue(self, request):  # noqa: C901

        """Get pages pending moderation review."""

        pending_pages = (

            self.get_queryset()

            .filter(status="pending_review")

            .order_by("submitted_for_review_at")

        )



        # Optional filtering

        author_id = request.query_params.get("author_id")

        if author_id:

            try:



                User = get_user_model()

                author = User.objects.get(id=author_id)

                # Filter by author through audit entries or created_by if available

                pending_pages = pending_pages.filter(

                    pagerevision__user=author

                ).distinct()

            except (ValueError, User.DoesNotExist):
                pass



        serializer = PageReadSerializer(pending_pages, many=True)

        return Response(serializer.data)



    @action(detail=False, methods=["get"])

    def moderation_stats(self, request):  # noqa: C901

        """Get moderation statistics."""



        stats = {

            "pending_review": self.get_queryset()

            .filter(status="pending_review")

            .count(),

            "approved": self.get_queryset().filter(status="approved").count(),

            "rejected": self.get_queryset().filter(status="rejected").count(),

            "published": self.get_queryset().filter(status="published").count(),

        }



        # Top reviewers this month



        last_month = timezone.now() - timedelta(days=30)

        reviewer_stats = (

            self.get_queryset()

            .filter(reviewed_by__isnull=False, updated_at__gte=last_month)

            .values(

                "reviewed_by__email",

                "reviewed_by__first_name",

                "reviewed_by__last_name",

            )

            .annotate(

                approved_count=Count("id", filter=Q(status="approved")),

                rejected_count=Count("id", filter=Q(status="rejected")),

                total_reviews=Count("id"),

            )

            .order_by("-total_reviews")[:10]

        )



        stats["top_reviewers"] = list(reviewer_stats)



        return Response(stats)



    # Block editing endpoints

    @action(detail=True, methods=["patch"], url_path="blocks/(?P<block_index>[^/.]+)")

    def update_block(self, request, pk=None, block_index=None):  # noqa: C901

        """Update a specific block."""

        page = self.get_object()



        try:

            index = int(block_index)

            if index < 0 or index >= len(page.blocks):

                return Response(

                    {"error": "Block index out of range"},

                    status=status.HTTP_400_BAD_REQUEST,

                )

        except ValueError:

            return Response(

                {"error": "Invalid block index"}, status=status.HTTP_400_BAD_REQUEST

            )



        # Update block props

        props = request.data.get("props", {})

        page.blocks[index]["props"] = {**page.blocks[index].get("props", {}), **props}



        # Set user context and validate updated blocks

        page._current_user = self.request.user

        page._current_request = self.request

        try:

            page.clean()

            page.save(update_fields=["blocks"])

        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



        return Response(PageReadSerializer(page).data)



    @action(detail=True, methods=["post"], url_path="blocks/insert")

    def insert_block(self, request, pk=None):  # noqa: C901

        """Insert a new block."""

        page = self.get_object()

        at_index = request.data.get("at", len(page.blocks))

        new_block = request.data.get("block", {})



        if at_index < 0 or at_index > len(page.blocks):

            return Response(

                {"error": "Invalid insertion index"}, status=status.HTTP_400_BAD_REQUEST

            )



        page.blocks.insert(at_index, new_block)



        # Set user context

        page._current_user = self.request.user

        page._current_request = self.request

        try:

            page.clean()

            page.save(update_fields=["blocks"])

        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



        return Response(PageReadSerializer(page).data)



    @action(detail=True, methods=["post"], url_path="blocks/reorder")

    def reorder_blocks(self, request, pk=None):  # noqa: C901

        """Reorder blocks."""

        page = self.get_object()

        from_index = request.data.get("from")

        to_index = request.data.get("to")



        if from_index is None or to_index is None:

            return Response(

                {"error": "from and to indices are required"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        if (

            from_index < 0

            or from_index >= len(page.blocks)

            or to_index < 0

            or to_index >= len(page.blocks)

        ):

            return Response(

                {"error": "Block indices out of range"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        # Move block

        block = page.blocks.pop(from_index)

        page.blocks.insert(to_index, block)



        # Set user context

        page._current_user = self.request.user

        page._current_request = self.request

        page.save(update_fields=["blocks"])

        return Response(PageReadSerializer(page).data)



    @action(detail=True, methods=["delete"], url_path="blocks/(?P<block_index>[^/.]+)")

    def delete_block(self, request, pk=None, block_index=None):  # noqa: C901

        """Delete a block."""

        page = self.get_object()



        try:

            index = int(block_index)

            if index < 0 or index >= len(page.blocks):

                return Response(

                    {"error": "Block index out of range"},

                    status=status.HTTP_400_BAD_REQUEST,

                )

        except ValueError:

            return Response(

                {"error": "Invalid block index"}, status=status.HTTP_400_BAD_REQUEST

            )



        page.blocks.pop(index)



        # Set user context

        page._current_user = self.request.user

        page._current_request = self.request

        page.save(update_fields=["blocks"])

        return Response(PageReadSerializer(page).data)



    @action(detail=False, methods=["get"])

    def presentation_templates(self, request):  # noqa: C901

        """Get all presentation templates for a content type."""

        content_type = request.query_params.get("content_type")

        if not content_type:

            return Response(

                {"error": "content_type parameter required"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        # Find pages with matching detail block

        block_type = f"{content_type}_detail"

        locale_code = request.query_params.get("locale", "en")



        # Filter pages that have the specific detail block

        pages = Page.objects.filter(

            locale__code=locale_code, status="published"

        ).select_related("locale")



        # Filter in Python to check block contents

        template_pages = []

        for page in pages:

            if page.blocks and isinstance(page.blocks, list):

                for block in page.blocks:

                    if isinstance(block, dict) and block.get("type") == block_type:

                        """template_pages.append(page)"""



        return Response(

            {

                "templates": PageReadSerializer(

                    template_pages, many=True, context={"request": request}

                ).data,

                "content_type": content_type,

                "block_type": block_type,

            }

        )



    @action(detail=False, methods=["get"])

    def resolve_content(self, request):  # noqa: C901

        """Resolve content with presentation page."""

        path = request.query_params.get("path")

        locale_code = request.query_params.get("locale", "en")



        if not path:

            return Response(

                {"error": "path parameter required"}, status=status.HTTP_400_BAD_REQUEST

            )



        # Parse path to determine content type and slug

        path_parts = path.strip("/").split("/")

        if len(path_parts) < 2:

            return Response(

                {"error": "Invalid path format"}, status=status.HTTP_404_NOT_FOUND

            )



        content_type = path_parts[0]

        slug = path_parts[1]



        # Handle blog posts

        if content_type == "blog":

            return self._resolve_blog_post(slug, locale_code, request)



        # Could be extended for other content types

        return Response(

            {"error": "Content type not supported"}, status=status.HTTP_404_NOT_FOUND

        )



    def _resolve_blog_post(self, slug, locale_code, request):  # noqa: C901

        """Resolve blog post with presentation page."""



        try:

            locale = Locale.objects.get(code=locale_code)

        except Locale.DoesNotExist:

            return Response(

                {"error": "Invalid locale"}, status=status.HTTP_400_BAD_REQUEST

            )



        # Get the blog post

        try:

            post = (

                BlogPost.objects.select_related(

                    "category",

                    "locale",

                    "presentation_page",

                    "category__presentation_page",

                )

                .prefetch_related("tags")

                .get(slug=slug, locale=locale, status="published")

            )

        except BlogPost.DoesNotExist:

            return Response(

                {"error": "Blog post not found"}, status=status.HTTP_404_NOT_FOUND

            )



        # Determine presentation page using hierarchy

        presentation_page = None

        resolution_source = "fallback"



        # 1. Check individual post override

        if hasattr(post, "presentation_page") and post.presentation_page:

            presentation_page = post.presentation_page

            resolution_source = "individual"

        # 2. Check category override

        elif (

            post.category

            and hasattr(post.category, "presentation_page")

            and post.category.presentation_page

        ):

            presentation_page = post.category.presentation_page

            resolution_source = "category"

        # 3. Check global default

        else:

            try:

                settings = BlogSettings.objects.select_related(

                    "default_presentation_page"

                ).get(locale=locale)

                if settings.default_presentation_page:

                    presentation_page = settings.default_presentation_page

                    resolution_source = "global_default"

            except BlogSettings.DoesNotExist:
                pass



        # Build SEO data

        seo_data = {

            "title": post.seo.get("title") if post.seo else post.title,

            "description": post.seo.get("description") if post.seo else post.excerpt,

            "og_image": post.seo.get("og_image") if post.seo else None,

            "canonical_url": f"/blog/{post.slug}",

        }



        # Serialize response

        response_data = {

            "content": BlogPostSerializer(post, context={"request": request}).data,

            "presentation_page": (

                PageReadSerializer(presentation_page, context={"request": request}).data

                if presentation_page

                else None

            ),

            "resolution_source": resolution_source,

            "seo": seo_data,

        }



        return Response(response_data)



@cache_page(60 * 60)  # Cache for 1 hour

@ratelimit(key="ip", rate="10/h", method="GET")

def sitemap_view(request, locale_code):  # noqa: C901

    """Generate XML sitemap for a specific locale with optional hreflang alternates."""

    try:

        locale = Locale.objects.get(code=locale_code, is_active=True)

    except Locale.DoesNotExist:

        return HttpResponse("Locale not found", status=404)



    # Limit sitemap to 50,000 URLs as per sitemap protocol

    # Use iterator for memory efficiency

    pages = (

        Page.objects.filter(locale=locale, status="published")

        .order_by("updated_at")[:50000]

        .iterator(chunk_size=1000)

    )



    # Build XML with hreflang namespace if alternates requested

    include_alternates = request.GET.get("alternates") == "1"



    if include_alternates:

        xml_lines = [

            '<?xml version="1.0" encoding="UTF-8"?>',

            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',

        ]

    else:

        xml_lines = [

            '<?xml version="1.0" encoding="UTF-8"?>',

            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',

        ]



    base_url = getattr(settings, "CMS_SITEMAP_BASE_URL", "http://localhost:8000")



    for page in pages:

        xml_lines.extend(

            [

                "  <url>",

                f"    <loc>{base_url}{page.path}</loc>",

                f"    <lastmod>{page.updated_at.isoformat()}</lastmod>",

            ]

        )



        # Add hreflang alternates if requested

        if include_alternates:



            alternates = generate_hreflang_alternates(page, base_url)

            for alternate in alternates:

                """xml_lines.append("""

                    f'    <xhtml:link rel="alternate" hreflang="{alternate["hreflang"]}" href="{alternate["href"]}" />'

                )



        """xml_lines.append("  </url>")"""



    """xml_lines.append("</urlset>")"""



    xml_content = "\n".join(xml_lines)

    response = HttpResponse(xml_content, content_type="application/xml")

    response["Cache-Control"] = "public, max-age=300"  # 5 minutes cache

    return response
