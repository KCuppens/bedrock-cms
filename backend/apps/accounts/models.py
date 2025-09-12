from typing import Any

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateTimeField,
    OneToOneField,
    TextField,
    URLField,
)
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager["User"]):
    """Custom user manager for email-based authentication"""

    def create_user(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> "User":
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> "User":
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """Custom user model with email as username"""

    username = None  # type: ignore  # Remove username field
    email = models.EmailField(_("Email address"), unique=True)
    name: CharField = models.CharField(_("Full name"), max_length=150, blank=True)
    avatar = models.ImageField(
        _("Avatar"),
        upload_to="avatars/%Y/%m/%d/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "gif", "webp"]
            )
        ],
    )
    last_seen: DateTimeField = models.DateTimeField(
        _("Last seen"), default=timezone.now, db_index=True
    )

    # Additional fields for SaaS features
    created_at: DateTimeField = models.DateTimeField(_("Created"), auto_now_add=True)
    updated_at: DateTimeField = models.DateTimeField(_("Updated"), auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()  # type: ignore

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["last_seen"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):  # noqa: C901
        return self.email

    def get_full_name(self):  # noqa: C901
        """Return the full name for the user."""
        # Try first_name and last_name first (from AbstractUser)
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        # Fall back to name field
        return self.name or self.email

    def get_short_name(self):  # noqa: C901
        """Return the short name for the user."""
        # Try first_name first (from AbstractUser)
        if self.first_name:
            return self.first_name
        # Fall back to name field
        return self.name.split(" ")[0] if self.name else self.email.split("@")[0]

    def update_last_seen(self):  # noqa: C901
        """Update the last_seen timestamp using F expression for atomic update"""
        User.objects.filter(pk=self.pk).update(last_seen=timezone.now())

    @cached_property
    def user_groups(self):  # noqa: C901
        """Cache user groups to prevent repeated database queries"""
        return set(self.groups.values_list("name", flat=True))

    def has_group(self, group_name):  # noqa: C901
        """Check if user belongs to a specific group"""
        return group_name in self.user_groups

    def is_admin(self):  # noqa: C901
        """Check if user is an admin"""
        return "Admin" in self.user_groups or self.is_superuser

    def is_manager(self):  # noqa: C901
        """Check if user is a manager or admin"""
        return "Manager" in self.user_groups or self.is_admin()

    def is_member(self):  # noqa: C901
        """Check if user is a member, manager, or admin"""
        return "Member" in self.user_groups or self.is_manager()

class UserProfile(models.Model):
    """Extended user profile information"""

    user: OneToOneField = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )

    # Profile fields
    bio: TextField = models.TextField(_("Biography"), max_length=500, blank=True)
    location: CharField = models.CharField(_("Location"), max_length=100, blank=True)
    website: URLField = models.URLField(_("Website"), blank=True)
    phone: CharField = models.CharField(_("Phone number"), max_length=20, blank=True)

    # Preferences
    timezone: CharField = models.CharField(_("Timezone"), max_length=50, default="UTC")
    language: CharField = models.CharField(_("Language"), max_length=10, default="en")
    receive_notifications: BooleanField = models.BooleanField(
        _("Receive notifications"), default=True
    )
    receive_marketing_emails: BooleanField = models.BooleanField(
        _("Receive marketing emails"), default=False
    )

    # Timestamps
    created_at: DateTimeField = models.DateTimeField(_("Created"), auto_now_add=True)
    updated_at: DateTimeField = models.DateTimeField(_("Updated"), auto_now=True)

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):  # noqa: C901
        return f"{self.user.email} Profile"

# Import RBAC models
