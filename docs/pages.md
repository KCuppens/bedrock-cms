# Page System Overview

The Bedrock CMS page system provides hierarchical content management with flexible routing, tree structures, and mutations.

## What are Pages?

Pages are the primary content type in Bedrock CMS with:
- **Hierarchical Structure**: Parent-child relationships forming a tree
- **Flexible Routing**: URL patterns and path resolution
- **Block Content**: Structured content using the block system
- **SEO Integration**: Meta tags, social sharing, and search optimization
- **Multi-language Support**: Translation units and locale fallbacks

## Page Model

```python
from apps.cms.models import Page

page = Page.objects.create(
    title="About Us",
    slug="about",
    path="/about/",
    status="published",
    blocks=[
        {
            "type": "hero",
            "props": {
                "title": "About Our Company",
                "subtitle": "Learn about our mission"
            }
        }
    ]
)
```

## Page Structure

### Core Fields

- **title**: Page display title
- **slug**: URL-friendly identifier
- **path**: Full URL path (auto-generated for nested pages)
- **status**: `draft`, `published`, `archived`
- **blocks**: JSON array of content blocks
- **parent**: Reference to parent page (for hierarchy)
- **order**: Sort order within siblings
- **template**: Template name for custom rendering

### Metadata Fields

- **meta_title**: SEO title tag
- **meta_description**: SEO meta description
- **meta_keywords**: SEO keywords
- **social_title**: Open Graph title
- **social_description**: Open Graph description
- **social_image**: Open Graph image

## Tree Structure

Pages form a hierarchical tree structure:

```
/                    (Home)
├── /about/          (About)
├── /services/       (Services)
│   ├── /services/web-design/
│   └── /services/consulting/
└── /contact/        (Contact)
```

### Working with Tree Structure

```python
from apps.cms.models import Page

# Get root pages (no parent)
root_pages = Page.objects.filter(parent=None)

# Get children of a page
about_page = Page.objects.get(slug="about")
children = about_page.children.all()

# Get full path hierarchy
def get_breadcrumbs(page):
    breadcrumbs = []
    current = page
    while current:
        breadcrumbs.insert(0, current)
        current = current.parent
    return breadcrumbs

# Build navigation tree
def build_nav_tree():
    return Page.objects.filter(
        parent=None, 
        status="published"
    ).prefetch_related('children')
```

## Path Resolution

Page paths are automatically generated based on the tree structure:

- Root page: `/`
- Top-level pages: `/{slug}/`
- Nested pages: `/{parent_path}/{slug}/`

### Path Generation

```python
class Page(models.Model):
    def save(self, *args, **kwargs):
        # Auto-generate path from hierarchy
        if self.parent:
            self.path = f"{self.parent.path.rstrip('/')}/{self.slug}/"
        else:
            self.path = f"/{self.slug}/" if self.slug else "/"
        
        super().save(*args, **kwargs)
        
        # Update children paths if this page's path changed
        self._update_children_paths()
```

### URL Patterns

```python
# urls.py
from apps.cms.views import PageDetailView

urlpatterns = [
    # Catch-all pattern for pages (should be last)
    re_path(r'^(?P<path>.*)/$', PageDetailView.as_view(), name='page_detail'),
]
```

## Page Mutations

The system supports various mutations for page management:

### Create Page

```python
from apps.cms.mutations import PageMutations

page_data = {
    "title": "New Page",
    "slug": "new-page",
    "parent_id": 1,  # Optional
    "blocks": [
        {
            "type": "rich_text",
            "props": {"content": "<p>Welcome to our new page!</p>"}
        }
    ]
}

page = PageMutations.create_page(page_data)
```

### Update Page

```python
updates = {
    "title": "Updated Title",
    "status": "published",
    "blocks": [
        # Updated blocks
    ]
}

PageMutations.update_page(page.id, updates)
```

### Move Page

```python
# Move page to new parent (updates paths automatically)
PageMutations.move_page(page.id, new_parent_id=2)

# Reorder within siblings
PageMutations.reorder_page(page.id, new_order=1)
```

### Delete Page

```python
# Soft delete (archives the page)
PageMutations.archive_page(page.id)

# Hard delete (also handles children)
PageMutations.delete_page(page.id, cascade=True)
```

## Page Templates

Pages can use custom templates for different layouts:

```python
class Page(models.Model):
    TEMPLATE_CHOICES = [
        ('default', 'Default'),
        ('landing', 'Landing Page'),
        ('article', 'Article'),
        ('gallery', 'Gallery'),
    ]
    
    template = models.CharField(
        max_length=50,
        choices=TEMPLATE_CHOICES,
        default='default'
    )
```

### Template Rendering

```python
# views.py
class PageDetailView(DetailView):
    model = Page
    
    def get_template_names(self):
        page = self.get_object()
        return [
            f'cms/page_{page.template}.html',
            'cms/page_default.html',
        ]
```

## API Usage

### Page List API

```http
GET /api/v1/cms/pages/
```

```json
{
  "results": [
    {
      "id": 1,
      "title": "Home",
      "slug": "",
      "path": "/",
      "status": "published",
      "parent": null,
      "children_count": 3,
      "blocks": [...]
    }
  ]
}
```

### Page Detail API

```http
GET /api/v1/cms/pages/1/
```

```json
{
  "id": 1,
  "title": "About Us",
  "slug": "about",
  "path": "/about/",
  "status": "published",
  "meta_title": "About Us - Company Name",
  "meta_description": "Learn about our company...",
  "blocks": [
    {
      "type": "hero",
      "props": {
        "title": "About Our Company"
      }
    }
  ],
  "breadcrumbs": [
    {"title": "Home", "path": "/"},
    {"title": "About Us", "path": "/about/"}
  ]
}
```

### Create Page API

```http
POST /api/v1/cms/pages/
{
  "title": "New Page",
  "slug": "new-page",
  "parent": 1,
  "status": "draft",
  "blocks": [...]
}
```

## Navigation Building

### Site Navigation

```python
from apps.cms.models import Page

def build_navigation():
    """Build site navigation from page tree."""
    nav_items = []
    root_pages = Page.objects.filter(
        parent=None,
        status="published"
    ).order_by('order', 'title')
    
    for page in root_pages:
        nav_item = {
            'title': page.title,
            'path': page.path,
            'children': []
        }
        
        # Add children (limit depth as needed)
        for child in page.children.filter(status="published"):
            nav_item['children'].append({
                'title': child.title,
                'path': child.path,
            })
        
        nav_items.append(nav_item)
    
    return nav_items
```

### Breadcrumb Navigation

```python
def get_page_breadcrumbs(page):
    """Get breadcrumb navigation for a page."""
    breadcrumbs = []
    current = page
    
    while current:
        breadcrumbs.insert(0, {
            'title': current.title,
            'path': current.path,
            'is_current': current == page
        })
        current = current.parent
    
    return breadcrumbs
```

## Performance Considerations

### Tree Queries

```python
# Use select_related for parent relationships
pages = Page.objects.select_related('parent').filter(status="published")

# Use prefetch_related for children
nav_pages = Page.objects.prefetch_related('children').filter(parent=None)

# Use annotation for children counts
pages_with_counts = Page.objects.annotate(
    children_count=Count('children')
)
```

### Caching

```python
from django.core.cache import cache

def get_navigation_cached():
    """Get navigation with caching."""
    cache_key = 'site_navigation'
    nav = cache.get(cache_key)
    
    if nav is None:
        nav = build_navigation()
        cache.set(cache_key, nav, 300)  # 5 minutes
    
    return nav

# Invalidate cache when pages change
def invalidate_navigation_cache():
    cache.delete('site_navigation')
```

## Common Patterns

### Landing Pages

```python
# Create a standalone landing page
landing_page = Page.objects.create(
    title="Special Offer",
    slug="special-offer",
    template="landing",
    blocks=[
        {
            "type": "hero",
            "props": {
                "title": "Limited Time Offer!",
                "cta_text": "Get Started Now"
            }
        },
        {
            "type": "cta_band",
            "props": {
                "title": "Don't Miss Out",
                "cta_url": "/signup/"
            }
        }
    ]
)
```

### Article Pages

```python
# Create article-style pages
article = Page.objects.create(
    title="How to Build a Website",
    slug="how-to-build-website",
    parent=blog_section,
    template="article",
    meta_description="Learn how to build a website...",
    blocks=[
        {
            "type": "rich_text",
            "props": {
                "content": "<p>Building a website involves...</p>"
            }
        }
    ]
)
```

## Best Practices

- **Keep URLs Simple**: Use clear, descriptive slugs
- **Maintain Hierarchy**: Organize content logically
- **SEO Optimization**: Always set meta titles and descriptions
- **Performance**: Use select_related and prefetch_related
- **Caching**: Cache navigation and frequently accessed pages
- **Validation**: Validate block content before saving
- **Migration**: Plan URL structure changes carefully

## Common Issues

### Path Conflicts

```python
# Prevent duplicate paths
def clean_path(self):
    if Page.objects.filter(path=self.path).exclude(pk=self.pk).exists():
        raise ValidationError("A page with this path already exists")
```

### Circular References

```python
def clean_parent(self):
    if self.parent == self:
        raise ValidationError("A page cannot be its own parent")
    
    # Check for circular references
    current = self.parent
    while current:
        if current == self:
            raise ValidationError("Circular reference detected")
        current = current.parent
```

### Deep Nesting

Consider limiting tree depth for performance:

```python
MAX_DEPTH = 5

def clean_parent(self):
    depth = 0
    current = self.parent
    while current:
        depth += 1
        if depth >= MAX_DEPTH:
            raise ValidationError(f"Maximum depth of {MAX_DEPTH} exceeded")
        current = current.parent
```

## Related Documentation

- [Block System](blocks.md)
- [SEO Integration](seo.md)
- [Internationalization](i18n.md)
- [Content Registry](registry.md)