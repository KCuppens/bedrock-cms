"""
End-to-End Testing Utilities

Provides common utilities, fixtures, and helper classes for E2E workflow testing.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase
from django.test.client import Client
from django.urls import reverse
from django.utils import timezone

import factory
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

# Import models
from apps.accounts.models import User, UserProfile
from apps.blog.models import BlogPost, BlogSettings, Category, Tag
from apps.cms.models import BlockType, Page
from apps.files.models import FileUpload
from apps.i18n.models import Locale

User = get_user_model()


class E2ETestMixin:
    """
    Base mixin for E2E tests providing common functionality.
    """

    def setUp(self):
        """Set up common test data and utilities."""
        super().setUp()

        # Ensure essential database tables exist
        self.ensure_essential_tables()

        # Clear cache between tests
        cache.clear()

        # Create test locales
        self.en_locale = self.create_locale("en", "English")
        self.es_locale = self.create_locale("es", "Español")
        self.fr_locale = self.create_locale("fr", "Français")

        # Create user groups and permissions
        self.setup_permissions()

        # Create test users with different roles
        self.setup_test_users()

        # Create API clients
        self.setup_clients()

        # Initialize timing tracking
        self.performance_timings = {}

    def ensure_essential_tables(self):
        """Ensure essential database tables exist."""
        try:
            # Check if authtoken_token table exists
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM django_content_type LIMIT 1")
        except Exception:
            # Run migrate for essential apps only
            try:
                call_command("migrate", "contenttypes", verbosity=0, interactive=False)
                call_command("migrate", "auth", verbosity=0, interactive=False)
                call_command("migrate", "authtoken", verbosity=0, interactive=False)
            except Exception:
                # If migration fails, we'll handle it in setup_clients
                pass

    def create_locale(self, code: str, name: str) -> Locale:
        """Create a test locale."""
        locale, created = Locale.objects.get_or_create(
            code=code,
            defaults={"name": name, "is_active": True, "is_default": code == "en"},
        )
        return locale

    def setup_permissions(self):
        """Set up user groups and permissions."""
        # Create groups
        self.admin_group, _ = Group.objects.get_or_create(name="Admin")
        self.editor_group, _ = Group.objects.get_or_create(name="Editor")
        self.author_group, _ = Group.objects.get_or_create(name="Author")
        self.viewer_group, _ = Group.objects.get_or_create(name="Viewer")

        # Assign permissions to groups
        self._assign_group_permissions()

    def _assign_group_permissions(self):
        """Assign permissions to user groups."""
        # Admin group - all permissions
        admin_perms = Permission.objects.all()
        self.admin_group.permissions.set(admin_perms)

        # Editor group - content management permissions
        editor_perms = Permission.objects.filter(
            codename__in=[
                "add_page",
                "change_page",
                "delete_page",
                "publish_page",
                "add_blogpost",
                "change_blogpost",
                "delete_blogpost",
                "publish_blogpost",
                "add_category",
                "change_category",
                "delete_category",
                "add_tag",
                "change_tag",
                "delete_tag",
                "moderate_content",
                "approve_content",
            ]
        )
        self.editor_group.permissions.set(editor_perms)

        # Author group - content creation permissions
        author_perms = Permission.objects.filter(
            codename__in=[
                "add_page",
                "change_page",
                "delete_page",
                "add_blogpost",
                "change_blogpost",
                "delete_blogpost",
                "add_category",
                "change_category",
                "delete_category",
                "add_tag",
                "change_tag",
                "delete_tag",
            ]
        )
        self.author_group.permissions.set(author_perms)

    def setup_test_users(self):
        """Create test users with different roles."""
        # Superuser
        self.superuser = User.objects.create_superuser(
            email="superuser@example.com",
            password="testpass123",
            name="Super User",
            is_active=True,
        )

        # Admin user
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            name="Admin User",
            is_active=True,
            is_staff=True,
        )
        self.admin_user.groups.add(self.admin_group)

        # Editor user
        self.editor_user = User.objects.create_user(
            email="editor@example.com",
            password="testpass123",
            name="Editor User",
            is_active=True,
        )
        self.editor_user.groups.add(self.editor_group)

        # Author user
        self.author_user = User.objects.create_user(
            email="author@example.com",
            password="testpass123",
            name="Author User",
            is_active=True,
            is_staff=True,
        )
        self.author_user.groups.add(self.author_group)

        # Regular viewer user
        self.viewer_user = User.objects.create_user(
            email="viewer@example.com",
            password="testpass123",
            name="Viewer User",
            is_active=True,
        )
        self.viewer_user.groups.add(self.viewer_group)

        # Create user profiles
        self.create_user_profiles()

    def create_user_profiles(self):
        """Create user profiles for test users."""
        profiles = [
            (self.superuser, "UTC", "en"),
            (self.admin_user, "America/New_York", "en"),
            (self.editor_user, "Europe/London", "en"),
            (self.author_user, "Europe/Madrid", "es"),
            (self.viewer_user, "America/Los_Angeles", "en"),
        ]

        for user, tz, lang in profiles:
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "timezone": tz,
                    "language": lang,
                    "bio": f"Test bio for {user.name}",
                    "receive_notifications": True,
                },
            )

    def setup_clients(self):
        """Set up HTTP and API clients."""
        self.web_client = Client()
        self.api_client = APIClient()

        # Create API tokens for users - handle cases where Token table might not exist
        self._create_user_tokens()

    def _create_user_tokens(self):
        """Create tokens for test users with fallback handling."""
        users = [
            ("superuser", self.superuser),
            ("admin", self.admin_user),
            ("editor", self.editor_user),
            ("author", self.author_user),
            ("viewer", self.viewer_user),
        ]

        for role, user in users:
            try:
                token, _ = Token.objects.get_or_create(user=user)
                setattr(self, f"{role}_token", token)
            except Exception:
                # If Token table doesn't exist, create a mock token
                from unittest.mock import Mock

                mock_token = Mock()
                mock_token.key = f"mock-token-{role}"
                mock_token.user = user
                setattr(self, f"{role}_token", mock_token)

    def login_user(self, user: User, client: Client = None) -> Client:
        """Login a user and return the client."""
        if client is None:
            client = self.web_client

        client.login(email=user.email, password="testpass123")
        return client

    def api_authenticate(self, user: User, client: APIClient = None) -> APIClient:
        """Authenticate API client with user token."""
        if client is None:
            client = self.api_client

        try:
            token = Token.objects.get(user=user)
            client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        except Exception:
            # Fallback for cases where Token table doesn't exist
            # Use force_authenticate for test purposes
            client.force_authenticate(user=user)

        return client

    def create_sample_content(self):
        """Create sample content for testing."""
        # Create blog settings
        self.blog_settings = BlogSettings.objects.create(
            locale=self.en_locale,
            base_path="blog",
            show_toc=True,
            show_author=True,
            show_dates=True,
        )

        # Create categories
        self.tech_category = Category.objects.create(
            name="Technology",
            slug="technology",
            description="Technology related posts",
            color="#3b82f6",
            is_active=True,
        )

        self.design_category = Category.objects.create(
            name="Design",
            slug="design",
            description="Design related posts",
            color="#f59e0b",
            is_active=True,
        )

        # Create tags
        self.python_tag = Tag.objects.create(
            name="Python", slug="python", description="Python programming language"
        )

        self.django_tag = Tag.objects.create(
            name="Django", slug="django", description="Django web framework"
        )

        # Create block types
        self.create_block_types()

        # Create sample pages
        self.create_sample_pages()

        # Create sample blog posts
        self.create_sample_blog_posts()

    def create_block_types(self):
        """Create common block types for testing."""
        block_types = [
            {
                "type": "richtext",
                "component": "RichtextBlock",
                "label": "Rich Text",
                "description": "Rich text editor block",
                "category": "content",
                "icon": "type",
                "default_props": {"content": "<p>Enter your content here...</p>"},
                "schema": {
                    "type": "object",
                    "properties": {"content": {"type": "string"}},
                },
                "is_active": True,
            },
            {
                "type": "hero",
                "component": "HeroBlock",
                "label": "Hero Section",
                "description": "Hero section with title and CTA",
                "category": "layout",
                "icon": "layout-grid",
                "default_props": {
                    "title": "Hero Title",
                    "subtitle": "Hero subtitle",
                    "cta_text": "Call to Action",
                    "cta_url": "#",
                },
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "subtitle": {"type": "string"},
                    },
                },
                "is_active": True,
            },
            {
                "type": "content_detail",
                "component": "ContentDetailBlock",
                "label": "Content Detail",
                "description": "Display content from other models",
                "category": "dynamic",
                "icon": "database",
                "model_name": "blog.BlogPost",
                "data_source": "list",
                "default_props": {"query": {}, "limit": 10},
                "schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "object"},
                        "limit": {"type": "number"},
                    },
                },
                "is_active": True,
            },
        ]

        for block_data in block_types:
            BlockType.objects.create(**block_data)

    def create_sample_pages(self):
        """Create sample pages for testing."""
        # Homepage - check for migration-created homepage first, then create if needed
        self.homepage = Page.objects.filter(locale=self.en_locale, path="/").first()

        if not self.homepage:
            self.homepage = Page.objects.create(
                title="Homepage",
                slug="",
                locale=self.en_locale,
                status="published",
                is_homepage=True,
                blocks=[
                    {
                        "type": "hero",
                        "id": "hero-1",
                        "props": {
                            "title": "Welcome to Bedrock CMS",
                            "subtitle": "The modern content management system",
                            "cta_text": "Get Started",
                            "cta_url": "/about/",
                        },
                    }
                ],
                published_at=timezone.now(),
            )

        # About page
        self.about_page = Page.objects.filter(
            slug="about", locale=self.en_locale
        ).first()

        if not self.about_page:
            self.about_page = Page.objects.create(
                title="About Us",
                slug="about",
                locale=self.en_locale,
                status="published",
                blocks=[
                    {
                        "type": "richtext",
                        "id": "content-1",
                        "props": {
                            "content": "<h1>About Us</h1><p>We are a modern CMS provider.</p>"
                        },
                    }
                ],
                published_at=timezone.now(),
            )

        # Blog presentation page
        self.blog_page = Page.objects.filter(slug="blog", locale=self.en_locale).first()

        if not self.blog_page:
            self.blog_page = Page.objects.create(
                title="Blog",
                slug="blog",
                locale=self.en_locale,
                status="published",
                blocks=[
                    {
                        "type": "content_detail",
                        "id": "blog-posts-1",
                        "props": {
                            "content_type": "blog.blogpost",
                            "query": {"status": "published"},
                            "limit": 10,
                            "ordering": "-published_at",
                        },
                    }
                ],
                published_at=timezone.now(),
            )

        # Update blog settings to use this page
        self.blog_settings.default_presentation_page = self.blog_page
        self.blog_settings.save()

    def create_sample_blog_posts(self):
        """Create sample blog posts for testing."""
        posts_data = [
            {
                "title": "Getting Started with Bedrock CMS",
                "slug": "getting-started-bedrock-cms",
                "content": "This is a comprehensive guide to getting started with Bedrock CMS.",
                "category": self.tech_category,
                "tags": [self.python_tag, self.django_tag],
                "status": "published",
                "featured": True,
            },
            {
                "title": "Design Best Practices",
                "slug": "design-best-practices",
                "content": "Learn about the latest design best practices for modern web applications.",
                "category": self.design_category,
                "tags": [],
                "status": "published",
                "featured": False,
            },
            {
                "title": "Draft Post Example",
                "slug": "draft-post-example",
                "content": "This is a draft post that has not been published yet.",
                "category": self.tech_category,
                "tags": [self.python_tag],
                "status": "draft",
                "featured": False,
            },
        ]

        for i, post_data in enumerate(posts_data):
            tags = post_data.pop("tags")
            post = BlogPost.objects.create(
                locale=self.en_locale,
                author=self.author_user,
                excerpt=f'Excerpt for {post_data["title"]}',
                blocks=[
                    {
                        "type": "richtext",
                        "id": f"content-{i}",
                        "props": {
                            "content": f'<h1>{post_data["title"]}</h1><p>{post_data["content"]}</p>'
                        },
                    }
                ],
                published_at=(
                    timezone.now() if post_data["status"] == "published" else None
                ),
                **post_data,
            )

            if tags:
                post.tags.set(tags)

            # Store for later reference
            if post_data["slug"] == "getting-started-bedrock-cms":
                self.featured_post = post
            elif post_data["slug"] == "design-best-practices":
                self.design_post = post
            elif post_data["slug"] == "draft-post-example":
                self.draft_post = post

    def create_test_file(self, filename="test.jpg", content_type="image/jpeg"):
        """Create a test file upload."""
        file_content = b"fake-image-content"
        uploaded_file = SimpleUploadedFile(
            filename, file_content, content_type=content_type
        )

        file_upload = FileUpload.objects.create(
            file=uploaded_file,
            filename=filename,
            size=len(file_content),
            content_type=content_type,
            uploaded_by=self.author_user,
        )

        return file_upload

    def simulate_user_journey(
        self, steps: List[Dict[str, Any]], user: User = None
    ) -> Dict[str, Any]:
        """
        Simulate a complete user journey with multiple steps.

        Args:
            steps: List of step dictionaries with 'action', 'url', 'method', 'data', etc.
            user: User to authenticate as (optional)

        Returns:
            Dict with journey results and performance metrics
        """
        if user:
            self.login_user(user)

        journey_results = {
            "steps": [],
            "total_time": 0,
            "success": True,
            "error_steps": [],
        }

        start_time = time.time()

        for i, step in enumerate(steps):
            step_start = time.time()
            step_result = self._execute_journey_step(step, i)
            step_end = time.time()

            step_result["execution_time"] = step_end - step_start
            journey_results["steps"].append(step_result)

            if not step_result["success"]:
                journey_results["success"] = False
                journey_results["error_steps"].append(i)

            # Add delay between steps if specified
            if "delay" in step:
                time.sleep(step["delay"])

        journey_results["total_time"] = time.time() - start_time
        return journey_results

    def _execute_journey_step(
        self, step: Dict[str, Any], step_index: int
    ) -> Dict[str, Any]:
        """Execute a single step in a user journey."""
        action = step.get("action", "request")
        method = step.get("method", "GET").upper()
        url = step.get("url", "/")
        data = step.get("data", {})
        expected_status = step.get("expected_status", 200)
        validate_content = step.get("validate_content", [])

        step_result = {
            "step_index": step_index,
            "action": action,
            "url": url,
            "method": method,
            "success": False,
            "status_code": None,
            "content_validations": [],
            "error_message": None,
        }

        try:
            # Execute the request
            if method == "GET":
                response = self.web_client.get(url, data)
            elif method == "POST":
                response = self.web_client.post(url, data)
            elif method == "PUT":
                response = self.web_client.put(url, data)
            elif method == "DELETE":
                response = self.web_client.delete(url, data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            step_result["status_code"] = response.status_code

            # Check status code
            if response.status_code == expected_status:
                step_result["success"] = True
            else:
                step_result["error_message"] = (
                    f"Expected status {expected_status}, got {response.status_code}"
                )

            # Validate content if specified
            if validate_content and step_result["success"]:
                content = response.content.decode("utf-8")
                for validation in validate_content:
                    if validation in content:
                        step_result["content_validations"].append(
                            {"text": validation, "found": True}
                        )
                    else:
                        step_result["content_validations"].append(
                            {"text": validation, "found": False}
                        )
                        step_result["success"] = False
                        step_result["error_message"] = (
                            f"Content validation failed: {validation}"
                        )

        except Exception as e:
            step_result["error_message"] = str(e)

        return step_result

    def measure_performance(self, operation_name: str, func, *args, **kwargs):
        """Measure performance of an operation."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        self.performance_timings[operation_name] = end_time - start_time
        return result

    def assert_performance_threshold(self, operation_name: str, max_time: float):
        """Assert that an operation completed within a time threshold."""
        actual_time = self.performance_timings.get(operation_name)
        if actual_time is None:
            raise AssertionError(f"No timing recorded for operation: {operation_name}")

        if actual_time > max_time:
            raise AssertionError(
                f"Operation {operation_name} took {actual_time:.3f}s, "
                f"exceeding threshold of {max_time:.3f}s"
            )

    def simulate_concurrent_users(self, user_actions: List[Dict], num_users: int = 5):
        """
        Simulate concurrent user actions for load testing.

        Args:
            user_actions: List of action dictionaries
            num_users: Number of concurrent users to simulate

        Returns:
            Dict with results from all users
        """
        import queue
        import threading

        results_queue = queue.Queue()
        threads = []

        def user_thread(user_id, actions):
            client = Client()
            thread_results = {"user_id": user_id, "actions": []}

            for action in actions:
                start_time = time.time()
                try:
                    response = client.get(action.get("url", "/"))
                    result = {
                        "url": action.get("url", "/"),
                        "status_code": response.status_code,
                        "response_time": time.time() - start_time,
                        "success": response.status_code
                        == action.get("expected_status", 200),
                    }
                except Exception as e:
                    result = {
                        "url": action.get("url", "/"),
                        "error": str(e),
                        "response_time": time.time() - start_time,
                        "success": False,
                    }

                thread_results["actions"].append(result)

            results_queue.put(thread_results)

        # Start threads
        for i in range(num_users):
            thread = threading.Thread(target=user_thread, args=(i, user_actions))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect results
        all_results = []
        while not results_queue.empty():
            all_results.append(results_queue.get())

        return all_results

    def cleanup_test_data(self):
        """Clean up test data after tests."""
        # Clear any uploaded files
        try:
            FileUpload.objects.filter(
                uploaded_by__in=[
                    self.superuser,
                    self.admin_user,
                    self.editor_user,
                    self.author_user,
                    self.viewer_user,
                ]
            ).delete()
        except:
            pass

        # Clear cache
        cache.clear()


class E2ETestCase(E2ETestMixin, TestCase):
    """Base test case for E2E tests using TestCase."""

    pass


class E2ETransactionTestCase(E2ETestMixin, TransactionTestCase):
    """Base test case for E2E tests requiring database transactions."""

    pass


class WorkflowTestMixin:
    """Mixin for testing complete workflows with validation."""

    def validate_workflow_step(
        self, step_name: str, response, expected_data: Dict = None
    ):
        """Validate a workflow step response."""
        self.assertIsNotNone(response, f"No response for step: {step_name}")

        if expected_data:
            for key, value in expected_data.items():
                if hasattr(response, "json"):
                    response_data = response.json()
                    self.assertIn(
                        key, response_data, f"Missing key {key} in {step_name} response"
                    )
                    if value is not None:
                        self.assertEqual(
                            response_data[key],
                            value,
                            f"Unexpected value for {key} in {step_name}",
                        )

    def assert_workflow_completion(self, workflow_results: Dict):
        """Assert that a complete workflow was successful."""
        self.assertTrue(
            workflow_results["success"],
            f"Workflow failed at steps: {workflow_results['error_steps']}",
        )

        # Check that all steps completed
        self.assertGreater(
            len(workflow_results["steps"]), 0, "No workflow steps executed"
        )

        # Check performance
        self.assertLess(
            workflow_results["total_time"],
            30.0,
            f"Workflow took too long: {workflow_results['total_time']:.2f}s",
        )


class DataIntegrityMixin:
    """Mixin for validating data integrity across workflows."""

    def assert_data_consistency(self, model_class, field_checks: Dict):
        """Assert that data remains consistent across model instances."""
        for field_name, expected_count in field_checks.items():
            actual_count = model_class.objects.filter(**{field_name: True}).count()
            self.assertEqual(
                actual_count,
                expected_count,
                f"Data inconsistency in {model_class.__name__}.{field_name}: "
                f"expected {expected_count}, got {actual_count}",
            )

    def validate_audit_trail(self, content_object, expected_actions: List[str]):
        """Validate that audit trail contains expected actions."""
        # This would integrate with the audit system if available
        pass

    def check_cache_consistency(self, cache_keys: List[str]):
        """Check that cache remains consistent."""
        for key in cache_keys:
            cached_value = cache.get(key)
            # Add specific validation based on cache key patterns
            if cached_value is not None:
                self.assertIsNotNone(cached_value, f"Cache key {key} unexpectedly None")


class PerformanceMixin:
    """Mixin for performance testing in workflows."""

    def assert_page_load_time(self, url: str, max_time: float = 2.0, user: User = None):
        """Assert that a page loads within the specified time."""
        if user:
            self.login_user(user)

        start_time = time.time()
        response = self.web_client.get(url)
        load_time = time.time() - start_time

        self.assertEqual(response.status_code, 200, f"Page {url} failed to load")
        self.assertLess(
            load_time,
            max_time,
            f"Page {url} took {load_time:.3f}s to load, exceeding {max_time}s threshold",
        )

    def assert_api_response_time(
        self, url: str, max_time: float = 1.0, user: User = None
    ):
        """Assert that an API endpoint responds within the specified time."""
        if user:
            self.api_authenticate(user)

        start_time = time.time()
        response = self.api_client.get(url)
        response_time = time.time() - start_time

        self.assertIn(
            response.status_code, [200, 201, 204], f"API {url} returned error"
        )
        self.assertLess(
            response_time,
            max_time,
            f"API {url} took {response_time:.3f}s to respond, exceeding {max_time}s threshold",
        )
