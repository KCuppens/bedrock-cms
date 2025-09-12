"""
Management command to scaffold CRUD API endpoints for registered models.
"""

from pathlib import Path

import inflection
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.template import Context, Template

from apps.registry.registry import content_registry


class Command(BaseCommand):
    help = "Generate CRUD API endpoints for a registered model"

    def add_arguments(self, parser):
        parser.add_argument(
            "model_label",
            type=str,
            help='Model label in format "app.Model" (e.g., "blog.BlogPost")',
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default=".",
            help="Output directory for generated files (default: current directory)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating files",
        )
        parser.add_argument(
            "--force", action="store_true", help="Overwrite existing files"
        )

    def handle(self, *args, **options):
        model_label = options["model_label"]
        output_dir = Path(options["output_dir"])
        dry_run = options["dry_run"]
        force = options["force"]

        # Validate model label format
        if "." not in model_label:
            raise CommandError('Model label must be in format "app.Model"')

        app_label, model_name = model_label.split(".", 1)

        # Get the model
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            raise CommandError(f"Model {model_label} not found")

        # Check if model is registered in content registry
        config = content_registry.get_config(model_label)
        if not config:
            raise CommandError(
                f"Model {model_label} is not registered in content registry. Register it first."
            )

        # Generate context for templates
        context = self._build_context(model, config, app_label, model_name)

        self.stdout.write(
            self.style.SUCCESS(f"Scaffolding API endpoints for {model_label}")
        )

        if dry_run:
            self._show_dry_run(context, output_dir)
            return

        try:
            # Create serializers file
            self._create_serializers_file(context, output_dir, force)

            # Create views file
            self._create_views_file(context, output_dir, force)

            # Create URLs file
            self._create_urls_file(context, output_dir, force)

            # Create admin integration
            self._create_admin_file(context, output_dir, force)

            # Create basic documentation
            self._create_docs_file(context, output_dir, force)

            self.stdout.write(
                self.style.SUCCESS(f"Successfully scaffolded API for {model_label}")
            )
            self._show_next_steps(context)

        except Exception as e:
            raise CommandError(f"Failed to scaffold API: {e}")

    def _build_context(self, model, config, app_label, model_name):
        """Build template context from model and config."""
        # Get model fields for serializer
        fields = []
        for field in model._meta.get_fields():
            if not field.many_to_many and not (field.one_to_many or field.one_to_one):
                field_info = {
                    "name": field.name,
                    "type": field.__class__.__name__,
                    "required": not field.null
                    and not field.blank
                    and not hasattr(field, "default"),
                    "help_text": getattr(field, "help_text", "")
                    or f"{field.name} field",
                }
                fields.append(field_info)

        return {
            "app_label": app_label,
            "model_name": model_name,
            "model_class": model.__name__,
            "model_label": f"{app_label}.{model_name}",
            "model_verbose": model._meta.verbose_name,
            "model_verbose_plural": model._meta.verbose_name_plural,
            "snake_name": inflection.underscore(model_name),
            "kebab_name": inflection.dasherize(inflection.underscore(model_name)),
            "plural_name": inflection.pluralize(inflection.underscore(model_name)),
            "fields": fields,
            "config": {
                "kind": config.kind,
                "slug_field": config.slug_field,
                "locale_field": config.locale_field,
                "translatable_fields": config.translatable_fields or [],
                "searchable_fields": config.searchable_fields or [],
                "can_publish": config.can_publish,
                "route_pattern": config.route_pattern or "",
            },
        }

    def _show_dry_run(self, context, output_dir):
        """Show what would be created in dry run mode."""
        files = [
            f"{context['snake_name']}_serializers.py",
            f"{context['snake_name']}_views.py",
            f"{context['snake_name']}_urls.py",
            f"{context['snake_name']}_admin.py",
            f"docs/api/{context['kebab_name']}.md",
        ]

        self.stdout.write("\nFiles that would be created:")
        for file_name in files:
            file_path = output_dir / file_name
            self.stdout.write(f"  * {file_path}")

        self.stdout.write("\nAPI endpoints that would be available:")
        self.stdout.write(
            f"  GET    /api/content/{context['model_label']}/           - List {context['model_verbose_plural']}"
        )
        self.stdout.write(
            f"  POST   /api/content/{context['model_label']}/           - Create {context['model_verbose']}"
        )
        self.stdout.write(
            f"  GET    /api/content/{context['model_label']}/{{id}}/       - Get {context['model_verbose']}"
        )
        self.stdout.write(
            f"  PUT    /api/content/{context['model_label']}/{{id}}/       - Update {context['model_verbose']}"
        )
        self.stdout.write(
            f"  PATCH  /api/content/{context['model_label']}/{{id}}/       - Partial update {context['model_verbose']}"
        )
        self.stdout.write(
            f"  DELETE /api/content/{context['model_label']}/{{id}}/       - Delete {context['model_verbose']}"
        )

        if context["config"]["slug_field"]:
            self.stdout.write(
                f"  GET    /api/content/{context['model_label']}:by-slug    - Get by slug"
            )

        if context["config"]["can_publish"]:
            self.stdout.write(
                f"  POST   /api/content/{context['model_label']}/{{id}}/publish   - Publish {context['model_verbose']}"
            )
            self.stdout.write(
                f"  POST   /api/content/{context['model_label']}/{{id}}/unpublish - Unpublish {context['model_verbose']}"
            )

    def _create_serializers_file(self, context, output_dir, force):
        """Create serializers file."""
        template = Template(
            '''"""
Serializers for {{ model_class }} model.
"""

from rest_framework import serializers
from {{ app_label }}.models import {{ model_class }}


class {{ model_class }}ListSerializer(serializers.ModelSerializer):
    """Serializer for {{ model_class }} list view."""

    class Meta:
        model = {{ model_class }}
        fields = [
            {% for field in fields %}'{{ field.name }}',{% if not forloop.last %}
            {% endif %}{% endfor %}
        ]
        read_only_fields = ['created_at', 'updated_at']


class {{ model_class }}DetailSerializer(serializers.ModelSerializer):
    """Serializer for {{ model_class }} detail view."""

    class Meta:
        model = {{ model_class }}
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class {{ model_class }}WriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating {{ model_class }}."""

    class Meta:
        model = {{ model_class }}
        fields = [
            {% for field in fields %}{% if not field.name in 'id,created_at,updated_at' %}'{{ field.name }}',{% if not forloop.last %}
            {% endif %}{% endif %}{% endfor %}
        ]

    def validate(self, attrs):
        """Custom validation for {{ model_class }}."""
        # Add your custom validation logic here
        return attrs


{% if config.can_publish %}class {{ model_class }}PublishSerializer(serializers.Serializer):
    """Serializer for publish/unpublish actions."""

    published_at = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        fields = ['published_at', 'status']
{% endif %}
'''
        )

        file_path = output_dir / f"{context['snake_name']}_serializers.py"
        self._write_file(file_path, template.render(Context(context)), force)
        self.stdout.write(f"  * Created {file_path}")

    def _create_views_file(self, context, output_dir, force):
        """Create views file."""
        template = Template(
            '''"""
API views for {{ model_class }} model.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter

from {{ app_label }}.models import {{ model_class }}
from .{{ snake_name }}_serializers import (
    {{ model_class }}ListSerializer,
    {{ model_class }}DetailSerializer,
    {{ model_class }}WriteSerializer,{% if config.can_publish %}
    {{ model_class }}PublishSerializer,{% endif %}
)


class {{ model_class }}ViewSet(viewsets.ModelViewSet):
    """
    ViewSet for {{ model_class }} model.

    Provides standard CRUD operations{% if config.can_publish %} plus publish/unpublish{% endif %}.
    """

    queryset = {{ model_class }}.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # Configure filtering
    filterset_fields = [{% for field in fields %}{% if field.type in 'CharField,BooleanField,IntegerField' %}'{{ field.name }}', {% endif %}{% endfor %}]
    search_fields = [{% for field in config.searchable_fields %}'{{ field }}', {% endfor %}]
    ordering_fields = ['created_at', 'updated_at'{% if config.slug_field %}, '{{ config.slug_field }}'{% endif %}]
    ordering = ['-updated_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return {{ model_class }}ListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return {{ model_class }}WriteSerializer{% if config.can_publish %}
        elif self.action in ['publish', 'unpublish']:
            return {{ model_class }}PublishSerializer{% endif %}
        return {{ model_class }}DetailSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions and locale."""
        queryset = super().get_queryset()

        {% if config.locale_field %}# Filter by locale if specified
        locale = self.request.query_params.get('locale')
        if locale:
            queryset = queryset.filter({{ config.locale_field }}__code=locale)
        {% endif %}

        return queryset{% if config.locale_field %}.select_related('{{ config.locale_field }}'){% endif %}

    {% if config.slug_field %}@extend_schema(
        parameters=[
            OpenApiParameter('slug', str, description='{{ model_class }} slug'),
            OpenApiParameter('locale', str, description='Locale code'),
        ]
    )
    @action(detail=False, methods=['get'], url_path='by-slug')
    def get_by_slug(self, request):
        """Get {{ model_class }} by slug."""
        slug = request.query_params.get('slug')
        if not slug:
            return Response(
                {'error': 'slug parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            filters = {'{{ config.slug_field }}': slug}
            {% if config.locale_field %}locale = request.query_params.get('locale')
            if locale:
                filters['{{ config.locale_field }}__code'] = locale
            {% endif %}

            instance = self.get_queryset().get(**filters)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except {{ model_class }}.DoesNotExist:
            return Response(
                {'error': '{{ model_class }} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    {% endif %}

    {% if config.can_publish %}@action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish {{ model_class }}."""
        instance = self.get_object()

        # Implement your publish logic here
        instance.status = 'published'
        instance.published_at = timezone.now()
        instance.save()

        serializer = {{ model_class }}PublishSerializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """Unpublish {{ model_class }}."""
        instance = self.get_object()

        # Implement your unpublish logic here
        instance.status = 'draft'
        instance.published_at = None
        instance.save()

        serializer = {{ model_class }}PublishSerializer(instance)
        return Response(serializer.data)
    {% endif %}
'''
        )

        file_path = output_dir / f"{context['snake_name']}_views.py"
        self._write_file(file_path, template.render(Context(context)), force)
        self.stdout.write(f"  * Created {file_path}")

    def _create_urls_file(self, context, output_dir, force):
        """Create URLs file."""
        template = Template(
            '''"""
URL configuration for {{ model_class }} API.
"""

from rest_framework.routers import DefaultRouter
from .{{ snake_name }}_views import {{ model_class }}ViewSet

# Create router and register viewset
router = DefaultRouter()
router.register(r'{{ plural_name }}', {{ model_class }}ViewSet, basename='{{ snake_name }}')

urlpatterns = router.urls
'''
        )

        file_path = output_dir / f"{context['snake_name']}_urls.py"
        self._write_file(file_path, template.render(Context(context)), force)
        self.stdout.write(f"  * Created {file_path}")

    def _create_admin_file(self, context, output_dir, force):
        """Create admin integration file."""
        template = Template(
            '''"""
Admin configuration for {{ model_class }} model.
"""

from django.contrib import admin
from {{ app_label }}.models import {{ model_class }}


@admin.register({{ model_class }})
class {{ model_class }}Admin(admin.ModelAdmin):
    """Admin interface for {{ model_class }}."""

    list_display = [{% for field in fields %}{% if forloop.counter0 < 6 %}'{{ field.name }}', {% endif %}{% endfor %}]
    list_filter = [{% for field in fields %}{% if field.type in 'BooleanField,CharField' and forloop.counter0 < 4 %}'{{ field.name }}', {% endif %}{% endfor %}]
    search_fields = [{% for field in config.searchable_fields %}'{{ field }}', {% endfor %}]
    {% if config.slug_field %}prepopulated_fields = {'{{ config.slug_field }}': ('title',)}  # Adjust based on your title field
    {% endif %}
    {% if config.can_publish %}actions = ['make_published', 'make_draft']

    def make_published(self, request, queryset):
        """Bulk publish action."""
        updated = queryset.update(status='published')
        self.message_user(request, f'{updated} {{ model_verbose_plural }} were successfully published.')
    make_published.short_description = "Mark selected {{ model_verbose_plural }} as published"

    def make_draft(self, request, queryset):
        """Bulk draft action."""
        updated = queryset.update(status='draft')
        self.message_user(request, f'{updated} {{ model_verbose_plural }} were marked as draft.')
    make_draft.short_description = "Mark selected {{ model_verbose_plural }} as draft"
    {% endif %}

    # Customize fieldsets as needed
    fieldsets = (
        ('Basic Information', {
            'fields': ({% for field in fields %}{% if forloop.counter0 < 4 %}'{{ field.name }}', {% endif %}{% endfor %})
        }),
        # Add more fieldsets as needed
    )
'''
        )

        file_path = output_dir / f"{context['snake_name']}_admin.py"
        self._write_file(file_path, template.render(Context(context)), force)
        self.stdout.write(f"  * Created {file_path}")

    def _create_docs_file(self, context, output_dir, force):
        """Create documentation file."""
        docs_dir = output_dir / "docs/api"
        docs_dir.mkdir(parents=True, exist_ok=True)

        template = Template(
            """# {{ model_class }} API

{{ model_verbose_plural }} management API endpoints.

## Overview

- **Model**: `{{ model_label }}`
- **Kind**: {{ config.kind }}{% if config.can_publish %}
- **Publishable**: Yes{% endif %}{% if config.slug_field %}
- **Slug Field**: `{{ config.slug_field }}`{% endif %}{% if config.locale_field %}
- **Locale Support**: Yes (via `{{ config.locale_field }}`){% endif %}

## Endpoints

### List {{ model_verbose_plural }}

```http
GET /api/content/{{ model_label }}/
```

**Parameters:**
- `page` - Page number for pagination
- `search` - Search query{% if config.locale_field %}
- `locale` - Filter by locale code{% endif %}
{% for field in fields %}{% if field.type in 'CharField,BooleanField,IntegerField' %}- `{{ field.name }}` - Filter by {{ field.name }}
{% endif %}{% endfor %}

### Create {{ model_verbose }}

```http
POST /api/content/{{ model_label }}/
```

**Request Body:**
```json
{
  {% for field in fields %}{% if not field.name in 'id,created_at,updated_at' %}"{{ field.name }}": "value"{% if not forloop.last %},{% endif %}
  {% endif %}{% endfor %}
}
```

### Get {{ model_verbose }}

```http
GET /api/content/{{ model_label }}/{id}/
```

{% if config.slug_field %}### Get {{ model_verbose }} by Slug

```http
GET /api/content/{{ model_label }}:by-slug?slug=example-slug{% if config.locale_field %}&locale=en{% endif %}
```
{% endif %}

### Update {{ model_verbose }}

```http
PUT /api/content/{{ model_label }}/{id}/
```

### Partial Update {{ model_verbose }}

```http
PATCH /api/content/{{ model_label }}/{id}/
```

### Delete {{ model_verbose }}

```http
DELETE /api/content/{{ model_label }}/{id}/
```

{% if config.can_publish %}### Publish {{ model_verbose }}

```http
POST /api/content/{{ model_label }}/{id}/publish
```

### Unpublish {{ model_verbose }}

```http
POST /api/content/{{ model_label }}/{id}/unpublish
```
{% endif %}

## Fields

{% for field in fields %}### `{{ field.name }}` ({{ field.type }})

{{ field.help_text }}

- **Required**: {% if field.required %}Yes{% else %}No{% endif %}

{% endfor %}

## Examples

### Create Example

```bash
curl -X POST /api/content/{{ model_label }}/ \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{
    {% for field in fields %}{% if not field.name in 'id,created_at,updated_at' %}"{{ field.name }}": "example_value"{% if not forloop.last %},{% endif %}
    {% endif %}{% endfor %}
  }'
```

### List with Filtering

```bash
curl "/api/content/{{ model_label }}/?search=example{% if config.locale_field %}&locale=en{% endif %}"
```

## Permissions

- **List/Read**: Authenticated users
- **Create/Update/Delete**: Users with appropriate model permissions{% if config.can_publish %}
- **Publish/Unpublish**: Users with publish permissions{% endif %}

## Related Documentation

- [Content Registry](../registry.md)
- [API Authentication](../authentication.md)
- [Permissions](../permissions.md)
"""
        )

        file_path = docs_dir / f"{context['kebab_name']}.md"
        self._write_file(file_path, template.render(Context(context)), force)
        self.stdout.write(f"  * Created {file_path}")

    def _write_file(self, file_path, content, force):
        """Write content to file, checking for existing files."""
        if file_path.exists() and not force:
            raise CommandError(
                f"File {file_path} already exists. Use --force to overwrite."
            )

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)

    def _show_next_steps(self, context):
        """Show next steps to the user."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("NEXT STEPS")
        self.stdout.write("=" * 60)

        self.stdout.write("\n1. Add the URLs to your main URL configuration:")
        self.stdout.write("   # In your main urls.py")
        self.stdout.write(
            f'   path("api/content/{{ model_label }}/", include("path.to.{context["snake_name"]}_urls")),'
        )

        self.stdout.write("\n2. Review and customize the generated files:")
        self.stdout.write("   - Adjust field configurations in serializers")
        self.stdout.write("   - Add custom validation logic")
        self.stdout.write("   - Customize admin interface")

        self.stdout.write("\n3. Test the API endpoints:")
        self.stdout.write("   python manage.py test  # Run your tests")
        self.stdout.write("   # Or test manually:")
        self.stdout.write(f"   curl /api/content/{context['model_label']}/")

        self.stdout.write("\n4. Update API documentation as needed")

        self.stdout.write(
            f"\nAPI endpoints for {context['model_label']} are ready to use!"
        )
