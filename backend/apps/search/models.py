"""
Search models for the CMS.

This module provides search functionality including indexing, analytics, and query logging.
"""

import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKey,
    GenericIPAddressField,
    PositiveIntegerField,
    TextField,
    URLField,
    UUIDField,
)
from django.utils import timezone

from apps.registry.registry import content_registry

# PostgreSQL search functionality (optional)
try:
    from django.contrib.postgres.indexes import GinIndex
    HAS_POSTGRES_SEARCH = True
except ImportError:
    HAS_POSTGRES_SEARCH = False
    GinIndex = None

User = get_user_model()


class SearchIndex(models.Model):
    """
    Search index for all searchable content.

    This model stores preprocessed search data for fast full-text search
    across all registered content types.
    """

    id: UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )

    # Generic foreign key to the indexed object
    content_type: ForeignKey = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id: PositiveIntegerField = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    # Search-specific fields
    title: CharField = models.CharField(max_length=500, help_text="Searchable title")
    content: TextField = models.TextField(help_text="Full searchable content")
    excerpt: TextField = models.TextField(
        blank=True, help_text="Short excerpt for results"
    )

    # Metadata for search results
    url: URLField = models.URLField(
        blank=True, help_text="Canonical URL for this content"
    )
    image_url: URLField = models.URLField(blank=True, help_text="Representative image")
    locale_code: CharField = models.CharField(max_length=10, blank=True)

    # Search weighting and categorization
    search_category: CharField = models.CharField(
        max_length=50,
        help_text="Category for search filtering (e.g., 'blog', 'page', 'product')",
    )
    search_tags = models.JSONField(default=list, help_text="Tags for faceted search")

    # Publication and relevance
    is_published: BooleanField = models.BooleanField(default=True)
    published_at: DateTimeField = models.DateTimeField(null=True, blank=True)
    search_weight = models.FloatField(
        default=1.0, help_text="Weight for search ranking (higher = more relevant)"
    )

    # Full-text search fields (PostgreSQL specific) - removed class-level definition
    # search_vector field will be populated via trigger or update method

    # Timestamps
    indexed_at: DateTimeField = models.DateTimeField(auto_now=True)
    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Search Index Entry"
        verbose_name_plural = "Search Index Entries"
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["search_category", "-published_at"]),
            models.Index(fields=["is_published", "-published_at"]),
            models.Index(fields=["locale_code", "is_published"]),
            models.Index(fields=["-search_weight", "-published_at"]),
            models.Index(fields=["title"]),
            # GIN index for PostgreSQL full-text search on JSONField
            (
                GinIndex(fields=["search_tags"])
                if GinIndex
                else models.Index(fields=["search_tags"])
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                name="unique_search_index_per_object",
            ),
        ]

    def __str__(self):  # noqa: C901
        return f"{self.title} ({self.search_category})"

    def update_from_object(self, obj):  # noqa: C901
        """Update search index from the source object."""

        # Get content configuration
        model_label = f"{obj._meta.app_label}.{obj._meta.model_name}"
        config = content_registry.get_config(model_label)

        if not config:
            raise ValidationError(f"No content configuration found for {model_label}")

        # Extract searchable content
        title_parts = []
        content_parts = []

        for field_name in config.searchable_fields:
            if "." in field_name:
                # Handle nested fields (like JSON fields)
                root_field, nested_key = field_name.split(".", 1)
                if hasattr(obj, root_field):
                    field_value = getattr(obj, root_field)
                    if isinstance(field_value, dict) and nested_key in field_value:
                        content_parts.append(str(field_value[nested_key]))
                    elif isinstance(field_value, list):
                        # Handle blocks or arrays
                        for item in field_value:
                            if isinstance(item, dict) and "props" in item:
                                props = item["props"]
                                if nested_key in props:
                                    content_parts.append(str(props[nested_key]))
            else:
                # Handle regular fields
                if hasattr(obj, field_name):
                    field_value = getattr(obj, field_name)
                    if field_value:
                        if field_name in ["title", "name"]:
                            title_parts.append(str(field_value))
                        else:
                            content_parts.append(str(field_value))

        # Set search fields
        self.title = " ".join(title_parts) if title_parts else str(obj)
        self.content = " ".join(content_parts)

        # Set excerpt (first 200 chars of content)
        if content_parts:
            full_content = " ".join(content_parts)
            self.excerpt = full_content[:200] + (
                "..." if len(full_content) > 200 else ""
            )

        # Set metadata
        self.search_category = config.kind
        if hasattr(obj, "get_absolute_url"):
            try:
                self.url = obj.get_absolute_url()
            except Exception:
                self.url = ""

        # Set locale
        if config.locale_field and hasattr(obj, config.locale_field):
            locale = getattr(obj, config.locale_field)
            if locale:
                self.locale_code = (
                    locale.code if hasattr(locale, "code") else str(locale)
                )

        # Set publication status
        if hasattr(obj, "status"):
            self.is_published = obj.status == "published"
        elif hasattr(obj, "is_published"):
            self.is_published = obj.is_published
        else:
            self.is_published = True

        # Set published date
        if hasattr(obj, "published_at"):
            self.published_at = obj.published_at
        elif hasattr(obj, "created_at"):
            self.published_at = obj.created_at

        # Set search weight based on content type
        weight_map = {
            "page": 1.0,
            "collection": 0.8,
            "singleton": 1.2,
            "snippet": 0.6,
        }
        self.search_weight = weight_map.get(config.kind, 1.0)

        # Handle tags
        tags = []
        if hasattr(obj, "tags") and hasattr(obj.tags, "all"):
            # Use values_list to avoid N+1 queries
            tags.extend(list(obj.tags.values_list("name", flat=True)))
        if hasattr(obj, "category") and obj.category:
            tags.append(obj.category.name)
        self.search_tags = tags


class SearchQuery(models.Model):
    """
    Log of search queries for analytics and improvement.
    """

    id: UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )

    # Query details
    query_text: CharField = models.CharField(
        max_length=500, help_text="The search query"
    )
    filters = models.JSONField(
        default=dict, help_text="Applied filters (category, locale, etc.)"
    )

    # User and session info
    user: ForeignKey = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="search_queries",
    )
    session_key: CharField = models.CharField(max_length=40, blank=True)
    ip_address: GenericIPAddressField = models.GenericIPAddressField(
        null=True, blank=True
    )

    # Results and performance
    result_count: PositiveIntegerField = models.PositiveIntegerField(default=0)
    execution_time_ms: PositiveIntegerField = models.PositiveIntegerField(
        null=True, blank=True, help_text="Query execution time in milliseconds"
    )

    # Interaction tracking
    clicked_result: ForeignKey = models.ForeignKey(
        SearchIndex,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clicks",
    )
    click_position: PositiveIntegerField = models.PositiveIntegerField(
        null=True, blank=True, help_text="Position of clicked result (1-based)"
    )

    # Timestamps
    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Search Query"
        verbose_name_plural = "Search Queries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["query_text", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["result_count", "-created_at"]),
        ]

    def __str__(self):  # noqa: C901
        return f'"{self.query_text}" ({self.result_count} results)'


class SearchSuggestion(models.Model):
    """
    Search suggestions and autocomplete data.
    """

    id: UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )

    # Suggestion details
    suggestion_text: CharField = models.CharField(max_length=200, unique=True)
    normalized_text: CharField = models.CharField(
        max_length=200, help_text="Normalized version for matching"
    )

    # Popularity and relevance
    search_count: PositiveIntegerField = models.PositiveIntegerField(
        default=0, help_text="Number of times this was searched"
    )
    result_count: PositiveIntegerField = models.PositiveIntegerField(
        default=0, help_text="Average number of results for this query"
    )
    click_through_rate = models.FloatField(
        default=0.0, help_text="Percentage of searches that result in clicks"
    )

    # Categorization
    categories = models.JSONField(
        default=list, help_text="Content categories this suggestion relates to"
    )
    locale_codes = models.JSONField(
        default=list, help_text="Locales where this suggestion is relevant"
    )

    # Management
    is_active: BooleanField = models.BooleanField(default=True)
    is_promoted: BooleanField = models.BooleanField(
        default=False, help_text="Manually promoted suggestion"
    )

    # Timestamps
    last_searched_at: DateTimeField = models.DateTimeField(null=True, blank=True)
    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Search Suggestion"
        verbose_name_plural = "Search Suggestions"
        ordering = ["-search_count", "suggestion_text"]
        indexes = [
            models.Index(fields=["normalized_text"]),
            models.Index(fields=["-search_count", "is_active"]),
            models.Index(fields=["is_promoted", "-search_count"]),
        ]

    def __str__(self):  # noqa: C901
        return self.suggestion_text

    def save(self, *args, **kwargs):  # noqa: C901
        # Auto-generate normalized text
        if not self.normalized_text:
            self.normalized_text = self.suggestion_text.lower().strip()
        super().save(*args, **kwargs)

    def increment_search_count(self, result_count=0):  # noqa: C901
        """Increment search count and update stats."""
        self.search_count += 1
        self.last_searched_at = timezone.now()

        # Update average result count
        if result_count > 0:
            if self.result_count == 0:
                self.result_count = result_count
            else:
                # Running average
                self.result_count = int((self.result_count + result_count) / 2)

        self.save(update_fields=["search_count", "last_searched_at", "result_count"])
