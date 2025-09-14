"""Analytics factories for testing metrics and events."""

from django.utils import timezone

import factory
import factory.django
from faker import Faker

from apps.analytics.models import PageView

from .base import BaseFactory, UserFactory
from .cms import PageFactory

fake = Faker()


# Dummy factories to satisfy imports (models don't exist yet)
class EventFactory(BaseFactory):
    """Dummy factory for analytics events."""

    class Meta:
        abstract = True


class SessionFactory(BaseFactory):
    """Dummy factory for sessions."""

    class Meta:
        abstract = True


class PageViewFactory(BaseFactory):
    """Factory for page view analytics."""

    class Meta:
        model = PageView

    # Comment out session since SessionFactory doesn't exist
    # session = factory.SubFactory(SessionFactory)

    page = factory.SubFactory(PageFactory)

    url = factory.LazyAttribute(lambda obj: f"/page/{obj.page.slug}/")

    referrer = factory.Faker("url")

    time_on_page = factory.LazyAttribute(
        lambda obj: fake.random_int(5, 600)
    )  # 5 seconds to 10 minutes

    timestamp = factory.LazyFunction(timezone.now)
