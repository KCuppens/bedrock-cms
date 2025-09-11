"""
Async tasks for heavy operations using Celery.
"""

from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def track_view_async(self, content_type, object_id, user_id=None):
    """
    Asynchronously track view counts for any content.
    
    Args:
        content_type: String identifier for content type
        object_id: ID of the object being viewed
        user_id: Optional user ID for tracking unique views
    """
    try:
        if content_type == 'blog_post':
            from apps.blog.models import BlogPost
            from apps.blog.versioning import BlogPostViewTracker
            
            post = BlogPost.objects.get(id=object_id)
            tracker, created = BlogPostViewTracker.objects.get_or_create(
                blog_post=post,
                defaults={'view_count': 0, 'unique_view_count': 0}
            )
            tracker.increment_view(user_id=user_id)
            
        elif content_type == 'page':
            from apps.analytics.models import PageView
            from apps.cms.models import Page
            
            page = Page.objects.get(id=object_id)
            PageView.objects.create(
                page=page,
                user_id=user_id,
                viewed_at=timezone.now()
            )
        
        return {'status': 'success', 'content_type': content_type, 'object_id': object_id}
        
    except Exception as e:
        logger.error(f"Error tracking view: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def warm_cache_async(self, cache_key, callable_path, args=None, kwargs=None, timeout=600):
    """
    Warm cache asynchronously by executing a callable and storing result.
    
    Args:
        cache_key: Key to store the result
        callable_path: Import path to the callable (e.g., 'apps.cms.utils.get_page_data')
        args: Arguments for the callable
        kwargs: Keyword arguments for the callable
        timeout: Cache timeout in seconds
    """
    try:
        # Import the callable
        module_path, func_name = callable_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[func_name])
        func = getattr(module, func_name)
        
        # Execute and cache
        result = func(*(args or []), **(kwargs or {}))
        cache.set(cache_key, result, timeout)
        
        return {'status': 'success', 'cache_key': cache_key}
        
    except Exception as e:
        logger.error(f"Error warming cache: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task
def bulk_warm_cache(cache_configs):
    """
    Warm multiple cache entries in parallel.
    
    Args:
        cache_configs: List of dicts with cache configuration
    """
    results = []
    for config in cache_configs:
        warm_cache_async.delay(
            cache_key=config['key'],
            callable_path=config['callable'],
            args=config.get('args'),
            kwargs=config.get('kwargs'),
            timeout=config.get('timeout', 600)
        )
        results.append(config['key'])
    
    return {'warmed_keys': results}


@shared_task(bind=True, max_retries=3)
def process_search_index_async(self, model_label, object_id, action='update'):
    """
    Asynchronously update search index.
    
    Args:
        model_label: Label of the model (e.g., 'cms.page')
        object_id: ID of the object
        action: 'update' or 'delete'
    """
    try:
        from apps.search.services import search_service
        
        if action == 'update':
            search_service.index_object(model_label, object_id)
        elif action == 'delete':
            search_service.remove_from_index(model_label, object_id)
        
        return {'status': 'success', 'model': model_label, 'object_id': object_id, 'action': action}
        
    except Exception as e:
        logger.error(f"Error updating search index: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task
def send_email_async(to_email, subject, template_name, context):
    """
    Send email asynchronously.
    
    Args:
        to_email: Recipient email
        subject: Email subject
        template_name: Email template name
        context: Template context dictionary
    """
    try:
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        
        html_message = render_to_string(f'emails/{template_name}.html', context)
        text_message = render_to_string(f'emails/{template_name}.txt', context)
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False
        )
        
        return {'status': 'success', 'to': to_email}
        
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def generate_thumbnails_async(image_id):
    """
    Generate image thumbnails asynchronously.
    
    Args:
        image_id: ID of the image to process
    """
    try:
        from apps.files.models import File
        from PIL import Image
        import io
        
        file_obj = File.objects.get(id=image_id)
        
        # Define thumbnail sizes
        sizes = {
            'small': (150, 150),
            'medium': (300, 300),
            'large': (800, 800)
        }
        
        # Open original image
        img = Image.open(file_obj.file)
        
        for size_name, dimensions in sizes.items():
            # Create thumbnail
            thumb = img.copy()
            thumb.thumbnail(dimensions, Image.Resampling.LANCZOS)
            
            # Save to buffer
            buffer = io.BytesIO()
            thumb.save(buffer, format=img.format)
            buffer.seek(0)
            
            # Store thumbnail (implementation depends on storage backend)
            # This is a simplified example
            cache_key = f"thumb:{image_id}:{size_name}"
            cache.set(cache_key, buffer.getvalue(), timeout=86400)  # 24 hours
        
        return {'status': 'success', 'image_id': image_id, 'sizes': list(sizes.keys())}
        
    except Exception as e:
        logger.error(f"Error generating thumbnails: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_old_revisions():
    """
    Clean up old revisions to prevent database bloat.
    Keeps only the last 50 revisions per content item.
    """
    try:
        from apps.cms.versioning import PageRevision
        from apps.blog.versioning import BlogPostRevision
        from django.db.models import Count
        
        # Clean up page revisions
        pages_with_many_revisions = PageRevision.objects.values('page').annotate(
            revision_count=Count('id')
        ).filter(revision_count__gt=50)
        
        for page_data in pages_with_many_revisions:
            # Keep only the latest 50 revisions
            old_revisions = PageRevision.objects.filter(
                page_id=page_data['page']
            ).order_by('-created_at')[50:]
            
            PageRevision.objects.filter(
                id__in=[r.id for r in old_revisions]
            ).delete()
        
        # Clean up blog post revisions
        posts_with_many_revisions = BlogPostRevision.objects.values('blog_post').annotate(
            revision_count=Count('id')
        ).filter(revision_count__gt=50)
        
        for post_data in posts_with_many_revisions:
            old_revisions = BlogPostRevision.objects.filter(
                blog_post_id=post_data['blog_post']
            ).order_by('-created_at')[50:]
            
            BlogPostRevision.objects.filter(
                id__in=[r.id for r in old_revisions]
            ).delete()
        
        return {'status': 'success', 'cleaned': True}
        
    except Exception as e:
        logger.error(f"Error cleaning up revisions: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def invalidate_cache_pattern_async(pattern):
    """
    Asynchronously invalidate cache by pattern.
    
    Args:
        pattern: Cache key pattern to invalidate
    """
    try:
        from apps.core.cache import cache_manager
        cache_manager.delete_pattern(pattern)
        return {'status': 'success', 'pattern': pattern}
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def optimize_database_async():
    """
    Run database optimization tasks.
    Should be scheduled to run during low-traffic periods.
    """
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Analyze tables for query optimization (PostgreSQL)
            if 'postgresql' in connection.settings_dict['ENGINE']:
                cursor.execute("ANALYZE;")
                
                # Update table statistics
                cursor.execute("""
                    SELECT schemaname, tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                tables = cursor.fetchall()
                
                for schema, table in tables:
                    cursor.execute(f"VACUUM ANALYZE {schema}.{table};")
        
        return {'status': 'success', 'optimized': True}
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        return {'status': 'error', 'error': str(e)}