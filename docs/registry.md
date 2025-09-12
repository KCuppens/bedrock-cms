# Content Registry System

The Content Registry allows you to register Django models for automatic API generation, admin integration, and CMS features.

## What is the Content Registry?

The Content Registry is a centralized system that:
- **Auto-generates APIs**: Creates CRUD endpoints for registered models
- **Provides Admin Integration**: Configures Django admin interfaces
- **Enables CMS Features**: Integrates models with pages and blocks
- **Supports Scaffolding**: Generates boilerplate code automatically

## Registering Models

### Basic Registration

```python
from apps.registry.registry import content_registry
from .models import BlogPost

# Basic registration
content_registry.register('blog.blogpost', BlogPost, {
    'admin_config': {
        'list_display': ['title', 'author', 'created_at'],
        'search_fields': ['title', 'content'],
        'list_filter': ['author', 'created_at'],
    },
    'api_config': {
        'serializer_fields': ['title', 'content', 'author', 'created_at'],
        'filterset_fields': ['author', 'created_at'],
        'search_fields': ['title', 'content'],
        'ordering': ['-created_at'],
    }
})
```

### Advanced Registration

```python
from apps.registry.registry import content_registry
from .models import BlogPost
from .serializers import BlogPostSerializer
from .admin import BlogPostAdmin

content_registry.register('blog.blogpost', BlogPost, {
    'label': 'Blog Post',
    'description': 'Blog posts with rich content',

    # Admin configuration
    'admin_config': {
        'admin_class': BlogPostAdmin,  # Custom admin class
        'list_display': ['title', 'author', 'status', 'created_at'],
        'list_filter': ['status', 'author', 'created_at'],
        'search_fields': ['title', 'content'],
        'readonly_fields': ['created_at', 'updated_at'],
        'ordering': ['-created_at'],
    },

    # API configuration
    'api_config': {
        'serializer_class': BlogPostSerializer,  # Custom serializer
        'viewset_class': None,  # Use default viewset
        'permission_classes': ['rest_framework.permissions.IsAuthenticated'],
        'filterset_fields': ['author', 'status', 'created_at'],
        'search_fields': ['title', 'content'],
        'ordering_fields': ['created_at', 'updated_at', 'title'],
        'ordering': ['-created_at'],
        'pagination_class': 'rest_framework.pagination.PageNumberPagination',
    },

    # CMS integration
    'cms_config': {
        'list_template': 'blog/post_list.html',
        'detail_template': 'blog/post_detail.html',
        'supports_blocks': True,
        'supports_seo': True,
    },

    # Features
    'features': {
        'versioning': True,
        'soft_delete': True,
        'search_indexing': True,
        'cache_invalidation': True,
    }
})
```

## Registry Configuration Options

### Admin Configuration

```python
'admin_config': {
    'admin_class': CustomAdminClass,         # Custom admin class
    'list_display': ['field1', 'field2'],   # Fields shown in list view
    'list_filter': ['field1', 'field2'],    # Sidebar filters
    'search_fields': ['field1', 'field2'],  # Search functionality
    'readonly_fields': ['created_at'],       # Read-only fields
    'ordering': ['-created_at'],             # Default ordering
    'list_per_page': 25,                     # Pagination
    'actions': ['custom_action'],            # Custom actions
    'fieldsets': [...],                      # Field organization
    'inlines': [InlineModelAdmin],           # Inline models
}
```

### API Configuration

```python
'api_config': {
    'serializer_class': CustomSerializer,           # Custom serializer
    'viewset_class': CustomViewSet,                 # Custom viewset
    'permission_classes': [...],                    # Permissions
    'throttle_classes': [...],                      # Rate limiting
    'filterset_class': CustomFilterSet,             # Custom filters
    'filterset_fields': ['field1', 'field2'],      # Simple filters
    'search_fields': ['field1', 'field2'],         # Search fields
    'ordering_fields': ['field1', 'field2'],       # Sortable fields
    'ordering': ['-created_at'],                    # Default ordering
    'pagination_class': CustomPagination,          # Pagination
}
```

### CMS Configuration

```python
'cms_config': {
    'list_template': 'app/model_list.html',         # List template
    'detail_template': 'app/model_detail.html',     # Detail template
    'supports_blocks': True,                        # Block content
    'supports_seo': True,                           # SEO fields
    'url_patterns': {                               # Custom URLs
        'list': 'app/models/',
        'detail': 'app/models/<slug:slug>/',
    },
}
```

## Using the Registry

### Getting Registered Models

```python
from apps.registry.registry import content_registry

# Get all registered models
all_models = content_registry.get_all_models()

# Get specific model configuration
blog_config = content_registry.get_config('blog.blogpost')

# Check if model is registered
if content_registry.is_registered('blog.blogpost'):
    print("Blog post model is registered")

# Get model class
BlogPost = content_registry.get_model_class('blog.blogpost')
```

### Registry Information

```python
# Get registry statistics
stats = content_registry.get_stats()
print(f"Registered models: {stats['total_models']}")
print(f"With API: {stats['with_api']}")
print(f"With admin: {stats['with_admin']}")

# Get models by feature
searchable_models = content_registry.get_models_with_feature('search_indexing')
versioned_models = content_registry.get_models_with_feature('versioning')
```

## Auto-Generated APIs

When you register a model, the registry automatically creates:

### CRUD Endpoints

```http
GET    /api/v1/blog/blogposts/           # List posts
POST   /api/v1/blog/blogposts/           # Create post
GET    /api/v1/blog/blogposts/{id}/      # Get post
PUT    /api/v1/blog/blogposts/{id}/      # Update post
PATCH  /api/v1/blog/blogposts/{id}/      # Partial update
DELETE /api/v1/blog/blogposts/{id}/      # Delete post
```

### Query Parameters

```http
# Filtering
GET /api/v1/blog/blogposts/?author=john&status=published

# Search
GET /api/v1/blog/blogposts/?search=django

# Ordering
GET /api/v1/blog/blogposts/?ordering=-created_at

# Pagination
GET /api/v1/blog/blogposts/?page=2&page_size=10
```

### Response Format

```json
{
  "count": 150,
  "next": "http://api.example.com/blog/posts/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Django Best Practices",
      "content": "...",
      "author": {
        "id": 1,
        "username": "john"
      },
      "status": "published",
      "created_at": "2023-01-01T10:00:00Z"
    }
  ]
}
```

## Scaffolding with Registry

### Generate Complete API

```bash
python manage.py cms_scaffold blog.blogpost --output-dir apps/blog/
```

This creates:
- `serializers.py` - DRF serializers
- `views.py` - DRF viewsets
- `urls.py` - URL patterns
- `admin.py` - Django admin configuration
- `filters.py` - django-filter FilterSets
- `permissions.py` - Custom permissions
- `tests/` - Unit tests
- `docs/` - API documentation

### Generated Files Structure

```
apps/blog/
├── serializers.py
├── views.py
├── urls.py
├── admin.py
├── filters.py
├── permissions.py
├── tests/
│   ├── test_serializers.py
│   ├── test_views.py
│   └── test_admin.py
└── docs/
    └── api.md
```

## Custom Model Integration

### Model Requirements

To work well with the registry, models should follow these patterns:

```python
from django.db import models
from apps.core.models import TimestampedModel, SluggedModel

class BlogPost(TimestampedModel, SluggedModel):
    """Blog post model."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('published', 'Published'),
            ('archived', 'Archived'),
        ],
        default='draft'
    )

    class Meta:
        db_table = 'blog_post'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return f'/blog/{self.slug}/'
```

### Registry Integration

```python
# apps/blog/apps.py
from django.apps import AppConfig

class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.blog'

    def ready(self):
        from . import registry  # Import registry configuration
```

```python
# apps/blog/registry.py
from apps.registry.registry import content_registry
from .models import BlogPost

content_registry.register('blog.blogpost', BlogPost, {
    'label': 'Blog Post',
    'admin_config': {
        'list_display': ['title', 'author', 'status', 'created_at'],
        'list_filter': ['status', 'author'],
        'search_fields': ['title', 'content'],
    },
    'api_config': {
        'serializer_fields': '__all__',
        'filterset_fields': ['author', 'status'],
        'search_fields': ['title', 'content'],
    }
})
```

## Advanced Features

### Custom Serializers

```python
from rest_framework import serializers
from .models import BlogPost

class BlogPostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    read_time = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = '__all__'

    def get_read_time(self, obj):
        words = len(obj.content.split())
        return max(1, words // 200)  # Assume 200 words per minute
```

### Custom ViewSets

```python
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import BlogPost
from .serializers import BlogPostSerializer

class BlogPostViewSet(viewsets.ModelViewSet):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'author']
    search_fields = ['title', 'content']

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            queryset = queryset.select_related('author')
        return queryset
```

### Custom Admin

```python
from django.contrib import admin
from .models import BlogPost

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'status', 'created_at']
    list_filter = ['status', 'author', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = [
        (None, {
            'fields': ['title', 'slug', 'content']
        }),
        ('Publishing', {
            'fields': ['status', 'author']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
```

## Registry Management

### Management Commands

```bash
# List all registered models
python manage.py registry_list

# Show model configuration
python manage.py registry_show blog.blogpost

# Validate registry configurations
python manage.py registry_validate

# Generate URLs for all registered models
python manage.py registry_urls
```

### Registry Health Check

```python
from apps.registry.registry import content_registry

def check_registry_health():
    """Check registry for common issues."""
    issues = []

    for label, config in content_registry._registry.items():
        # Check model exists
        try:
            model_class = content_registry.get_model_class(label)
        except ImportError:
            issues.append(f"Model {label} cannot be imported")
            continue

        # Check serializer
        if 'api_config' in config:
            serializer_class = config['api_config'].get('serializer_class')
            if serializer_class and not hasattr(serializer_class, 'Meta'):
                issues.append(f"Serializer for {label} missing Meta class")

    return issues
```

## Best Practices

### Model Design

- Use descriptive field names
- Include proper `__str__` methods
- Add `get_absolute_url` methods
- Use consistent field types
- Follow Django naming conventions

### Registry Configuration

- Keep configurations in separate files
- Use descriptive labels
- Document custom configurations
- Test generated APIs
- Validate configurations

### Performance

- Use `select_related` and `prefetch_related` in viewsets
- Add appropriate database indexes
- Configure pagination for large datasets
- Use caching for frequently accessed data

### Security

- Configure appropriate permissions
- Validate all input data
- Use proper authentication
- Implement rate limiting
- Audit API access

## Common Patterns

### Blog System

```python
# Register blog models
content_registry.register('blog.post', BlogPost, {
    'api_config': {
        'filterset_fields': ['category', 'tags', 'status'],
        'search_fields': ['title', 'content'],
        'ordering': ['-published_at'],
    }
})

content_registry.register('blog.category', Category, {
    'api_config': {
        'serializer_fields': ['name', 'slug', 'description'],
    }
})
```

### E-commerce System

```python
# Register product models
content_registry.register('shop.product', Product, {
    'api_config': {
        'filterset_fields': ['category', 'price', 'in_stock'],
        'search_fields': ['name', 'description'],
        'ordering': ['name'],
    }
})

content_registry.register('shop.order', Order, {
    'admin_config': {
        'readonly_fields': ['order_number', 'created_at'],
    },
    'api_config': {
        'permission_classes': ['rest_framework.permissions.IsAuthenticated'],
    }
})
```

## Troubleshooting

### Common Issues

1. **ImportError**: Model cannot be imported
   - Check model is in `INSTALLED_APPS`
   - Verify import paths are correct
   - Ensure models are properly defined

2. **API not generated**: Endpoints not appearing
   - Check URL configuration
   - Verify registry configuration
   - Run `python manage.py show_urls`

3. **Permission errors**: 403 Forbidden responses
   - Check permission classes
   - Verify authentication
   - Review user permissions

4. **Serializer errors**: Invalid serialization
   - Check field definitions
   - Verify relationships
   - Test serializer directly

## Related Documentation

- [API Development](api.md)
- [Django Admin](admin.md)
- [Authentication](authentication.md)
- [Permissions](permissions.md)
