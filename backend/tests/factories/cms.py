
CMS-specific factories for pages, categories, and content.

from django.utils.text import slugify

import factory
import factory.django
from faker import Faker

from apps.cms.model_parts.category import Category, Tag
from apps.cms.models import Page
from apps.i18n.models import Locale

from .base import BaseFactory

fake = Faker()

class LocaleFactory(BaseFactory):
    """Factory for creating locales."""

    class Meta:
        model = Locale
        django_get_or_create = ("code",)

    code = factory.Iterator(["en", "es", "fr", "de", "it", "pt"])
    name = factory.LazyAttribute(
        lambda obj: {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
        }.get(obj.code, obj.code.title())
    )
    native_name = factory.LazyAttribute(
        lambda obj: {
            "en": "English",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
            "it": "Italiano",
            "pt": "Português",
        }.get(obj.code, obj.code.title())
    )
    is_active = True
    is_default = factory.LazyAttribute(lambda obj: obj.code == "en")

class CategoryFactory(BaseFactory):
    """Factory for creating categories."""

    class Meta:
        model = Category

    name = factory.Faker("word")
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))
    description = factory.Faker("sentence", nb_words=10)
    is_active = True

class TagFactory(BaseFactory):
    """Factory for creating tags."""

    class Meta:
        model = Tag

    name = factory.Faker("word")
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name))

class PageFactory(BaseFactory):
    """Factory for creating CMS pages."""

    class Meta:
        model = Page

    title = factory.Faker("sentence", nb_words=4)
    slug = factory.LazyAttribute(lambda obj: slugify(obj.title))
    locale = factory.SubFactory(LocaleFactory, code="en", is_default=True)
    status = factory.Iterator(["draft", "published", "archived"])

    # Generate realistic block content
    blocks = factory.LazyAttribute(
        lambda obj: [
            {"type": "text", "props": {"content": fake.paragraph(nb_sentences=5)}},
            {
                "type": "heading",
                "props": {
                    "text": fake.sentence(nb_words=6),
                    "level": fake.random_int(min=1, max=6),
                },
            },
        ]
    )

    # SEO fields
    seo = factory.LazyAttribute(
        lambda obj: {
            "title": obj.title,
            "description": fake.sentence(nb_words=15),
            "keywords": [fake.word() for _ in range(5)],
        }
    )

    @factory.post_generation
    def categories(self, create, extracted, **kwargs):
        if not create:

        if extracted:
            for category in extracted:
                self.categories.add(category)
        else:
            # Add 1-3 random categories
            categories = CategoryFactory.create_batch(fake.random_int(min=1, max=3))
            for category in categories:
                self.categories.add(category)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:

        if extracted:
            for tag in extracted:
                self.tags.add(tag)
        else:
            # Add 2-5 random tags
            tags = TagFactory.create_batch(fake.random_int(min=2, max=5))
            for tag in tags:
                self.tags.add(tag)

class PublishedPageFactory(PageFactory):
    """Factory for published pages."""

    status = "published"
    published_at = factory.LazyFunction(lambda: fake.date_time_this_year())

class DraftPageFactory(PageFactory):
    """Factory for draft pages."""

    status = "draft"
    published_at = None
