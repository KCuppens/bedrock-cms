from .base import UserFactory
from .i18n import LocaleFactory

Account-specific factories for users, roles, and permissions.

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

import factory
import factory.django
from faker import Faker

from apps.accounts.models import ScopedLocale, ScopedSection, UserProfile

from .base import BaseFactory

fake = Faker()

User = get_user_model()

class GroupFactory(BaseFactory):
    """Factory for creating groups."""

    class Meta:
        model = Group

    name = factory.Faker("word")

    @factory.post_generation
    def permissions(self, create, extracted, **kwargs):
        if not create:

        if extracted:
            for permission in extracted:
                self.permissions.add(permission)

class UserProfileFactory(BaseFactory):
    """Factory for user profiles."""

    class Meta:
        model = UserProfile

    user = factory.SubFactory(lambda: None)
    avatar = None
    bio = factory.Faker("paragraph", nb_sentences=3)
    timezone = factory.Iterator(
        [
            "UTC",
            "America/New_York",
            "Europe/London",
            "Europe/Paris",
            "Asia/Tokyo",
            "Australia/Sydney",
        ]
    )
    language_preference = factory.Iterator(["en", "es", "fr", "de"])

class ScopedSectionFactory(BaseFactory):
    """Factory for scoped sections."""

    class Meta:
        model = ScopedSection

    user = factory.SubFactory(lambda: None)
    section = factory.Iterator(["cms", "blog", "media", "analytics"])
    permission_level = factory.Iterator(["view", "edit", "admin"])

class ScopedLocaleFactory(BaseFactory):
    """Factory for scoped locales."""

    class Meta:
        model = ScopedLocale

    user = factory.SubFactory(lambda: None)
    locale = factory.SubFactory(lambda: None)
    permission_level = factory.Iterator(["view", "edit", "admin"])

# Specialized user factories with specific roles
class EditorUserFactory(UserFactory):
    """Factory for editor users with CMS permissions."""

    @factory.post_generation
    def setup_editor_permissions(self, create, extracted, **kwargs):
        if not create:

        # Add to editors group
        editor_group, _ = Group.objects.get_or_create(name="Editors")
        self.groups.add(editor_group)

        # Create profile
        UserProfileFactory(user=self)

        # Add CMS section access
        ScopedSectionFactory(user=self, section="cms", permission_level="edit")

class TranslatorUserFactory(UserFactory):
    """Factory for translator users with i18n permissions."""

    @factory.post_generation
    def setup_translator_permissions(self, create, extracted, **kwargs):
        if not create:

        # Add to translators group
        translator_group, _ = Group.objects.get_or_create(name="Translators")
        self.groups.add(translator_group)

        # Create profile
        UserProfileFactory(user=self)

        # Add locale access for Spanish
        locale_es = LocaleFactory(code="es")
        ScopedLocaleFactory(user=self, locale=locale_es, permission_level="edit")
