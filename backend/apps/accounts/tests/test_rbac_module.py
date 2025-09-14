"""
Tests for RBAC (Role-Based Access Control) functionality.

Tests all models and mixins in apps/accounts/rbac.py for high coverage.
"""

import os

import django

# Configure Django settings before any imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.rbac import RBACMixin, ScopedLocale, ScopedSection
from apps.i18n.models import Locale

User = get_user_model()


class ScopedLocaleModelTest(TestCase):
    """Test cases for ScopedLocale model."""

    def setUp(self):
        self.group = Group.objects.create(name="Test Editors")
        self.locale = Locale.objects.create(code="en", name="English")

    def test_scoped_locale_creation(self):
        """Test creating a ScopedLocale instance."""
        scoped_locale = ScopedLocale.objects.create(
            group=self.group, locale=self.locale
        )

        self.assertEqual(scoped_locale.group, self.group)
        self.assertEqual(scoped_locale.locale, self.locale)
        self.assertIsNotNone(scoped_locale.created_at)

    def test_scoped_locale_str_method(self):
        """Test ScopedLocale __str__ method."""
        scoped_locale = ScopedLocale.objects.create(
            group=self.group, locale=self.locale
        )

        expected_str = f"{self.group.name} → {self.locale.name}"
        self.assertEqual(str(scoped_locale), expected_str)

    def test_unique_together_constraint(self):
        """Test that group-locale combination must be unique."""
        # Create first scoped locale
        ScopedLocale.objects.create(group=self.group, locale=self.locale)

        # Trying to create another with same group-locale should fail
        with self.assertRaises(Exception):  # IntegrityError
            ScopedLocale.objects.create(group=self.group, locale=self.locale)

    def test_related_names(self):
        """Test related name access."""
        scoped_locale = ScopedLocale.objects.create(
            group=self.group, locale=self.locale
        )

        # Test reverse relations
        self.assertIn(scoped_locale, self.group.locale_scopes.all())
        self.assertIn(scoped_locale, self.locale.group_scopes.all())


class ScopedSectionModelTest(TestCase):
    """Test cases for ScopedSection model."""

    def setUp(self):
        self.group = Group.objects.create(name="Blog Editors")

    def test_scoped_section_creation(self):
        """Test creating a ScopedSection instance."""
        scoped_section = ScopedSection.objects.create(
            group=self.group,
            path_prefix="/blog",
            name="Blog Section",
            description="Blog management area",
        )

        self.assertEqual(scoped_section.group, self.group)
        self.assertEqual(scoped_section.path_prefix, "/blog")
        self.assertEqual(scoped_section.name, "Blog Section")
        self.assertEqual(scoped_section.description, "Blog management area")
        self.assertIsNotNone(scoped_section.created_at)

    def test_scoped_section_str_method(self):
        """Test ScopedSection __str__ method."""
        scoped_section = ScopedSection.objects.create(
            group=self.group, path_prefix="/products", name="Products"
        )

        expected_str = f"{self.group.name} → Products (/products)"
        self.assertEqual(str(scoped_section), expected_str)

    def test_clean_method_validates_path_prefix(self):
        """Test that clean method validates path prefix format."""
        # Invalid path prefix (doesn't start with /)
        scoped_section = ScopedSection(
            group=self.group, path_prefix="invalid", name="Invalid"
        )

        with self.assertRaises(ValidationError) as cm:
            scoped_section.clean()

        self.assertIn("path_prefix", cm.exception.message_dict)
        self.assertIn(
            'must start with "/"', str(cm.exception.message_dict["path_prefix"])
        )

    def test_clean_method_normalizes_trailing_slash(self):
        """Test that clean method normalizes trailing slashes."""
        scoped_section = ScopedSection(
            group=self.group, path_prefix="/blog/", name="Blog"
        )

        scoped_section.clean()
        self.assertEqual(scoped_section.path_prefix, "/blog")

        # Root path should keep its slash
        root_section = ScopedSection(group=self.group, path_prefix="/", name="Root")

        root_section.clean()
        self.assertEqual(root_section.path_prefix, "/")

    def test_save_calls_clean(self):
        """Test that save method calls clean automatically."""
        scoped_section = ScopedSection.objects.create(
            group=self.group, path_prefix="/news/", name="News"
        )

        # Should have been normalized during save
        self.assertEqual(scoped_section.path_prefix, "/news")

    def test_matches_path_method(self):
        """Test path matching logic."""
        # Root access section
        root_section = ScopedSection.objects.create(
            group=self.group, path_prefix="/", name="Root Access"
        )

        # Root should match everything
        self.assertTrue(root_section.matches_path("/"))
        self.assertTrue(root_section.matches_path("/blog"))
        self.assertTrue(root_section.matches_path("/blog/posts"))
        self.assertTrue(root_section.matches_path("/products/categories"))

        # Specific section
        blog_section = ScopedSection.objects.create(
            group=self.group, path_prefix="/blog", name="Blog Section"
        )

        # Should match exact path
        self.assertTrue(blog_section.matches_path("/blog"))

        # Should match sub-paths
        self.assertTrue(blog_section.matches_path("/blog/posts"))
        self.assertTrue(blog_section.matches_path("/blog/categories/tech"))

        # Should NOT match different paths
        self.assertFalse(blog_section.matches_path("/"))
        self.assertFalse(blog_section.matches_path("/products"))
        self.assertFalse(blog_section.matches_path("/blogpost"))  # Not a sub-path
        self.assertFalse(blog_section.matches_path("/news"))

    def test_unique_together_constraint(self):
        """Test that group-path_prefix combination must be unique."""
        # Create first scoped section
        ScopedSection.objects.create(group=self.group, path_prefix="/blog", name="Blog")

        # Trying to create another with same group-path_prefix should fail
        with self.assertRaises(Exception):  # IntegrityError
            ScopedSection.objects.create(
                group=self.group, path_prefix="/blog", name="Another Blog"
            )

    def test_ordering(self):
        """Test model ordering (longer paths first)."""
        # Create sections in random order
        section1 = ScopedSection.objects.create(
            group=self.group, path_prefix="/a", name="A"
        )
        section2 = ScopedSection.objects.create(
            group=self.group, path_prefix="/blog/categories", name="Blog Categories"
        )
        section3 = ScopedSection.objects.create(
            group=self.group, path_prefix="/blog", name="Blog"
        )

        # Should be ordered by -path_prefix (longer paths first)
        sections = list(ScopedSection.objects.all())
        paths = [s.path_prefix for s in sections]

        # Longer paths should come first for proper matching
        self.assertEqual(paths[0], "/blog/categories")
        self.assertEqual(paths[1], "/blog")
        self.assertEqual(paths[2], "/a")


class TestModel(RBACMixin):
    """Test model that uses RBACMixin for testing."""

    def __init__(self, locale=None, path=None):
        self.locale = locale
        self.path = path


class RBACMixinTest(TestCase):
    """Test cases for RBACMixin."""

    def setUp(self):
        # Create users
        self.superuser = User.objects.create_user(
            email="admin@example.com", is_superuser=True
        )

        self.regular_user = User.objects.create_user(email="user@example.com")

        self.anonymous_user = User(email="anonymous@example.com")  # Not authenticated

        # Create groups
        self.blog_editors = Group.objects.create(name="Blog Editors")
        self.news_editors = Group.objects.create(name="News Editors")

        # Add user to groups
        self.regular_user.groups.add(self.blog_editors)

        # Create locales
        self.en_locale = Locale.objects.create(code="en", name="English")
        self.fr_locale = Locale.objects.create(code="fr", name="French")

        # Create scoped permissions
        ScopedLocale.objects.create(group=self.blog_editors, locale=self.en_locale)
        ScopedSection.objects.create(
            group=self.blog_editors, path_prefix="/blog", name="Blog"
        )

    def test_user_has_locale_access_superuser(self):
        """Test that superuser has access to all locales."""
        test_obj = TestModel(locale=self.en_locale)
        self.assertTrue(test_obj.user_has_locale_access(self.superuser))

        test_obj = TestModel(locale=self.fr_locale)
        self.assertTrue(test_obj.user_has_locale_access(self.superuser))

    def test_user_has_locale_access_with_permission(self):
        """Test user with scoped locale access."""
        test_obj = TestModel(locale=self.en_locale)
        self.assertTrue(test_obj.user_has_locale_access(self.regular_user))

    def test_user_has_locale_access_without_permission(self):
        """Test user without scoped locale access."""
        test_obj = TestModel(locale=self.fr_locale)
        self.assertFalse(test_obj.user_has_locale_access(self.regular_user))

    def test_user_has_locale_access_anonymous_user(self):
        """Test that anonymous users have no locale access."""
        test_obj = TestModel(locale=self.en_locale)
        self.assertFalse(test_obj.user_has_locale_access(self.anonymous_user))

    def test_user_has_locale_access_no_locale_attribute(self):
        """Test objects without locale attribute."""
        test_obj = TestModel()  # No locale
        self.assertFalse(test_obj.user_has_locale_access(self.regular_user))

    def test_user_has_section_access_superuser(self):
        """Test that superuser has access to all sections."""
        test_obj = TestModel(path="/blog/posts")
        self.assertTrue(test_obj.user_has_section_access(self.superuser))

        test_obj = TestModel(path="/products")
        self.assertTrue(test_obj.user_has_section_access(self.superuser))

    def test_user_has_section_access_with_permission(self):
        """Test user with scoped section access."""
        test_obj = TestModel(path="/blog")
        self.assertTrue(test_obj.user_has_section_access(self.regular_user))

        test_obj = TestModel(path="/blog/posts/123")
        self.assertTrue(test_obj.user_has_section_access(self.regular_user))

    def test_user_has_section_access_without_permission(self):
        """Test user without scoped section access."""
        test_obj = TestModel(path="/products")
        self.assertFalse(test_obj.user_has_section_access(self.regular_user))

        test_obj = TestModel(path="/news")
        self.assertFalse(test_obj.user_has_section_access(self.regular_user))

    def test_user_has_section_access_anonymous_user(self):
        """Test that anonymous users have no section access."""
        test_obj = TestModel(path="/blog")
        self.assertFalse(test_obj.user_has_section_access(self.anonymous_user))

    def test_user_has_section_access_no_path_attribute(self):
        """Test objects without path attribute."""
        test_obj = TestModel()  # No path
        self.assertFalse(test_obj.user_has_section_access(self.regular_user))

    def test_user_has_scope_access_both_required(self):
        """Test that user_has_scope_access requires both locale AND section access."""
        # User has both permissions
        test_obj = TestModel(locale=self.en_locale, path="/blog")
        self.assertTrue(test_obj.user_has_scope_access(self.regular_user))

        # User has locale but not section permission
        test_obj = TestModel(locale=self.en_locale, path="/products")
        self.assertFalse(test_obj.user_has_scope_access(self.regular_user))

        # User has section but not locale permission
        test_obj = TestModel(locale=self.fr_locale, path="/blog")
        self.assertFalse(test_obj.user_has_scope_access(self.regular_user))

        # User has neither permission
        test_obj = TestModel(locale=self.fr_locale, path="/products")
        self.assertFalse(test_obj.user_has_scope_access(self.regular_user))

    def test_user_has_scope_access_superuser(self):
        """Test that superuser has full scope access."""
        test_obj = TestModel(locale=self.fr_locale, path="/products")
        self.assertTrue(test_obj.user_has_scope_access(self.superuser))


class RBACIntegrationTest(TestCase):
    """Integration tests for RBAC functionality."""

    def setUp(self):
        # Create a more complex setup
        self.superuser = User.objects.create_user(
            email="admin@example.com", is_superuser=True
        )

        self.content_manager = User.objects.create_user(email="manager@example.com")

        self.blog_editor = User.objects.create_user(email="blogger@example.com")

        # Create groups
        self.managers = Group.objects.create(name="Content Managers")
        self.bloggers = Group.objects.create(name="Blog Editors")

        # Assign users to groups
        self.content_manager.groups.add(self.managers)
        self.blog_editor.groups.add(self.bloggers)

        # Create locales
        self.en = Locale.objects.create(code="en", name="English")
        self.es = Locale.objects.create(code="es", name="Spanish")

        # Create scoped permissions
        # Managers have access to all content (root path) in English
        ScopedLocale.objects.create(group=self.managers, locale=self.en)
        ScopedSection.objects.create(
            group=self.managers, path_prefix="/", name="Full Site"
        )

        # Blog editors have access to blog section in both locales
        ScopedLocale.objects.create(group=self.bloggers, locale=self.en)
        ScopedLocale.objects.create(group=self.bloggers, locale=self.es)
        ScopedSection.objects.create(
            group=self.bloggers, path_prefix="/blog", name="Blog Section"
        )

    def test_manager_permissions(self):
        """Test content manager permissions."""
        # Manager should have access to English content anywhere
        en_blog = TestModel(locale=self.en, path="/blog/post-1")
        en_product = TestModel(locale=self.en, path="/products/item-1")

        self.assertTrue(en_blog.user_has_scope_access(self.content_manager))
        self.assertTrue(en_product.user_has_scope_access(self.content_manager))

        # Manager should NOT have access to Spanish content
        es_blog = TestModel(locale=self.es, path="/blog/post-1")
        self.assertFalse(es_blog.user_has_scope_access(self.content_manager))

    def test_blog_editor_permissions(self):
        """Test blog editor permissions."""
        # Blog editor should have access to blog content in both locales
        en_blog = TestModel(locale=self.en, path="/blog/post-1")
        es_blog = TestModel(locale=self.es, path="/blog/post-1")

        self.assertTrue(en_blog.user_has_scope_access(self.blog_editor))
        self.assertTrue(es_blog.user_has_scope_access(self.blog_editor))

        # Blog editor should NOT have access to product content
        en_product = TestModel(locale=self.en, path="/products/item-1")
        es_product = TestModel(locale=self.es, path="/products/item-1")

        self.assertFalse(en_product.user_has_scope_access(self.blog_editor))
        self.assertFalse(es_product.user_has_scope_access(self.blog_editor))

    def test_superuser_permissions(self):
        """Test that superuser bypasses all RBAC restrictions."""
        # Superuser should have access to everything
        test_objects = [
            TestModel(locale=self.en, path="/blog/post-1"),
            TestModel(locale=self.es, path="/blog/post-1"),
            TestModel(locale=self.en, path="/products/item-1"),
            TestModel(locale=self.es, path="/products/item-1"),
        ]

        for obj in test_objects:
            self.assertTrue(obj.user_has_scope_access(self.superuser))

    def test_multiple_section_scopes(self):
        """Test users with multiple section scopes."""
        # Give blog editor additional access to news section
        ScopedSection.objects.create(
            group=self.bloggers, path_prefix="/news", name="News Section"
        )

        # Now blog editor should have access to both blog and news
        blog_post = TestModel(locale=self.en, path="/blog/post-1")
        news_article = TestModel(locale=self.en, path="/news/article-1")
        product_page = TestModel(locale=self.en, path="/products/item-1")

        self.assertTrue(blog_post.user_has_scope_access(self.blog_editor))
        self.assertTrue(news_article.user_has_scope_access(self.blog_editor))
        self.assertFalse(product_page.user_has_scope_access(self.blog_editor))

    def test_path_hierarchy_matching(self):
        """Test that path matching works correctly with hierarchies."""
        # Create nested path scopes
        blog_editors = Group.objects.create(name="General Blog Editors")
        tech_editors = Group.objects.create(name="Tech Blog Editors")

        user1 = User.objects.create_user(
            email="user1@example.com", password="testpass123"
        )
        user2 = User.objects.create_user(
            email="user2@example.com", password="testpass123"
        )

        user1.groups.add(blog_editors)
        user2.groups.add(tech_editors)

        # Set up locale access for both
        ScopedLocale.objects.create(group=blog_editors, locale=self.en)
        ScopedLocale.objects.create(group=tech_editors, locale=self.en)

        # Set up section access
        ScopedSection.objects.create(
            group=blog_editors, path_prefix="/blog", name="All Blog"
        )
        ScopedSection.objects.create(
            group=tech_editors, path_prefix="/blog/tech", name="Tech Blog"
        )

        # Test access patterns
        general_post = TestModel(locale=self.en, path="/blog/general-post")
        tech_post = TestModel(locale=self.en, path="/blog/tech/new-framework")
        deep_tech_post = TestModel(locale=self.en, path="/blog/tech/tutorials/advanced")

        # General blog editor should have access to all blog content
        self.assertTrue(general_post.user_has_scope_access(user1))
        self.assertTrue(tech_post.user_has_scope_access(user1))
        self.assertTrue(deep_tech_post.user_has_scope_access(user1))

        # Tech editor should only have access to tech blog content
        self.assertFalse(general_post.user_has_scope_access(user2))
        self.assertTrue(tech_post.user_has_scope_access(user2))
        self.assertTrue(deep_tech_post.user_has_scope_access(user2))
