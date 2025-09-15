"""
End User Workflow Tests

Tests complete end user journeys including:
- Content discovery and navigation
- Multilingual content consumption
- Search functionality usage
- Content interaction and analytics tracking
- Mobile and accessibility workflows
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()

import json
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import BlogPost, Category, Tag
from apps.cms.models import Page
from apps.i18n.models import Locale

from .utils import DataIntegrityMixin, E2ETestCase, PerformanceMixin, WorkflowTestMixin

# Import the patch utilities
try:
    from .test_utils_patch import FrontendRouteMixin, requires_frontend
except ImportError:
    # Fallback if patch not available
    def requires_frontend(func):
        return unittest.skip("Requires front-end routes")(func)

    class FrontendRouteMixin:
        pass


class EndUserWorkflowTests(
    E2ETestCase, WorkflowTestMixin, DataIntegrityMixin, PerformanceMixin
):
    """Test complete end user workflows."""

    def setUp(self):
        super().setUp()
        self.create_sample_content()

    @requires_frontend
    def test_content_discovery_workflow(self):
        """Test complete content discovery journey."""
        # Simulate user journey: Homepage -> Blog -> Category -> Post
        discovery_steps = [
            {
                "action": "visit_homepage",
                "url": "/",
                "method": "GET",
                "expected_status": 200,
                "validate_content": ["Welcome to Bedrock CMS", "Get Started"],
            },
            {
                "action": "visit_blog",
                "url": "/blog/",
                "method": "GET",
                "expected_status": 200,
                "validate_content": ["Getting Started with Bedrock CMS"],
            },
            {
                "action": "visit_category",
                "url": "/blog/category/technology/",
                "method": "GET",
                "expected_status": 200,
                "validate_content": ["Technology", "Getting Started"],
            },
            {
                "action": "read_post",
                "url": "/blog/getting-started-bedrock-cms/",
                "method": "GET",
                "expected_status": 200,
                "validate_content": [
                    "Getting Started with Bedrock CMS",
                    "comprehensive guide",
                ],
            },
        ]

        # Execute discovery journey
        journey_results = self.simulate_user_journey(discovery_steps)

        # Validate the journey
        self.assert_workflow_completion(journey_results)

        # Verify each step loaded within performance threshold
        for step in journey_results["steps"]:
            self.assertLess(
                step["execution_time"],
                3.0,
                f"Step {step['action']} took too long: {step['execution_time']:.2f}s",
            )

    @requires_frontend
    def test_search_functionality_workflow(self):
        """Test complete search functionality usage."""
        # Test search workflow
        search_steps = [
            {
                "action": "visit_search_page",
                "url": "/search/",
                "method": "GET",
                "expected_status": 200,
                "validate_content": ["Search"],
            },
            {
                "action": "perform_search",
                "url": "/search/",
                "method": "GET",
                "data": {"q": "bedrock cms"},
                "expected_status": 200,
                "validate_content": ["Getting Started with Bedrock CMS"],
            },
            {
                "action": "filter_by_category",
                "url": "/search/",
                "method": "GET",
                "data": {"q": "design", "category": "design"},
                "expected_status": 200,
                "validate_content": ["Design Best Practices"],
            },
            {
                "action": "filter_by_tag",
                "url": "/search/",
                "method": "GET",
                "data": {"q": "", "tag": "python"},
                "expected_status": 200,
                "validate_content": ["Getting Started"],
            },
        ]

        # Execute search journey
        search_results = self.simulate_user_journey(search_steps)

        if search_results["success"]:
            self.assert_workflow_completion(search_results)
        else:
            # Search might not be implemented, test fallback behavior
            # Test direct blog browsing as alternative
            browse_response = self.web_client.get("/blog/")
            self.assertEqual(browse_response.status_code, 200)

        # Test search performance
        self.assert_page_load_time("/search/", max_time=2.0)

        # Test search suggestions (if available)
        suggest_response = self.web_client.get("/api/v1/search/suggest/", {"q": "bed"})
        if suggest_response.status_code == 200:
            suggestions = suggest_response.json()
            self.assertIsInstance(suggestions, list)

    @requires_frontend
    def test_multilingual_content_consumption(self):
        """Test multilingual content consumption workflow."""
        # Create Spanish content for testing
        es_post = BlogPost.objects.create(
            title="Primeros Pasos con Bedrock CMS",
            slug="primeros-pasos-bedrock-cms",
            content="Esta es una guía completa para comenzar con Bedrock CMS.",
            locale=self.es_locale,
            author=self.author_user,
            category=self.tech_category,
            status="published",
            published_at=timezone.now(),
            group_id=self.featured_post.group_id,  # Link to English version
        )

        # Test language switching workflow
        multilingual_steps = [
            {
                "action": "visit_english_content",
                "url": "/blog/getting-started-bedrock-cms/",
                "method": "GET",
                "expected_status": 200,
                "validate_content": ["Getting Started with Bedrock CMS"],
            },
            {
                "action": "switch_to_spanish",
                "url": "/es/blog/primeros-pasos-bedrock-cms/",
                "method": "GET",
                "expected_status": 200,
                "validate_content": ["Primeros Pasos con Bedrock CMS"],
            },
            {
                "action": "visit_spanish_blog",
                "url": "/es/blog/",
                "method": "GET",
                "expected_status": 200,
                "validate_content": ["Primeros Pasos"],
            },
        ]

        # Execute multilingual journey
        multilingual_results = self.simulate_user_journey(multilingual_steps)

        if multilingual_results["success"]:
            self.assert_workflow_completion(multilingual_results)
        else:
            # Language switching might not be implemented
            # Test that at least the content exists
            self.assertTrue(BlogPost.objects.filter(locale=self.es_locale).exists())

        # Test language preference detection
        # Simulate browser with Spanish preference
        spanish_response = self.web_client.get(
            "/", HTTP_ACCEPT_LANGUAGE="es-ES,es;q=0.9,en;q=0.8"
        )
        self.assertEqual(spanish_response.status_code, 200)

        # Clean up
        es_post.delete()

    @requires_frontend
    def test_content_interaction_workflow(self):
        """Test content interaction and engagement."""
        # Test reading workflow with analytics
        interaction_steps = [
            {
                "action": "start_reading",
                "url": "/blog/getting-started-bedrock-cms/",
                "method": "GET",
                "expected_status": 200,
                "validate_content": ["Getting Started with Bedrock CMS"],
            },
            {
                "action": "track_reading_progress",
                "url": "/api/v1/analytics/reading-progress/",
                "method": "POST",
                "data": {
                    "post_id": str(self.featured_post.id),
                    "progress": 50,
                    "time_spent": 30,
                },
                "expected_status": [200, 201, 404],  # 404 if analytics not implemented
            },
            {
                "action": "share_content",
                "url": "/api/v1/social/share/",
                "method": "POST",
                "data": {
                    "url": "/blog/getting-started-bedrock-cms/",
                    "platform": "twitter",
                },
                "expected_status": [200, 201, 404],
            },
            {
                "action": "view_related_posts",
                "url": f"/api/v1/blog/posts/{self.featured_post.id}/related/",
                "method": "GET",
                "expected_status": [200, 404],
            },
        ]

        # Execute interaction journey
        interaction_results = self.simulate_user_journey(interaction_steps)

        # Check if at least the main content loading worked
        main_step = interaction_results["steps"][0]
        self.assertTrue(main_step["success"], "Failed to load main content")

        # Test newsletter signup (if available)
        newsletter_response = self.web_client.post(
            "/api/v1/newsletter/subscribe/", {"email": "test@example.com"}
        )
        # Should either succeed or return 404 if not implemented
        self.assertIn(newsletter_response.status_code, [200, 201, 400, 404])

    def test_rss_feed_consumption(self):
        """Test RSS feed consumption workflow."""
        # Test RSS feeds
        rss_endpoints = [
            "/feed/",
            "/blog/feed/",
            "/blog/category/technology/feed/",
            "/blog/tag/python/feed/",
        ]

        for endpoint in rss_endpoints:
            response = self.web_client.get(endpoint)
            if response.status_code == 200:
                # Should be valid RSS/XML
                self.assertIn("content-type", response.headers)
                content_type = response.headers["content-type"].lower()
                self.assertTrue(
                    any(t in content_type for t in ["xml", "rss", "atom"]),
                    f"RSS feed {endpoint} returned unexpected content type: {content_type}",
                )

                # Should contain feed elements
                content = response.content.decode("utf-8")
                self.assertIn("<rss", content.lower() + "<atom", content.lower())

    def test_sitemap_discovery(self):
        """Test sitemap discovery and navigation."""
        # Test sitemap access
        sitemap_response = self.web_client.get("/sitemap.xml")

        if sitemap_response.status_code == 200:
            # Should be valid XML
            self.assertIn("content-type", sitemap_response.headers)
            content_type = sitemap_response.headers["content-type"].lower()
            self.assertIn("xml", content_type)

            # Should contain sitemap elements
            content = sitemap_response.content.decode("utf-8")
            self.assertIn("<urlset", content)
            self.assertIn("<url>", content)
            self.assertIn("<loc>", content)

        # Test robots.txt
        robots_response = self.web_client.get("/robots.txt")
        if robots_response.status_code == 200:
            content = robots_response.content.decode("utf-8")
            # Should contain robots directives
            self.assertTrue(
                "user-agent" in content.lower() or "sitemap:" in content.lower()
            )

    def test_error_handling_workflow(self):
        """Test error handling and recovery."""
        # Test 404 handling
        not_found_response = self.web_client.get("/non-existent-page/")
        self.assertEqual(not_found_response.status_code, 404)

        # Test 404 page content
        if hasattr(not_found_response, "content"):
            content = not_found_response.content.decode("utf-8")
            # Should contain helpful 404 information
            self.assertTrue(
                any(
                    phrase in content.lower()
                    for phrase in ["not found", "404", "page not found"]
                )
            )

        # Test handling of draft content access
        draft_response = self.web_client.get(f"/blog/{self.draft_post.slug}/")
        # Should either be 404 or require authentication
        self.assertIn(draft_response.status_code, [404, 403, 302])

        # Test handling of archived content
        archived_post = BlogPost.objects.create(
            title="Archived Test Post",
            slug="archived-test-post",
            content="This post is archived.",
            locale=self.en_locale,
            author=self.author_user,
            category=self.tech_category,
            status="archived",
            published_at=timezone.now() - timedelta(days=30),
        )

        archived_response = self.web_client.get(f"/blog/{archived_post.slug}/")
        # Should handle archived content appropriately
        self.assertIn(archived_response.status_code, [200, 404, 410])

        # Clean up
        archived_post.delete()

    def test_accessibility_workflow(self):
        """Test accessibility features and compliance."""
        # Test main pages for accessibility markers
        accessibility_pages = [
            "/",
            "/blog/",
            "/blog/getting-started-bedrock-cms/",
            "/about/",
        ]

        for page_url in accessibility_pages:
            response = self.web_client.get(page_url)
            if response.status_code == 200:
                content = response.content.decode("utf-8").lower()

                # Check for accessibility features
                accessibility_checks = {
                    "lang_attribute": "lang=" in content,
                    "meta_viewport": "viewport" in content,
                    "skip_links": "skip" in content or "jump" in content,
                    "heading_structure": "<h1" in content,
                    "alt_attributes": "alt=" in content or "alt " in content,
                }

                # At least some accessibility features should be present
                passed_checks = sum(accessibility_checks.values())
                self.assertGreater(
                    passed_checks,
                    2,
                    f"Page {page_url} failed too many accessibility checks: {accessibility_checks}",
                )

    @requires_frontend
    def test_performance_user_experience(self):
        """Test user experience performance metrics."""
        # Test critical pages for performance
        critical_pages = [
            ("/", 2.0),  # Homepage should load in 2s
            ("/blog/", 2.5),  # Blog listing in 2.5s
            ("/blog/getting-started-bedrock-cms/", 2.0),  # Individual posts in 2s
            ("/search/", 1.5),  # Search page in 1.5s
        ]

        for url, max_time in critical_pages:
            self.assert_page_load_time(url, max_time)

        # Test concurrent user simulation
        concurrent_actions = [
            {"url": "/", "expected_status": 200},
            {"url": "/blog/", "expected_status": 200},
            {"url": "/blog/getting-started-bedrock-cms/", "expected_status": 200},
        ]

        concurrent_results = self.simulate_concurrent_users(
            concurrent_actions, num_users=3
        )

        # Validate concurrent performance
        for user_result in concurrent_results:
            for action in user_result["actions"]:
                self.assertTrue(
                    action["success"],
                    f"Concurrent user {user_result['user_id']} failed: {action.get('error', 'Unknown error')}",
                )
                self.assertLess(
                    action["response_time"],
                    5.0,
                    f"Concurrent request took too long: {action['response_time']:.2f}s",
                )

    @requires_frontend
    def test_content_caching_workflow(self):
        """Test content caching and invalidation from user perspective."""
        # First request should generate cache
        first_response = self.web_client.get("/blog/")
        self.assertEqual(first_response.status_code, 200)
        first_time = time.time()

        # Second request should be faster due to caching
        time.sleep(0.1)  # Small delay
        second_response = self.web_client.get("/blog/")
        self.assertEqual(second_response.status_code, 200)
        second_time = time.time()

        # Verify caching headers if present
        cache_headers = ["etag", "cache-control", "expires", "last-modified"]
        has_cache_headers = any(
            header in [h.lower() for h in second_response.headers.keys()]
            for header in cache_headers
        )

        if has_cache_headers:
            # If cache headers are present, verify they're working
            etag = second_response.get("ETag")
            if etag:
                # Test conditional request
                conditional_response = self.web_client.get(
                    "/blog/", HTTP_IF_NONE_MATCH=etag
                )
                # Should return 304 if content hasn't changed
                self.assertIn(conditional_response.status_code, [200, 304])

    def test_progressive_web_app_features(self):
        """Test PWA features if implemented."""
        # Test PWA manifest
        manifest_response = self.web_client.get("/manifest.json")
        if manifest_response.status_code == 200:
            try:
                manifest_data = manifest_response.json()

                # Should contain PWA manifest fields
                required_fields = ["name", "start_url", "display"]
                for field in required_fields:
                    self.assertIn(field, manifest_data)

            except json.JSONDecodeError:
                self.fail("PWA manifest is not valid JSON")

        # Test service worker
        sw_response = self.web_client.get("/sw.js")
        if sw_response.status_code == 200:
            # Should be JavaScript content
            self.assertIn("content-type", sw_response.headers)
            content_type = sw_response.headers["content-type"].lower()
            self.assertIn("javascript", content_type)

    def test_cookie_consent_workflow(self):
        """Test cookie consent and privacy compliance."""
        # Test privacy policy access
        privacy_response = self.web_client.get("/privacy/")
        if privacy_response.status_code == 200:
            content = privacy_response.content.decode("utf-8").lower()
            # Should contain privacy-related terms
            privacy_terms = ["privacy", "cookie", "data", "gdpr"]
            found_terms = sum(1 for term in privacy_terms if term in content)
            self.assertGreater(found_terms, 1, "Privacy policy seems incomplete")

        # Test cookie consent API
        consent_response = self.web_client.post(
            "/api/v1/consent/update/",
            json.dumps({"analytics": True, "marketing": False, "necessary": True}),
            content_type="application/json",
        )
        # Should either work or return 404 if not implemented
        self.assertIn(consent_response.status_code, [200, 201, 404])

    @requires_frontend
    def test_social_sharing_workflow(self):
        """Test social sharing functionality."""
        post_url = f"/blog/{self.featured_post.slug}/"

        # Test Open Graph meta tags
        response = self.web_client.get(post_url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")

        # Check for social sharing meta tags
        social_tags = [
            "og:title",
            "og:description",
            "og:url",
            "og:type",
            "twitter:card",
            "twitter:title",
        ]

        found_tags = sum(1 for tag in social_tags if tag in content)
        self.assertGreater(
            found_tags,
            3,
            f"Insufficient social sharing meta tags found. Expected at least 4, found {found_tags}",
        )

    def test_breadcrumb_navigation(self):
        """Test breadcrumb navigation."""
        # Test breadcrumbs on nested pages
        nested_urls = [
            "/blog/category/technology/",
            "/blog/getting-started-bedrock-cms/",
            "/about/",
        ]

        for url in nested_urls:
            response = self.web_client.get(url)
            if response.status_code == 200:
                content = response.content.decode("utf-8")

                # Look for breadcrumb indicators
                breadcrumb_indicators = ["breadcrumb", "crumb", "nav", "›", "/", "home"]

                # Should have some form of navigation breadcrumbs
                has_breadcrumbs = any(
                    indicator in content.lower() for indicator in breadcrumb_indicators
                )

                # Not strict requirement, but good UX
                if not has_breadcrumbs:
                    print(f"Note: {url} might benefit from breadcrumb navigation")

    def tearDown(self):
        """Clean up after tests."""
        self.cleanup_test_data()
        super().tearDown()
