import re
import uuid
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    AutoField,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKey,
    ManyToManyField,
    OneToOneField,
    SlugField,
    TextField,
    UUIDField,
)
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.accounts.rbac import RBACMixin
from apps.cms import versioning
from apps.core.validators import JSONSizeValidator, validate_json_structure

User = get_user_model()

if TYPE_CHECKING:
    from apps.cms.models import Page
    from apps.files.models import FileUpload


class Category(models.Model, RBACMixin):
    """Blog category model."""

    id: AutoField = models.AutoField(primary_key=True)

    name: CharField = models.CharField(max_length=100, unique=True)

    slug: SlugField = models.SlugField(max_length=120, unique=True)

    description: TextField = models.TextField(blank=True)

    color: CharField = models.CharField(
        max_length=7, default="#6366f1", help_text=_("Hex color code for the category")
    )

    presentation_page: "ForeignKey[Page | None]" = models.ForeignKey(
        "cms.Page",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="category_presentations",
        help_text=_("Optional presentation page override for this category"),
    )

    is_active: BooleanField = models.BooleanField(default=True, db_index=True)

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:

        verbose_name = _("Category")

        verbose_name_plural = _("Categories")

        ordering = ["name"]

    def __str__(self):  # noqa: C901

        return self.name

    def save(self, *args, **kwargs):  # noqa: C901

        if not self.slug:

            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def get_absolute_url(self):  # noqa: C901

        return f"/blog/category/{self.slug}/"


class Tag(models.Model, RBACMixin):
    """Blog tag model."""

    id: AutoField = models.AutoField(primary_key=True)

    name: CharField = models.CharField(max_length=50, unique=True)

    slug: SlugField = models.SlugField(max_length=60, unique=True)

    description: TextField = models.TextField(blank=True)

    is_active: BooleanField = models.BooleanField(default=True, db_index=True)

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:

        verbose_name = _("Tag")

        verbose_name_plural = _("Tags")

        ordering = ["name"]

    def __str__(self):  # noqa: C901

        return self.name

    def save(self, *args, **kwargs):  # noqa: C901

        if not self.slug:

            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def get_absolute_url(self):  # noqa: C901

        return f"/blog/tag/{self.slug}/"


class BlogPost(models.Model, RBACMixin):
    """Blog post model."""

    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("published", _("Published")),
        ("scheduled", _("Scheduled")),
        ("archived", _("Archived")),
    ]

    id: AutoField = models.AutoField(primary_key=True)

    group_id: UUIDField = models.UUIDField(default=uuid.uuid4, db_index=True)

    locale: ForeignKey = models.ForeignKey("i18n.Locale", on_delete=models.PROTECT)

    # Content fields

    title: CharField = models.CharField(max_length=200)

    slug: SlugField = models.SlugField(max_length=250)

    excerpt: TextField = models.TextField(
        max_length=500, blank=True, help_text=_("Short description of the post")
    )

    content: TextField = models.TextField(help_text=_("Main content of the blog post"))

    blocks = models.JSONField(
        default=list,
        help_text=_("Structured content blocks"),
        validators=[JSONSizeValidator(max_size_mb=5), validate_json_structure],
    )

    # Metadata

    author: ForeignKey = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="blog_posts"
    )

    category: "ForeignKey[Category | None]" = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts"
    )

    tags: ManyToManyField = models.ManyToManyField(
        Tag, blank=True, related_name="posts"
    )

    # SEO fields

    seo = models.JSONField(
        default=dict,
        help_text=_("SEO metadata including title, description, and image"),
        validators=[JSONSizeValidator(max_size_mb=0.5)],
    )

    # Publishing fields

    status: CharField = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default="draft"
    )

    featured: BooleanField = models.BooleanField(
        default=False, help_text=_("Mark as featured post")
    )

    allow_comments: BooleanField = models.BooleanField(default=True)

    # Timestamps

    published_at: DateTimeField = models.DateTimeField(
        null=True, blank=True, help_text=_("When this post was actually published")
    )

    # Scheduling fields (replacing scheduled_for)

    scheduled_publish_at: DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("When to automatically publish this post"),
    )

    scheduled_unpublish_at: DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("When to automatically unpublish this post"),
    )

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: DateTimeField = models.DateTimeField(auto_now=True)

    # Social sharing

    social_image: "ForeignKey[FileUpload | None]" = models.ForeignKey(
        "files.FileUpload",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_post_social_images",
        help_text=_("Image for social media sharing"),
    )

    class Meta:

        verbose_name = _("Blog Post")

        verbose_name_plural = _("Blog Posts")

        ordering = ["-published_at", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["slug", "locale"], name="unique_blog_slug_per_locale"
            ),
        ]

        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["locale", "status", "-published_at"]),
            models.Index(fields=["category", "status", "-published_at"]),
            models.Index(fields=["author", "-published_at"]),
            models.Index(fields=["featured", "status", "-published_at"]),
            models.Index(
                fields=["category", "status", "featured", "-published_at"]
            ),  # For featured posts by category
            models.Index(fields=["locale", "slug"]),  # For slug lookups
            models.Index(fields=["group_id"]),
        ]

        permissions = [
            ("publish_blogpost", _("Can publish blog posts")),
            ("unpublish_blogpost", _("Can unpublish blog posts")),
            ("feature_blogpost", _("Can feature blog posts")),
            ("moderate_comments", _("Can moderate blog comments")),
            ("bulk_delete_blogpost", _("Can bulk delete blog posts")),
        ]

    def __str__(self):  # noqa: C901

        return self.title

    def save(self, *args, **kwargs):  # noqa: C901

        if not self.slug:

            self.slug = slugify(self.title)

        # Auto-set published_at when status changes to published

        if self.status == "published" and not self.published_at:

            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def clean(self):  # noqa: C901

        errors = {}

        # Title validation
        if not self.title or not self.title.strip():
            errors["title"] = _("Title is required and cannot be empty")

        # Scheduling validation

        # Rule 1: Scheduled status requires scheduled_publish_at

        if self.status == "scheduled":

            if not self.scheduled_publish_at:

                errors["scheduled_publish_at"] = _("Required when status is scheduled")

            elif self.scheduled_publish_at <= timezone.now():

                errors["scheduled_publish_at"] = _("Must be in the future")

        # Rule 2: Cannot have scheduled_publish_at when published

        if self.status == "published" and self.scheduled_publish_at:

            errors["scheduled_publish_at"] = _(
                "Cannot schedule publishing for already published content"
            )

        # Rule 3: Unpublish scheduling only for published content

        if self.scheduled_unpublish_at:

            if self.status != "published":

                errors["scheduled_unpublish_at"] = _(
                    "Can only schedule unpublishing for published content"
                )

            elif self.scheduled_unpublish_at <= timezone.now():

                errors["scheduled_unpublish_at"] = _("Must be in the future")

        # Rule 4: Unpublish must be after publish

        if self.scheduled_publish_at and self.scheduled_unpublish_at:

            if self.scheduled_unpublish_at <= self.scheduled_publish_at:

                errors["scheduled_unpublish_at"] = _(
                    "Must be after scheduled publish time"
                )

        # Validate published posts have published_at date

        if self.status == "published" and not self.published_at:

            self.published_at = timezone.now()

        if errors:

            raise ValidationError(errors)

    def get_absolute_url(self):  # noqa: C901

        return f"/blog/{self.slug}/"

    def get_reading_time(self):  # noqa: C901
        """Calculate estimated reading time in minutes."""

        # Combine content and blocks for word count using list for efficiency

        text_parts = [strip_tags(self.content)]

        # Add text from blocks with size limit

        max_text_length = 100000  # Limit to 100KB of text

        current_length = len(text_parts[0])

        if self.blocks and current_length < max_text_length:

            for block in self.blocks[:100]:  # Limit blocks processed

                if isinstance(block, dict) and "props" in block:

                    props = block["props"]

                    text_to_add = None

                    if "content" in props:

                        text_to_add = strip_tags(
                            str(props["content"])[:1000]
                        )  # Limit each block

                    elif "text" in props:

                        text_to_add = strip_tags(str(props["text"])[:1000])

                    if text_to_add:

                        current_length += len(text_to_add)

                        if current_length > max_text_length:
                            break
                        text_parts.append(text_to_add)

        # Join all parts efficiently

        text_content = " ".join(text_parts)

        # Count words (average 250 words per minute)

        word_count = len(re.findall(r"\w+", text_content))

        return max(1, round(word_count / 250))

    def get_related_posts(self, limit=5):  # noqa: C901
        """Get related posts based on category and tags."""

        # Use select_related and prefetch_related to avoid N+1 queries

        related = (
            BlogPost.objects.select_related("category", "locale", "author")
            .prefetch_related("tags")
            .filter(status="published", locale=self.locale)  # type: ignore[misc]
            .exclude(id=self.id)
        )

        # Prefer posts from same category

        if self.category:

            related = related.filter(category=self.category)

        # If we have tags, include posts with similar tags

        if self.tags.exists():

            # Get tag IDs to avoid N+1 queries

            tag_ids = list(self.tags.values_list("id", flat=True))

            related = related.filter(tags__id__in=tag_ids).distinct()

        return related[:limit]

    @property
    def is_published(self):  # noqa: C901
        """Check if the post is published."""

        return self.status == "published" and self.published_at

    @property
    def is_scheduled(self):  # noqa: C901
        """Check if the post is scheduled for future publication."""

        if self.status != "scheduled" or not self.scheduled_publish_at:

            return False

        return self.scheduled_publish_at > timezone.now()


class BlogSettings(models.Model):
    """Global blog settings and presentation configuration."""

    locale: OneToOneField = models.OneToOneField(
        "i18n.Locale", on_delete=models.CASCADE, related_name="blog_settings"
    )

    # Base configuration

    base_path: CharField = models.CharField(
        max_length=100,
        default="blog",
        help_text=_("Base path for blog URLs (without leading/trailing slashes)"),
    )

    # Presentation page configuration

    default_presentation_page: "ForeignKey[Page | None]" = models.ForeignKey(
        "cms.Page",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_presentations",
        help_text=_("Default presentation page template for blog posts"),
    )

    # Design tokens

    design_tokens = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            'Design configuration, e.g.: {"content_width": "prose", "typography_scale": "md", "accent_color": "#3b82f6"}'
        ),
    )

    # Display toggles

    show_toc: BooleanField = models.BooleanField(
        default=True, help_text=_("Show table of contents by default")
    )

    show_author: BooleanField = models.BooleanField(
        default=True, help_text=_("Show author information by default")
    )

    show_dates: BooleanField = models.BooleanField(
        default=True, help_text=_("Show publication dates by default")
    )

    show_share: BooleanField = models.BooleanField(
        default=True, help_text=_("Show social sharing buttons by default")
    )

    show_reading_time: BooleanField = models.BooleanField(
        default=True, help_text=_("Show estimated reading time by default")
    )

    # Feed configuration

    feeds_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            'RSS/Atom feed configuration, e.g.: {"title": "My Blog", "description": "Latest posts from my blog", "items_per_feed": 20}'
        ),
    )

    # SEO defaults

    seo_defaults = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            'Default SEO settings for blog posts, e.g.: {"title_template": "{title} - Blog", "meta_description_template": "Read about {title} on our blog"}'
        ),
    )

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:

        verbose_name = _("Blog Settings")

        verbose_name_plural = _("Blog Settings")

    def __str__(self):  # noqa: C901

        return f"Blog Settings ({self.locale.code})"

    def get_display_options(self, category=None, post=None):  # noqa: C901
        """Get effective display options with precedence:

        post override -> category override -> global settings
        """
        options = {
            "show_toc": self.show_toc,
            "show_author": self.show_author,
            "show_dates": self.show_dates,
            "show_share": self.show_share,
            "show_reading_time": self.show_reading_time,
        }

        # Category overrides (could be extended later)

        if category and hasattr(category, "display_options"):

            options.update(category.display_options or {})

        # Post overrides (could be extended later)

        if post and hasattr(post, "display_options"):

            options.update(post.display_options or {})

        return options

    def get_presentation_page(self, category=None, post=None):  # noqa: C901
        """Get the effective presentation page with precedence:

        post override -> category override -> global default
        """
        # Post override (could be extended later)

        if post and hasattr(post, "presentation_page") and post.presentation_page:

            return post.presentation_page

        # Category override

        if category and category.presentation_page:

            return category.presentation_page

        # Global default

        return self.default_presentation_page


# Import versioning models to ensure they are registered
