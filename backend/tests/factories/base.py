"""
Base factory classes and utilities for test data generation.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone

import factory
import factory.django
from faker import Faker

fake = Faker()

User = get_user_model()


class BaseFactory(factory.django.DjangoModelFactory):
    """Base factory with common patterns."""

    class Meta:
        abstract = True

    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class UserFactory(BaseFactory):
    """Factory for creating test users."""

    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        password = extracted or "testpass123"
        self.set_password(password)
        self.save()


class AdminUserFactory(UserFactory):
    """Factory for admin users."""

    is_staff = True
    is_superuser = True
    email = factory.Sequence(lambda n: f"admin{n}@example.com")


class StaffUserFactory(UserFactory):
    """Factory for staff users."""

    is_staff = True
    email = factory.Sequence(lambda n: f"staff{n}@example.com")
