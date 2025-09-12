

Internationalization factories for translation testing.



import factory

import factory.django

from faker import Faker



from apps.cms.models import Page

from apps.i18n.models import TranslationUnit, UiMessage, UiMessageTranslation



from .base import BaseFactory, UserFactory

from .cms import LocaleFactory, PageFactory



fake = Faker()



class TranslationUnitFactory(BaseFactory):

    """Factory for creating translation units."""



    class Meta:

        model = TranslationUnit



    source_locale = factory.SubFactory(LocaleFactory, code="en", is_default=True)

    target_locale = factory.SubFactory(LocaleFactory, code="es")

    field = factory.Iterator(["title", "blocks", "description"])

    source_text = factory.Faker("sentence", nb_words=8)

    target_text = factory.Faker("sentence", nb_words=8)

    status = factory.Iterator(["draft", "needs_review", "approved", "rejected"])

    updated_by = factory.SubFactory(UserFactory)



    # Set up content object (usually a Page)

    @factory.lazy_attribute

    def content_type(self):

        from django.contrib.contenttypes.models import ContentType



        return ContentType.objects.get_for_model(Page)



    @factory.lazy_attribute

    def object_id(self):

        page = PageFactory()

        return page.id



class UiMessageFactory(BaseFactory):

    """Factory for UI messages."""



    class Meta:

        model = UiMessage

        django_get_or_create = ("key",)



    key = factory.Sequence(lambda n: f"ui.message.{n}")

    namespace = factory.Iterator(["general", "forms", "navigation", "errors"])

    description = factory.Faker("sentence", nb_words=6)

    default_value = factory.Faker("sentence", nb_words=4)



class UiMessageTranslationFactory(BaseFactory):

    """Factory for UI message translations."""



    class Meta:

        model = UiMessageTranslation



    message = factory.SubFactory(UiMessageFactory)

    locale = factory.SubFactory(LocaleFactory)

    value = factory.Faker("sentence", nb_words=4)

    status = factory.Iterator(["draft", "approved", "rejected"])

    updated_by = factory.SubFactory(UserFactory)

