from django.db.models import Count, Q

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.blog.models import Category, Tag
from apps.cms.model_parts.category import Collection
from apps.cms.serializers.category import (
    CategorySerializer,
    CollectionSerializer,
    TagSerializer,
    datetime,
    django.utils,
    timedelta,
    timezone,
)


@extend_schema_view(

    list=extend_schema(summary="List categories", tags=["Categories"]),

    create=extend_schema(summary="Create category", tags=["Categories"]),

    retrieve=extend_schema(summary="Get category details", tags=["Categories"]),

    update=extend_schema(summary="Update category", tags=["Categories"]),

    partial_update=extend_schema(

        summary="Partially update category", tags=["Categories"]

    ),

    destroy=extend_schema(summary="Delete category", tags=["Categories"]),

)

class CategoryViewSet(viewsets.ModelViewSet):

    """ViewSet for managing categories"""



    queryset = Category.objects.all()

    serializer_class = CategorySerializer

    permission_classes = [IsAuthenticated]

    lookup_field = "id"



    def get_queryset(self):

        """Get categories with post count and filtering"""

        queryset = self.queryset



        # Filter by active status

        is_active = self.request.query_params.get("is_active")

        if is_active is not None:

            queryset = queryset.filter(is_active=is_active.lower() == "true")

        else:

            # Default to showing active categories

            queryset = queryset.filter(is_active=True)



        # Search by name

        search = self.request.query_params.get("search")

        if search:

            queryset = queryset.filter(name__icontains=search)



        return queryset.annotate(post_count=Count("posts")).order_by("name")



    def perform_create(self, serializer):

        """Create category (Blog Category model doesn't have created_by field)"""

        serializer.save()



    @extend_schema(summary="Get category tree", tags=["Categories"])

    @action(detail=False, methods=["get"])

    def tree(self, request):

        """Get hierarchical category tree"""

        # Get root categories (no parent)

        root_categories = self.get_queryset().filter(parent__isnull=True)

        serializer = self.get_serializer(root_categories, many=True)

        return Response(serializer.data)



@extend_schema_view(

    list=extend_schema(summary="List tags", tags=["Tags"]),

    create=extend_schema(summary="Create tag", tags=["Tags"]),

    retrieve=extend_schema(summary="Get tag details", tags=["Tags"]),

    update=extend_schema(summary="Update tag", tags=["Tags"]),

    partial_update=extend_schema(summary="Partially update tag", tags=["Tags"]),

    destroy=extend_schema(summary="Delete tag", tags=["Tags"]),

)

class TagViewSet(viewsets.ModelViewSet):

    """ViewSet for managing tags"""



    queryset = Tag.objects.all()

    serializer_class = TagSerializer

    permission_classes = [IsAuthenticated]

    lookup_field = "slug"



    def get_queryset(self):

        """Get tags with post count and filtering"""

        queryset = self.queryset



        # Search by name

        search = self.request.query_params.get("search")

        if search:

            queryset = queryset.filter(name__icontains=search)



        # Filter by trending (has posts in last 30 days)

        trending = self.request.query_params.get("trending")

        if trending and trending.lower() == "true":



            thirty_days_ago = timezone.now() - timedelta(days=30)

            queryset = queryset.filter(

                posts__created_at__gte=thirty_days_ago

            ).distinct()



        # Filter by popular (minimum post count)

        min_count = self.request.query_params.get("min_count")

        if min_count:

            queryset = queryset.annotate(post_count=Count("posts")).filter(

                post_count__gte=int(min_count)

            )

            return queryset.order_by("-post_count")



        return queryset.annotate(post_count=Count("posts")).order_by("name")



    def perform_create(self, serializer):

        """Create tag (Blog Tag model doesn't have created_by field)"""

        serializer.save()



    @extend_schema(summary="Get popular tags", tags=["Tags"])

    @action(detail=False, methods=["get"])

    def popular(self, request):

        """Get most popular tags"""

        limit = int(request.query_params.get("limit", 10))

        tags = self.get_queryset().order_by("-post_count")[:limit]

        serializer = self.get_serializer(tags, many=True)

        return Response(serializer.data)



    @extend_schema(summary="Get trending tags", tags=["Tags"])

    @action(detail=False, methods=["get"])

    def trending(self, request):

        """Get trending tags (with recent posts)"""



        thirty_days_ago = timezone.now() - timedelta(days=30)



        limit = int(request.query_params.get("limit", 10))

        tags = (

            self.queryset.filter(posts__created_at__gte=thirty_days_ago)

            .annotate(

                post_count=Count("posts"),

                recent_post_count=Count(

                    "posts", filter=Q(posts__created_at__gte=thirty_days_ago)

                ),

            )

            .filter(recent_post_count__gt=0)

            .order_by("-recent_post_count")[:limit]

        )



        serializer = self.get_serializer(tags, many=True)

        return Response(serializer.data)



    @extend_schema(summary="Get unused tags", tags=["Tags"])

    @action(detail=False, methods=["get"])

    def unused(self, request):

        """Get tags that have no posts"""

        unused_tags = (

            self.queryset.annotate(post_count=Count("posts"))

            .filter(post_count=0)

            .order_by("name")

        )



        serializer = self.get_serializer(unused_tags, many=True)

        return Response(serializer.data)



@extend_schema_view(

    list=extend_schema(summary="List collections", tags=["Collections"]),

    create=extend_schema(summary="Create collection", tags=["Collections"]),

    retrieve=extend_schema(summary="Get collection details", tags=["Collections"]),

    update=extend_schema(summary="Update collection", tags=["Collections"]),

    partial_update=extend_schema(

        summary="Partially update collection", tags=["Collections"]

    ),

    destroy=extend_schema(summary="Delete collection", tags=["Collections"]),

)

class CollectionViewSet(viewsets.ModelViewSet):

    """ViewSet for managing collections"""



    queryset = Collection.objects.all()

    serializer_class = CollectionSerializer

    permission_classes = [IsAuthenticated]

    lookup_field = "slug"



    def get_queryset(self):

        """Get collections with item count"""

        queryset = self.queryset



        # Filter by status if provided

        status_filter = self.request.query_params.get("status")

        if status_filter:

            queryset = queryset.filter(status=status_filter)



        # Annotate with item count (pages in collection)

        return queryset.annotate(item_count=Count("pages"))



    def perform_create(self, serializer):

        """Set created_by when creating collection"""

        # Collection model does have created_by field

        serializer.save(created_by=self.request.user)



    @extend_schema(summary="Publish collection", tags=["Collections"])

    @action(detail=True, methods=["post"])

    def publish(self, request, slug=None):

        """Publish a collection"""

        collection = self.get_object()

        collection.status = "published"

        if not collection.published_at:



            collection.published_at = timezone.now()

        collection.save()

        serializer = self.get_serializer(collection)

        return Response(serializer.data)



    @extend_schema(summary="Unpublish collection", tags=["Collections"])

    @action(detail=True, methods=["post"])

    def unpublish(self, request, slug=None):

        """Unpublish a collection"""

        collection = self.get_object()

        collection.status = "draft"

        collection.save()

        serializer = self.get_serializer(collection)

        return Response(serializer.data)



    @extend_schema(summary="Get collection items", tags=["Collections"])

    @action(detail=True, methods=["get"])

    def items(self, request, slug=None):

        """Get all items in a collection"""

        self.get_object()

        # This would return pages/posts in the collection

        # Implementation depends on how items are related to collections

        return Response(

            {

                "pages": [],  # Add page serialization here

                "posts": [],  # Add post serialization here

            }

        )
