# SEO System Overview

Bedrock CMS provides comprehensive SEO features including URL resolution, link management, meta tag generation, and search optimization.

## SEO Features

The SEO system includes:
- **Meta Tag Management**: Title, description, keywords, Open Graph
- **URL Resolution**: Clean URLs, redirects, canonical links
- **Link Management**: Internal link tracking and validation
- **Structured Data**: Schema.org markup generation
- **Sitemap Generation**: XML sitemaps for search engines
- **Performance Optimization**: Page speed and Core Web Vitals

## Meta Tag Management

### Page Meta Tags

```python
from apps.cms.models import Page

page = Page.objects.create(
    title="About Our Company",
    slug="about",
    meta_title="About Us - Learn About Our Mission | Company Name",
    meta_description="Discover our company's mission, values, and team. Learn how we're making a difference in the industry.",
    meta_keywords="company, about us, mission, values, team",

    # Open Graph tags
    social_title="About Our Amazing Company",
    social_description="Meet the team behind the innovation. Learn our story.",
    social_image="/media/images/about-og-image.jpg",

    # Additional SEO fields
    canonical_url="https://example.com/about/",
    robots_meta="index, follow",
    structured_data={
        "@type": "Organization",
        "name": "Company Name",
        "url": "https://example.com",
        "description": "Company description..."
    }
)
```

### Meta Tag Templates

```html
<!-- apps/cms/templates/cms/meta_tags.html -->
{% load seo_tags %}

<title>{{ page.meta_title|default:page.title }} | {{ site.name }}</title>
<meta name="description" content="{{ page.meta_description|truncate_meta_description }}">
<meta name="keywords" content="{{ page.meta_keywords }}">
<meta name="robots" content="{{ page.robots_meta|default:'index, follow' }}">

{% if page.canonical_url %}
<link rel="canonical" href="{{ page.canonical_url }}">
{% endif %}

<!-- Open Graph -->
<meta property="og:title" content="{{ page.social_title|default:page.meta_title|default:page.title }}">
<meta property="og:description" content="{{ page.social_description|default:page.meta_description }}">
<meta property="og:image" content="{{ page.social_image|default:site.default_og_image }}">
<meta property="og:url" content="{{ request.build_absolute_uri }}">
<meta property="og:type" content="website">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ page.social_title|default:page.meta_title|default:page.title }}">
<meta name="twitter:description" content="{{ page.social_description|default:page.meta_description }}">
<meta name="twitter:image" content="{{ page.social_image|default:site.default_og_image }}">

<!-- Structured Data -->
{% if page.structured_data %}
<script type="application/ld+json">
{{ page.structured_data|json_script|safe }}
</script>
{% endif %}
```

### SEO Template Tags

```python
# apps/seo/templatetags/seo_tags.py
from django import template
from django.utils.html import strip_tags
import json

register = template.Library()

@register.filter
def truncate_meta_description(value, length=160):
    """Truncate meta description to optimal length."""
    if not value:
        return ""

    clean_text = strip_tags(value)
    if len(clean_text) <= length:
        return clean_text

    return clean_text[:length-3] + "..."

@register.filter
def json_script(value):
    """Convert dict to JSON for structured data."""
    return json.dumps(value, ensure_ascii=False, indent=2)

@register.simple_tag(takes_context=True)
def absolute_url(context, path):
    """Generate absolute URL from relative path."""
    request = context.get('request')
    if request:
        return request.build_absolute_uri(path)
    return path
```

## URL Resolution System

### Clean URL Generation

```python
from django.utils.text import slugify
from apps.seo.utils import generate_unique_slug

class Page(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    path = models.CharField(max_length=500, unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self.title, Page)

        # Generate hierarchical path
        if self.parent:
            self.path = f"{self.parent.path.rstrip('/')}/{self.slug}/"
        else:
            self.path = f"/{self.slug}/" if self.slug else "/"

        super().save(*args, **kwargs)

        # Update child paths if needed
        self._update_children_paths()
```

### URL Resolution Middleware

```python
# apps/seo/middleware.py
from django.http import HttpResponsePermanentRedirect
from apps.seo.models import URLRedirect

class SEOMiddleware:
    """Middleware for SEO-related URL processing."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check for URL redirects
        redirect_url = self.check_redirects(request.path)
        if redirect_url:
            return HttpResponsePermanentRedirect(redirect_url)

        # Add trailing slash if needed
        if not request.path.endswith('/') and not request.path.startswith('/api/'):
            return HttpResponsePermanentRedirect(request.path + '/')

        response = self.get_response(request)

        # Add SEO headers
        response = self.add_seo_headers(request, response)

        return response

    def check_redirects(self, path):
        """Check for configured redirects."""
        try:
            redirect = URLRedirect.objects.get(old_path=path, is_active=True)
            return redirect.new_path
        except URLRedirect.DoesNotExist:
            return None
```

### Redirect Management

```python
from apps.seo.models import URLRedirect

# Create redirects
URLRedirect.objects.create(
    old_path="/old-page/",
    new_path="/new-page/",
    redirect_type=301,  # Permanent redirect
    is_active=True
)

# Bulk create redirects
redirects = [
    ("/old-about/", "/about/", 301),
    ("/old-contact/", "/contact/", 301),
    ("/legacy/services/", "/services/", 301),
]

for old, new, status in redirects:
    URLRedirect.objects.get_or_create(
        old_path=old,
        defaults={
            'new_path': new,
            'redirect_type': status,
            'is_active': True
        }
    )
```

## Link Management

### Internal Link Tracking

```python
from apps.seo.models import InternalLink
from apps.seo.utils import extract_internal_links

def update_page_links(page):
    """Extract and track internal links from page content."""
    # Clear existing links
    InternalLink.objects.filter(source_page=page).delete()

    # Extract links from blocks
    links = []
    for block in page.blocks:
        if block.get('type') == 'rich_text':
            content = block.get('props', {}).get('content', '')
            links.extend(extract_internal_links(content))

    # Create link records
    for link_url in links:
        try:
            target_page = Page.objects.get(path=link_url)
            InternalLink.objects.create(
                source_page=page,
                target_page=target_page,
                link_url=link_url,
                is_valid=True
            )
        except Page.DoesNotExist:
            InternalLink.objects.create(
                source_page=page,
                link_url=link_url,
                is_valid=False
            )
```

### Link Validation

```python
from apps.seo.tasks import validate_internal_links

# Celery task for link validation
@shared_task
def validate_internal_links():
    """Validate all internal links and update status."""
    invalid_links = []

    for link in InternalLink.objects.all():
        try:
            if link.target_page:
                # Check if target page still exists and is published
                if link.target_page.status != 'published':
                    link.is_valid = False
                    invalid_links.append(link)
            else:
                # Check if URL resolves to a page
                try:
                    page = Page.objects.get(path=link.link_url, status='published')
                    link.target_page = page
                    link.is_valid = True
                except Page.DoesNotExist:
                    link.is_valid = False
                    invalid_links.append(link)

            link.save()

        except Exception as e:
            link.is_valid = False
            link.save()
            invalid_links.append(link)

    return f"Validated links. Found {len(invalid_links)} invalid links."
```

### Link Report

```python
def generate_link_report():
    """Generate comprehensive link report."""
    return {
        'total_links': InternalLink.objects.count(),
        'valid_links': InternalLink.objects.filter(is_valid=True).count(),
        'invalid_links': InternalLink.objects.filter(is_valid=False).count(),
        'pages_with_broken_links': InternalLink.objects.filter(
            is_valid=False
        ).values_list('source_page__title', flat=True).distinct(),
        'most_linked_pages': InternalLink.objects.filter(
            is_valid=True
        ).values('target_page__title').annotate(
            link_count=Count('id')
        ).order_by('-link_count')[:10]
    }
```

## Structured Data

### Schema.org Integration

```python
from apps.seo.utils import generate_structured_data

def generate_page_structured_data(page):
    """Generate structured data for a page."""
    base_data = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": page.title,
        "description": page.meta_description,
        "url": page.get_absolute_url(),
        "datePublished": page.created_at.isoformat(),
        "dateModified": page.updated_at.isoformat(),
    }

    # Add organization data
    if hasattr(page, 'organization'):
        base_data["publisher"] = {
            "@type": "Organization",
            "name": page.organization.name,
            "url": page.organization.website,
        }

    # Add breadcrumb navigation
    breadcrumbs = get_page_breadcrumbs(page)
    if len(breadcrumbs) > 1:
        base_data["breadcrumb"] = {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": i + 1,
                    "name": crumb.title,
                    "item": crumb.get_absolute_url()
                }
                for i, crumb in enumerate(breadcrumbs)
            ]
        }

    return base_data
```

### Block-specific Structured Data

```python
def generate_block_structured_data(block):
    """Generate structured data for specific block types."""
    block_type = block.get('type')
    props = block.get('props', {})

    if block_type == 'faq':
        return {
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": item.get('question'),
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": item.get('answer')
                    }
                }
                for item in props.get('items', [])
            ]
        }

    elif block_type == 'gallery':
        return {
            "@type": "ImageGallery",
            "image": [
                {
                    "@type": "ImageObject",
                    "url": img.get('src'),
                    "caption": img.get('caption', ''),
                    "description": img.get('alt', '')
                }
                for img in props.get('images', [])
            ]
        }

    return None
```

## Sitemap Generation

### XML Sitemap

```python
# apps/seo/sitemaps.py
from django.contrib.sitemaps import Sitemap
from apps.cms.models import Page

class PageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5
    protocol = "https"

    def items(self):
        return Page.objects.filter(
            status='published',
            robots_meta__icontains='index'
        ).exclude(
            robots_meta__icontains='noindex'
        )

    def lastmod(self, obj):
        return obj.updated_at

    def priority(self, obj):
        if obj.path == '/':
            return 1.0
        elif obj.parent is None:
            return 0.8
        else:
            return 0.6

    def changefreq(self, obj):
        if obj.path == '/':
            return 'daily'
        elif 'blog' in obj.path:
            return 'weekly'
        else:
            return 'monthly'
```

### Sitemap URLs

```python
# urls.py
from django.contrib.sitemaps.views import sitemap
from apps.seo.sitemaps import PageSitemap

sitemaps = {
    'pages': PageSitemap,
}

urlpatterns = [
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
]
```

## Performance Optimization

### Core Web Vitals

```python
# apps/seo/performance.py
class PerformanceMiddleware:
    """Middleware to track Core Web Vitals and performance metrics."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        # Calculate server response time
        response_time = (time.time() - start_time) * 1000

        # Add performance headers
        response['Server-Timing'] = f'app;dur={response_time:.2f}'

        # Track slow pages
        if response_time > 1000:  # 1 second threshold
            self.log_slow_page(request.path, response_time)

        return response

    def log_slow_page(self, path, response_time):
        """Log slow page loads for optimization."""
        # Log to monitoring system
        pass
```

### Image Optimization

```python
from apps.seo.utils import optimize_images_in_content

def optimize_page_images(page):
    """Optimize images in page content for performance."""
    for block in page.blocks:
        if block.get('type') == 'image':
            props = block.get('props', {})
            if 'src' in props:
                props['src'] = optimize_image_url(props['src'])
                # Add lazy loading
                props['loading'] = 'lazy'
                # Add appropriate dimensions
                props['width'] = props.get('width', 'auto')
                props['height'] = props.get('height', 'auto')

        elif block.get('type') == 'rich_text':
            content = block.get('props', {}).get('content', '')
            optimized_content = optimize_images_in_content(content)
            block['props']['content'] = optimized_content
```

## SEO Analytics

### SEO Score Calculation

```python
from apps.seo.analyzer import SEOAnalyzer

def calculate_seo_score(page):
    """Calculate SEO score for a page."""
    analyzer = SEOAnalyzer(page)

    score_components = {
        'title': analyzer.check_title(),
        'meta_description': analyzer.check_meta_description(),
        'headings': analyzer.check_heading_structure(),
        'images': analyzer.check_image_alt_tags(),
        'internal_links': analyzer.check_internal_links(),
        'url_structure': analyzer.check_url_structure(),
        'content_length': analyzer.check_content_length(),
        'keyword_density': analyzer.check_keyword_density(),
    }

    total_score = sum(score_components.values()) / len(score_components)

    return {
        'total_score': round(total_score, 2),
        'components': score_components,
        'recommendations': analyzer.get_recommendations()
    }
```

### SEO Audit Report

```python
def generate_seo_audit():
    """Generate comprehensive SEO audit report."""
    pages = Page.objects.filter(status='published')

    audit_results = {
        'total_pages': pages.count(),
        'issues': {
            'missing_meta_description': pages.filter(meta_description='').count(),
            'duplicate_titles': get_duplicate_titles_count(),
            'broken_links': InternalLink.objects.filter(is_valid=False).count(),
            'missing_alt_tags': count_missing_alt_tags(),
            'slow_pages': get_slow_pages_count(),
        },
        'recommendations': [],
        'top_performing_pages': get_top_performing_pages(),
        'improvement_opportunities': get_improvement_opportunities()
    }

    return audit_results
```

## Search Console Integration

### Google Search Console API

```python
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

class SearchConsoleIntegration:
    def __init__(self, service_account_file, site_url):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            service_account_file,
            ['https://www.googleapis.com/auth/webmasters.readonly']
        )
        self.service = build('webmasters', 'v3', credentials=credentials)
        self.site_url = site_url

    def get_search_analytics(self, start_date, end_date):
        """Get search analytics data."""
        request = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['page', 'query'],
            'rowLimit': 1000
        }

        response = self.service.searchanalytics().query(
            siteUrl=self.site_url,
            body=request
        ).execute()

        return response.get('rows', [])

    def get_indexing_status(self, url):
        """Check indexing status of a URL."""
        request_body = {'inspectionUrl': url}

        response = self.service.urlInspection().index().inspect(
            siteUrl=self.site_url,
            body=request_body
        ).execute()

        return response
```

## API Integration

### SEO API Endpoints

```python
# apps/seo/urls.py
urlpatterns = [
    path('seo/analyze/<int:page_id>/', SEOAnalysisView.as_view()),
    path('seo/sitemap/', SitemapView.as_view()),
    path('seo/redirects/', RedirectListView.as_view()),
    path('seo/links/validate/', LinkValidationView.as_view()),
]
```

### SEO Analysis API

```http
POST /api/v1/seo/analyze/123/
{
  "analysis_type": "full",
  "include_recommendations": true
}

Response:
{
  "page_id": 123,
  "seo_score": 85,
  "analysis": {
    "title": {
      "score": 90,
      "issues": [],
      "recommendations": ["Consider adding brand name"]
    },
    "meta_description": {
      "score": 85,
      "issues": ["Length could be optimized"],
      "recommendations": ["Add call-to-action"]
    }
  },
  "recommendations": [
    "Improve meta description length",
    "Add more internal links",
    "Optimize images with alt tags"
  ]
}
```

## Management Commands

### SEO Management Commands

```bash
# Generate sitemap
python manage.py generate_sitemap

# Analyze all pages
python manage.py seo_analyze --all

# Validate internal links
python manage.py validate_links

# Check for duplicate content
python manage.py check_duplicates

# Update structured data
python manage.py update_structured_data

# SEO audit report
python manage.py seo_audit --output=report.json
```

## Best Practices

### URL Structure

- Use descriptive, keyword-rich URLs
- Keep URLs short and readable
- Use hyphens to separate words
- Maintain consistent URL patterns
- Implement proper redirects for changed URLs

### Meta Tags

- Write unique, descriptive titles (50-60 characters)
- Create compelling meta descriptions (150-160 characters)
- Use relevant keywords naturally
- Include brand name in titles
- Optimize for social media sharing

### Content Optimization

- Use proper heading hierarchy (H1, H2, H3)
- Include relevant keywords naturally
- Write for users first, search engines second
- Ensure content is substantial and valuable
- Use internal linking strategically

### Technical SEO

- Ensure fast page load times
- Implement proper redirects
- Use structured data markup
- Create comprehensive sitemaps
- Monitor and fix broken links

### Performance

- Optimize images with proper alt tags
- Minimize HTTP requests
- Use caching strategies
- Implement lazy loading
- Monitor Core Web Vitals

## Common Issues

### Duplicate Content

```python
def find_duplicate_content():
    """Find pages with duplicate title or meta description."""
    duplicates = []

    # Check duplicate titles
    title_counts = Page.objects.values('title').annotate(
        count=Count('id')
    ).filter(count__gt=1)

    for item in title_counts:
        pages = Page.objects.filter(title=item['title'])
        duplicates.append({
            'type': 'title',
            'value': item['title'],
            'pages': list(pages.values('id', 'path'))
        })

    return duplicates
```

### Missing Meta Tags

```python
def find_missing_meta_tags():
    """Find pages missing essential meta tags."""
    return {
        'missing_title': Page.objects.filter(
            Q(title='') | Q(title__isnull=True)
        ).count(),
        'missing_description': Page.objects.filter(
            Q(meta_description='') | Q(meta_description__isnull=True)
        ).count(),
        'missing_og_image': Page.objects.filter(
            Q(social_image='') | Q(social_image__isnull=True)
        ).count()
    }
```

## Related Documentation

- [Pages System](pages.md)
- [Block System](blocks.md)
- [URL Routing](routing.md)
- [Performance Optimization](performance.md)
