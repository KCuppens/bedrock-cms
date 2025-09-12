from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import BlogPost, BlogSettings, Category, Tag

"""
Blog admin interface.
"""


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for blog categories."""

    list_display = (
        "name",
        "slug",
        "color_display",
        "post_count",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "color", "is_active")}),
        ("Presentation", {"fields": ("presentation_page",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def color_display(self, obj):  # noqa: C901
        """Display color as a colored box."""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; display: inline-block; border: 1px solid #ccc;"></div>',
            obj.color,
        )

    color_display.short_description = "Color"

    def post_count(self, obj):  # noqa: C901
        """Display number of posts in this category."""
        return obj.posts.filter(status="published").count()

    post_count.short_description = "Published Posts"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin for blog tags."""

    list_display = ("name", "slug", "post_count", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "is_active")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def post_count(self, obj):  # noqa: C901
        """Display number of posts with this tag."""
        return obj.posts.filter(status="published").count()

    post_count.short_description = "Published Posts"


class TagInline(admin.TabularInline):
    """Inline admin for post tags."""

    model = BlogPost.tags.through
    extra = 1


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    """Admin for blog posts."""

    list_display = (
        "title",
        "author",
        "category",
        "status",
        "featured",
        "reading_time_display",
        "published_at",
        "created_at",
    )
    list_filter = (
        "status",
        "featured",
        "category",
        "tags",
        "allow_comments",
        "created_at",
        "published_at",
        "locale",
    )
    search_fields = ("title", "excerpt", "content", "author__email")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("tags",)
    readonly_fields = (
        "group_id",
        "created_at",
        "updated_at",
        "reading_time_display",
        "related_posts_display",
    )
    date_hierarchy = "published_at"

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("title", "slug", "author", "category", "locale")},
        ),
        ("Content", {"fields": ("excerpt", "content", "blocks", "tags")}),
        (
            "Publishing",
            {
                "fields": (
                    "status",
                    "featured",
                    "allow_comments",
                    "published_at",
                    "scheduled_for",
                )
            },
        ),
        ("SEO", {"fields": ("seo", "social_image"), "classes": ("collapse",)}),
        (
            "Metadata",
            {
                "fields": (
                    "group_id",
                    "reading_time_display",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):  # noqa: C901
        """Optimize queryset with related data."""
        return (
            super()
            .get_queryset(request)
            .select_related("author", "category", "locale", "social_image")
            .prefetch_related("tags")
        )

    def reading_time_display(self, obj):  # noqa: C901
        """Display reading time."""
        reading_time = obj.get_reading_time()
        return f"{reading_time} min" if reading_time > 1 else "1 min"

    reading_time_display.short_description = "Reading Time"

    def related_posts_display(self, obj):  # noqa: C901
        """Display related posts."""
        if not obj.pk:
            return "Save the post to see related posts"

        related = obj.get_related_posts(limit=3)
        if not related:
            return "No related posts found"

        links = []
        for post in related:
            url = reverse("admin:blog_blogpost_change", args=[post.pk])
            links.append(format_html('<a href="{}">{}</a>', url, post.title))

        return format_html("<br>".join(links))

    related_posts_display.short_description = "Related Posts"

    def save_model(self, request, obj, form, change):  # noqa: C901
        """Custom save logic."""
        # Set author to current user if creating new post
        if not change:
            obj.author = request.user

        # Handle automatic publishing of scheduled posts
        if obj.status == "scheduled" and obj.scheduled_for:
            if obj.scheduled_for <= timezone.now():
                obj.status = "published"
                obj.published_at = obj.scheduled_for
                obj.scheduled_for = None

        super().save_model(request, obj, form, change)

    actions = ["make_published", "make_draft", "make_featured", "remove_featured"]

    def make_published(self, request, queryset):  # noqa: C901
        """Bulk action to publish posts."""
        updated = queryset.update(status="published", published_at=timezone.now())
        self.message_user(request, f"{updated} posts were published.")

    make_published.short_description = "Publish selected posts"

    def make_draft(self, request, queryset):  # noqa: C901
        """Bulk action to make posts draft."""
        updated = queryset.update(status="draft", published_at=None)
        self.message_user(request, f"{updated} posts were set to draft.")

    make_draft.short_description = "Set selected posts to draft"

    def make_featured(self, request, queryset):  # noqa: C901
        """Bulk action to make posts featured."""
        updated = queryset.update(featured=True)
        self.message_user(request, f"{updated} posts were marked as featured.")

    make_featured.short_description = "Mark selected posts as featured"

    def remove_featured(self, request, queryset):  # noqa: C901
        """Bulk action to remove featured status."""
        updated = queryset.update(featured=False)
        self.message_user(request, f"{updated} posts had featured status removed.")

    remove_featured.short_description = "Remove featured status from selected posts"


@admin.register(BlogSettings)
class BlogSettingsAdmin(admin.ModelAdmin):
    """Admin for blog settings."""

    list_display = ("locale", "base_path", "default_presentation_page", "created_at")
    list_filter = ("locale", "created_at")

    fieldsets = (
        (
            "Basic Configuration",
            {"fields": ("locale", "base_path", "default_presentation_page")},
        ),
        (
            "Display Options",
            {
                "fields": (
                    "show_toc",
                    "show_author",
                    "show_dates",
                    "show_share",
                    "show_reading_time",
                )
            },
        ),
        (
            "Design & SEO",
            {"fields": ("design_tokens", "seo_defaults"), "classes": ("collapse",)},
        ),
        ("Feeds", {"fields": ("feeds_config",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ("created_at", "updated_at")

    def has_add_permission(self, request):  # noqa: C901
        """Only allow one settings instance per locale."""
        # Check if user can add based on available locales without settings
        return super().has_add_permission(request)

    def get_queryset(self, request):  # noqa: C901
        """Optimize queryset."""
        return (
            super()
            .get_queryset(request)
            .select_related("locale", "default_presentation_page")
        )
