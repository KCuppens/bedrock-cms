"""
Blog API views and viewsets.
"""

from datetime import datetime
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q, F
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.throttling import UserRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view

from apps.core.throttling import WriteOperationThrottle, BurstWriteThrottle, PublishOperationThrottle
from apps.i18n.models import Locale
from .models import BlogPost, Category, Tag, BlogSettings
from .serializers import (
    BlogPostSerializer, 
    BlogPostListSerializer,
    BlogPostWriteSerializer,
    BlogPostRevisionSerializer,
    BlogPostAutosaveSerializer,
    BlogPostDuplicateSerializer,
    CategorySerializer,
    TagSerializer,
    BlogSettingsSerializer
)
from .versioning import BlogPostRevision, BlogPostViewTracker


@extend_schema_view(
    list=extend_schema(description="List all blog posts with filtering and pagination"),
    create=extend_schema(description="Create a new blog post"),
    retrieve=extend_schema(description="Get a specific blog post by ID"),
    update=extend_schema(description="Update a blog post"),
    partial_update=extend_schema(description="Partially update a blog post"),
    destroy=extend_schema(description="Delete a blog post"),
)
class BlogPostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing blog posts with full CRUD operations and additional actions.
    
    Provides comprehensive blog post management including:
    - Standard CRUD operations
    - Publishing/unpublishing
    - Duplication across locales
    - Revision tracking
    - Autosave functionality
    - View count tracking
    """
    
    throttle_classes = [UserRateThrottle, WriteOperationThrottle, BurstWriteThrottle, PublishOperationThrottle]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'category', 'tags', 'author', 'locale', 'featured']
    search_fields = ['title', 'excerpt', 'content']
    ordering_fields = ['created_at', 'updated_at', 'published_at', 'title']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get queryset with optimizations and filtering."""
        from django.db.models import Prefetch
        
        # Optimize based on action
        if self.action == 'list':
            # For list view, only load essential fields
            queryset = BlogPost.objects.select_related(
                'locale', 'author', 'category'
            ).prefetch_related(
                Prefetch('tags', queryset=Tag.objects.only('id', 'name', 'slug'))
            ).defer(
                'content', 'blocks', 'seo'  # Don't load heavy fields for lists
            ).annotate(
                view_count=Count('view_tracker__view_count', distinct=True)
            )
        else:
            # For detail views, load everything
            queryset = BlogPost.objects.select_related(
                'locale', 'author', 'category', 'social_image'
            ).prefetch_related(
                'tags',
                Prefetch('revisions', queryset=BlogPostRevision.objects.order_by('-created_at')[:5])
            ).annotate(
                view_count=Count('view_tracker__view_count', distinct=True)
            )
        
        # Filter by locale if specified
        locale_code = self.request.query_params.get('locale')
        if locale_code:
            queryset = queryset.filter(locale__code=locale_code)
        
        # Public API - only show published posts for non-authenticated users
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(status='published')
        
        return queryset
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return BlogPostWriteSerializer
        elif self.action == 'list':
            return BlogPostListSerializer
        elif self.action == 'autosave':
            return BlogPostAutosaveSerializer
        elif self.action == 'duplicate':
            return BlogPostDuplicateSerializer
        elif self.action == 'revisions':
            return BlogPostRevisionSerializer
        return BlogPostSerializer
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['list', 'retrieve']:
            # Read operations - public for published posts, authenticated for drafts
            return [AllowAny()]
        elif self.action in ['publish', 'unpublish']:
            # Publish operations require special permission
            return [IsAuthenticated(), permissions.DjangoModelPermissions()]
        else:
            # Write operations require authentication
            return [IsAuthenticated(), permissions.DjangoModelPermissions()]
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a blog post and track view count."""
        instance = self.get_object()
        
        # Track view count asynchronously for published posts
        if instance.status == 'published':
            from apps.core.tasks import track_view_async
            # Defer view tracking to background task
            track_view_async.delay(
                content_type='blog_post',
                object_id=instance.id,
                user_id=request.user.id if request.user.is_authenticated else None
            )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """Set author and create initial revision on create."""
        # Set author to current user if not specified
        blog_post = serializer.save(author=self.request.user)
        
        # Create initial revision
        BlogPostRevision.create_snapshot(
            blog_post=blog_post,
            user=self.request.user,
            comment="Initial creation"
        )
    
    def perform_update(self, serializer):
        """Create revision on update."""
        blog_post = serializer.save()
        
        # Create revision for significant updates (not autosaves)
        BlogPostRevision.create_snapshot(
            blog_post=blog_post,
            user=self.request.user,
            comment="Manual update"
        )
    
    @extend_schema(
        methods=['post'],
        description="Publish a blog post",
        request=None,
        responses={200: BlogPostSerializer}
    )
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a blog post."""
        blog_post = self.get_object()
        
        if blog_post.status == 'published':
            return Response(
                {'error': 'Blog post is already published'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        blog_post.status = 'published'
        blog_post.published_at = timezone.now()
        blog_post.scheduled_publish_at = None  # Clear any scheduled date
        blog_post.save()
        
        # Create published snapshot
        BlogPostRevision.create_snapshot(
            blog_post=blog_post,
            user=request.user,
            is_published=True,
            comment="Published via API"
        )
        
        serializer = BlogPostSerializer(blog_post)
        return Response(serializer.data)
    
    @extend_schema(
        methods=['post'],
        description="Unpublish a blog post",
        request=None,
        responses={200: BlogPostSerializer}
    )
    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """Unpublish a blog post."""
        blog_post = self.get_object()
        
        if blog_post.status != 'published':
            return Response(
                {'error': 'Blog post is not published'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        blog_post.status = 'draft'
        blog_post.save()
        
        # Create revision
        BlogPostRevision.create_snapshot(
            blog_post=blog_post,
            user=request.user,
            comment="Unpublished via API"
        )
        
        serializer = BlogPostSerializer(blog_post)
        return Response(serializer.data)
    
    @extend_schema(
        methods=['post'],
        description="Duplicate a blog post to another locale or within the same locale",
        request=BlogPostDuplicateSerializer,
        responses={201: BlogPostSerializer}
    )
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a blog post."""
        source_post = self.get_object()
        serializer = BlogPostDuplicateSerializer(data=request.data)
        
        if serializer.is_valid():
            target_locale = serializer.validated_data['locale']
            new_title = serializer.validated_data['title']
            copy_tags = serializer.validated_data['copy_tags']
            copy_category = serializer.validated_data['copy_category']
            
            # Create new blog post
            with transaction.atomic():
                new_post = BlogPost.objects.create(
                    locale=target_locale,
                    title=new_title,
                    slug=slugify(new_title),
                    excerpt=source_post.excerpt,
                    content=source_post.content,
                    blocks=source_post.blocks,
                    seo=source_post.seo.copy() if source_post.seo else {},
                    author=request.user,
                    category=source_post.category if copy_category else None,
                    status='draft',  # Always create as draft
                    featured=False,  # Don't copy featured status
                    allow_comments=source_post.allow_comments,
                    social_image=source_post.social_image
                )
                
                # Copy tags if requested
                if copy_tags and source_post.tags.exists():
                    # Find equivalent tags in target locale or create them
                    for tag in source_post.tags.all():
                        # Try to find existing tag with same name
                        target_tag, created = Tag.objects.get_or_create(
                            name=tag.name,
                            defaults={
                                'description': tag.description,
                                'is_active': tag.is_active
                            }
                        )
                        new_post.tags.add(target_tag)
                
                # Create initial revision
                BlogPostRevision.create_snapshot(
                    blog_post=new_post,
                    user=request.user,
                    comment=f"Duplicated from post ID {source_post.id}"
                )
            
            response_serializer = BlogPostSerializer(new_post)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        methods=['get'],
        description="Get revision history for a blog post",
        responses={200: BlogPostRevisionSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def revisions(self, request, pk=None):
        """Get revision history for a blog post."""
        blog_post = self.get_object()
        revisions = BlogPostRevision.objects.filter(blog_post=blog_post).select_related('created_by')
        
        # Pagination
        page = self.paginate_queryset(revisions)
        if page is not None:
            serializer = BlogPostRevisionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = BlogPostRevisionSerializer(revisions, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        methods=['post'],
        description="Autosave blog post content",
        request=BlogPostAutosaveSerializer,
        responses={200: {'type': 'object', 'properties': {'success': {'type': 'boolean'}}}}
    )
    @action(detail=True, methods=['post'])
    def autosave(self, request, pk=None):
        """Autosave blog post content."""
        blog_post = self.get_object()
        serializer = BlogPostAutosaveSerializer(data=request.data)
        
        if serializer.is_valid():
            # Update fields that were provided
            updated_fields = []
            for field, value in serializer.validated_data.items():
                if hasattr(blog_post, field):
                    setattr(blog_post, field, value)
                    updated_fields.append(field)
            
            if updated_fields:
                blog_post.save(update_fields=updated_fields + ['updated_at'])
                
                # Create autosave revision
                BlogPostRevision.create_snapshot(
                    blog_post=blog_post,
                    user=request.user,
                    is_autosave=True,
                    comment="Autosave"
                )
            
            return Response({'success': True})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        methods=['post'],
        description="Revert blog post to a specific revision",
        parameters=[OpenApiParameter('revision_id', str, description='Revision ID to revert to')],
        responses={200: BlogPostSerializer}
    )
    @action(detail=True, methods=['post'], url_path='revert/(?P<revision_id>[^/.]+)')
    def revert(self, request, pk=None, revision_id=None):
        """Revert blog post to a specific revision."""
        blog_post = self.get_object()
        
        try:
            revision = BlogPostRevision.objects.get(
                id=revision_id,
                blog_post=blog_post
            )
        except BlogPostRevision.DoesNotExist:
            return Response(
                {'error': 'Revision not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Restore the revision
        restored_post = revision.restore_to_blog_post(user=request.user)
        
        serializer = BlogPostSerializer(restored_post)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(description="List all blog categories"),
    create=extend_schema(description="Create a new blog category"),
    retrieve=extend_schema(description="Get a specific blog category"),
    update=extend_schema(description="Update a blog category"),
    destroy=extend_schema(description="Delete a blog category"),
)
class BlogCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing blog categories."""
    
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Get categories with post counts."""
        return Category.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published'))
        )
    
    def get_permissions(self):
        """Public read access, authenticated write access."""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), permissions.DjangoModelPermissions()]


@extend_schema_view(
    list=extend_schema(description="List all blog tags"),
    create=extend_schema(description="Create a new blog tag"),
    retrieve=extend_schema(description="Get a specific blog tag"),
    update=extend_schema(description="Update a blog tag"),
    destroy=extend_schema(description="Delete a blog tag"),
)
class BlogTagViewSet(viewsets.ModelViewSet):
    """ViewSet for managing blog tags."""
    
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Get tags with post counts."""
        return Tag.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published'))
        )
    
    def get_permissions(self):
        """Public read access, authenticated write access."""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), permissions.DjangoModelPermissions()]


@extend_schema_view(
    list=extend_schema(description="List blog settings for all locales"),
    retrieve=extend_schema(description="Get blog settings for a specific locale"),
    update=extend_schema(description="Update blog settings for a locale"),
    create=extend_schema(description="Create blog settings for a locale"),
)
class BlogSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for managing blog settings per locale."""
    
    serializer_class = BlogSettingsSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'locale__code'
    lookup_url_kwarg = 'locale_code'
    
    def get_queryset(self):
        """Get blog settings with related data."""
        return BlogSettings.objects.select_related(
            'locale', 'default_presentation_page'
        )
    
    def get_object(self):
        """Get or create blog settings for a locale."""
        locale_code = self.kwargs.get('locale_code')
        if locale_code:
            locale = get_object_or_404(Locale, code=locale_code)
            obj, created = BlogSettings.objects.get_or_create(
                locale=locale,
                defaults={
                    'base_path': 'blog',
                    'show_toc': True,
                    'show_author': True,
                    'show_dates': True,
                    'show_share': True,
                    'show_reading_time': True,
                }
            )
            return obj
        return super().get_object()
    
    def perform_create(self, serializer):
        """Ensure locale is set when creating."""
        locale_code = self.kwargs.get('locale_code')
        if locale_code:
            locale = get_object_or_404(Locale, code=locale_code)
            serializer.save(locale=locale)
        else:
            serializer.save()


# Legacy function-based views for backwards compatibility
from rest_framework.decorators import api_view, permission_classes

@api_view(['GET', 'POST', 'PATCH', 'PUT'])
@permission_classes([IsAuthenticated, IsAdminUser])
def blog_settings_api(request, locale_code=None):
    """
    Legacy API for blog settings.
    
    GET /api/v1/blog/settings/{locale_code}/
    POST /api/v1/blog/settings/{locale_code}/
    PATCH /api/v1/blog/settings/{locale_code}/
    PUT /api/v1/blog/settings/{locale_code}/
    """
    if locale_code:
        locale = get_object_or_404(Locale, code=locale_code)
    else:
        # Default to first active locale if none specified
        locale = Locale.objects.filter(is_active=True).first()
        if not locale:
            return Response(
                {'error': 'No active locales found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    if request.method == 'GET':
        try:
            settings = BlogSettings.objects.get(locale=locale)
            serializer = BlogSettingsSerializer(settings)
            return Response(serializer.data)
        except BlogSettings.DoesNotExist:
            # Return default settings structure
            return Response({
                'locale': locale.code,
                'base_path': 'blog',
                'default_presentation_page': None,
                'design_tokens': {},
                'show_toc': True,
                'show_author': True,
                'show_dates': True,
                'show_share': True,
                'show_reading_time': True,
                'feeds_config': {},
                'seo_defaults': {}
            })
    
    elif request.method in ['POST', 'PATCH', 'PUT']:
        try:
            settings = BlogSettings.objects.get(locale=locale)
            # For PATCH, allow partial updates
            partial = request.method == 'PATCH'
            serializer = BlogSettingsSerializer(settings, data=request.data, partial=partial)
        except BlogSettings.DoesNotExist:
            # Create new settings
            data = request.data.copy()
            data['locale'] = locale.id
            serializer = BlogSettingsSerializer(data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(
                {'errors': serializer.errors, 'method': request.method, 'locale': locale.code}, 
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def blog_settings_list(request):
    """
    Legacy API to list all blog settings across locales.
    
    GET /api/v1/blog/settings/
    """
    settings = BlogSettings.objects.select_related(
        'locale', 'default_presentation_page'
    ).all()
    
    serializer = BlogSettingsSerializer(settings, many=True)
    return Response(serializer.data)