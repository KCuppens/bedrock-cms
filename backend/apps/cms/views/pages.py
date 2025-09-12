from django.conf import settings

from django.db import transaction

from django.http import HttpResponse



from drf_spectacular.utils import OpenApiParameter, extend_schema

from rest_framework import permissions, status, viewsets

from rest_framework.decorators import action

from rest_framework.response import Response

from rest_framework.throttling import UserRateThrottle



from apps.cms.serializers import (

    AuditEntry,

    Case,

    Count,

    IntegerField,

    Locale,

    Page,

    PageReadSerializer,

    PageTreeItemSerializer,

    PageWriteSerializer,

    PublicPageSerializer,

    Value,

    VersioningMixin,

    When,

    ..models,

    ..seo_utils,

    ..versioning,

    ..versioning_views,

    apps.cms.serializers.public,

    apps.core.throttling,

    apps.i18n.models,

    cache_page,

    copy,

    django.db.models,

    django.shortcuts,

    django.utils,

    django.views.decorators.cache,

    django_ratelimit.decorators,

    generate_hreflang_alternates,

    ratelimit,

    redirect,

    timezone,

    uuid,

)



    BurstWriteThrottle,

    PublishOperationThrottle,

    WriteOperationThrottle,

)



class PagesViewSet(VersioningMixin, viewsets.ModelViewSet):

    """API endpoints for managing pages."""



    throttle_classes = [

        UserRateThrottle,

        WriteOperationThrottle,

        BurstWriteThrottle,

        PublishOperationThrottle,

    ]



    def get_queryset(self):



        return (

            Page.objects.select_related("locale", "parent")

            .annotate(_children_count=Count("children"))

            .all()

        )



    def get_serializer_class(self):

        if self.action in ["create", "update", "partial_update"]:

            return PageWriteSerializer

        return PageReadSerializer



    def create(self, request, *args, **kwargs):

        """Create a new page."""

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)



        # Set position at end of siblings

        parent = serializer.validated_data.get("parent")

        last_position = Page.objects.filter(parent=parent).count()



        with transaction.atomic():

            page = serializer.save(position=last_position)

            # Refresh from database to get all fields including defaults

            page.refresh_from_db()



        # Use select_related to include locale data

        page = Page.objects.select_related("locale").get(pk=page.pk)

        return Response(PageReadSerializer(page).data, status=status.HTTP_201_CREATED)



    def get_permissions(self):

        """Set permissions based on action."""

        if self.action in ["list", "retrieve", "get_by_path", "children", "tree"]:

            # Read operations

            return [permissions.AllowAny()]

        elif self.action in ["publish", "unpublish"]:

            # Publish operations require special permission

            return [permissions.IsAuthenticated(), permissions.DjangoModelPermissions()]

        else:

            # Write operations require change permission

            return [permissions.IsAuthenticated(), permissions.DjangoModelPermissions()]



    @extend_schema(

        parameters=[

            OpenApiParameter("path", str, description="Page path", required=True),

            OpenApiParameter("locale", str, description="Locale code (default: en)"),

            OpenApiParameter(

                "preview", str, description="Preview token UUID for draft pages"

            ),

        ],

        responses={

            200: PublicPageSerializer,

            404: "Page not found",

            403: "Permission denied",

        },

    )

    @action(detail=False, methods=["get"])

    def get_by_path(self, request):



        Get page by path with optimized SEO data for frontend consumption.



        This endpoint is optimized for public-facing pages and includes:

        - Resolved SEO data (global + page overrides)

        - Canonical URLs and hreflang alternates

        - Block data for rendering

        - Minimal response payload for performance



        path = request.query_params.get("path")

        locale_code = request.query_params.get("locale", "en")

        preview_token = request.query_params.get("preview")



        if not path:

            return Response(

                {"error": "Path parameter is required"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        # Normalize path (ensure leading slash, no trailing slash except for root)

        if not path.startswith("/"):

            path = f"/{path}"

        if len(path) > 1 and path.endswith("/"):

            path = path.rstrip("/")



        try:

            # Use select_related to optimize locale lookup

            locale = Locale.objects.select_related().get(

                code=locale_code, is_active=True

            )

        except Locale.DoesNotExist:

            return Response(

                {"error": f'Locale "{locale_code}" not found or inactive'},

                status=status.HTTP_400_BAD_REQUEST,

            )



        # Get page with optimized query using select_related for locale

        try:

            page = Page.objects.select_related("locale").get(path=path, locale=locale)

        except Page.DoesNotExist:

            return Response(

                {"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND

            )



        # Security: Check if page is published or has valid preview access

        if page.status != "published":

            if page.status == "draft":

                if preview_token:

                    # Validate preview token

                    if str(page.preview_token) != preview_token:

                        return Response(

                            {"error": "Invalid preview token"},

                            status=status.HTTP_403_FORBIDDEN,

                        )

                else:

                    # Check if user has preview permission

                    if not request.user.is_authenticated or not request.user.has_perm(

                        "cms.preview_page"

                    ):

                        return Response(

                            {"error": "Page not published"},

                            status=status.HTTP_404_NOT_FOUND,

                        )

            else:

                # For scheduled, pending_review, etc - only show if authenticated with permission

                if not request.user.is_authenticated or not request.user.has_perm(

                    "cms.view_page"

                ):

                    return Response(

                        {"error": "Page not available"},

                        status=status.HTTP_404_NOT_FOUND,

                    )



        # Use optimized public serializer

        serializer = PublicPageSerializer(page, context={"request": request})

        response_data = serializer.data



        # Add cache headers for published pages

        response = Response(response_data)

        if page.status == "published":

            # Cache for 5 minutes for published pages

            response["Cache-Control"] = "public, max-age=300, s-maxage=600"

            response["Vary"] = "Accept-Language, Accept-Encoding"

            if page.updated_at:

                response["Last-Modified"] = page.updated_at.strftime(

                    "%a, %d %b %Y %H:%M:%S GMT"

                )

        else:

            # No cache for non-published pages

            response["Cache-Control"] = "no-cache, no-store, must-revalidate"



        return response



    @extend_schema(

        parameters=[

            OpenApiParameter("locale", str, description="Locale code"),

            OpenApiParameter("depth", int, description="Tree depth (1 or 2)"),

        ]

    )

    @action(detail=True, methods=["get"])

    def children(self, request, pk=None):

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

    def tree(self, request):

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



        # Annotate with children count for the serializer



        queryset = queryset.annotate(_children_count=Count("children"))



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

    def retrieve(self, request, *args, **kwargs):

        """Get a single page by ID with optional SEO data."""

        result = super().retrieve(request, *args, **kwargs)

        return result



    def update(self, request, *args, **kwargs):

        """Update a page."""

        partial = kwargs.pop("partial", False)

        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        serializer.is_valid(raise_exception=True)



        with transaction.atomic():

            page = serializer.save()

            # Refresh from database to get all fields

            page.refresh_from_db()



        # Use select_related to include locale data

        page = Page.objects.select_related("locale").get(pk=page.pk)

        return Response(PageReadSerializer(page).data)



    @action(detail=True, methods=["post"])

    def move(self, request, pk=None):

        """Move a page to a new parent and position."""

        page = self.get_object()

        new_parent_id = request.data.get("new_parent_id")

        new_position = request.data.get("position", 0)

        old_parent_id = page.parent_id



        with transaction.atomic():

            # Store old parent for resequencing



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



            # Get siblings at the new parent level

            siblings = (

                Page.objects.filter(parent_id=page.parent_id, locale=page.locale)

                .exclude(pk=page.pk)

                .order_by("position", "id")

            )



            # Convert to list and insert the moved page at the desired position

            siblings_list = list(siblings)

            siblings_list.insert(min(new_position, len(siblings_list)), page)



            # Update positions for all siblings including the moved page

            for index, sibling in enumerate(siblings_list):

                sibling.position = index

                sibling.save(

                    update_fields=(

                        ["position"]

                        if sibling.pk != page.pk

                        else ["parent", "position"]

                    )

                )



            # If page moved to different parent, resequence old parent's children

            if old_parent_id != page.parent_id:

                Page.siblings_resequence(old_parent_id)



        return Response(PageReadSerializer(page).data)



    @extend_schema(

        request={

            "application/json": {

                "type": "object",

                "properties": {

                    "parent_id": {

                        "type": ["integer", "null"],

                        "description": "Parent page ID, null for root pages",

                    },

                    "page_ids": {

                        "type": "array",

                        "items": {"type": "integer"},

                        "description": "Ordered list of page IDs to reorder",

                    },

                },

                "required": ["page_ids"],

            }

        },

        responses={200: {"description": "Pages reordered successfully"}},

    )

    @action(detail=False, methods=["post"], url_path="reorder")

    def reorder(self, request):



        Reorder pages by providing an ordered list of page IDs.



        This endpoint efficiently updates the position field for multiple pages

        in a single database transaction. All pages must belong to the same parent.



        Request body:

        {

            "parent_id": null | number,  // Parent page ID (null for root pages)

            "page_ids": [1, 2, 3, ...]   // Ordered list of page IDs

        }



        Returns:

        {

            "success": true,

            "reordered_count": 3,

            "parent_id": null | number

        }



        parent_id = request.data.get("parent_id")

        page_ids = request.data.get("page_ids", [])



        # Validate input

        if not isinstance(page_ids, list):

            return Response(

                {"error": "page_ids must be a list"}, status=status.HTTP_400_BAD_REQUEST

            )



        if not page_ids:

            return Response(

                {"error": "page_ids cannot be empty"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        # Remove duplicates while preserving order

        seen = set()

        unique_page_ids = []

        for page_id in page_ids:

            if page_id not in seen:

                seen.add(page_id)

                unique_page_ids.append(page_id)



        if len(unique_page_ids) != len(page_ids):

            return Response(

                {"error": "Duplicate page IDs found"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        with transaction.atomic():

            # Lock the pages we're updating to prevent race conditions

            pages_query = Page.objects.select_for_update()



            # Build the filter based on parent_id

            if parent_id is None:

                pages_filter = pages_query.filter(id__in=page_ids, parent__isnull=True)

            else:

                # Validate parent exists

                if not Page.objects.filter(id=parent_id).exists():

                    return Response(

                        {"error": f"Parent page with ID {parent_id} does not exist"},

                        status=status.HTTP_400_BAD_REQUEST,

                    )



                pages_filter = pages_query.filter(id__in=page_ids, parent_id=parent_id)



            # Validate all pages exist with the correct parent

            valid_page_ids = list(pages_filter.values_list("id", flat=True))



            if len(valid_page_ids) != len(page_ids):

                invalid_ids = set(page_ids) - set(valid_page_ids)

                return Response(

                    {"error": f"Invalid page IDs or wrong parent: {list(invalid_ids)}"},

                    status=status.HTTP_400_BAD_REQUEST,

                )



            # Bulk update positions using CASE statement for efficiency



            cases = [

                When(id=page_id, then=Value(position))

                for position, page_id in enumerate(page_ids)

            ]



            updated_count = Page.objects.filter(id__in=page_ids).update(

                position=Case(*cases, output_field=IntegerField())

            )



            # Optional: Resequence any remaining siblings not in the list

            # This ensures there are no gaps in positioning

            all_siblings = (

                Page.objects.filter(

                    parent_id=parent_id if parent_id is not None else None

                )

                .exclude(id__in=page_ids)

                .order_by("position", "id")

            )



            # Start position after the reordered pages

            start_position = len(page_ids)

            for position, page in enumerate(all_siblings, start=start_position):

                if page.position != position:

                    Page.objects.filter(pk=page.pk).update(position=position)



        return Response(

            {"success": True, "reordered_count": updated_count, "parent_id": parent_id}

        )



    def perform_create(self, serializer):

        """Set user context when creating pages."""

        page = serializer.save()

        page._current_user = self.request.user

        page._current_request = self.request

        page.save()



        # Add revision_id to response if available

        revision_id = getattr(page, "_revision_id", None)

        if revision_id:

            serializer.instance._revision_id = revision_id



    def perform_update(self, serializer):

        """Set user context when updating pages."""

        page = serializer.save()

        page._current_user = self.request.user

        page._current_request = self.request

        page.save()



        # Add revision_id to response if available

        revision_id = getattr(page, "_revision_id", None)

        if revision_id:

            serializer.instance._revision_id = revision_id



    # Block editing endpoints

    @action(detail=True, methods=["patch"], url_path="update-block")

    def update_block(self, request, pk=None, block_index=None):

        """Update a specific block."""

        page = self.get_object()



        # Get block index from request data

        block_index = request.data.get("block_index")

        if block_index is None:

            return Response(

                {"error": "block_index is required"}, status=status.HTTP_400_BAD_REQUEST

            )



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

    def insert_block(self, request, pk=None):

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

    def reorder_blocks(self, request, pk=None):

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



    @action(detail=True, methods=["post"], url_path="blocks/duplicate")

    def duplicate_block(self, request, pk=None):

        """Duplicate a block."""

        page = self.get_object()

        block_index = request.data.get("block_index")



        if block_index is None:

            return Response(

                {"error": "block_index is required"}, status=status.HTTP_400_BAD_REQUEST

            )



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



        # Duplicate the block



        original_block = page.blocks[index]

        duplicated_block = copy.deepcopy(original_block)



        # Generate new ID for the duplicated block

        duplicated_block["id"] = str(uuid.uuid4())



        # Insert duplicated block right after the original

        insert_position = index + 1

        page.blocks.insert(insert_position, duplicated_block)



        # Update positions for all blocks after the insertion point

        for i in range(insert_position, len(page.blocks)):

            page.blocks[i]["position"] = i



        # Set user context and save

        page._current_user = self.request.user

        page._current_request = self.request

        try:

            page.clean()

            page.save(update_fields=["blocks"])

        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



        return Response(PageReadSerializer(page).data)



    @action(detail=True, methods=["delete"], url_path=r"blocks/(?P<block_index>\d+)")

    def remove_block(self, request, pk=None, block_index=None):

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



    @action(detail=True, methods=["post"])

    def publish(self, request, pk=None):

        """Publish a page."""

        page = self.get_object()



        page.status = "published"

        page.published_at = timezone.now()

        page._current_user = request.user

        page._current_request = request

        page._was_published_now = True

        page.save()



        return Response(PageReadSerializer(page).data)



    @action(detail=True, methods=["post"])

    def unpublish(self, request, pk=None):

        """Unpublish a page."""

        page = self.get_object()



        page.status = "draft"

        page.published_at = None

        page._current_user = request.user

        page._current_request = request

        page._was_unpublished_now = True

        page.save()



        return Response(PageReadSerializer(page).data)



    @action(detail=True, methods=["post"])

    def duplicate(self, request, pk=None):

        """Duplicate a page with all its content."""



        page = self.get_object()



        # Generate a unique slug

        base_slug = page.slug if page.slug else "page"

        new_slug = f"{base_slug}-copy-{uuid.uuid4().hex[:6]}"



        # Ensure blocks is a list (not None)

        blocks_copy = copy.deepcopy(page.blocks) if page.blocks else []



        # Generate new IDs for blocks

        for block in blocks_copy:

            if "id" in block:

                block["id"] = str(uuid.uuid4())



        # Ensure seo is a dict (not None)

        seo_copy = copy.deepcopy(page.seo) if page.seo else {}



        # Create a copy of the page

        duplicated_page = Page(

            parent=page.parent,

            locale=page.locale,

            title=f"{page.title} (Copy)",

            slug=new_slug,

            blocks=blocks_copy,

            seo=seo_copy,

            status="draft",  # Always create as draft

            in_main_menu=False,  # Don't duplicate menu settings

            in_footer=False,

            is_homepage=False,

            position=Page.objects.filter(parent=page.parent).count(),

        )



        # Set user context

        duplicated_page._current_user = request.user

        duplicated_page._current_request = request



        try:

            # Save will automatically compute the path

            duplicated_page.save()



            # Refresh to get all computed fields

            duplicated_page.refresh_from_db()



            # Create audit entry for duplication



            AuditEntry.objects.create(

                content_object=duplicated_page,

                action="duplicate",

                actor=request.user,

                model_label="cms.Page",

                meta={"original_page_id": page.id, "original_page_title": page.title},

            )



            # Get with related data for proper serialization

            duplicated_page = Page.objects.select_related("locale").get(

                pk=duplicated_page.pk

            )

            return Response(

                PageReadSerializer(duplicated_page).data, status=status.HTTP_201_CREATED

            )

        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



    def destroy(self, request, *args, **kwargs):

        """Delete a page and optionally its children."""

        page = self.get_object()



        # Check if page has children

        children_count = page.children.count()

        cascade = request.query_params.get("cascade", "false").lower() == "true"



        if children_count > 0 and not cascade:

            return Response(

                {

                    "error": f"Page has {children_count} child page(s). Set cascade=true to delete them all.",

                    "children_count": children_count,

                },

                status=status.HTTP_400_BAD_REQUEST,

            )



        # Store page info for audit log before deletion

        page_title = page.title

        page_path = page.path



        try:

            with transaction.atomic():

                # Create audit entry before deletion



                AuditEntry.objects.create(

                    content_object=page,

                    action="delete",

                    actor=request.user,

                    model_label="cms.Page",

                    meta={

                        "page_title": page_title,

                        "page_path": page_path,

                        "children_deleted": children_count if cascade else 0,

                    },

                )



                # Delete the page (will cascade to children if they exist)

                page.delete()



            return Response(status=status.HTTP_204_NO_CONTENT)



        except Exception as e:

            return Response(

                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR

            )



def default_sitemap_view(request):

    """Redirect /sitemap.xml to the default locale's sitemap."""

    try:

        # Get the default locale (first active locale or 'en' as fallback)

        default_locale = Locale.objects.filter(is_active=True).first()

        if not default_locale:

            # Fallback to 'en' if no active locales

            default_locale = Locale.objects.filter(code="en").first()



        if default_locale:

            return redirect(f"/sitemap-{default_locale.code}.xml", permanent=False)

        else:

            return HttpResponse("No active locales found", status=404)

    except Exception:

        return HttpResponse("Service unavailable", status=503)



@cache_page(60 * 60)  # Cache for 1 hour

@ratelimit(key="ip", rate="10/h", method="GET")

def sitemap_view(request, locale_code):

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

                xml_lines.append(

                    f'    <xhtml:link rel="alternate" hreflang="{alternate["hreflang"]}" href="{alternate["href"]}" />'

                )



        xml_lines.append("  </url>")



    xml_lines.append("</urlset>")



    xml_content = "\n".join(xml_lines)

    response = HttpResponse(xml_content, content_type="application/xml")

    response["Cache-Control"] = "public, max-age=300"  # 5 minutes cache

    return response

