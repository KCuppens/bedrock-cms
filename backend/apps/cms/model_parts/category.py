from django.contrib.auth import get_user_model

from django.db import models

from django.utils.text import slugify


User = get_user_model()


class Category(models.Model):
    """Category model for organizing content"""

    name: models.CharField = models.CharField(max_length=100)

    slug: models.SlugField = models.SlugField(max_length=100, unique=True, blank=True)

    description: models.TextField = models.TextField(blank=True)

    parent: models.ForeignKey = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )

    color: models.CharField = models.CharField(
        max_length=7, default="#6B7280"
    )  # Hex color

    icon: models.CharField = models.CharField(
        max_length=50, blank=True
    )  # Icon name/class

    order: models.IntegerField = models.IntegerField(default=0)

    is_active: models.BooleanField = models.BooleanField(default=True)

    created_by: models.ForeignKey = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_categories"
    )

    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:

        verbose_name_plural = "Categories"

        ordering = ["order", "name"]

        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):

        return self.name


class Tag(models.Model):
    """Tag model for content tagging"""

    name: models.CharField = models.CharField(max_length=50, unique=True)

    slug: models.SlugField = models.SlugField(max_length=50, unique=True, blank=True)

    description: models.TextField = models.TextField(blank=True)

    color: models.CharField = models.CharField(
        max_length=7, default="#6B7280"
    )  # Hex color

    created_by: models.ForeignKey = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_tags"
    )

    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:

        ordering = ["name"]

        indexes = [
            models.Index(fields=["slug"]),
        ]

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):

        return self.name


class Collection(models.Model):
    """Collection model for grouping content"""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    name: models.CharField = models.CharField(max_length=200)

    slug: models.SlugField = models.SlugField(max_length=200, unique=True, blank=True)

    description: models.TextField = models.TextField(blank=True)

    cover_image: models.URLField = models.URLField(blank=True)

    status: models.CharField = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft"
    )

    # Relations

    categories: models.ManyToManyField = models.ManyToManyField(
        Category, blank=True, related_name="collections"
    )

    tags: models.ManyToManyField = models.ManyToManyField(
        Tag, blank=True, related_name="collections"
    )

    # Metadata

    meta_title: models.CharField = models.CharField(max_length=200, blank=True)

    meta_description: models.TextField = models.TextField(blank=True)

    # Tracking

    created_by: models.ForeignKey = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_collections"
    )

    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    published_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    class Meta:

        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):

        return self.name
