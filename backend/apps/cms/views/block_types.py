from django.core.cache import cache
from django.db.models import Count, Q

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cms.models import BlockType, BlockTypeCategory
from apps.cms.serializers.block_types import (
    BlockTypeCategorySerializer,
    BlockTypeCreateSerializer,
    BlockTypeListSerializer,
    BlockTypeSerializer,
    BlockTypeUpdateSerializer,
)
from apps.core.permissions import RBACPermission


@extend_schema_view(
    list=extend_schema(
        summary="List block types",
        description="Get a paginated list of all block types with filtering and search.",
    ),
    create=extend_schema(
        summary="Create block type",
        description="Create a new block type configuration.",
    ),
    retrieve=extend_schema(
        summary="Get block type",
        description="Get detailed information about a specific block type.",
    ),
    update=extend_schema(
        summary="Update block type",
        description="Update an existing block type configuration.",
    ),
    partial_update=extend_schema(
        summary="Partially update block type",
        description="Partially update an existing block type configuration.",
    ),
    destroy=extend_schema(
        summary="Delete block type",
        description="Delete a block type. This will make it unavailable in the editor.",
    ),
)
class BlockTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing block types with full CRUD operations.
    """

    queryset = BlockType.objects.select_related("created_by", "updated_by").all()

    permission_classes = [IsAuthenticated, RBACPermission]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["category", "is_active", "preload", "editing_mode"]

    search_fields = ["label", "description", "type", "component"]

    ordering_fields = ["label", "category", "created_at", "updated_at"]

    ordering = ["category", "label"]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""

        if self.action == "list":

            return BlockTypeListSerializer

        elif self.action == "create":

            return BlockTypeCreateSerializer

        elif self.action in ["update", "partial_update"]:

            return BlockTypeUpdateSerializer

        return BlockTypeSerializer

    def perform_create(self, serializer):
        """Set creator when creating block type."""

        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        """Set updater when updating block type."""

        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete by deactivating instead of hard delete."""

        instance.is_active = False

        instance.save(update_fields=["is_active"])

    @extend_schema(
        summary="Get block type categories",
        description="Get all available block type categories.",
        responses={200: BlockTypeCategorySerializer(many=True)},
    )
    @action(detail=False, methods=["get"])
    def categories(self, request):
        """Get all available block type categories."""

        cache_key = "block_type_categories"

        categories = cache.get(cache_key)

        if categories is None:

            categories = BlockTypeCategorySerializer.get_categories()

            cache.set(cache_key, categories, timeout=3600)  # Cache for 1 hour

        return Response(categories)

    @extend_schema(
        summary="Toggle block type active status",
        description="Toggle the active status of a block type.",
        request=None,
        responses={
            200: {"description": "Status toggled successfully"},
            404: {"description": "Block type not found"},
        },
    )
    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        """Toggle the active status of a block type."""

        block_type = self.get_object()

        block_type.is_active = not block_type.is_active

        block_type.updated_by = request.user

        block_type.save(update_fields=["is_active", "updated_by", "updated_at"])

        return Response(
            {
                "id": block_type.id,
                "is_active": block_type.is_active,
                "message": f"Block type {block_type.label} is now {'active' if block_type.is_active else 'inactive'}",
            }
        )

    @extend_schema(
        summary="Duplicate block type",
        description="Create a copy of an existing block type with a new name.",
        request=None,
        responses={
            201: BlockTypeSerializer,
            404: {"description": "Block type not found"},
            400: {"description": "Validation error"},
        },
    )
    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Create a duplicate of an existing block type."""

        original = self.get_object()

        # Create new type name

        base_type = original.type

        counter = 1

        new_type = f"{base_type}_copy"

        while BlockType.objects.filter(type=new_type).exists():

            counter += 1

            new_type = f"{base_type}_copy_{counter}"

        # Create new component name

        base_component = original.component.replace("Block", "")

        new_component = f"{base_component}CopyBlock"

        if counter > 1:

            new_component = f"{base_component}Copy{counter}Block"

        # Create duplicate

        duplicate_data = {
            "type": new_type,
            "component": new_component,
            "label": f"{original.label} (Copy)",
            "description": original.description,
            "category": original.category,
            "icon": original.icon,
            "is_active": False,  # Start as inactive
            "preload": original.preload,
            "editing_mode": original.editing_mode,
            "schema": original.schema.copy() if original.schema else {},
            "default_props": (
                original.default_props.copy() if original.default_props else {}
            ),
            "created_by": request.user,
            "updated_by": request.user,
        }

        duplicate = BlockType.objects.create(**duplicate_data)

        serializer = BlockTypeSerializer(duplicate)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Bulk update block types",
        description="Update multiple block types at once.",
        request={
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of block type IDs to update",
                },
                "updates": {
                    "type": "object",
                    "description": "Fields to update on all selected block types",
                },
            },
        },
        responses={
            200: {"description": "Bulk update completed"},
            400: {"description": "Invalid request data"},
        },
    )
    @action(detail=False, methods=["patch"])
    def bulk_update(self, request):
        """Bulk update multiple block types."""

        ids = request.data.get("ids", [])

        updates = request.data.get("updates", {})

        if not ids or not updates:

            return Response(
                {"error": "Both ids and updates are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Filter allowed update fields

        allowed_fields = ["is_active", "category", "preload", "editing_mode"]

        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered_updates:

            return Response(
                {"error": "No valid update fields provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Add updated_by to all updates

        filtered_updates["updated_by"] = request.user

        # Perform bulk update

        updated_count = BlockType.objects.filter(id__in=ids).update(**filtered_updates)

        # Clear cache

        cache.delete("block_types_registry")

        return Response(
            {
                "updated_count": updated_count,
                "message": f"Updated {updated_count} block types",
            }
        )

    @extend_schema(
        summary="Fetch dynamic data for block",
        description="Fetch data from the configured model for a dynamic block type",
        parameters=[
            {
                "name": "block_type",
                "in": "query",
                "required": True,
                "description": "Block type identifier",
                "schema": {"type": "string"},
            },
            {
                "name": "filters",
                "in": "query",
                "required": False,
                """"description": "JSON object of filters to apply","""
                "schema": {"type": "string"},
            },
            {
                "name": "limit",
                "in": "query",
                "required": False,
                "description": "Number of items to return (for list queries)",
                "schema": {"type": "integer", "default": 10},
            },
            {
                "name": "offset",
                "in": "query",
                "required": False,
                "description": "Number of items to skip (for pagination)",
                "schema": {"type": "integer", "default": 0},
            },
            {
                "name": "ordering",
                "in": "query",
                "required": False,
                "description": "Field to order by",
                "schema": {"type": "string"},
            },
            {
                "name": "search",
                "in": "query",
                "required": False,
                "description": "Search query for text fields",
                "schema": {"type": "string"},
            },
            {
                "name": "item_id",
                "in": "query",
                "required": False,
                "description": "Specific item ID (for single queries)",
                "schema": {"type": "integer"},
            },
        ],
        responses={
            200: {"description": "Dynamic data fetched successfully"},
            400: {"description": "Invalid request parameters"},
            404: {"description": "Block type not found or has no model configured"},
        },
    )
    @action(detail=False, methods=["get"])
    def fetch_data(self, request):
        """Fetch dynamic data for a block based on its model configuration."""

        block_type_str = request.query_params.get("block_type")

        if not block_type_str:

            return Response(
                {"error": "block_type parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the block type

        try:

            block_type = BlockType.objects.get(type=block_type_str, is_active=True)

        except BlockType.DoesNotExist:

            return Response(
                {"error": f'Block type "{block_type_str}" not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if this block has a model configured

        if not block_type.model_name or block_type.data_source == "static":

            return Response(
                {"error": "This block type does not support dynamic data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the model class

        model_class = block_type.get_model_class()

        if not model_class:

            return Response(
                {"error": f"Model {block_type.model_name} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Handle different data source types

        if block_type.data_source == "single":

            # Fetch a single item

            item_id = request.query_params.get("item_id")

            if not item_id:

                return Response(
                    {"error": "item_id is required for single data source"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:

                instance = model_class.objects.get(pk=item_id)

                # Use the model's serializer if available

                serializer = self._get_model_serializer(model_class, instance)

                return Response(serializer.data)

            except model_class.DoesNotExist:

                return Response(
                    {"error": f"Item with ID {item_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        elif block_type.data_source == "list":

            # Build queryset

            queryset = block_type.get_queryset()

            if queryset is None:

                queryset = model_class.objects.all()

            # Apply filters from query parameters

            filters_str = request.query_params.get("filters")

            if filters_str:

                try:

                    filters = json.loads(filters_str)

                    queryset = queryset.filter(**filters)

                except (json.JSONDecodeError, TypeError) as e:

                    return Response(
                        {"error": f"Invalid filters format: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Apply search if provided

            search = request.query_params.get("search")

            if search and block_type.query_schema:

                search_fields = block_type.query_schema.get("search_fields", [])

                if search_fields:

                    q_objects = Q()

                    for field in search_fields:

                        q_objects |= Q(**{f"{field}__icontains": search})

                    queryset = queryset.filter(q_objects)

            # Apply ordering

            ordering = request.query_params.get("ordering")

            if ordering:

                queryset = queryset.order_by(ordering)

            elif block_type.query_schema and block_type.query_schema.get("ordering"):

                default_ordering = block_type.query_schema["ordering"][0]

                queryset = queryset.order_by(f"-{default_ordering}")

            # Apply pagination

            limit = int(request.query_params.get("limit", 10))

            offset = int(request.query_params.get("offset", 0))

            total_count = queryset.count()

            items = queryset[offset : offset + limit]

            # Serialize the results

            serializer = self._get_model_serializer(model_class, items, many=True)

            return Response(
                {
                    "count": total_count,
                    "next": offset + limit < total_count,
                    "previous": offset > 0,
                    "results": serializer.data,
                }
            )

        elif block_type.data_source == "custom":

            # For custom data sources, we'd need a custom handler

            # This could be implemented via a plugin system or custom methods

            return Response(
                {"error": "Custom data sources are not yet implemented"},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        return Response(
            {"error": "Unknown data source type"}, status=status.HTTP_400_BAD_REQUEST
        )

    def _get_model_serializer(self, model_class, instance, many=False):
        """Get the appropriate serializer for a model."""

        # Try to find a registered serializer for this model

        # For now, create a dynamic serializer

        class DynamicModelSerializer(serializers.ModelSerializer):

            class Meta:

                model = model_class

                fields = "__all__"

        return DynamicModelSerializer(instance, many=many)

    @extend_schema(
        summary="Get block type statistics",
        description="Get statistics about block types usage and distribution.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "total": {"type": "integer"},
                    "active": {"type": "integer"},
                    "inactive": {"type": "integer"},
                    "by_category": {"type": "object"},
                    "preload_enabled": {"type": "integer"},
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get statistics about block types."""

        queryset = self.get_queryset()

        total = queryset.count()

        active = queryset.filter(is_active=True).count()

        inactive = total - active

        preload_enabled = queryset.filter(preload=True).count()

        # Count by category

        by_category = {}

        for category, label in BlockTypeCategory.choices:

            by_category[category] = {
                "label": label,
                "count": queryset.filter(category=category).count(),
                "active": queryset.filter(category=category, is_active=True).count(),
            }

        return Response(
            {
                "total": total,
                "active": active,
                "inactive": inactive,
                "by_category": by_category,
                "preload_enabled": preload_enabled,
            }
        )

    @extend_schema(
        summary="Get dashboard data",
        description="Get all data needed for the blocks dashboard in a single request.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "block_types": {"type": "array"},
                    "categories": {"type": "array"},
                    "stats": {
                        "type": "object",
                        "properties": {
                            "total": {"type": "integer"},
                            "active": {"type": "integer"},
                            "inactive": {"type": "integer"},
                            "by_category": {"type": "object"},
                            "preload_enabled": {"type": "integer"},
                        },
                    },
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def dashboard_data(self, request):
        """Single endpoint for dashboard initialization with all required data."""

        # Get block types with optimized query

        queryset = self.get_queryset()

        # Serialize block types efficiently

        block_types_data = BlockTypeListSerializer(
            queryset, many=True, context={"request": request}
        ).data

        # Add user names to block types data

        for block_type in block_types_data:

            block_obj = next((b for b in queryset if b.id == block_type["id"]), None)

            if block_obj:

                block_type["created_by_name"] = (
                    block_obj.created_by.get_full_name()
                    if block_obj.created_by
                    else None
                )

                block_type["updated_by_name"] = (
                    block_obj.updated_by.get_full_name()
                    if block_obj.updated_by
                    else None
                )

        # Get categories from cache

        cache_key = "block_type_categories"

        categories = cache.get(cache_key)

        if categories is None:

            categories = BlockTypeCategorySerializer.get_categories()

            cache.set(cache_key, categories, timeout=3600)

        # Get stats with optimized aggregation

        stats = queryset.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
            preload_enabled=Count("id", filter=Q(preload=True)),
        )

        # Calculate inactive count

        stats["inactive"] = stats["total"] - stats["active"]

        # Add category counts efficiently

        stats["by_category"] = {}

        category_counts = queryset.values("category").annotate(
            count=Count("id"), active_count=Count("id", filter=Q(is_active=True))
        )

        for cat_count in category_counts:

            category = cat_count["category"]

            label = dict(BlockTypeCategory.choices).get(category, category)

            stats["by_category"][category] = {
                "label": label,
                "count": cat_count["count"],
                "active": cat_count["active_count"],
            }

        # Ensure all categories are represented

        for category, label in BlockTypeCategory.choices:

            if category not in stats["by_category"]:

                stats["by_category"][category] = {
                    "label": label,
                    "count": 0,
                    "active": 0,
                }

        return Response(
            {"block_types": block_types_data, "categories": categories, "stats": stats}
        )
