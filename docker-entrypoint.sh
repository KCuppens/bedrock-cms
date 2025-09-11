#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z ${DB_HOST:-localhost} ${DB_PORT:-5432}; do
  sleep 0.1
done
echo "Database is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-localhost} ${REDIS_PORT:-6379}; do
  sleep 0.1
done
echo "Redis is ready!"

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create cache table if using database cache
python manage.py createcachetable 2>/dev/null || true

# Load initial data if specified
if [ "$LOAD_INITIAL_DATA" = "true" ]; then
    echo "Loading initial data..."
    python manage.py loaddata initial_data.json 2>/dev/null || true
fi

# Create superuser if specified
if [ "$DJANGO_SUPERUSER_EMAIL" ]; then
    python manage.py createsuperuser \
        --noinput \
        --email "$DJANGO_SUPERUSER_EMAIL" \
        2>/dev/null || true
fi

# Warm cache after deployment
if [ "$WARM_CACHE" = "true" ]; then
    echo "Warming cache..."
    python manage.py cache_warming warm --target all || true
fi

# Start Celery workers in background if enabled
if [ "$CELERY_ENABLED" = "true" ]; then
    echo "Starting Celery workers..."
    celery -A apps.config worker \
        --loglevel=info \
        --concurrency=2 \
        --queues=default,publishing,translations,maintenance \
        --detach
    
    # Start Celery beat scheduler
    celery -A apps.config beat \
        --loglevel=info \
        --scheduler django_celery_beat.schedulers:DatabaseScheduler \
        --detach
fi

# Start nginx in background for static files
if [ "$NGINX_ENABLED" = "true" ]; then
    echo "Starting nginx..."
    nginx -g 'daemon off;' &
fi

# Execute the main command
exec "$@"