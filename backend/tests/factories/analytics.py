

"""Analytics factories for testing metrics and events."""



from django.utils import timezone



import factory

import factory.django

from faker import Faker



from apps.analytics.models import Event, PageView, Session



from .base import BaseFactory, UserFactory

from .cms import PageFactory



fake = Faker()



class SessionFactory(BaseFactory):

    """Factory for user sessions."""



    class Meta:

        model = Session



    session_id = factory.LazyFunction(lambda: fake.uuid4())

    user = factory.SubFactory(UserFactory)

    ip_address = factory.Faker("ipv4")

    user_agent = factory.Faker("user_agent")

    started_at = factory.LazyFunction(timezone.now)

    ended_at = factory.LazyAttribute(

        lambda obj: fake.date_time_between(start_date=obj.started_at, end_date="+1h")

    )



class EventFactory(BaseFactory):

    """Factory for analytics events."""



    class Meta:

        model = Event



    session = factory.SubFactory(SessionFactory)

    event_type = factory.Iterator(

        ["page_view", "click", "form_submit", "download", "search"]

    )

    event_data = factory.LazyAttribute(

        lambda obj: {

            "page_view": {"url": fake.url(), "title": fake.sentence()},

            "click": {

                "element": fake.word(),

                "position": {

                    "x": fake.random_int(0, 1920),

                    "y": fake.random_int(0, 1080),

                },

            },

            "form_submit": {"form_id": fake.word(), "fields": fake.random_int(1, 10)},

            "download": {

                "filename": fake.file_name(),

                "size": fake.random_int(1024, 10485760),

            },

            "search": {

                "query": fake.sentence(nb_words=3),

                "results": fake.random_int(0, 100),

            },

        }.get(obj.event_type, {})

    )



    timestamp = factory.LazyFunction(timezone.now)



class PageViewFactory(BaseFactory):

    """Factory for page view analytics."""



    class Meta:

        model = PageView



    session = factory.SubFactory(SessionFactory)

    page = factory.SubFactory(PageFactory)

    url = factory.LazyAttribute(lambda obj: f"/page/{obj.page.slug}/")

    referrer = factory.Faker("url")

    time_on_page = factory.LazyAttribute(

        lambda obj: fake.random_int(5, 600)

    )  # 5 seconds to 10 minutes

    timestamp = factory.LazyFunction(timezone.now)

