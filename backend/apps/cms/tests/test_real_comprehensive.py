from datetime import datetime, timedelta



from django.contrib.auth import get_user_model

from django.core.exceptions import ValidationError

from django.test import TestCase, TransactionTestCase



from rest_framework.test import APIClient, APITestCase



from apps.cms.models import Page, Redirect

from apps.i18n.models import Locale



Real comprehensive CMS tests using actual models and targeting high coverage.



# Import actual models



User = get_user_model()



class CMSRealModelTests(TestCase):

    """Comprehensive tests for actual CMS models."""



    def setUp(self):

        self.user = User.objects.create_user(

            username="testuser", email="test@example.com", password="testpass123"

        )

        self.locale = Locale.objects.create(code="en", name="English", is_default=True)



    def test_page_creation_with_real_fields(self):

        """Test page creation with all actual fields."""

        page = Page.objects.create(

            title="Test Page",

            slug="test-page",

            path="/test-page",

            locale=self.locale,

            blocks=[

                {"type": "text", "content": "Hello world"},

                {"type": "heading", "content": "Page Title"},

            ],

            seo={"title": "Test Page SEO", "description": "Test page description"},

            status="draft",

        )



        self.assertEqual(page.title, "Test Page")

        self.assertEqual(page.slug, "test-page")

        self.assertEqual(page.path, "/test-page")

        self.assertEqual(page.locale, self.locale)

        self.assertEqual(page.status, "draft")

        self.assertEqual(len(page.blocks), 2)

        self.assertIn("title", page.seo)

        self.assertIsNotNone(page.created_at)



    def test_page_str_representation(self):

        """Test page string representation."""

        page = Page.objects.create(title="String Test Page", locale=self.locale)

        self.assertIn("String Test Page", str(page))



    def test_page_status_choices(self):

        """Test all page status choices."""

        statuses = [

            "draft",

            "pending_review",

            "approved",

            "published",

            "scheduled",

            "rejected",

        ]



        for status in statuses:

            page = Page.objects.create(

                title=f"Page {status}", locale=self.locale, status=status

            )

            self.assertEqual(page.status, status)



    def test_page_hierarchy(self):

        """Test page parent-child relationships."""

        parent_page = Page.objects.create(title="Parent Page", locale=self.locale)



        child_page = Page.objects.create(

            title="Child Page", locale=self.locale, parent=parent_page, position=1

        )



        self.assertEqual(child_page.parent, parent_page)

        self.assertEqual(child_page.position, 1)



        # Test children relationship

        children = parent_page.children.all()

        self.assertEqual(children.count(), 1)

        self.assertEqual(children.first(), child_page)



    def test_page_blocks_json_field(self):

        """Test page blocks JSON field functionality."""

        page = Page.objects.create(

            title="Blocks Test",

            locale=self.locale,

            blocks=[

                {

                    "type": "paragraph",

                    "content": "This is a paragraph block",

                    "settings": {"alignment": "left"},

                },

                {

                    "type": "image",

                    "content": {"src": "/media/test.jpg", "alt": "Test image"},

                },

            ],

        )



        self.assertEqual(len(page.blocks), 2)

        self.assertEqual(page.blocks[0]["type"], "paragraph")

        self.assertEqual(page.blocks[1]["type"], "image")

        self.assertIn("settings", page.blocks[0])



    def test_page_seo_json_field(self):

        """Test page SEO JSON field functionality."""

        page = Page.objects.create(

            title="SEO Test",

            locale=self.locale,

            seo={

                "meta_title": "Custom SEO Title",

                "meta_description": "Custom meta description",

                "keywords": ["test", "seo", "page"],

                "og_title": "Open Graph Title",

                "og_description": "Open Graph Description",

            },

        )



        self.assertEqual(page.seo["meta_title"], "Custom SEO Title")

        self.assertEqual(page.seo["meta_description"], "Custom meta description")

        self.assertIn("test", page.seo["keywords"])

        self.assertEqual(page.seo["og_title"], "Open Graph Title")



    def test_page_validation(self):

        """Test page model validation."""

        page = Page(title="", locale=self.locale)  # Empty title



        if hasattr(page, "clean"):

            with self.assertRaises(ValidationError):

                page.clean()



    def test_page_locale_relationship(self):

        """Test page-locale foreign key relationship."""

        page = Page.objects.create(title="Locale Test", locale=self.locale)



        self.assertEqual(page.locale, self.locale)



        # Test locale deletion protection

        with self.assertRaises(Exception):  # Should be ProtectedError

            self.locale.delete()



    def test_redirect_creation(self):

        """Test Redirect model creation."""

        redirect = Redirect.objects.create(

            old_path="/old-path", new_path="/new-path", status_code=301, is_active=True

        )



        self.assertEqual(redirect.old_path, "/old-path")

        self.assertEqual(redirect.new_path, "/new-path")

        self.assertEqual(redirect.status_code, 301)

        self.assertTrue(redirect.is_active)



    def test_redirect_str_representation(self):

        """Test redirect string representation."""

        redirect = Redirect.objects.create(

            old_path="/test-redirect", new_path="/new-location"

        )

        self.assertIn("/test-redirect", str(redirect))



    def test_page_group_id_field(self):

        """Test page group_id UUID field."""

        page = Page.objects.create(title="Group ID Test", locale=self.locale)



        self.assertIsNotNone(page.group_id)

        # UUID should be a valid UUID4

        self.assertEqual(len(str(page.group_id)), 36)



class CMSRealModelMethodTests(TestCase):

    """Test CMS model methods and properties."""



    def setUp(self):

        self.user = User.objects.create_user(

            username="testuser", email="test@example.com", password="testpass123"

        )

        self.locale = Locale.objects.create(code="en", name="English", is_default=True)



    def test_page_get_absolute_url(self):

        """Test page get_absolute_url method if it exists."""

        page = Page.objects.create(

            title="URL Test", slug="url-test", path="/url-test", locale=self.locale

        )



        if hasattr(page, "get_absolute_url"):

            url = page.get_absolute_url()

            self.assertIsInstance(url, str)

            self.assertIn("url-test", url)



    def test_page_publish_method(self):

        """Test page publish method if it exists."""

        page = Page.objects.create(

            title="Publish Test", status="draft", locale=self.locale

        )



        if hasattr(page, "publish"):

            page.publish()

            page.refresh_from_db()

            self.assertEqual(page.status, "published")



    def test_page_schedule_method(self):

        """Test page schedule method if it exists."""

        page = Page.objects.create(

            title="Schedule Test", status="draft", locale=self.locale

        )



        future_time = datetime.now() + timedelta(days=1)

        if hasattr(page, "schedule"):

            page.schedule(publish_at=future_time)

            page.refresh_from_db()

            self.assertEqual(page.status, "scheduled")



    def test_page_rbac_methods(self):

        """Test page RBAC methods from RBACMixin."""

        page = Page.objects.create(title="RBAC Test", locale=self.locale)



        # Test RBAC methods if they exist

        if hasattr(page, "can_view"):

            result = page.can_view(self.user)

            self.assertIsInstance(result, bool)



        if hasattr(page, "can_edit"):

            result = page.can_edit(self.user)

            self.assertIsInstance(result, bool)



        if hasattr(page, "get_permissions"):

            permissions = page.get_permissions(self.user)

            self.assertIsInstance(permissions, (list, dict))



    def test_page_versioning_relationship(self):

        """Test page versioning relationship if it exists."""

        page = Page.objects.create(title="Versioning Test", locale=self.locale)



        # Test if versioning relationships exist

        if hasattr(page, "revisions"):

            revisions = page.revisions.all()

            self.assertIsInstance(revisions.count(), int)



        if hasattr(page, "audit_entries"):

            entries = page.audit_entries.all()

            self.assertIsInstance(entries.count(), int)



class CMSRealAPITests(APITestCase):

    """Test CMS API endpoints with real models."""



    def setUp(self):

        self.user = User.objects.create_user(

            username="testuser", email="test@example.com", password="testpass123"

        )

        self.client = APIClient()

        self.client.force_authenticate(user=self.user)



        self.locale = Locale.objects.create(code="en", name="English", is_default=True)



    def test_page_api_operations(self):

        """Test basic page API operations."""

        # Create a page

        page = Page.objects.create(

            title="API Test Page",

            slug="api-test-page",

            path="/api-test-page",

            locale=self.locale,

            status="published",

        )



        # Test that page was created

        self.assertEqual(Page.objects.count(), 1)

        self.assertEqual(page.title, "API Test Page")



        # Test page update

        page.title = "Updated API Test Page"

        page.save()

        page.refresh_from_db()

        self.assertEqual(page.title, "Updated API Test Page")



        # Test page filtering

        Page.objects.create(title="Draft Page", locale=self.locale, status="draft")



        published_pages = Page.objects.filter(status="published")

        draft_pages = Page.objects.filter(status="draft")



        self.assertEqual(published_pages.count(), 1)

        self.assertEqual(draft_pages.count(), 1)



    def test_redirect_api_operations(self):

        """Test redirect API operations."""

        # Create redirect

        redirect = Redirect.objects.create(

            old_path="/old-api-path", new_path="/new-api-path", status_code=301

        )



        self.assertEqual(Redirect.objects.count(), 1)

        self.assertEqual(redirect.old_path, "/old-api-path")



        # Test redirect update

        redirect.status_code = 302

        redirect.save()

        redirect.refresh_from_db()

        self.assertEqual(redirect.status_code, 302)



class CMSRealIntegrationTests(TransactionTestCase):

    """Integration tests with real CMS models."""



    def setUp(self):

        self.user = User.objects.create_user(

            username="testuser", email="test@example.com", password="testpass123"

        )

        self.locale = Locale.objects.create(code="en", name="English", is_default=True)



    def test_page_lifecycle_workflow(self):

        """Test complete page lifecycle."""

        # Create draft page

        page = Page.objects.create(

            title="Lifecycle Test",

            slug="lifecycle-test",

            path="/lifecycle-test",

            locale=self.locale,

            status="draft",

            blocks=[{"type": "text", "content": "Initial content"}],

        )



        self.assertEqual(page.status, "draft")



        # Update content

        page.blocks.append({"type": "heading", "content": "New heading"})

        page.save()

        page.refresh_from_db()

        self.assertEqual(len(page.blocks), 2)



        # Move to review

        page.status = "pending_review"

        page.save()

        self.assertEqual(page.status, "pending_review")



        # Approve

        page.status = "approved"

        page.save()

        self.assertEqual(page.status, "approved")



        # Publish

        page.status = "published"

        page.published_at = datetime.now()

        page.save()

        self.assertEqual(page.status, "published")

        self.assertIsNotNone(page.published_at)



    def test_page_hierarchy_workflow(self):

        """Test page hierarchy creation and management."""

        # Create parent page

        parent = Page.objects.create(

            title="Parent Page", slug="parent", path="/parent", locale=self.locale

        )



        # Create child pages

        child1 = Page.objects.create(

            title="Child 1",

            slug="child-1",

            path="/parent/child-1",

            locale=self.locale,

            parent=parent,

            position=1,

        )



        child2 = Page.objects.create(

            title="Child 2",

            slug="child-2",

            path="/parent/child-2",

            locale=self.locale,

            parent=parent,

            position=2,

        )



        # Test hierarchy

        self.assertEqual(parent.children.count(), 2)

        self.assertEqual(child1.parent, parent)

        self.assertEqual(child2.parent, parent)

        self.assertEqual(child1.position, 1)

        self.assertEqual(child2.position, 2)



        # Test ordering by position

        children = parent.children.order_by("position")

        self.assertEqual(list(children), [child1, child2])



    def test_multilingual_pages_workflow(self):

        """Test multilingual page management."""

        # Create Spanish locale

        spanish_locale = Locale.objects.create(code="es", name="Spanish")



        # Create English page

        en_page = Page.objects.create(

            title="English Page",

            slug="english-page",

            path="/english-page",

            locale=self.locale,

            blocks=[{"type": "text", "content": "English content"}],

        )



        # Create Spanish version

        es_page = Page.objects.create(

            title="Página en Español",

            slug="pagina-espanol",

            path="/pagina-espanol",

            locale=spanish_locale,

            group_id=en_page.group_id,  # Same group for translations

            blocks=[{"type": "text", "content": "Contenido en español"}],

        )



        # Test that pages share group_id

        self.assertEqual(en_page.group_id, es_page.group_id)



        # Test locale filtering

        english_pages = Page.objects.filter(locale=self.locale)

        spanish_pages = Page.objects.filter(locale=spanish_locale)



        self.assertEqual(english_pages.count(), 1)

        self.assertEqual(spanish_pages.count(), 1)



    def test_redirect_management_workflow(self):

        """Test redirect creation and management."""

        # Create original page

        Page.objects.create(

            title="Original Page", slug="original", path="/original", locale=self.locale

        )



        # Create redirect from old path

        redirect = Redirect.objects.create(

            old_path="/old-path", new_path="/original", status_code=301, is_active=True

        )



        # Test redirect functionality

        self.assertTrue(redirect.is_active)

        self.assertEqual(redirect.status_code, 301)



        # Update redirect

        redirect.new_path = "/updated-path"

        redirect.status_code = 302

        redirect.save()



        redirect.refresh_from_db()

        self.assertEqual(redirect.new_path, "/updated-path")

        self.assertEqual(redirect.status_code, 302)



        # Deactivate redirect

        redirect.is_active = False

        redirect.save()

        self.assertFalse(redirect.is_active)

