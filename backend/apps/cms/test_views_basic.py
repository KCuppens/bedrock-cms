from django.contrib.auth import get_user_model

from django.test import TestCase



from rest_framework import status

from rest_framework.test import APIClient, APITestCase



from apps.cms.models import Page

from apps.cms.views import PagesViewSet

from apps.i18n.models import Locale



Basic CMS Views tests - simplified approach for quick coverage gains.



User = get_user_model()



class PagesViewSetBasicTestCase(APITestCase):

    """Basic tests for PagesViewSet core functionality."""



    def setUp(self):

        """Set up test data."""

        self.client = APIClient()



        # Create locale

        self.locale_en = Locale.objects.create(

            code="en",

            name="English",

            native_name="English",

            is_default=True,

            is_active=True,

        )



        # Create users

        self.admin_user = User.objects.create_user(

            email="admin@example.com",

            password="testpass123",

            is_staff=True,

            is_superuser=True,

        )



        # Create test pages

        self.published_page = Page.objects.create(

            title="Published Page",

            slug="published-page",

            path="/published-page/",

            locale=self.locale_en,

            status="published",

            blocks=[{"type": "text", "props": {"content": "Test content"}}],

        )



    def test_get_serializer_class_selection(self):

        """Test serializer class selection based on action."""

        viewset = PagesViewSet()



        # Read actions should use PageReadSerializer

        viewset.action = "list"

        serializer_class = viewset.get_serializer_class()

        self.assertEqual(serializer_class.__name__, "PageReadSerializer")



        # Write actions should use PageWriteSerializer

        viewset.action = "create"

        serializer_class = viewset.get_serializer_class()

        self.assertEqual(serializer_class.__name__, "PageWriteSerializer")



    def test_list_pages_unauthenticated(self):

        """Test listing pages without authentication."""

        response = self.client.get("/api/v1/cms/api/pages/")



        # Should still work but only show published content

        self.assertEqual(response.status_code, status.HTTP_200_OK)



    def test_list_pages_authenticated(self):

        """Test listing pages with authentication."""

        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get("/api/v1/cms/api/pages/")



        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertIn("results", data)



    def test_retrieve_page(self):

        """Test page retrieval."""

        response = self.client.get(f"/api/v1/cms/api/pages/{self.published_page.id}/")



        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["id"], self.published_page.id)

        self.assertEqual(data["title"], self.published_page.title)



class PageModelTestCase(TestCase):

    """Test Page model functionality."""



    def setUp(self):

        """Set up test data."""

        self.locale_en = Locale.objects.create(

            code="en",

            name="English",

            native_name="English",

            is_default=True,

            is_active=True,

        )



    def test_page_creation(self):

        """Test basic page creation."""

        page = Page.objects.create(

            title="Test Page",

            slug="test-page",

            path="/test-page/",

            locale=self.locale_en,

            status="draft",

            blocks=[{"type": "text", "props": {"content": "Test content"}}],

        )



        self.assertEqual(page.title, "Test Page")

        self.assertEqual(page.slug, "test-page")

        self.assertEqual(page.status, "draft")

        self.assertEqual(len(page.blocks), 1)



    def test_page_string_representation(self):

        """Test page string representation."""

        page = Page.objects.create(

            title="Test Page",

            slug="test-page",

            path="/test-page/",

            locale=self.locale_en,

            status="draft",

            blocks=[],

        )



        self.assertEqual(str(page), "Test Page")



    def test_page_get_absolute_url(self):

        """Test page URL generation."""

        page = Page.objects.create(

            title="Test Page",

            slug="test-page",

            path="/test-page/",

            locale=self.locale_en,

            status="published",

            blocks=[],

        )



        # Should return the path

        self.assertEqual(page.get_absolute_url(), "/test-page/")

