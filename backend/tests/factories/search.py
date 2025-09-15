"""Test data factories for search app models."""

import uuid

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

import factory
import factory.django
from faker import Faker

from apps.search.models import SearchIndex, SearchQuery, SearchSuggestion

from .base import BaseFactory, UserFactory

fake = Faker()


class SearchIndexFactory(BaseFactory):
    """Factory for creating SearchIndex test data."""

    class Meta:
        model = SearchIndex

    id = factory.LazyFunction(uuid.uuid4)

    # Generic foreign key fields - these need to be set manually
    # content_type = factory.SubFactory(ContentTypeFactory)
    # object_id = factory.SelfAttribute('content_object.id')

    title = factory.Faker("sentence", nb_words=4)
    content = factory.Faker("text", max_nb_chars=1000)
    excerpt = factory.Faker("text", max_nb_chars=200)
    url = factory.Faker("url")
    image_url = factory.Faker("image_url")
    locale_code = "en"

    search_category = factory.Faker(
        "random_element", elements=("page", "blog", "product", "news")
    )
    search_tags = factory.LazyFunction(
        lambda: fake.words(nb=fake.random_int(min=1, max=5))
    )

    is_published = True
    published_at = factory.LazyFunction(timezone.now)
    search_weight = factory.Faker(
        "pyfloat", positive=True, min_value=0.1, max_value=2.0
    )

    @classmethod
    def create_for_object(cls, content_object, **kwargs):
        """Create a SearchIndex for a specific content object."""
        content_type = ContentType.objects.get_for_model(content_object)

        defaults = {
            "content_type": content_type,
            "object_id": content_object.id,
            "content_object": content_object,
        }

        # Try to extract meaningful data from the object
        if hasattr(content_object, "title"):
            defaults["title"] = content_object.title
        if hasattr(content_object, "locale") and content_object.locale:
            defaults["locale_code"] = content_object.locale.code
        if hasattr(content_object, "get_absolute_url"):
            try:
                defaults["url"] = content_object.get_absolute_url()
            except:
                pass

        defaults.update(kwargs)
        return cls.create(**defaults)


class SearchQueryFactory(BaseFactory):
    """Factory for creating SearchQuery test data."""

    class Meta:
        model = SearchQuery

    id = factory.LazyFunction(uuid.uuid4)

    query_text = factory.Faker("sentence", nb_words=fake.random_int(min=1, max=4))
    filters = factory.LazyFunction(
        lambda: (
            {
                "category": fake.random_element(["page", "blog", "product"]),
                "locale": fake.random_element(["en", "es", "fr"]),
            }
            if fake.boolean()
            else {}
        )
    )

    user = factory.SubFactory(UserFactory)
    session_key = factory.LazyFunction(lambda: fake.uuid4()[:40])
    ip_address = factory.Faker("ipv4")

    result_count = factory.Faker("random_int", min=0, max=50)
    execution_time_ms = factory.Faker("random_int", min=50, max=2000)

    # clicked_result and click_position can be set manually when needed
    clicked_result = None
    click_position = None

    @factory.post_generation
    def set_click_data(self, create, extracted, **kwargs):
        """Optionally set click data after creation."""
        if not create:
            return

        if extracted:
            if "clicked_result" in extracted:
                self.clicked_result = extracted["clicked_result"]
            if "click_position" in extracted:
                self.click_position = extracted["click_position"]
            self.save()


class SearchSuggestionFactory(BaseFactory):
    """Factory for creating SearchSuggestion test data."""

    class Meta:
        model = SearchSuggestion

    id = factory.LazyFunction(uuid.uuid4)

    suggestion_text = factory.Faker("sentence", nb_words=fake.random_int(min=1, max=3))
    normalized_text = factory.LazyAttribute(
        lambda obj: obj.suggestion_text.lower().strip()
    )

    search_count = factory.Faker("random_int", min=1, max=100)
    result_count = factory.Faker("random_int", min=1, max=20)
    click_through_rate = factory.Faker(
        "pyfloat", positive=True, min_value=0.0, max_value=1.0
    )

    categories = factory.LazyFunction(
        lambda: fake.words(nb=fake.random_int(min=1, max=3))
    )
    locale_codes = factory.LazyFunction(
        lambda: [fake.random_element(["en", "es", "fr", "de"])]
    )

    is_active = True
    is_promoted = factory.Faker("boolean", chance_of_getting_true=20)

    last_searched_at = factory.LazyFunction(
        lambda: fake.date_time_between(
            start_date="-30d", end_date="now", tzinfo=timezone.get_current_timezone()
        )
    )


# Specialized factories for common use cases


class PopularSearchSuggestionFactory(SearchSuggestionFactory):
    """Factory for popular search suggestions."""

    search_count = factory.Faker("random_int", min=50, max=500)
    click_through_rate = factory.Faker(
        "pyfloat", positive=True, min_value=0.3, max_value=0.8
    )
    is_promoted = True


class PageSearchIndexFactory(SearchIndexFactory):
    """Factory for page-specific search indices."""

    search_category = "page"
    search_weight = factory.Faker(
        "pyfloat", positive=True, min_value=0.8, max_value=1.5
    )


class BlogSearchIndexFactory(SearchIndexFactory):
    """Factory for blog-specific search indices."""

    search_category = "blog"
    search_weight = factory.Faker(
        "pyfloat", positive=True, min_value=0.6, max_value=1.2
    )
    search_tags = factory.LazyFunction(
        lambda: fake.words(nb=fake.random_int(min=2, max=6))
    )


class NoResultSearchQueryFactory(SearchQueryFactory):
    """Factory for search queries with no results."""

    result_count = 0
    execution_time_ms = factory.Faker("random_int", min=100, max=500)
    clicked_result = None
    click_position = None


class SlowSearchQueryFactory(SearchQueryFactory):
    """Factory for slow search queries."""

    execution_time_ms = factory.Faker("random_int", min=1000, max=5000)
    result_count = factory.Faker("random_int", min=1, max=100)


class AnonymousSearchQueryFactory(SearchQueryFactory):
    """Factory for anonymous search queries."""

    user = None
    session_key = factory.LazyFunction(lambda: f"anon_{fake.uuid4()[:20]}")


# Factory methods for creating related objects


def create_search_scenario(content_objects=None, num_queries=5, num_suggestions=3):
    """
    Create a complete search scenario with indices, queries, and suggestions.

    Args:
        content_objects: List of objects to create indices for
        num_queries: Number of search queries to create
        num_suggestions: Number of suggestions to create

    Returns:
        dict: Created objects organized by type
    """
    scenario_data = {"indices": [], "queries": [], "suggestions": []}

    # Create search indices for provided objects
    if content_objects:
        for obj in content_objects:
            index = SearchIndexFactory.create_for_object(obj)
            scenario_data["indices"].append(index)

    # Create search queries
    for _ in range(num_queries):
        query = SearchQueryFactory()
        scenario_data["queries"].append(query)

        # Randomly assign clicks to some queries
        if scenario_data["indices"] and fake.boolean(chance_of_getting_true=30):
            query.clicked_result = fake.random_element(scenario_data["indices"])
            query.click_position = fake.random_int(min=1, max=5)
            query.save()

    # Create suggestions based on queries
    query_texts = [q.query_text for q in scenario_data["queries"]]
    for _ in range(num_suggestions):
        suggestion_text = (
            fake.random_element(query_texts)
            if query_texts
            else fake.sentence(nb_words=2)
        )
        suggestion = SearchSuggestionFactory(suggestion_text=suggestion_text)
        scenario_data["suggestions"].append(suggestion)

    return scenario_data


def create_multilingual_search_data(locales=None):
    """
    Create search data for multiple locales.

    Args:
        locales: List of locale codes (defaults to ['en', 'es', 'fr'])

    Returns:
        dict: Search data organized by locale
    """
    if locales is None:
        locales = ["en", "es", "fr"]

    multilingual_data = {}

    for locale_code in locales:
        multilingual_data[locale_code] = {
            "indices": [
                SearchIndexFactory(locale_code=locale_code)
                for _ in range(fake.random_int(min=3, max=8))
            ],
            "queries": [
                SearchQueryFactory(filters={"locale": locale_code})
                for _ in range(fake.random_int(min=5, max=15))
            ],
            "suggestions": [
                SearchSuggestionFactory(locale_codes=[locale_code])
                for _ in range(fake.random_int(min=2, max=6))
            ],
        }

    return multilingual_data
