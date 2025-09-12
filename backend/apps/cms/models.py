import uuid


from django.core.exceptions import ValidationError

from django.db import models

from django.db.models import (
    AutoField,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKey,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    SlugField,
    TextField,
    UUIDField,
)

# Import additional modules
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .blocks.validation import validate_blocks
from .presentation import presentation_resolver
from django.core.validators import validate_json_structure


# Import scheduling models

# Import SEO models

# Import versioning models


class Page(models.Model, RBACMixin):

    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("pending_review", _("Pending Review")),
        """("approved", _("Approved")),"""
        ("published", _("Published")),
        ("scheduled", _("Scheduled")),
        ("rejected", _("Rejected")),
    ]

    id: AutoField = models.AutoField(primary_key=True)

    group_id: UUIDField = models.UUIDField(default=uuid.uuid4, db_index=True)

    parent: ForeignKey = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    position: PositiveIntegerField = models.PositiveIntegerField(
        default=0, db_index=True
    )

    locale: ForeignKey = models.ForeignKey("i18n.Locale", on_delete=models.PROTECT)

    title: CharField = models.CharField(max_length=180)

    slug: SlugField = models.SlugField(max_length=120)

    path: CharField = models.CharField(max_length=512, db_index=True)

    blocks = models.JSONField(
        default=list,
        validators=[JSONSizeValidator(max_size_mb=2), validate_json_structure],
    )

    seo = models.JSONField(
        default=dict, validators=[JSONSizeValidator(max_size_mb=0.5)]
    )

    status: CharField = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="draft"
    )

    published_at: DateTimeField = models.DateTimeField(
        null=True, blank=True, help_text=_("When this page was actually published")
    )

    # Scheduling fields

    scheduled_publish_at: DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("When to automatically publish this page"),
    )

    scheduled_unpublish_at: DateTimeField = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("When to automatically unpublish this page"),
    )

    updated_at: DateTimeField = models.DateTimeField(auto_now=True)

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    preview_token: UUIDField = models.UUIDField(default=uuid.uuid4, editable=False)

    # Navigation fields

    in_main_menu: BooleanField = models.BooleanField(default=False, db_index=True)

    in_footer: BooleanField = models.BooleanField(default=False, db_index=True)

    is_homepage: BooleanField = models.BooleanField(default=False, db_index=True)

    # Moderation fields

    submitted_for_review_at: DateTimeField = models.DateTimeField(null=True, blank=True)

    reviewed_by: ForeignKey = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_pages",
    )

    review_notes: TextField = models.TextField(blank=True)

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=["locale", "parent", "slug"], name="uq_page_slug_parent_locale"
            )
        ]

        indexes = [
            models.Index(fields=["group_id", "locale"]),
            models.Index(fields=["locale", "path"]),  # Composite index for get_by_path
            models.Index(
                fields=["locale", "status", "-updated_at"]
            ),  # For sitemap queries
            models.Index(fields=["parent", "position"]),  # For tree navigation
            models.Index(
                fields=["status", "submitted_for_review_at"]
            ),  # For moderation queue
            models.Index(fields=["reviewed_by", "status"]),  # For reviewer stats
        ]

        ordering = ["parent_id", "position", "id"]

        permissions = [
            ("publish_page", _("Can publish pages")),
            ("unpublish_page", _("Can unpublish pages")),
            ("preview_page", _("Can preview draft pages")),
            ("revert_page", _("Can revert page to previous version")),
            ("translate_page", _("Can translate pages")),
            ("manage_page_seo", _("Can manage page SEO settings")),
            ("bulk_delete_pages", _("Can bulk delete pages")),
            ("export_pages", _("Can export pages")),
            ("import_pages", _("Can import pages")),
            ("moderate_content", _("Can moderate content")),
            """("approve_content", _("Can approve content")),"""
            ("reject_content", _("Can reject content")),
            ("view_moderation_queue", _("Can view moderation queue")),
            ("schedule_content", _("Can schedule content")),
        ]

    def __str__(self):  # noqa: C901

        return f"{self.title} ({self.locale})"

    def clean(self):  # noqa: C901
        """Validate the page, including blocks validation."""

        errors = {}

        if self.blocks:

            validate_blocks(self.blocks)

            # Check if this is a presentation page

            self._validate_presentation_page_blocks()

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

        if errors:

            raise ValidationError(errors)

    def compute_path(self):  # noqa: C901
        """Compute the full path for this page based on ancestry."""

        if self.parent is None:

            return f"/{self.slug}"

        # Get all ancestors for same locale

        ancestors = []

        current = self.parent

        while current is not None:

            if current.locale_id == self.locale_id:

                """ancestors.append(current.slug)"""

            current = current.parent

        # Build path from root to this page

        path_parts = list(reversed(ancestors))

        # Handle homepage case (empty slug)

        if self.slug:

            """path_parts.append(self.slug)"""

        # For homepage with no parent and no slug, return just "/"

        if not path_parts:

            return "/"

        return "/" + "/".join(path_parts)

    def save(self, *args, **kwargs):  # noqa: C901

        # Recompute path if slug, parent, or locale changed

        update_descendants = False

        if self.pk:

            old_instance = Page.objects.get(pk=self.pk)

            if (
                old_instance.slug != self.slug
                or old_instance.parent_id != self.parent_id
                or old_instance.locale_id != self.locale_id
            ):

                self.path = self.compute_path()

                # Need to update descendants if parent or slug changed

                if (
                    old_instance.parent_id != self.parent_id
                    or old_instance.slug != self.slug
                ):

                    update_descendants = True

        else:

            self.path = self.compute_path()

        super().save(*args, **kwargs)

        # Update descendant paths if needed

        if update_descendants:

            self._update_descendant_paths()

    def _update_descendant_paths(self):  # noqa: C901
        """Update the paths of all descendants when a page is moved or renamed."""

        # Recursively update all descendants

        for child in self.children.all():

            child.path = child.compute_path()

            child.save(update_fields=["path"])

            # Recursively update child's descendants

            child._update_descendant_paths()

    @classmethod
    def siblings_resequence(cls, parent_id=None):  # noqa: C901
        """Resequence siblings to maintain contiguous positions."""

        siblings = cls.objects.filter(parent_id=parent_id).order_by("position", "id")

        for index, page in enumerate(siblings):

            if page.position != index:

                cls.objects.filter(pk=page.pk).update(position=index)

    def _validate_presentation_page_blocks(self):  # noqa: C901
        """
        Validate presentation page requirements.

        Checks if this page is used as a presentation page and validates
        that it has the correct content_detail block configuration.
        """

        # Check if this page is used as a presentation page anywhere

        is_presentation_page = False

        # Check if it's a default presentation page in blog settings

        try:

            if BlogSettings.objects.filter(default_presentation_page=self).exists():

                is_presentation_page = True
        except Exception:
            pass

        # Check if it's a category-specific presentation page

        try:
            if Category.objects.filter(presentation_page=self).exists():
                is_presentation_page = True
        except Exception:
            pass

        # If this is a presentation page, validate content_detail blocks

        if is_presentation_page:

            presentation_resolver.validate_content_detail_block(
                self.blocks or [],
                allowed_labels=[
                    "blog.blogpost"
                ],  # Could be extended for other content types
            )

    def is_presentation_page(self):  # noqa: C901
        """Check if this page is used as a presentation page."""

        try:

            # Check blog settings

            if BlogSettings.objects.filter(default_presentation_page=self).exists():

                return True

            # Check categories

            if Category.objects.filter(presentation_page=self).exists():

                return True

        except Exception:
            pass

        return False

    # Moderation workflow methods

    def submit_for_review(self, user=None):  # noqa: C901
        """Submit page for moderation review."""

        if self.status not in ["draft", "rejected"]:

            raise ValidationError(
                "Page must be in draft or rejected status to submit for review"
            )

        self.status = "pending_review"

        self.submitted_for_review_at = timezone.now()

        self.review_notes = ""  # Clear previous review notes

        self.reviewed_by = None  # Clear previous reviewer

        self.save(
            update_fields=[
                "status",
                "submitted_for_review_at",
                "review_notes",
                "reviewed_by",
            ]
        )

        # Create audit entry

        if hasattr(self, "_current_user") and self._current_user:

            AuditEntry.objects.create(
                content_object=self,
                action="submitted_for_review",
                user=self._current_user,
                metadata={"submitted_at": self.submitted_for_review_at.isoformat()},
            )

    def approve(self, reviewer, notes=""):  # noqa: C901
        """Approve the page."""

        if self.status != "pending_review":

            """raise ValidationError("Page must be pending review to approve")"""

        self.status = "approved"

        self.reviewed_by = reviewer

        self.review_notes = notes

        self.save(update_fields=["status", "reviewed_by", "review_notes"])

        # Create audit entry

        AuditEntry.objects.create(
            content_object=self,
            action="approved",
            user=reviewer,
            metadata={"notes": notes, "approved_at": timezone.now().isoformat()},
        )

    def reject(self, reviewer, notes=""):  # noqa: C901
        """Reject the page with review notes."""

        if self.status != "pending_review":

            raise ValidationError("Page must be pending review to reject")

        self.status = "rejected"

        self.reviewed_by = reviewer

        self.review_notes = notes

        self.save(update_fields=["status", "reviewed_by", "review_notes"])

        # Create audit entry

        AuditEntry.objects.create(
            content_object=self,
            action="rejected",
            user=reviewer,
            metadata={"notes": notes, "rejected_at": timezone.now().isoformat()},
        )

    def can_be_submitted_for_review(self):  # noqa: C901
        """Check if page can be submitted for review."""

        return self.status in ["draft", "rejected"]

    def can_be_approved(self):  # noqa: C901
        """Check if page can be approved."""

        return self.status == "pending_review"

    def can_be_rejected(self):  # noqa: C901
        """Check if page can be rejected."""

        return self.status == "pending_review"


class Redirect(models.Model):

    STATUS_CHOICES = [
        (301, _("301 Permanent")),
        (302, _("302 Temporary")),
        (307, _("307 Temporary Preserve")),
        (308, _("308 Permanent Preserve")),
    ]

    from_path: CharField = models.CharField(max_length=512, db_index=True)

    to_path: CharField = models.CharField(max_length=512)

    status: PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=301
    )

    is_active: BooleanField = models.BooleanField(
        default=True, help_text=_("Enable or disable this redirect")
    )

    notes: TextField = models.TextField(
        blank=True, null=True, help_text=_("Optional notes about this redirect")
    )

    hits: PositiveIntegerField = models.PositiveIntegerField(
        default=0, help_text=_("Number of times this redirect has been used")
    )

    locale: ForeignKey = models.ForeignKey(
        "i18n.Locale", null=True, blank=True, on_delete=models.SET_NULL
    )

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:

        unique_together = [("from_path", "locale")]

    def __str__(self):  # noqa: C901

        return f"{self.from_path} -> {self.to_path} ({self.status})"

    def clean(self):  # noqa: C901

        # Prevent self-redirect

        if self.from_path == self.to_path:

            raise ValidationError(_("Cannot redirect a path to itself."))

        # Normalize leading/trailing slashes

        if not self.from_path.startswith("/"):

            self.from_path = f"/{self.from_path}"

        if not self.to_path.startswith("/"):

            self.to_path = f"/{self.to_path}"

        # Remove trailing slashes except for root

        if len(self.from_path) > 1 and self.from_path.endswith("/"):

            self.from_path = self.from_path.rstrip("/")

        if len(self.to_path) > 1 and self.to_path.endswith("/"):

            self.to_path = self.to_path.rstrip("/")

    def save(self, *args, **kwargs):  # noqa: C901

        self.clean()

        super().save(*args, **kwargs)


# Legacy import compatibility - RedirectImport was removed

RedirectImport = None


# Import models from model_parts


class BlockTypeCategory(models.TextChoices):
    """Predefined categories for block types."""

    LAYOUT = "layout", _("Layout")

    CONTENT = "content", _("Content")

    MEDIA = "media", _("Media")

    MARKETING = "marketing", _("Marketing")

    DYNAMIC = "dynamic", _("Dynamic")

    OTHER = "other", _("Other")


class BlockType(models.Model):
    """
    Database model for managing block types dynamically.

    This replaces the hardcoded BLOCK_MODELS registry.
    """

    # Core identification

    type: CharField = models.CharField(
        max_length=50,
        unique=True,
        help_text=_('Unique identifier for this block type (e.g., "hero", "richtext")'),
    )

    component: CharField = models.CharField(
        max_length=100,
        help_text=_('Frontend component name (e.g., "HeroBlock", "RichtextBlock")'),
    )

    # Display metadata

    label: CharField = models.CharField(
        max_length=100, help_text=_("Human-readable label shown in the editor")
    )

    description: TextField = models.TextField(
        blank=True, help_text=_("Description of what this block does")
    )

    category: CharField = models.CharField(
        max_length=20,
        choices=BlockTypeCategory.choices,
        default=BlockTypeCategory.CONTENT,
        help_text=_("Category for organizing blocks in the editor"),
    )

    icon: CharField = models.CharField(
        max_length=50,
        default="square",
        help_text=_("Icon identifier (Lucide icon name)"),
    )

    # Model relationship for dynamic blocks

    model_name: CharField = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Model to fetch data from (e.g., "blog.BlogPost", "cms.Page")'),
    )

    data_source: CharField = models.CharField(
        max_length=50,
        choices=[
            ("static", _("Static - No data fetching")),
            ("single", _("Single - Select one item")),
            ("list", _("List - Query multiple items")),
            ("custom", _("Custom - Complex data fetching")),
        ],
        default="static",
        help_text=_("How this block fetches data"),
    )

    api_endpoint: CharField = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('API endpoint for data fetching (e.g., "/api/v1/blog/posts/")'),
    )

    # Query configuration for list blocks

    query_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Schema for query parameters (filters, ordering, etc.)"),
    )

    # Configuration

    is_active: BooleanField = models.BooleanField(
        default=True, help_text=_("Whether this block type is available in the editor")
    )

    preload: BooleanField = models.BooleanField(
        default=False,
        help_text=_("Whether to preload this component for better performance"),
    )

    editing_mode: CharField = models.CharField(
        max_length=20,
        choices=[
            ("inline", _("Inline")),
            ("modal", _("Modal")),
            ("sidebar", _("Sidebar")),
        ],
        default="inline",
        help_text=_("How this block should be edited"),
    )

    # Schema and defaults

    schema = models.JSONField(
        default=dict, help_text=_("JSON schema for validating block props")
    )

    default_props = models.JSONField(
        default=dict,
        help_text=_("Default props when creating a new instance of this block"),
    )

    # Metadata

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: DateTimeField = models.DateTimeField(auto_now=True)

    created_by: ForeignKey = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_block_types",
    )

    updated_by: ForeignKey = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_block_types",
    )

    class Meta:

        db_table = "cms_block_types"

        verbose_name = _("Block Type")

        verbose_name_plural = _("Block Types")

        ordering = ["category", "label"]

    def __str__(self):  # noqa: C901

        return f"{self.label} ({self.type})"

    def clean(self):  # noqa: C901
        """Validate block type configuration."""

        super().clean()

        # Ensure component follows naming convention

        if self.component and not self.component.endswith("Block"):

            raise ValidationError(
                {
                    "component": _(
                        'Component name should end with "Block" (e.g., "HeroBlock")'
                    )
                }
            )

        # Validate icon name (basic check)

        if self.icon and not self.icon.replace("-", "").replace("_", "").isalnum():

            raise ValidationError(
                {
                    "icon": _(
                        "Icon name should only contain letters, numbers, hyphens, and underscores"
                    )
                }
            )

    def save(self, *args, **kwargs):  # noqa: C901

        self.full_clean()

        super().save(*args, **kwargs)

        # Clear any cached block registry data

        cache.delete("block_types_registry")

    @classmethod
    def get_registry_dict(cls):  # noqa: C901
        """
        Get all active block types as a dictionary for the dynamic registry.

        Returns format compatible with existing BLOCK_MODELS structure.
        """

        registry = cache.get("block_types_registry")

        if registry is None:

            block_types = cls.objects.filter(is_active=True).values(
                "type",
                "component",
                "label",
                "description",
                "category",
                "icon",
                "preload",
                "editing_mode",
                "schema",
                "default_props",
                "model_name",
                "data_source",
                "api_endpoint",
                "query_schema",
            )

            registry = {bt["type"]: bt for bt in block_types}

            cache.set("block_types_registry", registry, timeout=300)  # 5 minutes

        return registry

    @classmethod
    def get_block_metadata(cls):  # noqa: C901
        """Get metadata for all active block types for API responses."""

        return cls.objects.filter(is_active=True).values(
            "type",
            "component",
            "label",
            "description",
            "category",
            "icon",
            "preload",
            "editing_mode",
            "schema",
            "default_props",
            "model_name",
            "data_source",
            "api_endpoint",
            "query_schema",
        )

    def get_model_class(self):  # noqa: C901
        """Get the actual model class for this block type."""

        if not self.model_name:

            return None

        try:

            app_label, model_name = self.model_name.split(".")

# Imports that were malformed - commented out
#             """return apps.get_model(app_label, model_name)"""

        except (ValueError, LookupError):

            return None

    def get_queryset(self):  # noqa: C901
        """Get the base queryset for list-type blocks."""

        model_class = self.get_model_class()

        if not model_class or self.data_source != "list":

            return None

        queryset = model_class.objects.all()

        # Apply common filters if the model has them

        if hasattr(model_class, "objects"):

            if hasattr(queryset, "published"):

                queryset = queryset.published()

            elif hasattr(model_class, "status"):

                queryset = queryset.filter(status="published")

            if hasattr(model_class, "is_active"):

                queryset = queryset.filter(is_active=True)

        return queryset
