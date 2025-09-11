import os

from celery import Celery
from kombu import Queue, Exchange

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.local")

app = Celery("django-saas-boilerplate")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Configure task queues with priorities
app.conf.task_routes = {
    'apps.emails.tasks.send_email_task': {'queue': 'high_priority'},
    'apps.emails.tasks.send_bulk_email_task': {'queue': 'low_priority'},
    'apps.emails.tasks.retry_failed_emails': {'queue': 'low_priority'},
    'apps.core.tasks.cleanup_expired_sessions': {'queue': 'maintenance'},
    'apps.ops.tasks.backup_database': {'queue': 'maintenance'},
}

# Define queues with different priorities
default_exchange = Exchange('default', type='direct')
high_priority_exchange = Exchange('high_priority', type='direct')
low_priority_exchange = Exchange('low_priority', type='direct')
maintenance_exchange = Exchange('maintenance', type='direct')

app.conf.task_queues = (
    Queue('default', default_exchange, routing_key='default'),
    Queue('high_priority', high_priority_exchange, routing_key='high_priority'),
    Queue('low_priority', low_priority_exchange, routing_key='low_priority'),
    Queue('maintenance', maintenance_exchange, routing_key='maintenance'),
)

# Set default queue
app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'

# Performance optimizations
app.conf.worker_prefetch_multiplier = 4  # Prefetch 4 tasks per worker
app.conf.task_acks_late = True  # Acknowledge tasks after completion
app.conf.worker_max_tasks_per_child = 1000  # Restart worker after 1000 tasks to prevent memory leaks
app.conf.task_soft_time_limit = 300  # 5 minutes soft time limit
app.conf.task_time_limit = 600  # 10 minutes hard time limit

# Result backend configuration
app.conf.result_expires = 3600  # Results expire after 1 hour
app.conf.result_compression = 'gzip'  # Compress results

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule with optimized timing
from celery.schedules import crontab

app.conf.beat_schedule = {
    "process-scheduled-publishing": {
        "task": "apps.cms.tasks.process_scheduled_publishing",
        "schedule": crontab(minute='*'),  # Run every minute
        "options": {
            "queue": "high_priority",
            "expires": 50.0,  # Expire after 50 seconds to avoid overlap
        },
    },
    "cleanup-expired-sessions": {
        "task": "apps.core.tasks.cleanup_expired_sessions",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
        "options": {
            "queue": "maintenance",
            "expires": 60.0 * 60.0 * 2.0,  # Expire after 2 hours
        },
    },
    "backup-database": {
        "task": "apps.ops.tasks.backup_database",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        "options": {
            "queue": "maintenance",
            "expires": 60.0 * 60.0 * 2.0,  # Expire after 2 hours
        },
    },
    "cleanup-old-email-logs": {
        "task": "apps.emails.tasks.cleanup_old_email_logs",
        "schedule": crontab(hour=4, minute=0),  # Daily at 4 AM
        "options": {
            "queue": "maintenance",
            "expires": 60.0 * 60.0 * 2.0,
        },
    },
    "retry-failed-emails": {
        "task": "apps.emails.tasks.retry_failed_emails",
        "schedule": crontab(minute='*/30'),  # Every 30 minutes
        "options": {
            "queue": "low_priority",
            "expires": 60.0 * 25.0,  # Expire after 25 minutes
        },
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
