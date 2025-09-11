import logging

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class LastSeenMiddleware(MiddlewareMixin):
    """
    Middleware to update user's last_seen timestamp.

    Uses Celery tasks in production, direct update in development.
    """

    def process_request(self, request):
        """Update last_seen for authenticated users"""
        if request.user.is_authenticated:
            try:
                # Check cache to avoid too frequent updates
                cache_key = f"last_seen_queued:{request.user.id}"

                # Only update if not recently updated (1 minute throttle)
                if not cache.get(cache_key):
                    # Check if Celery is in eager mode (local development)
                    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                        # In local development, update directly but still use cache throttling
                        from django.contrib.auth import get_user_model

                        User = get_user_model()

                        # Use update() to avoid triggering signals and other overhead
                        User.objects.filter(id=request.user.id).update(
                            last_seen=timezone.now()
                        )
                        logger.debug(
                            "Updated last_seen directly for user %s", request.user.id
                        )
                    else:
                        # In production, use Celery task
                        try:
                            from .tasks import update_user_last_seen

                            update_user_last_seen.delay(request.user.id)
                            logger.debug(
                                "Queued last_seen update for user %s", request.user.id
                            )
                        except Exception:
                            # If Celery fails, update directly as fallback
                            from django.contrib.auth import get_user_model

                            User = get_user_model()
                            User.objects.filter(id=request.user.id).update(
                                last_seen=timezone.now()
                            )
                            logger.debug(
                                "Celery unavailable, updated last_seen directly for user %s",
                                request.user.id,
                            )

                    # Mark as updated in cache
                    cache.set(cache_key, True, timeout=60)

            except Exception as e:
                # Log but don't fail the request
                logger.debug("Failed to update last_seen: %s", str(e))

        return None
