"""
Performance test fixtures for Bedrock CMS.

This module provides utilities for generating large datasets for performance testing:
- Bulk content creation (pages, blog posts, translations)
- User and permission data generation
- Multilingual content generation
- Search index data
- Analytics test data
"""

import os
import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Setup Django before any imports
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

# Import models - adjust based on actual model structure
try:
    from django.contrib.auth import get_user_model

    from apps.accounts.models import UserProfile
    from apps.blog.models import BlogPost, Category, Tag
    from apps.cms.models import Page, PageTranslation

    User = get_user_model()
    from apps.analytics.models import PageView, SearchQuery
    from apps.i18n.models import Locale, TranslationUnit
    from apps.search.models import SearchIndex
except ImportError as e:
    # Handle missing models gracefully for testing
    print(f"Warning: Could not import some models: {e}")
    Page = PageTranslation = BlogPost = Category = Tag = None
    UserProfile = Locale = TranslationUnit = None
    PageView = SearchQuery = SearchIndex = None

User = get_user_model()


class PerformanceDataFixtures:
    """Main class for generating performance test data."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize with optional random seed for reproducible data."""
        if seed:
            random.seed(seed)

    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate random string of specified length."""
        return "".join(random.choices(string.ascii_letters, k=length))

    @staticmethod
    def random_text(min_words: int = 10, max_words: int = 100) -> str:
        """Generate random text with specified word count range."""
        words = [
            "lorem",
            "ipsum",
            "dolor",
            "sit",
            "amet",
            "consectetur",
            "adipiscing",
            "elit",
            "sed",
            "do",
            "eiusmod",
            "tempor",
            "incididunt",
            "ut",
            "labore",
            "et",
            "dolore",
            "magna",
            "aliqua",
            "enim",
            "ad",
            "minim",
            "veniam",
            "quis",
            "nostrud",
            "exercitation",
            "ullamco",
            "laboris",
            "nisi",
            "aliquip",
            "ex",
            "ea",
            "commodo",
            "consequat",
            "duis",
            "aute",
            "irure",
            "in",
            "reprehenderit",
            "voluptate",
            "velit",
            "esse",
            "cillum",
            "fugiat",
            "nulla",
            "pariatur",
            "excepteur",
            "sint",
            "occaecat",
            "cupidatat",
            "non",
            "proident",
            "sunt",
            "culpa",
            "qui",
            "officia",
            "deserunt",
            "mollit",
            "anim",
            "id",
            "est",
            "laborum",
            "django",
            "python",
            "web",
            "development",
            "cms",
            "content",
            "management",
            "system",
            "performance",
            "testing",
            "optimization",
            "database",
            "queries",
            "caching",
            "scalability",
        ]

        word_count = random.randint(min_words, max_words)
        selected_words = random.choices(words, k=word_count)
        return " ".join(selected_words).capitalize() + "."

    def create_bulk_users(self, count: int = 100) -> List[User]:
        """Create bulk users for testing."""
        users = []

        with transaction.atomic():
            for i in range(count):
                email = f"testuser{i:04d}@example.com"

                user = User.objects.create_user(
                    email=email,
                    password="testpass123",
                    first_name=self.random_string(8),
                    last_name=self.random_string(10),
                    is_active=True,
                    is_staff=random.choice([True, False]) if i < count // 10 else False,
                    date_joined=timezone.now() - timedelta(days=random.randint(1, 365)),
                )
                users.append(user)

                # Create user profile if model exists
                if UserProfile:
                    UserProfile.objects.create(
                        user=user,
                        bio=self.random_text(20, 50),
                        date_of_birth=timezone.now().date()
                        - timedelta(days=random.randint(6000, 20000)),
                    )

        return users

    def create_bulk_pages(self, count: int = 500, max_depth: int = 3) -> List[Any]:
        """Create bulk CMS pages with hierarchical structure."""
        if not Page:
            return []

        # Create or get default locale if needed
        default_locale = None
        if Locale:
            default_locale, _ = Locale.objects.get_or_create(
                code="en",
                defaults={
                    "name": "English",
                    "native_name": "English",
                    "is_default": True,
                    "is_active": True,
                },
            )

        pages = []
        root_pages = []

        with transaction.atomic():
            # Create root pages first
            root_count = min(20, count // 10)
            for i in range(root_count):
                title = f"Root Page {i+1}: {self.random_string(15)}"
                slug = slugify(title)

                page_data = {
                    "title": title,
                    "slug": slug,
                    "status": "published" if random.random() > 0.2 else "draft",
                    "parent": None,
                }

                # Add locale if available
                if default_locale:
                    page_data["locale"] = default_locale

                # Add fields that exist
                if hasattr(Page, "content"):
                    page_data["content"] = self.random_text(100, 500)
                if hasattr(Page, "created_at"):
                    page_data["created_at"] = timezone.now() - timedelta(
                        days=random.randint(1, 180)
                    )
                if hasattr(Page, "updated_at"):
                    page_data["updated_at"] = timezone.now() - timedelta(
                        days=random.randint(0, 30)
                    )
                if hasattr(Page, "depth"):
                    page_data["depth"] = 0

                page = Page.objects.create(**page_data)
                pages.append(page)
                root_pages.append(page)

            # Create child pages
            remaining_count = count - root_count
            current_depth = 1
            current_parents = root_pages

            while remaining_count > 0 and current_depth <= max_depth:
                pages_this_level = min(remaining_count, len(current_parents) * 5)
                next_parents = []

                for i in range(pages_this_level):
                    parent = random.choice(current_parents)
                    title = (
                        f"Child Page {current_depth}-{i+1}: {self.random_string(12)}"
                    )
                    slug = slugify(title)

                    child_page_data = {
                        "title": title,
                        "slug": slug,
                        "status": "published" if random.random() > 0.15 else "draft",
                        "parent": parent,
                    }

                    # Add locale if available
                    if default_locale:
                        child_page_data["locale"] = default_locale

                    # Add fields that exist
                    if hasattr(Page, "content"):
                        child_page_data["content"] = self.random_text(50, 300)
                    if hasattr(Page, "created_at"):
                        child_page_data["created_at"] = timezone.now() - timedelta(
                            days=random.randint(1, 120)
                        )
                    if hasattr(Page, "updated_at"):
                        child_page_data["updated_at"] = timezone.now() - timedelta(
                            days=random.randint(0, 20)
                        )
                    if hasattr(Page, "depth"):
                        child_page_data["depth"] = current_depth

                    page = Page.objects.create(**child_page_data)
                    pages.append(page)

                    # Some child pages become parents for next level
                    if random.random() > 0.6:
                        next_parents.append(page)

                current_parents = next_parents
                current_depth += 1
                remaining_count -= pages_this_level

        return pages

    def create_bulk_blog_posts(
        self, count: int = 1000, users: Optional[List[User]] = None
    ) -> List[Any]:
        """Create bulk blog posts with categories and tags."""
        if not BlogPost:
            return []

        # Create users if not provided
        if not users:
            users = self.create_bulk_users(20)

        # Create categories
        categories = []
        if Category:
            category_names = [
                "Technology",
                "Web Development",
                "Python",
                "Django",
                "JavaScript",
                "Performance",
                "Optimization",
                "Testing",
                "DevOps",
                "Security",
                "Design",
                "UX/UI",
                "Mobile",
                "AI/ML",
                "Data Science",
            ]

            for name in category_names:
                category, created = Category.objects.get_or_create(
                    name=name,
                    defaults={
                        "slug": slugify(name),
                        "description": self.random_text(10, 30),
                    },
                )
                categories.append(category)

        # Create tags
        tags = []
        if Tag:
            tag_names = [
                "performance",
                "optimization",
                "django",
                "python",
                "javascript",
                "react",
                "vue",
                "testing",
                "automation",
                "ci/cd",
                "docker",
                "kubernetes",
                "aws",
                "microservices",
                "api",
                "rest",
                "graphql",
                "database",
                "postgresql",
                "redis",
                "elasticsearch",
                "monitoring",
                "logging",
                "debugging",
                "profiling",
                "caching",
                "scaling",
            ]

            for name in tag_names:
                tag, created = Tag.objects.get_or_create(
                    name=name, defaults={"slug": slugify(name)}
                )
                tags.append(tag)

        # Create blog posts
        posts = []
        with transaction.atomic():
            for i in range(count):
                title = f"Blog Post {i+1}: {self.random_text(3, 8).rstrip('.')}"
                slug = slugify(title)

                post = BlogPost.objects.create(
                    title=title,
                    slug=slug,
                    content=self.random_text(200, 1000),
                    excerpt=self.random_text(20, 50),
                    author=random.choice(users),
                    status="published" if random.random() > 0.1 else "draft",
                    featured=random.random() > 0.9,
                    created_at=timezone.now() - timedelta(days=random.randint(1, 365)),
                    updated_at=timezone.now() - timedelta(days=random.randint(0, 30)),
                )

                # Add categories and tags
                if categories:
                    post.categories.set(
                        random.sample(categories, k=random.randint(1, 3))
                    )

                if tags:
                    post.tags.set(random.sample(tags, k=random.randint(2, 6)))

                posts.append(post)

        return posts

    def create_bulk_translations(
        self, pages: List[Any], locales: List[str] = None
    ) -> List[Any]:
        """Create bulk translations for pages."""
        if not PageTranslation or not pages:
            return []

        if not locales:
            locales = ["es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"]

        translations = []

        # Create locale objects if needed
        locale_objects = []
        if Locale:
            for code in locales:
                locale, created = Locale.objects.get_or_create(
                    code=code,
                    defaults={"name": f"Language {code.upper()}", "is_active": True},
                )
                locale_objects.append(locale)

        with transaction.atomic():
            for page in pages:
                # Translate to random subset of languages (not all)
                num_translations = random.randint(1, min(4, len(locales)))
                selected_locales = random.sample(locales, num_translations)

                for locale_code in selected_locales:
                    translation = PageTranslation.objects.create(
                        page=page,
                        locale=locale_code,
                        title=f"[{locale_code.upper()}] {page.title}",
                        content=f"[Translated to {locale_code}] {self.random_text(100, 400)}",
                        meta_title=f"[{locale_code.upper()}] {page.title[:50]}",
                        meta_description=self.random_text(15, 25),
                        is_published=random.random() > 0.2,
                        created_at=page.created_at
                        + timedelta(days=random.randint(1, 7)),
                        updated_at=timezone.now()
                        - timedelta(days=random.randint(0, 15)),
                    )
                    translations.append(translation)

        return translations

    def create_analytics_data(
        self, pages: List[Any], users: List[User], days: int = 30
    ) -> Dict[str, int]:
        """Create analytics data for performance testing."""
        if not PageView or not SearchQuery:
            return {"page_views": 0, "search_queries": 0}

        page_views_created = 0
        search_queries_created = 0

        # Generate page views
        with transaction.atomic():
            for day in range(days):
                date = timezone.now() - timedelta(days=day)

                # Generate 100-1000 page views per day
                daily_views = random.randint(100, 1000)

                for _ in range(daily_views):
                    page = random.choice(pages) if pages else None
                    user = (
                        random.choice(users) if random.random() > 0.6 else None
                    )  # 40% anonymous

                    PageView.objects.create(
                        page=page,
                        user=user,
                        ip_address=f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
                        user_agent=random.choice(
                            [
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                            ]
                        ),
                        referer=(
                            random.choice(
                                [
                                    "https://google.com",
                                    "https://twitter.com",
                                    "direct",
                                    "https://linkedin.com",
                                    None,
                                ]
                            )
                            if random.random() > 0.3
                            else None
                        ),
                        timestamp=date
                        + timedelta(
                            hours=random.randint(0, 23), minutes=random.randint(0, 59)
                        ),
                    )
                    page_views_created += 1

                # Generate search queries (10-100 per day)
                daily_searches = random.randint(10, 100)

                search_terms = [
                    "django",
                    "python",
                    "web development",
                    "cms",
                    "performance",
                    "optimization",
                    "testing",
                    "api",
                    "rest",
                    "database",
                    "caching",
                    "scaling",
                    "deployment",
                    "security",
                    "tutorial",
                ]

                for _ in range(daily_searches):
                    user = random.choice(users) if random.random() > 0.5 else None

                    SearchQuery.objects.create(
                        query=random.choice(search_terms),
                        user=user,
                        results_count=random.randint(0, 50),
                        execution_time=random.uniform(0.05, 2.0),
                        timestamp=date
                        + timedelta(
                            hours=random.randint(0, 23), minutes=random.randint(0, 59)
                        ),
                    )
                    search_queries_created += 1

        return {
            "page_views": page_views_created,
            "search_queries": search_queries_created,
        }

    def create_search_index_data(self, pages: List[Any], posts: List[Any]) -> int:
        """Create search index data for testing search performance."""
        if not SearchIndex:
            return 0

        indexed_count = 0

        with transaction.atomic():
            # Index pages
            for page in pages:
                if page.status == "published":
                    SearchIndex.objects.create(
                        content_type=ContentType.objects.get_for_model(Page),
                        object_id=page.id,
                        title=page.title,
                        content=page.content,
                        url=f"/pages/{page.slug}/",
                        language="en",
                        indexed_at=timezone.now(),
                    )
                    indexed_count += 1

            # Index blog posts
            for post in posts:
                if post.status == "published":
                    SearchIndex.objects.create(
                        content_type=ContentType.objects.get_for_model(BlogPost),
                        object_id=post.id,
                        title=post.title,
                        content=post.content,
                        url=f"/blog/{post.slug}/",
                        language="en",
                        indexed_at=timezone.now(),
                    )
                    indexed_count += 1

        return indexed_count


# Convenience functions for common operations


def create_bulk_pages(count: int = 500, max_depth: int = 3) -> List[Any]:
    """Create bulk CMS pages."""
    fixtures = PerformanceDataFixtures()
    return fixtures.create_bulk_pages(count, max_depth)


def create_bulk_blog_posts(
    count: int = 1000, users: Optional[List[User]] = None
) -> List[Any]:
    """Create bulk blog posts."""
    fixtures = PerformanceDataFixtures()
    return fixtures.create_bulk_blog_posts(count, users)


def create_bulk_translations(pages: List[Any], locales: List[str] = None) -> List[Any]:
    """Create bulk translations."""
    fixtures = PerformanceDataFixtures()
    return fixtures.create_bulk_translations(pages, locales)


def create_test_users(count: int = 100) -> List[User]:
    """Create test users."""
    fixtures = PerformanceDataFixtures()
    return fixtures.create_bulk_users(count)


def create_multilingual_content(
    page_count: int = 200, post_count: int = 500
) -> Dict[str, Any]:
    """Create complete multilingual content dataset."""
    fixtures = PerformanceDataFixtures()

    # Create users first
    users = fixtures.create_bulk_users(50)

    # Create pages and translations
    pages = fixtures.create_bulk_pages(page_count)
    translations = fixtures.create_bulk_translations(pages)

    # Create blog posts
    posts = fixtures.create_bulk_blog_posts(post_count, users)

    # Create analytics data
    analytics = fixtures.create_analytics_data(pages, users, days=60)

    # Create search index
    indexed_items = fixtures.create_search_index_data(pages, posts)

    return {
        "users": users,
        "pages": pages,
        "translations": translations,
        "blog_posts": posts,
        "analytics": analytics,
        "indexed_items": indexed_items,
        "summary": {
            "total_users": len(users),
            "total_pages": len(pages),
            "total_translations": len(translations),
            "total_blog_posts": len(posts),
            "total_page_views": analytics.get("page_views", 0),
            "total_search_queries": analytics.get("search_queries", 0),
            "total_indexed_items": indexed_items,
        },
    }


def cleanup_performance_data():
    """Clean up all performance test data."""
    models_to_clean = [
        User,
        Page,
        PageTranslation,
        BlogPost,
        Category,
        Tag,
        UserProfile,
        Locale,
        TranslationUnit,
        PageView,
        SearchQuery,
        SearchIndex,
    ]

    # Delete in reverse order to handle foreign keys properly
    try:
        for model in reversed(models_to_clean):
            if model and hasattr(model, "objects") and hasattr(model.objects, "filter"):
                try:
                    # Only delete test data (with specific patterns)
                    if model == User:
                        # Delete test users in batches to avoid large transactions
                        test_users = model.objects.filter(email__startswith="testuser")
                        if test_users.exists():
                            # Delete in small batches
                            for user in test_users[:100]:  # Limit batch size
                                try:
                                    user.delete()
                                except Exception:
                                    # Skip if deletion fails due to constraints
                                    pass
                    elif hasattr(model, "title") and hasattr(model, "slug"):
                        # Pages and posts with test patterns
                        test_objects = model.objects.filter(title__icontains="Test")
                        if test_objects.exists():
                            test_objects.delete()
                    elif model in [PageView, SearchQuery, SearchIndex]:
                        # Analytics data - delete all for performance tests
                        if model.objects.exists():
                            model.objects.all().delete()
                except Exception as e:
                    # Log but don't fail if cleanup fails for a model
                    print(f"Warning: Could not clean up {model.__name__}: {e}")
                    continue

        # Clear cache
        cache.clear()

    except Exception as e:
        print(f"Warning: Performance test cleanup encountered issues: {e}")

    print("Performance test data cleanup completed")
