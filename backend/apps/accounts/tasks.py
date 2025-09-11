"""
Celery tasks for accounts app.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(
    bind=True,
    max_retries=3,
    soft_time_limit=10,
    time_limit=30,
    queue='low',
    ignore_result=True
)
def update_user_last_seen(self, user_id):
    """
    Update user's last_seen timestamp asynchronously.
    
    Uses cache-based throttling to avoid excessive database writes.
    """
    try:
        # Check cache to avoid too frequent updates
        cache_key = f'last_seen_update:{user_id}'
        if cache.get(cache_key):
            # Skip if updated recently (within 5 minutes)
            return
        
        # Update user's last_seen
        User.objects.filter(id=user_id).update(last_seen=timezone.now())
        
        # Set cache to prevent frequent updates (5 minutes TTL)
        cache.set(cache_key, True, timeout=300)
        
        logger.debug("Updated last_seen for user %s", user_id)
        
    except User.DoesNotExist:
        logger.warning("User %s not found for last_seen update", user_id)
    except Exception as e:
        logger.error("Error updating last_seen for user %s: %s", user_id, str(e))
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


@shared_task(
    bind=True,
    max_retries=3,
    soft_time_limit=30,
    time_limit=60,
    queue='low'
)
def bulk_update_last_seen(self, user_ids):
    """
    Bulk update last_seen for multiple users.
    
    More efficient for batch processing.
    """
    try:
        now = timezone.now()
        
        # Filter out users updated recently
        cache_keys = [f'last_seen_update:{uid}' for uid in user_ids]
        cached_updates = cache.get_many(cache_keys)
        
        # Only update users not in cache
        users_to_update = [
            uid for uid in user_ids 
            if f'last_seen_update:{uid}' not in cached_updates
        ]
        
        if users_to_update:
            # Bulk update
            updated = User.objects.filter(id__in=users_to_update).update(last_seen=now)
            
            # Set cache for updated users
            cache_data = {f'last_seen_update:{uid}': True for uid in users_to_update}
            cache.set_many(cache_data, timeout=300)
            
            logger.info("Bulk updated last_seen for %s users", updated)
        
    except Exception as e:
        logger.error("Error in bulk last_seen update: %s", str(e))
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


@shared_task(
    bind=True,
    max_retries=3,
    soft_time_limit=60,
    time_limit=120,
    queue='low'
)
def cleanup_inactive_sessions(self, days=30):
    """
    Clean up sessions for inactive users.
    
    Args:
        days: Number of days of inactivity before cleanup
    """
    try:
        from django.contrib.sessions.models import Session
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find inactive users
        inactive_users = User.objects.filter(
            last_seen__lt=cutoff_date
        ).values_list('id', flat=True)
        
        # Clean up their sessions
        deleted_count = 0
        for session in Session.objects.all():
            data = session.get_decoded()
            if data.get('_auth_user_id') in map(str, inactive_users):
                session.delete()
                deleted_count += 1
        
        logger.info("Cleaned up %s sessions for inactive users", deleted_count)
        
    except Exception as e:
        logger.error("Error cleaning up inactive sessions: %s", str(e))
        raise self.retry(exc=e, countdown=2 ** self.request.retries)