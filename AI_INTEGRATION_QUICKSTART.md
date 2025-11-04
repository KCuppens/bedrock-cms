# AI Integration Quickstart Guide

## Build an AI-Native CMS in 7 Days

This guide provides a concrete, step-by-step plan to add AI capabilities to Bedrock CMS, enabling autonomous operation with Claude, Lovable, and other AI assistants.

---

## Day 1: Setup & Infrastructure

### Goal: Create AI app structure and basic endpoints

### Tasks

1. **Create AI App**

```bash
cd backend/apps
python ../manage.py startapp ai
```

2. **Update Settings**

```python
# backend/apps/config/settings/base.py

INSTALLED_APPS = [
    # ... existing apps ...
    'apps.ai',
]

# AI Configuration
AI_CONFIG = {
    'OPENAI_API_KEY': env('OPENAI_API_KEY', default=''),
    'ANTHROPIC_API_KEY': env('ANTHROPIC_API_KEY', default=''),
    'DEFAULT_MODEL': env('AI_DEFAULT_MODEL', default='gpt-4'),
    'MAX_TOKENS': 4000,
    'TEMPERATURE': 0.7,
    'CONFIDENCE_THRESHOLD': 0.75,
}

# Rate Limiting for AI
AI_RATE_LIMITS = {
    'context_queries': 100,  # per hour
    'content_generation': 10,  # per hour
    'batch_operations': 5,  # per hour
}
```

3. **Create Base Models**

```python
# backend/apps/ai/models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class AIAPIKey(models.Model):
    """API keys for AI clients."""

    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scopes = models.JSONField(default=list)

    rate_limit_per_hour = models.IntegerField(default=100)
    rate_limit_per_day = models.IntegerField(default=1000)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ai_api_keys'


class AITask(models.Model):
    """Track AI operations."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    type = models.CharField(max_length=100)  # 'generation', 'translation', etc.
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    input_data = models.JSONField()
    output_data = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    progress = models.IntegerField(default=0)  # 0-100
    progress_message = models.CharField(max_length=255, blank=True)

    webhook_url = models.URLField(blank=True)
    webhook_called = models.BooleanField(default=False)

    class Meta:
        db_table = 'ai_tasks'
        ordering = ['-created_at']
```

4. **Run Migrations**

```bash
cd backend
python manage.py makemigrations ai
python manage.py migrate ai
```

---

## Day 2: Context Awareness APIs

### Goal: Enable AI to understand site structure and content

### Tasks

1. **Create Context Service**

```python
# backend/apps/ai/services/context.py
from apps.cms.models import Page
from apps.i18n.models import Locale
from django.db.models import Count, Q
from django.core.cache import cache

class ContextService:
    """Provide context about the CMS to AI."""

    @staticmethod
    def get_site_structure():
        """Get complete site structure."""

        # Cache for 5 minutes
        cache_key = 'ai_context_site_structure'
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Get all locales
        locales = Locale.objects.filter(is_active=True).values(
            'id', 'code', 'name', 'is_default'
        )

        # Get page statistics
        pages_stats = {
            'total': Page.objects.count(),
            'by_status': dict(
                Page.objects.values('status').annotate(count=Count('id'))
                .values_list('status', 'count')
            ),
            'by_locale': dict(
                Page.objects.values('locale__code').annotate(count=Count('id'))
                .values_list('locale__code', 'count')
            ),
        }

        # Get navigation structure (top-level pages)
        navigation = []
        root_pages = Page.objects.filter(
            parent__isnull=True,
            status='published'
        ).select_related('locale').prefetch_related('children')

        for page in root_pages:
            navigation.append({
                'id': page.id,
                'title': page.title,
                'path': page.path,
                'locale': page.locale.code,
                'children_count': page.children.count(),
            })

        result = {
            'locales': list(locales),
            'pages': pages_stats,
            'navigation': navigation,
        }

        cache.set(cache_key, result, 300)  # 5 minutes
        return result

    @staticmethod
    def get_content_schema():
        """Get content models and block types schema."""

        from apps.cms.models import BlockType

        # Page model schema
        page_schema = {
            'model': 'Page',
            'fields': {
                'title': {'type': 'string', 'max_length': 200, 'required': True},
                'slug': {'type': 'string', 'max_length': 200, 'required': True},
                'status': {
                    'type': 'choice',
                    'choices': ['draft', 'published', 'scheduled', 'archived']
                },
                'locale': {'type': 'foreign_key', 'to': 'Locale'},
                'blocks': {'type': 'json_array', 'description': 'Content blocks'},
                'meta_description': {'type': 'text', 'max_length': 160},
                'meta_keywords': {'type': 'string'},
            }
        }

        # Block types
        block_types = []
        for bt in BlockType.objects.filter(is_active=True):
            block_types.append({
                'name': bt.name,
                'display_name': bt.display_name,
                'category': bt.category,
                'data_source': bt.data_source,
                'example_content': bt.default_content,
            })

        return {
            'models': {'Page': page_schema},
            'block_types': block_types,
            'content_guidelines': {
                'title_length': {'min': 10, 'max': 60, 'recommended': 50},
                'meta_description_length': {'min': 50, 'max': 160, 'recommended': 155},
                'slug_rules': 'lowercase, hyphens only, no special characters',
            }
        }

    @staticmethod
    def get_content_gaps():
        """Identify content gaps and opportunities."""

        gaps = []

        # Missing translations
        default_locale = Locale.objects.get(is_default=True)
        active_locales = Locale.objects.filter(is_active=True).exclude(id=default_locale.id)

        for locale in active_locales:
            missing_count = Page.objects.filter(
                locale=default_locale,
                status='published'
            ).exclude(
                translations__locale=locale
            ).count()

            if missing_count > 0:
                gaps.append({
                    'type': 'missing_translation',
                    'locale': locale.code,
                    'count': missing_count,
                    'priority': 'high' if missing_count > 10 else 'medium',
                })

        # Pages without meta descriptions
        pages_without_meta = Page.objects.filter(
            status='published',
            Q(meta_description__isnull=True) | Q(meta_description='')
        ).count()

        if pages_without_meta > 0:
            gaps.append({
                'type': 'missing_seo_metadata',
                'field': 'meta_description',
                'count': pages_without_meta,
                'priority': 'high',
            })

        return gaps
```

2. **Create Context ViewSet**

```python
# backend/apps/ai/views/context.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.cache import cache_page
from ..services.context import ContextService

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 5)  # Cache for 5 minutes
def site_structure(request):
    """
    Get site structure overview.

    Returns navigation, page counts, locales, etc.
    """
    context = ContextService.get_site_structure()
    return Response(context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60 * 60)  # Cache for 1 hour
def content_schema(request):
    """
    Get content models and block types schema.

    Returns field definitions, block types, content guidelines.
    """
    schema = ContextService.get_content_schema()
    return Response(schema)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def content_gaps(request):
    """
    Identify content gaps and opportunities.

    Returns missing translations, SEO issues, etc.
    """
    gaps = ContextService.get_content_gaps()
    return Response({
        'gaps': gaps,
        'total_count': len(gaps),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommendations(request):
    """
    Get AI-powered content recommendations.
    """
    # This will be expanded in later days
    return Response({
        'content_ideas': [],
        'optimization_opportunities': [],
        'translation_priorities': [],
    })
```

3. **Create URLs**

```python
# backend/apps/ai/urls.py
from django.urls import path
from .views import context

app_name = 'ai'

urlpatterns = [
    # Context endpoints
    path('context/site-structure/', context.site_structure, name='site-structure'),
    path('context/content-schema/', context.content_schema, name='content-schema'),
    path('context/content-gaps/', context.content_gaps, name='content-gaps'),
    path('context/recommendations/', context.recommendations, name='recommendations'),
]
```

4. **Register URLs**

```python
# backend/apps/config/urls.py
urlpatterns = [
    # ... existing patterns ...
    path('api/ai/', include('apps.ai.urls', namespace='ai')),
]
```

5. **Test Endpoints**

```bash
# Start server
python manage.py runserver

# Test (in another terminal)
curl -H "Authorization: Bearer <your_token>" http://localhost:8000/api/ai/context/site-structure/
curl -H "Authorization: Bearer <your_token>" http://localhost:8000/api/ai/context/content-schema/
curl -H "Authorization: Bearer <your_token>" http://localhost:8000/api/ai/context/content-gaps/
```

---

## Day 3: Natural Language Interface

### Goal: Accept conversational commands from AI

### Tasks

1. **Install Dependencies**

```bash
pip install openai anthropic
```

2. **Create Intent Parser**

```python
# backend/apps/ai/services/intent_parser.py
from typing import Dict, Optional
import openai
from django.conf import settings
import json

class IntentParser:
    """Parse natural language commands into structured intents."""

    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.AI_CONFIG['OPENAI_API_KEY'])

    def parse(self, message: str, context: Dict = None) -> Dict:
        """
        Parse natural language message into structured intent.

        Args:
            message: Natural language command
            context: Additional context (current page, user, etc.)

        Returns:
            Structured intent with type, parameters, confidence
        """

        system_prompt = """You are an AI assistant that converts natural language
        commands into structured CMS operations.

        Available operations:
        - create_page: Create a new page
        - update_page: Update existing page
        - delete_page: Delete a page
        - translate_page: Translate page to other locales
        - schedule_page: Schedule page publication
        - generate_content: Generate content for a page

        Return JSON with:
        {
            "intent": "operation_name",
            "confidence": 0.0-1.0,
            "parameters": {...},
            "requires_confirmation": true/false
        }
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            result = json.loads(response.choices[0].message.content)

            return {
                'is_valid': True,
                'type': result.get('intent'),
                'parameters': result.get('parameters', {}),
                'confidence': result.get('confidence', 0.0),
                'requires_confirmation': result.get('requires_confirmation', True),
            }

        except Exception as e:
            return {
                'is_valid': False,
                'error': str(e),
                'suggestions': ['Try rephrasing your command'],
            }
```

3. **Create Action Translator**

```python
# backend/apps/ai/services/action_translator.py
from typing import Dict, List

class ActionTranslator:
    """Translate intents into CMS API actions."""

    def translate(self, intent: Dict) -> List[Dict]:
        """
        Translate intent into API actions.

        Returns:
            List of actions with endpoint, method, payload
        """

        intent_type = intent['type']
        params = intent['parameters']

        if intent_type == 'create_page':
            return self._translate_create_page(params)
        elif intent_type == 'update_page':
            return self._translate_update_page(params)
        elif intent_type == 'translate_page':
            return self._translate_translate_page(params)
        elif intent_type == 'schedule_page':
            return self._translate_schedule_page(params)
        else:
            return []

    def _translate_create_page(self, params: Dict) -> List[Dict]:
        """Translate create_page intent to API action."""

        # Build page data
        page_data = {
            'title': params.get('title', ''),
            'slug': params.get('slug', ''),
            'status': params.get('status', 'draft'),
            'locale': params.get('locale', 'en'),
        }

        # Add blocks if provided
        if params.get('blocks'):
            page_data['blocks'] = params['blocks']

        return [{
            'action': 'create_page',
            'endpoint': '/api/cms/pages/',
            'method': 'POST',
            'payload': page_data,
            'description': f"Create page: {params.get('title')}",
        }]

    def _translate_update_page(self, params: Dict) -> List[Dict]:
        """Translate update_page intent to API action."""

        page_id = params.get('page_id')
        updates = params.get('updates', {})

        return [{
            'action': 'update_page',
            'endpoint': f'/api/cms/pages/{page_id}/',
            'method': 'PATCH',
            'payload': updates,
            'description': f"Update page {page_id}",
        }]

    def _translate_translate_page(self, params: Dict) -> List[Dict]:
        """Translate translate_page intent to API action."""

        page_id = params.get('page_id')
        target_locales = params.get('target_locales', [])

        actions = []
        for locale in target_locales:
            actions.append({
                'action': 'translate_page',
                'endpoint': f'/api/cms/pages/{page_id}/translate/',
                'method': 'POST',
                'payload': {'target_locale': locale},
                'description': f"Translate page {page_id} to {locale}",
            })

        return actions

    def _translate_schedule_page(self, params: Dict) -> List[Dict]:
        """Translate schedule_page intent to API action."""

        page_id = params.get('page_id')
        publish_at = params.get('publish_at')

        return [{
            'action': 'schedule_page',
            'endpoint': f'/api/cms/pages/{page_id}/schedule/',
            'method': 'POST',
            'payload': {'publish_at': publish_at},
            'description': f"Schedule page {page_id} for {publish_at}",
        }]
```

4. **Create NLI View**

```python
# backend/apps/ai/views/nli.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from ..services.intent_parser import IntentParser
from ..services.action_translator import ActionTranslator

class NaturalLanguageInterfaceView(APIView):
    """
    Natural Language Interface for AI assistants.

    POST /api/ai/nli/
    {
        "message": "Create a blog post about Django",
        "context": {...}
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get('message')
        context = request.data.get('context', {})

        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse intent
        parser = IntentParser()
        intent = parser.parse(message, context)

        if not intent.get('is_valid'):
            return Response({
                'understood': False,
                'error': intent.get('error', 'Could not understand the request'),
                'suggestions': intent.get('suggestions', []),
            }, status=status.HTTP_400_BAD_REQUEST)

        # Translate to actions
        translator = ActionTranslator()
        actions = translator.translate(intent)

        # Return structured response
        return Response({
            'understood': True,
            'intent': intent['type'],
            'parameters': intent['parameters'],
            'actions': actions,
            'confirmation_required': intent['requires_confirmation'],
            'confidence': intent['confidence'],
        })
```

5. **Add URL**

```python
# backend/apps/ai/urls.py
from .views import nli

urlpatterns = [
    # ... existing patterns ...
    path('nli/', nli.NaturalLanguageInterfaceView.as_view(), name='nli'),
]
```

6. **Test NLI**

```bash
curl -X POST http://localhost:8000/api/ai/nli/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a blog post about Django security best practices"
  }'
```

---

## Day 4: Content Generation

### Goal: Generate complete content using AI

### Tasks

1. **Create Content Generator Service**

```python
# backend/apps/ai/services/content_generator.py
from typing import Dict, Generator
import openai
from django.conf import settings
from apps.cms.models import Page
import json

class ContentGenerator:
    """Generate content using AI."""

    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.AI_CONFIG['OPENAI_API_KEY'])

    def generate_blog_post(self, topic: str, parameters: Dict) -> Generator:
        """
        Generate a complete blog post.

        Yields progress events.
        """

        # Step 1: Generate outline
        yield {'event': 'outline_generated', 'data': self._generate_outline(topic)}

        # Step 2: Generate content
        outline = self._generate_outline(topic)
        blocks = []

        # Add hero block
        blocks.append({
            'type': 'hero',
            'content': {
                'title': outline['title'],
                'subtitle': outline['subtitle'],
            }
        })

        yield {'event': 'hero_created', 'data': blocks[0]}

        # Generate content for each section
        for i, section in enumerate(outline['sections']):
            yield {'event': 'section_progress', 'data': {
                'section': i + 1,
                'total': len(outline['sections']),
                'title': section['title']
            }}

            # Generate section content
            content = self._generate_section_content(section, parameters)

            blocks.append({
                'type': 'richtext',
                'content': {
                    'content': content
                }
            })

        # Step 3: Generate SEO metadata
        seo = self._generate_seo(topic, outline)
        yield {'event': 'seo_generated', 'data': seo}

        # Step 4: Create page
        page_data = {
            'title': outline['title'],
            'slug': self._slugify(outline['title']),
            'status': 'draft',
            'blocks': blocks,
            'meta_description': seo['meta_description'],
            'meta_keywords': ', '.join(seo['keywords']),
        }

        yield {'event': 'completed', 'data': page_data}

    def _generate_outline(self, topic: str) -> Dict:
        """Generate content outline."""

        prompt = f"""Generate a detailed outline for a blog post about: {topic}

        Return JSON with:
        {{
            "title": "engaging title",
            "subtitle": "brief description",
            "sections": [
                {{"title": "section title", "description": "what to cover"}},
                ...
            ]
        }}
        """

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)

    def _generate_section_content(self, section: Dict, parameters: Dict) -> str:
        """Generate content for a section."""

        tone = parameters.get('tone', 'professional')
        include_code = parameters.get('include_code_examples', False)

        prompt = f"""Write content for this section:
        Title: {section['title']}
        Description: {section['description']}

        Tone: {tone}
        Include code examples: {include_code}

        Write 2-3 paragraphs in HTML format.
        """

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
        )

        return response.choices[0].message.content

    def _generate_seo(self, topic: str, outline: Dict) -> Dict:
        """Generate SEO metadata."""

        prompt = f"""Generate SEO metadata for:
        Topic: {topic}
        Title: {outline['title']}

        Return JSON with:
        {{
            "meta_description": "150-160 chars",
            "keywords": ["keyword1", "keyword2", ...],
            "focus_keyword": "main keyword"
        }}
        """

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)

    def _slugify(self, text: str) -> str:
        """Convert title to URL-friendly slug."""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_-]+', '-', text)
        text = re.sub(r'^-+|-+$', '', text)
        return text
```

2. **Create Generation View with Streaming**

```python
# backend/apps/ai/views/generation.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import StreamingHttpResponse
from ..services.content_generator import ContentGenerator
import json

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_content(request):
    """
    Generate content with streaming progress.

    POST /api/ai/content/generate/
    {
        "type": "blog_post",
        "parameters": {
            "topic": "Django security",
            "tone": "professional",
            "include_code_examples": true
        }
    }
    """

    content_type = request.data.get('type')
    parameters = request.data.get('parameters', {})

    if content_type != 'blog_post':
        return Response(
            {'error': 'Only blog_post type is currently supported'},
            status=400
        )

    topic = parameters.get('topic')
    if not topic:
        return Response({'error': 'Topic is required'}, status=400)

    def event_stream():
        """Stream generation progress."""
        generator = ContentGenerator()

        try:
            for event in generator.generate_blog_post(topic, parameters):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'data': str(e)})}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'

    return response
```

3. **Add URL**

```python
# backend/apps/ai/urls.py
from .views import generation

urlpatterns = [
    # ... existing patterns ...
    path('content/generate/', generation.generate_content, name='generate-content'),
]
```

4. **Test Generation**

```python
# test_generation.py
import requests
import json

url = 'http://localhost:8000/api/ai/content/generate/'
headers = {
    'Authorization': 'Bearer <token>',
    'Content-Type': 'application/json',
}
data = {
    'type': 'blog_post',
    'parameters': {
        'topic': 'Django Performance Optimization',
        'tone': 'technical',
        'include_code_examples': True,
    }
}

response = requests.post(url, headers=headers, json=data, stream=True)

for line in response.iter_lines():
    if line:
        decoded_line = line.decode('utf-8')
        if decoded_line.startswith('data: '):
            event_data = json.loads(decoded_line[6:])
            print(f"Event: {event_data['event']}")
            print(f"Data: {event_data['data']}")
            print("---")
```

---

## Day 5: Validation & Safety

### Goal: Ensure AI-generated content is safe and high-quality

### Tasks

1. **Create Validation Service**

```python
# backend/apps/ai/services/validator.py
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class ValidationResult:
    valid: bool
    score: float
    issues: List[Dict]
    auto_fixable: bool

class ContentValidator:
    """Validate AI-generated content."""

    def validate(self, content: Dict) -> ValidationResult:
        """Run all validations."""

        issues = []
        scores = []

        # Security validation
        security_result = self._validate_security(content)
        issues.extend(security_result.issues)
        scores.append(security_result.score)

        # SEO validation
        seo_result = self._validate_seo(content)
        issues.extend(seo_result.issues)
        scores.append(seo_result.score)

        # Accessibility validation
        a11y_result = self._validate_accessibility(content)
        issues.extend(a11y_result.issues)
        scores.append(a11y_result.score)

        # Calculate overall score
        overall_score = sum(scores) / len(scores) if scores else 0.0

        return ValidationResult(
            valid=overall_score >= 0.7,
            score=overall_score,
            issues=issues,
            auto_fixable=self._can_auto_fix(issues)
        )

    def _validate_security(self, content: Dict) -> ValidationResult:
        """Check for security issues."""
        issues = []

        # Check for XSS in richtext blocks
        for block in content.get('blocks', []):
            if block['type'] == 'richtext':
                html = block.get('content', {}).get('content', '')
                if '<script>' in html.lower() or 'javascript:' in html.lower():
                    issues.append({
                        'type': 'security',
                        'severity': 'critical',
                        'message': 'Potential XSS in richtext block',
                    })

        return ValidationResult(
            valid=len(issues) == 0,
            score=1.0 if len(issues) == 0 else 0.0,
            issues=issues,
            auto_fixable=False
        )

    def _validate_seo(self, content: Dict) -> ValidationResult:
        """Check SEO best practices."""
        issues = []
        score = 1.0

        # Title length
        title = content.get('title', '')
        if len(title) < 30:
            issues.append({
                'type': 'seo',
                'severity': 'warning',
                'message': f'Title too short ({len(title)} chars)',
            })
            score -= 0.2

        # Meta description
        if not content.get('meta_description'):
            issues.append({
                'type': 'seo',
                'severity': 'error',
                'message': 'Missing meta description',
            })
            score -= 0.3

        return ValidationResult(
            valid=score >= 0.7,
            score=max(0.0, score),
            issues=issues,
            auto_fixable=True
        )

    def _validate_accessibility(self, content: Dict) -> ValidationResult:
        """Check accessibility standards."""
        issues = []

        # Check images have alt text
        for block in content.get('blocks', []):
            if block['type'] == 'image':
                if not block.get('content', {}).get('alt'):
                    issues.append({
                        'type': 'accessibility',
                        'severity': 'error',
                        'message': 'Image missing alt text',
                    })

        return ValidationResult(
            valid=len(issues) == 0,
            score=1.0 - (len(issues) * 0.2),
            issues=issues,
            auto_fixable=True
        )

    def _can_auto_fix(self, issues: List[Dict]) -> bool:
        """Check if issues can be auto-fixed."""
        return all(issue['severity'] != 'critical' for issue in issues)
```

2. **Create Validation View**

```python
# backend/apps/ai/views/validation.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..services.validator import ContentValidator

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_content(request):
    """
    Validate content for safety and quality.

    POST /api/ai/validate/
    {
        "content": {...}
    }
    """

    content = request.data.get('content')
    if not content:
        return Response({'error': 'Content is required'}, status=400)

    validator = ContentValidator()
    result = validator.validate(content)

    return Response({
        'valid': result.valid,
        'score': result.score,
        'issues': result.issues,
        'auto_fixable': result.auto_fixable,
    })
```

3. **Add URL**

```python
# backend/apps/ai/urls.py
urlpatterns = [
    # ... existing patterns ...
    path('validate/', validation.validate_content, name='validate'),
]
```

---

## Day 6: Claude Integration Example

### Goal: Create a complete example of Claude using the CMS

### Tasks

1. **Create Claude Integration Script**

```python
# scripts/claude_cms_agent.py
"""
Example: Claude autonomous CMS management.

This script demonstrates how Claude can manage the CMS autonomously.
"""

import requests
import json
from datetime import datetime, timedelta

class ClaudeCMSAgent:
    """Claude agent for autonomous CMS management."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

    def analyze_site(self):
        """Analyze site structure and identify opportunities."""

        print("📊 Analyzing site...")

        # Get site structure
        response = requests.get(
            f'{self.base_url}/api/ai/context/site-structure/',
            headers=self.headers
        )
        structure = response.json()

        # Get content gaps
        response = requests.get(
            f'{self.base_url}/api/ai/context/content-gaps/',
            headers=self.headers
        )
        gaps = response.json()

        print(f"✓ Found {structure['pages']['total']} pages")
        print(f"✓ Identified {len(gaps['gaps'])} content gaps")

        return structure, gaps

    def create_content_plan(self, gaps):
        """Create content plan based on gaps."""

        print("\n📝 Creating content plan...")

        plan = []
        for gap in gaps['gaps']:
            if gap['type'] == 'missing_translation':
                plan.append({
                    'action': 'translate',
                    'priority': gap['priority'],
                    'details': gap,
                })
            elif gap['type'] == 'missing_seo_metadata':
                plan.append({
                    'action': 'optimize_seo',
                    'priority': gap['priority'],
                    'details': gap,
                })

        print(f"✓ Created plan with {len(plan)} actions")
        return plan

    def generate_content(self, topic: str):
        """Generate content for a topic."""

        print(f"\n✍️  Generating content: {topic}")

        response = requests.post(
            f'{self.base_url}/api/ai/content/generate/',
            headers=self.headers,
            json={
                'type': 'blog_post',
                'parameters': {
                    'topic': topic,
                    'tone': 'professional',
                    'include_code_examples': True,
                }
            },
            stream=True
        )

        page_data = None
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    event = json.loads(decoded[6:])

                    if event['event'] == 'completed':
                        page_data = event['data']
                        print(f"✓ Content generated: {page_data['title']}")
                    else:
                        print(f"  {event['event']}...")

        return page_data

    def validate_content(self, content):
        """Validate generated content."""

        print("\n🔍 Validating content...")

        response = requests.post(
            f'{self.base_url}/api/ai/validate/',
            headers=self.headers,
            json={'content': content}
        )

        result = response.json()

        print(f"✓ Validation score: {result['score']:.2f}")
        if result['issues']:
            print(f"⚠️  Found {len(result['issues'])} issues")
            for issue in result['issues']:
                print(f"   - [{issue['severity']}] {issue['message']}")

        return result

    def create_page(self, page_data):
        """Create page in CMS."""

        print(f"\n📄 Creating page...")

        response = requests.post(
            f'{self.base_url}/api/cms/pages/',
            headers=self.headers,
            json=page_data
        )

        if response.status_code == 201:
            page = response.json()
            print(f"✓ Page created: ID {page['id']}")
            return page
        else:
            print(f"✗ Failed to create page: {response.text}")
            return None

    def run_daily_workflow(self):
        """Run daily autonomous workflow."""

        print("🤖 Claude CMS Agent - Daily Workflow")
        print("=" * 50)

        # 1. Analyze site
        structure, gaps = self.analyze_site()

        # 2. Create plan
        plan = self.create_content_plan(gaps['gaps'])

        if not plan:
            print("\n✓ No actions needed today!")
            return

        # 3. Execute plan (limit to 1 for demo)
        for i, action in enumerate(plan[:1]):
            print(f"\n--- Action {i+1}/{len(plan[:1])} ---")

            if action['action'] == 'optimize_seo':
                # Generate content for missing SEO
                page_data = self.generate_content("Django Security Best Practices")

                # Validate
                validation = self.validate_content(page_data)

                if validation['valid']:
                    # Create page
                    page = self.create_page(page_data)

                    if page:
                        print(f"✓ Successfully created page: {page['title']}")
                else:
                    print("✗ Content did not pass validation")

        print("\n" + "=" * 50)
        print("✓ Daily workflow completed!")


# Usage
if __name__ == '__main__':
    agent = ClaudeCMSAgent(
        base_url='http://localhost:8000',
        api_key='your_api_key_here'
    )

    agent.run_daily_workflow()
```

2. **Test the Agent**

```bash
python scripts/claude_cms_agent.py
```

---

## Day 7: Documentation & Polish

### Goal: Document the AI features and create examples

### Tasks

1. **Create API Documentation**

```bash
# backend/docs/ai_api.md - Create comprehensive API docs
```

2. **Create Integration Examples**

Create examples for:
- Claude integration
- Lovable code generation integration
- Custom AI agent integration

3. **Create Admin UI for AI Tasks**

Add a simple admin interface to view AI tasks:

```python
# backend/apps/ai/admin.py
from django.contrib import admin
from .models import AITask, AIAPIKey

@admin.register(AITask)
class AITaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'type', 'status', 'created_by', 'created_at', 'progress']
    list_filter = ['type', 'status', 'created_at']
    search_fields = ['id', 'type']
    readonly_fields = ['id', 'created_at', 'completed_at']

@admin.register(AIAPIKey)
class AIAPIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_active', 'created_at', 'last_used_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'key']
```

4. **Run Tests**

```bash
# Create basic tests
python manage.py test apps.ai
```

5. **Create README**

```markdown
# AI-Native CMS Features

## Overview

Bedrock CMS now includes AI capabilities for autonomous content management.

## Features

- Natural Language Interface
- Context-aware APIs
- Content generation
- Validation & safety
- Integration with Claude, Lovable, and other AI systems

## Quick Start

[Include setup instructions]

## Examples

[Include code examples]
```

---

## Complete Integration Test

After completing all 7 days, test the complete workflow:

```python
# integration_test.py
import requests

BASE_URL = 'http://localhost:8000'
TOKEN = 'your_token'

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json',
}

# 1. Get site context
print("1. Getting site context...")
response = requests.get(f'{BASE_URL}/api/ai/context/site-structure/', headers=headers)
print(f"   Status: {response.status_code}")
print(f"   Pages: {response.json()['pages']['total']}")

# 2. Natural language command
print("\n2. Sending natural language command...")
response = requests.post(
    f'{BASE_URL}/api/ai/nli/',
    headers=headers,
    json={'message': 'Create a blog post about Django performance'}
)
print(f"   Status: {response.status_code}")
print(f"   Intent: {response.json()['intent']}")

# 3. Generate content
print("\n3. Generating content...")
response = requests.post(
    f'{BASE_URL}/api/ai/content/generate/',
    headers=headers,
    json={
        'type': 'blog_post',
        'parameters': {'topic': 'Django Performance Optimization'}
    },
    stream=True
)

page_data = None
for line in response.iter_lines():
    if line:
        decoded = line.decode('utf-8')
        if decoded.startswith('data: '):
            event = json.loads(decoded[6:])
            if event['event'] == 'completed':
                page_data = event['data']
                break

print(f"   Generated: {page_data['title']}")

# 4. Validate content
print("\n4. Validating content...")
response = requests.post(
    f'{BASE_URL}/api/ai/validate/',
    headers=headers,
    json={'content': page_data}
)
validation = response.json()
print(f"   Score: {validation['score']:.2f}")
print(f"   Valid: {validation['valid']}")

print("\n✓ Integration test complete!")
```

---

## Next Steps

After completing the 7-day quickstart:

1. **Add more content types** - Support for landing pages, documentation, etc.
2. **Implement batch operations** - Bulk content creation and updates
3. **Add translation automation** - Auto-translate content to multiple locales
4. **Build approval workflows** - Human-in-the-loop for AI content
5. **Add analytics integration** - Performance-based optimization
6. **Create frontend UI** - Visual interface for AI features
7. **Implement A/B testing** - Automated content optimization

---

## Troubleshooting

### OpenAI API errors
- Check API key is set correctly
- Verify account has sufficient credits
- Check rate limits

### Streaming not working
- Ensure WSGI server supports streaming (use gunicorn with --worker-class=gevent)
- Check nginx/proxy settings for buffering

### Validation errors
- Review validation rules
- Check content format matches schema

---

## Resources

- [OpenAI API Docs](https://platform.openai.com/docs)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)

---

**Ready to make your CMS AI-native in 7 days!** 🚀
