

"""Comprehensive test data fixtures for consistent testing across modules."""



from unittest.mock import patch

from django.contrib.auth import get_user_model

import pytest
from faker import Faker

from ..factories import (
    AdminUserFactory,
    CategoryFactory,
    DraftPageFactory,
    EditorUserFactory,
    EventFactory,
    LocaleFactory,
    MediaItemFactory,
    PageFactory,
    PublishedPageFactory,
    SessionFactory,
    TagFactory,
    TranslationUnitFactory,
    TranslatorUserFactory,
    UserFactory,
)

User = get_user_model()

fake = Faker()



"""@pytest.fixture"""

def sample_users():

    """Create a comprehensive set of users for testing."""

    return {

        "admin": AdminUserFactory(),

        "editor": EditorUserFactory(),

        "translator": TranslatorUserFactory(),

        "regular": UserFactory(),

        "staff": UserFactory(is_staff=True),

    }



"""@pytest.fixture"""

def sample_locales():

    """Create standard locales for testing."""

    return {

        "en": LocaleFactory(code="en", is_default=True, is_active=True),

        "es": LocaleFactory(code="es", is_active=True),

        "fr": LocaleFactory(code="fr", is_active=True),

        "de": LocaleFactory(code="de", is_active=False),  # Inactive for testing

    }



"""@pytest.fixture"""

def sample_cms_data(sample_locales, sample_users):

    """Create comprehensive CMS test data."""

    # Create categories and tags

    categories = CategoryFactory.create_batch(5)

    tags = TagFactory.create_batch(10)



    # Create pages in different states

    published_pages = PublishedPageFactory.create_batch(

        3, locale=sample_locales["en"], categories=categories[:2], tags=tags[:5]

    )



    draft_pages = DraftPageFactory.create_batch(

        2, locale=sample_locales["en"], categories=categories[2:], tags=tags[5:]

    )



    # Create multilingual content

    spanish_pages = PageFactory.create_batch(

        2, locale=sample_locales["es"], status="published"

    )



    return {

        "categories": categories,

        "tags": tags,

        "published_pages": published_pages,

        "draft_pages": draft_pages,

        "spanish_pages": spanish_pages,

        "all_pages": published_pages + draft_pages + spanish_pages,

    }



"""@pytest.fixture"""

def sample_media_data():

    """Create media items for testing."""

    return {

        "images": MediaItemFactory.create_batch(5, file_type="image"),

        "documents": MediaItemFactory.create_batch(3, file_type="document"),

        "videos": MediaItemFactory.create_batch(2, file_type="video"),

    }



"""@pytest.fixture"""

def sample_translation_data(sample_cms_data, sample_locales, sample_users):

    """Create translation units for testing."""

    translation_units = []



    for page in sample_cms_data["all_pages"][:3]:  # First 3 pages

        for field in ["title", "blocks"]:

            unit = TranslationUnitFactory(

                content_object=page,

                field=field,

                source_locale=sample_locales["en"],

                target_locale=sample_locales["es"],

                updated_by=sample_users["translator"],

            )

            """translation_units.append(unit)"""



    return translation_units



"""@pytest.fixture"""

def sample_analytics_data():

    """Create analytics data for testing."""

    sessions = SessionFactory.create_batch(10)

    events = []



    for session in sessions:

        # Create 3-8 events per session

        session_events = EventFactory.create_batch(

            fake.random_int(min=3, max=8), session=session

        )

        events.extend(session_events)



    return {"sessions": sessions, "events": events}



"""@pytest.fixture"""

def mock_external_services():

    """Mock external services for isolated testing."""

    mocks = {}



    # Email service mock

    """with patch("apps.emails.services.EmailService") as email_mock:"""

        email_mock.send.return_value = {"status": "sent", "message_id": "test-123"}

        mocks["email"] = email_mock



        # File storage mock

        """with patch("apps.media.services.StorageService") as storage_mock:"""

            storage_mock.upload.return_value = {"url": "https://test.com/file.jpg"}

            mocks["storage"] = storage_mock



            # Analytics service mock

            """with patch("apps.analytics.services.AnalyticsService") as analytics_mock:"""

                analytics_mock.track.return_value = True

                mocks["analytics"] = analytics_mock



                yield mocks



"""@pytest.fixture"""

def api_client():

    """Enhanced API client for testing."""

    from rest_framework.test import APIClient



    return APIClient()



"""@pytest.fixture"""

def authenticated_client(api_client, sample_users):

    """API client authenticated as regular user."""

    api_client.force_authenticate(user=sample_users["regular"])

    return api_client



"""@pytest.fixture"""

def admin_client(api_client, sample_users):

    """API client authenticated as admin user."""

    api_client.force_authenticate(user=sample_users["admin"])

    return api_client



"""@pytest.fixture"""

def editor_client(api_client, sample_users):

    """API client authenticated as editor user."""

    api_client.force_authenticate(user=sample_users["editor"])

    return api_client
