# Performance Optimization Guide

This guide provides actionable steps to optimize Bedrock CMS performance for production deployments.

## Quick Performance Checklist

### ✅ Essential Optimizations (Must Do)

- [ ] **Setup Redis Cache**
  ```bash
  # Install Redis
  docker run -d -p 6379:6379 --name redis redis:alpine
  
  # Verify connection
  redis-cli ping  # Should return PONG
  ```

- [ ] **Add Database Indexes**
  ```python
  # Create migration
  python manage.py makemigrations --empty your_app_name
  
  # Add to migration file:
  from django.db import migrations
  
  class Migration(migrations.Migration):
      operations = [
          migrations.RunSQL("CREATE INDEX idx_page_path ON cms_page(path);"),
          migrations.RunSQL("CREATE INDEX idx_page_group_locale ON cms_page(group_id, locale_id);"),
          migrations.RunSQL("CREATE INDEX idx_blogpost_slug ON blog_blogpost(slug);"),
          migrations.RunSQL("CREATE INDEX idx_asset_checksum ON media_asset(checksum);"),
      ]
  ```

- [ ] **Configure Caching**
  ```python
  # settings/production.py
  CACHES = {
      'default': {
          'BACKEND': 'django_redis.cache.RedisCache',
          'LOCATION': 'redis://127.0.0.1:6379/1',
          'TIMEOUT': 300,
          'OPTIONS': {
              'CLIENT_CLASS': 'django_redis.client.DefaultClient',
          }
      }
  }
  ```

### 🔧 Performance Optimizations (Should Do)

- [ ] **Implement Query Optimization**
- [ ] **Add API Pagination** 
- [ ] **Setup CDN for Static Files**
- [ ] **Configure Database Connection Pooling**
- [ ] **Implement Application-Level Caching**

## Detailed Implementation Guide

### 1. Redis Cache Setup

**Docker Deployment:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

**Local Development:**
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis-server

# Windows
choco install redis-64
```

**Django Configuration:**
```python
# settings/base.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'TIMEOUT': 300,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 20,
                'retry_on_timeout': True,
            }
        }
    }
}

# Session storage
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

### 2. Database Optimization

**Index Creation Migration:**
```python
# apps/core/migrations/XXXX_add_performance_indexes.py
from django.db import migrations

class Migration(migrations.Migration):
    
    dependencies = [
        ('cms', '0001_initial'),
        ('blog', '0001_initial'),
        ('media', '0001_initial'),
    ]

    operations = [
        # Page performance indexes
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY idx_page_path_gin ON cms_page USING gin(path gin_trgm_ops);",
            reverse_sql="DROP INDEX IF EXISTS idx_page_path_gin;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY idx_page_group_locale ON cms_page(group_id, locale_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_page_group_locale;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY idx_page_status_locale ON cms_page(status, locale_id) WHERE status = 'published';",
            reverse_sql="DROP INDEX IF EXISTS idx_page_status_locale;"
        ),
        
        # Blog performance indexes  
        migrations.RunSQL(
            "CREATE UNIQUE INDEX CONCURRENTLY idx_blogpost_slug_locale ON blog_blogpost(slug, locale_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_blogpost_slug_locale;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY idx_blogpost_published ON blog_blogpost(published_at) WHERE status = 'published';",
            reverse_sql="DROP INDEX IF EXISTS idx_blogpost_published;"
        ),
        
        # Media performance indexes
        migrations.RunSQL(
            "CREATE UNIQUE INDEX CONCURRENTLY idx_asset_checksum ON media_asset(checksum);",
            reverse_sql="DROP INDEX IF EXISTS idx_asset_checksum;"
        ),
        
        # Translation performance indexes
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY idx_translation_key_locale ON i18n_translationunit(key, target_locale, status);",
            reverse_sql="DROP INDEX IF EXISTS idx_translation_key_locale;"
        ),
    ]
```

**Query Optimization Patterns:**
```python
# Optimized Page queries
def get_published_pages_optimized():
    return Page.objects.select_related(
        'parent', 'locale'
    ).prefetch_related(
        'children'
    ).filter(
        status='published'
    ).only(
        'id', 'title', 'slug', 'path', 'parent_id', 'locale_id'
    )

# Optimized Blog queries  
def get_blog_posts_optimized():
    return BlogPost.objects.select_related(
        'category', 'locale', 'hero_asset'
    ).prefetch_related(
        'tags'
    ).filter(
        status='published'
    ).order_by('-published_at')
```

### 3. Application-Level Caching

**Page Tree Caching:**
```python
# apps/cms/utils.py
from django.core.cache import cache
from django.utils.hash import make_template_fragment_key

def get_navigation_tree_cached(locale_code):
    """Get navigation tree with caching."""
    cache_key = f'nav_tree_{locale_code}'
    tree = cache.get(cache_key)
    
    if tree is None:
        tree = build_navigation_tree(locale_code)
        cache.set(cache_key, tree, 300)  # 5 minutes
    
    return tree

def invalidate_navigation_cache():
    """Invalidate navigation cache for all locales."""
    locales = Locale.objects.filter(is_active=True).values_list('code', flat=True)
    for locale_code in locales:
        cache.delete(f'nav_tree_{locale_code}')
```

**API Response Caching:**
```python
# apps/cms/views.py
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

@method_decorator(cache_page(60 * 5), name='list')  # 5 minutes
class PageViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return get_published_pages_optimized()
```

**Template Fragment Caching:**
```html
<!-- templates/cms/navigation.html -->
{% load cache %}
{% cache 300 navigation request.locale.code %}
    <nav>
        {% for item in navigation_tree %}
            <a href="{{ item.path }}">{{ item.title }}</a>
        {% endfor %}
    </nav>
{% endcache %}
```

### 4. API Performance Optimization

**Pagination Configuration:**
```python
# settings/base.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 100,
}

# Custom pagination for large datasets
class LargePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
```

**Response Optimization:**
```python
# apps/cms/serializers.py
class PageListSerializer(serializers.ModelSerializer):
    """Optimized serializer for page lists."""
    
    class Meta:
        model = Page
        fields = ['id', 'title', 'slug', 'path', 'status', 'updated_at']
        
class PageDetailSerializer(serializers.ModelSerializer):
    """Full serializer for page details."""
    
    class Meta:
        model = Page
        fields = '__all__'

# apps/cms/views.py  
class PageViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return PageListSerializer
        return PageDetailSerializer
```

### 5. Static File Optimization

**Development Settings:**
```python
# settings/development.py
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
```

**Production Settings:**
```python
# settings/production.py
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# CDN Configuration
AWS_S3_CUSTOM_DOMAIN = 'cdn.example.com'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
```

**Nginx Configuration:**
```nginx
# /etc/nginx/sites-enabled/bedrock-cms
server {
    listen 80;
    server_name example.com;
    
    location /static/ {
        alias /path/to/static/files/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /path/to/media/files/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 6. Database Connection Pooling

**PostgreSQL Configuration:**
```python
# settings/production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,  # Connection pooling
        'OPTIONS': {
            'MAX_CONNS': 20,
        }
    }
}
```

**Connection Pool with django-db-pool:**
```python
# Alternative: Use django-db-pool
DATABASES = {
    'default': {
        'ENGINE': 'dj_db_conn_pool.backends.postgresql',
        'POOL_OPTIONS': {
            'POOL_SIZE': 10,
            'MAX_OVERFLOW': 10,
            'RECYCLE': 24 * 60 * 60,  # 24 hours
        }
    }
}
```

### 7. Monitoring & Profiling

**Django Debug Toolbar (Development):**
```python
# settings/development.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: True,
}
```

**Performance Monitoring:**
```python
# apps/core/middleware.py
import time
import logging

logger = logging.getLogger('performance')

class PerformanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time
        
        if duration > 1.0:  # Log slow requests
            logger.warning(
                f'Slow request: {request.path} took {duration:.2f}s'
            )
        
        response['X-Response-Time'] = f'{duration:.3f}s'
        return response
```

**Sentry Integration:**
```python
# settings/production.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,  # Performance monitoring
    send_default_pii=True
)
```

### 8. Load Testing

**Basic Load Test:**
```python
# performance_test.py
from locust import HttpUser, task, between

class CmsUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def view_pages(self):
        self.client.get("/api/pages/")
    
    @task(2)
    def view_blog(self):
        self.client.get("/api/content/blog.blogpost/")
    
    @task(1)
    def search(self):
        self.client.get("/api/search/?q=test")
```

```bash
# Run load test
locust -f performance_test.py --host=http://localhost:8000 -u 10 -r 2
```

## Performance Monitoring Checklist

### Key Metrics to Track

**API Performance:**
- [ ] Average response time < 100ms
- [ ] 95th percentile response time < 500ms  
- [ ] Error rate < 0.1%

**Database Performance:**
- [ ] Average query time < 50ms
- [ ] Slow query count < 5 per minute
- [ ] Connection pool utilization < 80%

**Cache Performance:**
- [ ] Hit rate > 80%
- [ ] Average get time < 5ms
- [ ] Cache memory usage < 80%

**System Resources:**
- [ ] CPU usage < 70%
- [ ] Memory usage < 80%
- [ ] Disk I/O wait < 10%

### Alerting Rules

**Critical Alerts:**
- API response time > 1 second for 5 minutes
- Error rate > 1% for 2 minutes
- Database connection pool exhausted
- Cache hit rate < 50% for 10 minutes

**Warning Alerts:**
- API response time > 500ms for 10 minutes
- Database slow queries > 10 per minute
- Memory usage > 85%
- Disk space < 20% free

## Troubleshooting Performance Issues

### Common Issues & Solutions

**1. Slow API Responses**
```bash
# Debug with Django Debug Toolbar
# Check for N+1 queries, missing indexes, large result sets

# Quick fix: Add pagination
# Long term: Optimize queries, add caching
```

**2. High Database Load**
```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
WHERE mean_time > 100 
ORDER BY mean_time DESC;

-- Check missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE schemaname = 'public' 
AND n_distinct > 100;
```

**3. Cache Misses**
```python
# Monitor cache performance
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

# Check cache key patterns
cache_stats = cache.get_stats()
```

**4. Memory Leaks**
```python
# Monitor memory usage
import psutil
import gc

def check_memory():
    process = psutil.Process()
    memory_info = process.memory_info()
    print(f"RSS: {memory_info.rss / 1024 / 1024:.1f}MB")
    print(f"Objects: {len(gc.get_objects())}")
```

This guide provides a comprehensive approach to optimizing Bedrock CMS performance. Implement optimizations incrementally and monitor the impact of each change.