"""
Integration tests for Authentication-RBAC workflows.

This module tests the complete workflow integration between Authentication and RBAC,
focusing on:
- User permission workflows across different apps
- Locale-based access control
- Content publishing permissions with user roles
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.test import Client, TestCase
from django.urls import reverse

import pytest

from apps.accounts.models import User
from apps.accounts.rbac import RBACMixin, ScopedLocale, ScopedSection
from apps.cms.models import Page
from apps.i18n.models import Locale, TranslationUnit

try:
    from tests.factories import (
        AdminUserFactory,
        LocaleFactory,
        PageFactory,
        UserFactory,
    )

    HAS_FACTORIES = True
except ImportError:
    # Fallback if factories don't exist
    AdminUserFactory = None
    LocaleFactory = None
    PageFactory = None
    UserFactory = None
    HAS_FACTORIES = False


class RBACTestFactory:
    """Factory for creating RBAC-related test data."""

    @staticmethod
    def create_group_with_permissions(name, permissions=None):
        """Create a group with specified permissions."""
        group = Group.objects.create(name=name)
        if permissions:
            for perm_codename in permissions:
                try:
                    permission = Permission.objects.get(codename=perm_codename)
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    # Permission doesn't exist, skip it
                    pass
        return group

    @staticmethod
    def create_scoped_locale(group, locale):
        """Create a scoped locale for a group."""
        return ScopedLocale.objects.create(group=group, locale=locale)

    @staticmethod
    def create_scoped_section(group, path_prefix, name):
        """Create a scoped section for a group."""
        return ScopedSection.objects.create(
            group=group, path_prefix=path_prefix, name=name
        )

    @staticmethod
    def create_user_with_groups(email, groups=None):
        """Create a user and add to specified groups."""
        if UserFactory is None:
            # Fallback to direct model creation
            user = User.objects.create_user(email=email, password="testpass123")
        else:
            user = UserFactory(email=email)

        if groups:
            user.groups.set(groups)
        return user


@pytest.mark.django_db
class TestAuthRBACWorkflows(TestCase):
    """Test complete Authentication-RBAC integration workflows."""

    def setUp(self):
        """Set up test data."""
        if not HAS_FACTORIES:
            self.skipTest("Required factories not available")

        self.admin_user = AdminUserFactory()
        self.client = Client()

        # Create locales
        self.locale_en = LocaleFactory(code="en", name="English", is_default=True)
        self.locale_es = LocaleFactory(code="es", name="Spanish")
        self.locale_fr = LocaleFactory(code="fr", name="French")

        # Create groups with different permission levels
        self.editor_group = RBACTestFactory.create_group_with_permissions(
            "Editors", ["add_page", "change_page", "view_page"]
        )

        self.translator_group = RBACTestFactory.create_group_with_permissions(
            "Translators",
            ["view_page", "change_translationunit", "view_translationunit"],
        )

        self.publisher_group = RBACTestFactory.create_group_with_permissions(
            "Publishers",
            ["add_page", "change_page", "delete_page", "publish_page", "view_page"],
        )

        self.manager_group = RBACTestFactory.create_group_with_permissions(
            "Managers",
            [
                "add_page",
                "change_page",
                "delete_page",
                "publish_page",
                "view_page",
                "manage_page_seo",
                "moderate_content",
                "approve_content",
            ],
        )

        # Create locale scopes
        RBACTestFactory.create_scoped_locale(self.editor_group, self.locale_en)
        RBACTestFactory.create_scoped_locale(self.translator_group, self.locale_es)
        RBACTestFactory.create_scoped_locale(self.translator_group, self.locale_fr)
        RBACTestFactory.create_scoped_locale(self.publisher_group, self.locale_en)
        RBACTestFactory.create_scoped_locale(self.publisher_group, self.locale_es)

        # Managers have access to all locales
        for locale in [self.locale_en, self.locale_es, self.locale_fr]:
            RBACTestFactory.create_scoped_locale(self.manager_group, locale)

        # Create section scopes
        RBACTestFactory.create_scoped_section(
            self.editor_group, "/blog", "Blog Section"
        )
        RBACTestFactory.create_scoped_section(
            self.translator_group, "/", "All Sections"
        )
        RBACTestFactory.create_scoped_section(
            self.publisher_group, "/products", "Products Section"
        )
        RBACTestFactory.create_scoped_section(
            self.publisher_group, "/blog", "Blog Section"
        )
        RBACTestFactory.create_scoped_section(self.manager_group, "/", "All Sections")

        # Create users
        self.english_editor = RBACTestFactory.create_user_with_groups(
            "editor@example.com", [self.editor_group]
        )
        self.spanish_translator = RBACTestFactory.create_user_with_groups(
            "translator@example.com", [self.translator_group]
        )
        self.product_publisher = RBACTestFactory.create_user_with_groups(
            "publisher@example.com", [self.publisher_group]
        )
        self.content_manager = RBACTestFactory.create_user_with_groups(
            "manager@example.com", [self.manager_group]
        )

    def test_user_permission_workflows_across_different_apps(self):
        """Test user permissions work correctly across CMS and i18n apps."""
        # Create pages in different locales and sections
        # Create section parent pages first
        blog_section = Page.objects.create(
            title="Blog", locale=self.locale_en, slug="blog", status="published"
        )

        products_section = Page.objects.create(
            title="Products", locale=self.locale_en, slug="products", status="published"
        )

        # Create blog pages
        english_blog_page = Page.objects.create(
            title="English Blog Post",
            locale=self.locale_en,
            slug="english-blog",
            parent=blog_section,
            status="draft",
        )

        english_product_page = Page.objects.create(
            title="English Product Page",
            locale=self.locale_en,
            slug="english-product",
            parent=products_section,
            status="draft",
        )

        # Create Spanish blog section
        spanish_blog_section = Page.objects.create(
            title="Blog", locale=self.locale_es, slug="blog", status="published"
        )

        spanish_blog_page = Page.objects.create(
            title="Spanish Blog Post",
            locale=self.locale_es,
            slug="spanish-blog",
            parent=spanish_blog_section,
            status="draft",
        )

        # Test English editor permissions
        # Should have access to English blog content
        self.assertTrue(english_blog_page.user_has_locale_access(self.english_editor))
        self.assertTrue(english_blog_page.user_has_section_access(self.english_editor))
        self.assertTrue(english_blog_page.user_has_scope_access(self.english_editor))

        # Should not have access to products section
        self.assertTrue(
            english_product_page.user_has_locale_access(self.english_editor)
        )
        self.assertFalse(
            english_product_page.user_has_section_access(self.english_editor)
        )
        self.assertFalse(
            english_product_page.user_has_scope_access(self.english_editor)
        )

        # Should not have access to Spanish content
        self.assertFalse(spanish_blog_page.user_has_locale_access(self.english_editor))

        # Test Spanish translator permissions
        # Should have access to Spanish content in any section
        self.assertTrue(
            spanish_blog_page.user_has_locale_access(self.spanish_translator)
        )
        self.assertTrue(
            spanish_blog_page.user_has_section_access(self.spanish_translator)
        )
        self.assertTrue(
            spanish_blog_page.user_has_scope_access(self.spanish_translator)
        )

        # Should not have access to English content
        self.assertFalse(
            english_blog_page.user_has_locale_access(self.spanish_translator)
        )

        # Test product publisher permissions
        # Should have access to products in English and Spanish
        self.assertTrue(
            english_product_page.user_has_locale_access(self.product_publisher)
        )
        self.assertTrue(
            english_product_page.user_has_section_access(self.product_publisher)
        )
        self.assertTrue(
            english_product_page.user_has_scope_access(self.product_publisher)
        )

        # Should also have access to blog section
        self.assertTrue(
            english_blog_page.user_has_locale_access(self.product_publisher)
        )
        self.assertTrue(
            english_blog_page.user_has_section_access(self.product_publisher)
        )

        # Test content manager permissions
        # Should have access to everything
        for page in [english_blog_page, english_product_page, spanish_blog_page]:
            self.assertTrue(page.user_has_locale_access(self.content_manager))
            self.assertTrue(page.user_has_section_access(self.content_manager))
            self.assertTrue(page.user_has_scope_access(self.content_manager))

    def test_locale_based_access_control(self):
        """Test that locale-based access control works correctly."""
        # Create content in all locales
        pages_by_locale = {}
        for locale in [self.locale_en, self.locale_es, self.locale_fr]:
            page = PageFactory(
                title=f"Page in {locale.name}",
                locale=locale,
                slug=f"page-{locale.code}",
                path=f"/general/page-{locale.code}",
                status="published",
            )
            pages_by_locale[locale.code] = page

        # Test English editor - only English access
        english_page = pages_by_locale["en"]
        spanish_page = pages_by_locale["es"]
        french_page = pages_by_locale["fr"]

        self.assertTrue(english_page.user_has_locale_access(self.english_editor))
        self.assertFalse(spanish_page.user_has_locale_access(self.english_editor))
        self.assertFalse(french_page.user_has_locale_access(self.english_editor))

        # Test Spanish translator - Spanish and French access
        self.assertFalse(english_page.user_has_locale_access(self.spanish_translator))
        self.assertTrue(spanish_page.user_has_locale_access(self.spanish_translator))
        self.assertTrue(french_page.user_has_locale_access(self.spanish_translator))

        # Test translation unit access
        content_type = ContentType.objects.get_for_model(Page)

        # Create translation units
        spanish_translation_unit, created = TranslationUnit.objects.get_or_create(
            content_type=content_type,
            object_id=english_page.id,
            field="title",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            defaults={"source_text": "Page in English", "status": "missing"},
        )

        french_translation_unit, created = TranslationUnit.objects.get_or_create(
            content_type=content_type,
            object_id=english_page.id,
            field="title",
            source_locale=self.locale_en,
            target_locale=self.locale_fr,
            defaults={"source_text": "Page in English", "status": "missing"},
        )

        # Spanish translator should be able to work with Spanish and French translations
        # (This would be checked in the view layer typically)

    def test_content_publishing_permissions_with_user_roles(self):
        """Test content publishing workflow with different user roles."""
        # Create a draft page with proper hierarchy
        blog_page = Page.objects.create(
            title="Blog", locale=self.locale_en, slug="blog", status="published"
        )

        page = Page.objects.create(
            title="Article Awaiting Approval",
            locale=self.locale_en,
            slug="awaiting-approval",
            parent=blog_page,
            status="draft",
            blocks=[
                {
                    "type": "richtext",
                    "props": {
                        "content": "This article needs to be reviewed and published."
                    },
                }
            ],
        )

        # Editor creates content but cannot publish directly
        # This would be enforced in views/forms
        self.assertTrue(page.user_has_scope_access(self.english_editor))
        editor_can_publish = self.english_editor.has_perm("cms.publish_page")
        # Editors don't have publish permission in our setup
        self.assertFalse(editor_can_publish)

        # Submit for review (editor action)
        page.submit_for_review(user=self.english_editor)
        self.assertEqual(page.status, "pending_review")

        # Publisher can approve and publish
        publisher_can_publish = self.product_publisher.has_perm("cms.publish_page")
        self.assertTrue(publisher_can_publish)
        self.assertTrue(page.user_has_scope_access(self.product_publisher))

        # Manager approves the content
        page.approve(reviewer=self.content_manager, notes="Content looks good")
        self.assertEqual(page.status, "approved")

        # Publisher publishes
        page.status = "published"
        page.save()

        self.assertEqual(page.status, "published")

    def test_hierarchical_permission_inheritance(self):
        """Test that permission hierarchies work correctly."""
        # Create nested page structure
        # First create blog section page
        blog_page = Page.objects.create(
            title="Blog", locale=self.locale_en, slug="blog", status="published"
        )

        # Then create parent page under blog
        parent_page = Page.objects.create(
            title="Parent Section",
            locale=self.locale_en,
            slug="parent",
            parent=blog_page,
            status="published",
        )
        child_page = Page.objects.create(
            title="Child Page",
            locale=self.locale_en,
            slug="child",
            parent=parent_page,
            status="draft",
        )

        # Test that section access works for nested paths

        self.assertTrue(parent_page.user_has_section_access(self.english_editor))
        self.assertTrue(child_page.user_has_section_access(self.english_editor))

        # Create a page outside the blog section
        news_page = Page.objects.create(
            title="News", locale=self.locale_en, slug="news", status="published"
        )

        outside_page = Page.objects.create(
            title="Outside Blog",
            locale=self.locale_en,
            slug="outside",
            parent=news_page,
            status="draft",
        )

        # Editor should not have access to pages outside blog section
        self.assertFalse(outside_page.user_has_section_access(self.english_editor))

    def test_multi_group_user_permissions(self):
        """Test users with multiple group memberships."""
        # Create a user with both editor and translator roles
        multi_role_user = RBACTestFactory.create_user_with_groups(
            "multirole@example.com", [self.editor_group, self.translator_group]
        )

        # Create pages to test access
        english_blog_page = PageFactory(
            title="English Blog",
            locale=self.locale_en,
            path="/blog/english-blog",
            status="draft",
        )

        spanish_general_page = PageFactory(
            title="Spanish General",
            locale=self.locale_es,
            path="/general/spanish-page",
            status="draft",
        )

        french_blog_page = PageFactory(
            title="French Blog",
            locale=self.locale_fr,
            path="/blog/french-blog",
            status="draft",
        )

        # Should have English access from editor role
        self.assertTrue(english_blog_page.user_has_locale_access(multi_role_user))
        self.assertTrue(english_blog_page.user_has_section_access(multi_role_user))

        # Should have Spanish access from translator role
        self.assertTrue(spanish_general_page.user_has_locale_access(multi_role_user))
        self.assertTrue(spanish_general_page.user_has_section_access(multi_role_user))

        # Should have French access from translator role
        self.assertTrue(french_blog_page.user_has_locale_access(multi_role_user))
        # But blog section access from editor role
        self.assertTrue(french_blog_page.user_has_section_access(multi_role_user))

        # Combined permissions
        self.assertTrue(english_blog_page.user_has_scope_access(multi_role_user))
        self.assertTrue(spanish_general_page.user_has_scope_access(multi_role_user))
        self.assertTrue(french_blog_page.user_has_scope_access(multi_role_user))

    def test_permission_edge_cases_and_security(self):
        """Test edge cases and security aspects of permission system."""
        # Test with unsaved user (no primary key)
        unsaved_user = User(email="unsaved@example.com")
        test_page = PageFactory(
            title="Test Page", locale=self.locale_en, path="/blog/test"
        )

        # Unsaved user should not have access
        self.assertFalse(test_page.user_has_locale_access(unsaved_user))
        self.assertFalse(test_page.user_has_section_access(unsaved_user))

        # Test with None user
        self.assertFalse(test_page.user_has_locale_access(None))
        self.assertFalse(test_page.user_has_section_access(None))

        # Test with unauthenticated user
        unauthenticated_user = UserFactory(is_active=False)
        self.assertFalse(test_page.user_has_locale_access(unauthenticated_user))

        # Test superuser access (should have access to everything)
        self.assertTrue(test_page.user_has_locale_access(self.admin_user))
        self.assertTrue(test_page.user_has_section_access(self.admin_user))
        self.assertTrue(test_page.user_has_scope_access(self.admin_user))

        # Test page without locale or path
        page_no_locale = Page(title="No Locale Page")
        self.assertFalse(page_no_locale.user_has_locale_access(self.english_editor))

        page_no_path = Page(title="No Path Page", locale=self.locale_en, path="")
        self.assertFalse(page_no_path.user_has_section_access(self.english_editor))

    def test_scoped_section_path_matching(self):
        """Test that scoped section path matching works correctly."""
        # Test exact path matching
        blog_section = ScopedSection.objects.get(
            group=self.editor_group, path_prefix="/blog"
        )

        # Should match exact path
        self.assertTrue(blog_section.matches_path("/blog"))

        # Should match subpaths
        self.assertTrue(blog_section.matches_path("/blog/post-1"))
        self.assertTrue(blog_section.matches_path("/blog/category/tech"))

        # Should not match partial matches
        self.assertFalse(blog_section.matches_path("/blogpost"))
        self.assertFalse(blog_section.matches_path("/news/blog"))

        # Test root access
        root_section = ScopedSection.objects.get(
            group=self.manager_group, path_prefix="/"
        )

        # Root should match everything
        self.assertTrue(root_section.matches_path("/blog"))
        self.assertTrue(root_section.matches_path("/products"))
        self.assertTrue(root_section.matches_path("/any/path"))
        self.assertTrue(root_section.matches_path("/"))

    def test_complex_rbac_scenario_workflow(self):
        """Test a complete complex RBAC workflow scenario."""
        # Scenario: Multi-language product launch
        # 1. English editor creates product page
        # 2. Spanish translator adds Spanish translation
        # 3. Product publisher reviews and publishes in both languages
        # 4. Content manager moderates and approves

        # Step 1: English editor creates product page
        # Create products section page first
        products_section = Page.objects.create(
            title="Products", locale=self.locale_en, slug="products", status="published"
        )

        product_page = Page.objects.create(
            title="New Product Launch",
            locale=self.locale_en,
            slug="new-product",
            parent=products_section,
            status="draft",
            blocks=[
                {
                    "type": "hero",
                    "props": {
                        "heading": "Revolutionary New Product",
                        "description": "Discover our latest innovation",
                    },
                }
            ],
        )

        # Editor should NOT have access to products section in our setup
        self.assertTrue(product_page.user_has_locale_access(self.english_editor))
        self.assertFalse(product_page.user_has_section_access(self.english_editor))

        # But content manager can work with it
        self.assertTrue(product_page.user_has_scope_access(self.content_manager))

        # Step 2: Create Spanish translation units
        content_type = ContentType.objects.get_for_model(Page)
        spanish_title_unit, created = TranslationUnit.objects.get_or_create(
            content_type=content_type,
            object_id=product_page.id,
            field="title",
            source_locale=self.locale_en,
            target_locale=self.locale_es,
            defaults={"source_text": "New Product Launch", "status": "missing"},
        )

        # Spanish translator can work with Spanish translations
        # (but not access the original English product page due to section restrictions)
        self.assertFalse(product_page.user_has_locale_access(self.spanish_translator))
        # However, they can work with translation units targeting Spanish

        # Step 3: Publisher reviews and publishes
        # Publisher has access to products section
        self.assertTrue(product_page.user_has_scope_access(self.product_publisher))

        # Submit for review and publish
        product_page.submit_for_review(user=self.content_manager)  # Manager submits
        product_page.approve(reviewer=self.content_manager, notes="Ready for launch")
        product_page.status = "published"
        product_page.save()

        self.assertEqual(product_page.status, "published")

        # Step 4: Verify final permissions
        # Manager has full access
        self.assertTrue(product_page.user_has_scope_access(self.content_manager))

        # Publisher can publish in their allowed sections and locales
        self.assertTrue(product_page.user_has_scope_access(self.product_publisher))

        # Verify translation workflow permissions
        spanish_title_unit.target_text = "Lanzamiento de Nuevo Producto"
        spanish_title_unit.status = "approved"
        spanish_title_unit.updated_by = self.spanish_translator
        spanish_title_unit.save()

        self.assertEqual(spanish_title_unit.status, "approved")

    def test_rbac_performance_with_multiple_groups_and_scopes(self):
        """Test RBAC performance with multiple groups and scopes."""
        # Create additional groups and scopes
        additional_groups = []
        for i in range(5):
            group = RBACTestFactory.create_group_with_permissions(
                f"TestGroup{i}", ["view_page"]
            )
            additional_groups.append(group)

            # Add scopes
            RBACTestFactory.create_scoped_locale(group, self.locale_en)
            RBACTestFactory.create_scoped_section(group, f"/section{i}", f"Section {i}")

        # Create user with many groups
        multi_group_user = RBACTestFactory.create_user_with_groups(
            "multigroup@example.com", additional_groups
        )

        # Create test pages with proper hierarchy
        test_pages = []
        section_pages = {}

        # First create section parent pages
        for i in range(5):
            section_page = Page.objects.create(
                title=f"Section {i}",
                locale=self.locale_en,
                slug=f"section{i}",
                status="published",
            )
            section_pages[i] = section_page

        # Then create pages under each section
        for i in range(10):
            section_index = i % 5
            page = Page.objects.create(
                title=f"Test Page {i}",
                locale=self.locale_en,
                slug=f"page{i}",
                parent=section_pages[section_index],
                status="published",
            )
            test_pages.append(page)

        # Test access check performance
        # This should use efficient queries (not N+1)
        access_results = []
        for page in test_pages:
            has_access = page.user_has_scope_access(multi_group_user)
            access_results.append(has_access)

        # User should have access to pages in sections they have scope for
        # Pages 0-4 should have access (section0-section4)
        # Pages 5-9 should have access (section0-section4, repeating pattern)
        accessible_count = sum(access_results)
        self.assertEqual(accessible_count, 10)  # All should be accessible

    def test_rbac_with_inactive_users_and_groups(self):
        """Test RBAC behavior with inactive users and groups."""
        # Create inactive user
        inactive_user = RBACTestFactory.create_user_with_groups(
            "inactive@example.com", [self.editor_group]
        )
        inactive_user.is_active = False
        inactive_user.save()

        # Create test page with proper hierarchy
        blog_page = Page.objects.create(
            title="Blog", locale=self.locale_en, slug="blog", status="published"
        )

        test_page = Page.objects.create(
            title="Test Page for Inactive User",
            locale=self.locale_en,
            slug="test-inactive",
            parent=blog_page,
            status="draft",
        )

        # Inactive user should not have access
        self.assertFalse(test_page.user_has_locale_access(inactive_user))
        self.assertFalse(test_page.user_has_section_access(inactive_user))

        # Test with deleted group scopes
        # Remove locale scope for editor group
        ScopedLocale.objects.filter(
            group=self.editor_group, locale=self.locale_en
        ).delete()

        # Active editor should no longer have locale access
        self.assertFalse(test_page.user_has_locale_access(self.english_editor))
        # But still has section access
        self.assertTrue(test_page.user_has_section_access(self.english_editor))
        # Overall scope access should be False
        self.assertFalse(test_page.user_has_scope_access(self.english_editor))
