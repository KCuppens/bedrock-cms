"""Comprehensive tests to boost CMS coverage to 80%+"""

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.text import slugify

from apps.cms.models import Page
from apps.cms.seo_utils import (
    generate_meta_tags,
    generate_schema_org,
    generate_sitemap_entry,
    validate_seo_data,
)
from apps.cms.serializers import BlockSerializer, PageSerializer

User = get_user_model()


class CMSModelTest(TestCase):
    """Test all CMS models for coverage"""

    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@test.com", "pass")
        self.site = Site.objects.create(
            name="Test Site", domain="test.com", is_default=True
        )

    def test_page_model_str(self):
        """Test Page model string representation"""
        page = Page.objects.create(
            title="Test Page", slug="test-page", site=self.site, created_by=self.user
        )
        self.assertEqual(str(page), "Test Page")

    def test_page_get_absolute_url(self):
        """Test Page absolute URL generation"""
        page = Page.objects.create(
            title="Test Page", slug="test-page", site=self.site, created_by=self.user
        )
        self.assertEqual(page.get_absolute_url(), "/test-page/")

    def test_page_hierarchy(self):
        """Test Page parent-child relationships"""
        parent = Page.objects.create(
            title="Parent", slug="parent", site=self.site, created_by=self.user
        )
        child = Page.objects.create(
            title="Child",
            slug="child",
            parent=parent,
            site=self.site,
            created_by=self.user,
        )

        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())

    def test_page_published_status(self):
        """Test Page published status"""
        page = Page.objects.create(
            title="Test",
            slug="test",
            site=self.site,
            is_published=False,
            created_by=self.user,
        )
        self.assertFalse(page.is_published)

        page.publish()
        self.assertTrue(page.is_published)

        page.unpublish()
        self.assertFalse(page.is_published)

    def test_block_model(self):
        """Test Block model"""
        page = Page.objects.create(
            title="Test", slug="test", site=self.site, created_by=self.user
        )
        block = Block.objects.create(
            page=page, block_type="text", content={"text": "Hello World"}, order=1
        )

        self.assertEqual(str(block), f"text block on {page.title}")
        self.assertEqual(block.page, page)
        self.assertEqual(block.order, 1)

    def test_block_ordering(self):
        """Test Block ordering"""
        page = Page.objects.create(
            title="Test", slug="test", site=self.site, created_by=self.user
        )

        block1 = Block.objects.create(page=page, block_type="text", order=2)
        block2 = Block.objects.create(page=page, block_type="text", order=1)
        block3 = Block.objects.create(page=page, block_type="text", order=3)

        blocks = Block.objects.filter(page=page).order_by("order")
        self.assertEqual(list(blocks), [block2, block1, block3])

    def test_site_model(self):
        """Test Site model"""
        self.assertEqual(str(self.site), "Test Site (test.com)")
        self.assertTrue(self.site.is_default)

    def test_site_unique_default(self):
        """Test only one default site"""
        site2 = Site.objects.create(name="Site 2", domain="site2.com", is_default=True)

        self.site.refresh_from_db()
        self.assertFalse(self.site.is_default)
        self.assertTrue(site2.is_default)

    def test_menu_model(self):
        """Test Menu model"""
        menu = Menu.objects.create(name="Main Menu", slug="main-menu", site=self.site)

        self.assertEqual(str(menu), "Main Menu")
        self.assertEqual(menu.slug, "main-menu")

    def test_menu_item_model(self):
        """Test MenuItem model"""
        menu = Menu.objects.create(name="Main Menu", slug="main-menu", site=self.site)
        page = Page.objects.create(
            title="Test", slug="test", site=self.site, created_by=self.user
        )

        item = MenuItem.objects.create(menu=menu, title="Test Item", page=page, order=1)

        self.assertEqual(str(item), "Test Item")
        self.assertEqual(item.get_url(), page.get_absolute_url())

    def test_menu_item_custom_url(self):
        """Test MenuItem with custom URL"""
        menu = Menu.objects.create(name="Main Menu", slug="main-menu", site=self.site)

        item = MenuItem.objects.create(
            menu=menu, title="External", url="https://example.com", order=1
        )

        self.assertEqual(item.get_url(), "https://example.com")

    def test_media_model(self):
        """Test Media model"""
        media = Media.objects.create(
            title="Test Image",
            file="test.jpg",
            media_type="image",
            uploaded_by=self.user,
        )

        self.assertEqual(str(media), "Test Image")
        self.assertEqual(media.media_type, "image")

    def test_template_model(self):
        """Test Template model"""
        template = Template.objects.create(
            name="Test Template", slug="test-template", content="<h1>{{ title }}</h1>"
        )

        self.assertEqual(str(template), "Test Template")
        self.assertEqual(template.slug, "test-template")

    def test_seo_metadata_model(self):
        """Test SEOMetadata model"""
        page = Page.objects.create(
            title="Test", slug="test", site=self.site, created_by=self.user
        )

        seo = SEOMetadata.objects.create(
            page=page,
            meta_title="Custom Title",
            meta_description="Custom description",
            og_title="OG Title",
            og_description="OG Description",
        )

        self.assertEqual(str(seo), f"SEO for {page.title}")
        self.assertEqual(seo.meta_title, "Custom Title")


class CMSSerializerTest(TestCase):
    """Test CMS serializers"""

    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@test.com", "pass")
        self.site = Site.objects.create(
            name="Test Site", domain="test.com", is_default=True
        )

    def test_page_serializer(self):
        """Test PageSerializer"""
        page = Page.objects.create(
            title="Test Page",
            slug="test-page",
            site=self.site,
            content="Test content",
            created_by=self.user,
        )

        serializer = PageSerializer(page)
        data = serializer.data

        self.assertEqual(data["title"], "Test Page")
        self.assertEqual(data["slug"], "test-page")
        self.assertIn("content", data)

    def test_page_serializer_validation(self):
        """Test PageSerializer validation"""
        data = {
            "title": "New Page",
            "slug": "new-page",
            "site": self.site.id,
            "content": "Content",
        }

        serializer = PageSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_block_serializer(self):
        """Test BlockSerializer"""
        page = Page.objects.create(
            title="Test", slug="test", site=self.site, created_by=self.user
        )
        block = Block.objects.create(
            page=page, block_type="text", content={"text": "Hello"}, order=1
        )

        serializer = BlockSerializer(block)
        data = serializer.data

        self.assertEqual(data["block_type"], "text")
        self.assertEqual(data["order"], 1)


class CMSSEOUtilsTest(TestCase):
    """Test SEO utility functions"""

    def test_generate_meta_tags(self):
        """Test meta tag generation"""
        data = {
            "title": "Test Page",
            "description": "Test description",
            "keywords": "test, page, seo",
        }

        tags = generate_meta_tags(data)

        self.assertIn('<meta name="description"', tags)
        self.assertIn("Test description", tags)
        self.assertIn('<meta name="keywords"', tags)

    def test_generate_schema_org(self):
        """Test schema.org JSON-LD generation"""
        data = {
            "@type": "WebPage",
            "name": "Test Page",
            "description": "Test description",
        }

        schema = generate_schema_org(data)

        self.assertIn("application/ld+json", schema)
        self.assertIn("WebPage", schema)

    def test_generate_sitemap_entry(self):
        """Test sitemap entry generation"""
        page = MagicMock()
        page.get_absolute_url.return_value = "/test-page/"
        page.updated_at = "2024-01-01"

        entry = generate_sitemap_entry(page)

        self.assertIn("loc", entry)
        self.assertIn("lastmod", entry)
        self.assertIn("/test-page/", entry["loc"])

    def test_validate_seo_data(self):
        """Test SEO data validation"""
        # Valid data
        valid_data = {
            "title": "Good Title",
            "description": "A good description that is long enough",
        }
        self.assertTrue(validate_seo_data(valid_data))

        # Invalid - title too long
        invalid_data = {"title": "T" * 100, "description": "Description"}
        self.assertFalse(validate_seo_data(invalid_data))


class CMSViewTest(TestCase):
    """Test CMS views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("testuser", "test@test.com", "pass")
        self.site = Site.objects.create(
            name="Test Site", domain="test.com", is_default=True
        )

    def test_page_list_view(self):
        """Test page list view"""
        Page.objects.create(
            title="Page 1",
            slug="page-1",
            site=self.site,
            is_published=True,
            created_by=self.user,
        )
        Page.objects.create(
            title="Page 2",
            slug="page-2",
            site=self.site,
            is_published=True,
            created_by=self.user,
        )

        response = self.client.get("/api/pages/")
        self.assertEqual(response.status_code, 200)

    def test_page_detail_view(self):
        """Test page detail view"""
        page = Page.objects.create(
            title="Test Page",
            slug="test-page",
            site=self.site,
            is_published=True,
            created_by=self.user,
        )

        response = self.client.get(f"/api/pages/{page.slug}/")
        self.assertEqual(response.status_code, 200)

    def test_page_create_requires_auth(self):
        """Test page creation requires authentication"""
        data = {"title": "New Page", "slug": "new-page", "site": self.site.id}

        response = self.client.post("/api/pages/", data)
        self.assertIn(response.status_code, [401, 403])

    def test_page_update_requires_auth(self):
        """Test page update requires authentication"""
        page = Page.objects.create(
            title="Test", slug="test", site=self.site, created_by=self.user
        )

        response = self.client.patch(f"/api/pages/{page.slug}/", {"title": "Updated"})
        self.assertIn(response.status_code, [401, 403])


class CMSManagerTest(TestCase):
    """Test CMS model managers"""

    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@test.com", "pass")
        self.site = Site.objects.create(
            name="Test Site", domain="test.com", is_default=True
        )

    def test_published_pages_manager(self):
        """Test published pages manager"""
        Page.objects.create(
            title="Published",
            slug="published",
            site=self.site,
            is_published=True,
            created_by=self.user,
        )
        Page.objects.create(
            title="Unpublished",
            slug="unpublished",
            site=self.site,
            is_published=False,
            created_by=self.user,
        )

        published = Page.objects.published()
        self.assertEqual(published.count(), 1)
        self.assertEqual(published.first().title, "Published")

    def test_draft_pages_manager(self):
        """Test draft pages manager"""
        Page.objects.create(
            title="Published",
            slug="published",
            site=self.site,
            is_published=True,
            created_by=self.user,
        )
        Page.objects.create(
            title="Draft",
            slug="draft",
            site=self.site,
            is_published=False,
            created_by=self.user,
        )

        drafts = Page.objects.drafts()
        self.assertEqual(drafts.count(), 1)
        self.assertEqual(drafts.first().title, "Draft")
