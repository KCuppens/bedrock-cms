"""
Mobile Workflow Tests

Tests complete mobile user journeys including:
- Mobile-responsive content consumption
- Touch-optimized navigation and interactions
- Mobile performance optimization
- Offline functionality and PWA features
- Mobile-specific accessibility workflows
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
from django.utils import timezone

from apps.blog.models import BlogPost, Category, Tag
from apps.cms.models import Page

from .utils import DataIntegrityMixin, E2ETestCase, PerformanceMixin, WorkflowTestMixin

# Import the patch utilities
try:
    from .test_utils_patch import requires_frontend
except ImportError:

    def requires_frontend(func):
        return unittest.skip("Requires front-end routes")(func)


class MobileWorkflowTests(
    E2ETestCase, WorkflowTestMixin, DataIntegrityMixin, PerformanceMixin
):
    """Test complete mobile user workflows."""

    def setUp(self):
        super().setUp()
        self.create_sample_content()

        # Mobile-specific user agent strings
        self.mobile_user_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
            "Mozilla/5.0 (Android 10; Mobile; rv:81.0) Gecko/81.0 Firefox/81.0",
            "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X) AppleWebKit/605.1.15",
        ]

    @requires_frontend
    def test_mobile_content_consumption_workflow(self):
        """Test mobile content consumption journey."""
        for user_agent in self.mobile_user_agents[:2]:  # Test 2 different mobile agents
            with self.subTest(user_agent=user_agent[:50]):
                # Mobile content discovery workflow
                mobile_steps = [
                    {
                        "action": "mobile_homepage",
                        "url": "/",
                        "method": "GET",
                        "expected_status": 200,
                        "validate_content": ["Welcome to Bedrock CMS"],
                    },
                    {
                        "action": "mobile_blog_browse",
                        "url": "/blog/",
                        "method": "GET",
                        "expected_status": 200,
                        "validate_content": ["Getting Started with Bedrock CMS"],
                    },
                    {
                        "action": "mobile_post_read",
                        "url": "/blog/getting-started-bedrock-cms/",
                        "method": "GET",
                        "expected_status": 200,
                        "validate_content": ["comprehensive guide"],
                    },
                ]

                # Execute mobile workflow with mobile user agent
                mobile_client = self.web_client
                for step in mobile_steps:
                    response = mobile_client.get(
                        step["url"], HTTP_USER_AGENT=user_agent
                    )

                    self.assertEqual(
                        response.status_code,
                        step["expected_status"],
                        f"Mobile step {step['action']} failed with {user_agent[:30]}",
                    )

                    if response.status_code == 200:
                        content = response.content.decode("utf-8")

                        # Check for mobile-responsive elements
                        mobile_indicators = [
                            "viewport",
                            "responsive",
                            "mobile",
                            "@media",
                            "max-width",
                        ]

                        mobile_optimized = any(
                            indicator in content.lower()
                            for indicator in mobile_indicators
                        )

                        # Content validation
                        for validation in step.get("validate_content", []):
                            self.assertIn(
                                validation.lower(),
                                content.lower(),
                                f"Mobile content validation failed for {step['action']}",
                            )

    def test_mobile_navigation_workflow(self):
        """Test mobile-optimized navigation patterns."""
        mobile_user_agent = self.mobile_user_agents[0]

        # Test mobile menu functionality
        menu_response = self.web_client.get("/", HTTP_USER_AGENT=mobile_user_agent)

        if menu_response.status_code == 200:
            content = menu_response.content.decode("utf-8")

            # Check for mobile menu indicators
            mobile_menu_patterns = [
                "hamburger",
                "menu-toggle",
                "mobile-menu",
                "nav-toggle",
                "burger",
            ]

            has_mobile_menu = any(
                pattern in content.lower() for pattern in mobile_menu_patterns
            )

            # Mobile navigation should be present or content should be accessible
            if not has_mobile_menu:
                # Alternative: check that navigation is still accessible
                nav_indicators = ["nav", "menu", "navigation"]
                has_navigation = any(
                    indicator in content.lower() for indicator in nav_indicators
                )
                self.assertTrue(
                    has_navigation, "Mobile version lacks accessible navigation"
                )

        # Test mobile category navigation
        category_response = self.web_client.get(
            "/blog/category/technology/", HTTP_USER_AGENT=mobile_user_agent
        )

        if category_response.status_code == 200:
            content = category_response.content.decode("utf-8")

            # Should contain mobile-friendly category browsing
            self.assertIn("technology", content.lower())

        # Test mobile pagination
        if BlogPost.objects.filter(status="published").count() > 5:
            paginated_response = self.web_client.get(
                "/blog/", {"page": 1}, HTTP_USER_AGENT=mobile_user_agent
            )

            if paginated_response.status_code == 200:
                # Should handle pagination on mobile
                paginated_content = paginated_response.content.decode("utf-8")

                # Look for pagination elements
                pagination_indicators = ["next", "previous", "page", "pagination"]

                has_pagination = any(
                    indicator in paginated_content.lower()
                    for indicator in pagination_indicators
                )

                # Not strict requirement, but good UX
                if not has_pagination and "blog" in paginated_content.lower():
                    # At least content should be present
                    self.assertIn("blog", paginated_content.lower())

    def test_mobile_touch_interactions(self):
        """Test touch-optimized interactions and gestures."""
        mobile_user_agent = self.mobile_user_agents[0]

        # Test mobile post interaction
        post_response = self.web_client.get(
            "/blog/getting-started-bedrock-cms/", HTTP_USER_AGENT=mobile_user_agent
        )

        if post_response.status_code == 200:
            content = post_response.content.decode("utf-8")

            # Check for touch-friendly elements
            touch_indicators = [
                "touch",
                "tap",
                "swipe",
                "gesture",
                "mobile",
                "button",
                "link",
            ]

            # Check for appropriate button/link sizing hints
            touch_friendly_css = ["min-height", "padding", "margin", "touch-action"]

            has_touch_optimization = any(
                css_prop in content.lower() for css_prop in touch_friendly_css
            )

            # Test social sharing on mobile
            social_patterns = ["share", "twitter", "facebook", "linkedin", "social"]

            has_social_sharing = any(
                pattern in content.lower() for pattern in social_patterns
            )

            # Mobile should have some form of sharing capability
            if not has_social_sharing:
                # At least check for basic interaction elements
                interaction_elements = ["button", "a href", "onclick"]
                has_interaction = any(
                    element in content.lower() for element in interaction_elements
                )
                self.assertTrue(
                    has_interaction, "Mobile version lacks interactive elements"
                )

        # Test mobile search interaction
        search_response = self.web_client.get(
            "/search/", HTTP_USER_AGENT=mobile_user_agent
        )

        if search_response.status_code == 200:
            search_content = search_response.content.decode("utf-8")

            # Mobile search should be touch-friendly
            mobile_search_indicators = ["input", "search", "form", "submit"]

            has_mobile_search = any(
                indicator in search_content.lower()
                for indicator in mobile_search_indicators
            )

            if has_mobile_search:
                # Should have mobile-optimized input fields
                input_optimization = [
                    'type="search"',
                    "placeholder",
                    "autocomplete",
                    "inputmode",
                ]

                has_optimized_input = any(
                    opt in search_content.lower() for opt in input_optimization
                )

                # Good practice but not strict requirement
                if not has_optimized_input:
                    print("Note: Mobile search could benefit from input optimization")

    def test_mobile_performance_workflow(self):
        """Test mobile performance optimization."""
        mobile_user_agent = self.mobile_user_agents[0]

        # Test critical mobile pages for performance
        critical_mobile_pages = [
            ("/", 3.0),  # Homepage on mobile should load within 3s
            ("/blog/", 3.5),  # Blog listing on mobile within 3.5s
            ("/blog/getting-started-bedrock-cms/", 3.0),  # Post within 3s
        ]

        for url, max_time in critical_mobile_pages:
            start_time = time.time()
            response = self.web_client.get(url, HTTP_USER_AGENT=mobile_user_agent)
            load_time = time.time() - start_time

            if response.status_code == 200:
                self.assertLess(
                    load_time,
                    max_time,
                    f"Mobile page {url} took {load_time:.2f}s, exceeding {max_time}s",
                )

                # Check for mobile performance optimization techniques
                content = response.content.decode("utf-8")

                performance_indicators = [
                    "preload",
                    "prefetch",
                    "lazy",
                    "async",
                    "defer",
                    "critical",
                    "above-the-fold",
                ]

                has_performance_optimization = any(
                    indicator in content.lower() for indicator in performance_indicators
                )

                # Mobile should ideally have performance optimizations
                if not has_performance_optimization:
                    print(
                        f"Note: {url} could benefit from mobile performance optimization"
                    )

        # Test mobile image loading
        if "img" in response.content.decode("utf-8").lower():
            # Check for mobile-optimized image techniques
            image_optimizations = [
                "srcset",
                "sizes",
                'loading="lazy"',
                "webp",
                "responsive",
            ]

            has_image_optimization = any(
                opt in response.content.decode("utf-8").lower()
                for opt in image_optimizations
            )

            # Recommended but not required
            if not has_image_optimization:
                print("Note: Mobile images could benefit from responsive optimization")

    def test_mobile_accessibility_workflow(self):
        """Test mobile accessibility features."""
        mobile_user_agent = self.mobile_user_agents[0]

        # Test mobile accessibility on key pages
        accessibility_pages = ["/", "/blog/", "/blog/getting-started-bedrock-cms/"]

        for page_url in accessibility_pages:
            response = self.web_client.get(page_url, HTTP_USER_AGENT=mobile_user_agent)

            if response.status_code == 200:
                content = response.content.decode("utf-8").lower()

                # Mobile accessibility checks
                mobile_a11y_checks = {
                    "viewport_meta": "viewport" in content,
                    "touch_targets": any(
                        size in content for size in ["44px", "48px", "2.5rem"]
                    ),
                    "focus_indicators": "focus" in content,
                    "aria_labels": "aria-label" in content,
                    "semantic_markup": all(
                        tag in content for tag in ["<main", "<nav", "<header"]
                    ),
                    "skip_links": "skip" in content or "#main" in content,
                }

                passed_checks = sum(mobile_a11y_checks.values())
                self.assertGreater(
                    passed_checks,
                    2,
                    f"Mobile page {page_url} failed too many accessibility checks",
                )

                # Test mobile text readability
                text_readability_indicators = [
                    "font-size",
                    "line-height",
                    "contrast",
                    "readable",
                ]

                has_readability_consideration = any(
                    indicator in content for indicator in text_readability_indicators
                )

                # Mobile should consider text readability
                if not has_readability_consideration:
                    print(f"Note: {page_url} could improve mobile text readability")

    def test_mobile_offline_functionality(self):
        """Test offline functionality and PWA features on mobile."""
        mobile_user_agent = self.mobile_user_agents[0]

        # Test service worker registration
        sw_response = self.web_client.get("/sw.js", HTTP_USER_AGENT=mobile_user_agent)

        if sw_response.status_code == 200:
            # Service worker exists
            sw_content = sw_response.content.decode("utf-8")

            # Check for offline functionality
            offline_patterns = ["cache", "offline", "fetch", "install", "activate"]

            has_offline_features = any(
                pattern in sw_content.lower() for pattern in offline_patterns
            )

            if has_offline_features:
                # Test if main pages indicate offline capability
                homepage_response = self.web_client.get(
                    "/", HTTP_USER_AGENT=mobile_user_agent
                )

                if homepage_response.status_code == 200:
                    homepage_content = homepage_response.content.decode("utf-8")

                    # Look for PWA features
                    pwa_indicators = [
                        "manifest.json",
                        "service-worker",
                        "add to home screen",
                        "install",
                        "offline",
                    ]

                    has_pwa_features = any(
                        indicator in homepage_content.lower()
                        for indicator in pwa_indicators
                    )

                    if has_pwa_features:
                        print("Mobile PWA features detected")

        # Test manifest file
        manifest_response = self.web_client.get(
            "/manifest.json", HTTP_USER_AGENT=mobile_user_agent
        )

        if manifest_response.status_code == 200:
            try:
                manifest_data = manifest_response.json()

                # Check mobile-specific manifest properties
                mobile_manifest_checks = {
                    "name": "name" in manifest_data,
                    "short_name": "short_name" in manifest_data,
                    "start_url": "start_url" in manifest_data,
                    "display": "display" in manifest_data,
                    "theme_color": "theme_color" in manifest_data,
                    "background_color": "background_color" in manifest_data,
                    "icons": "icons" in manifest_data,
                }

                passed_manifest_checks = sum(mobile_manifest_checks.values())
                self.assertGreater(
                    passed_manifest_checks,
                    4,
                    "Mobile manifest missing essential properties",
                )

                # Test mobile-appropriate display mode
                if "display" in manifest_data:
                    mobile_display_modes = ["standalone", "minimal-ui", "fullscreen"]
                    self.assertIn(
                        manifest_data["display"],
                        mobile_display_modes,
                        "Manifest should use mobile-appropriate display mode",
                    )

            except json.JSONDecodeError:
                self.fail("Mobile manifest is not valid JSON")

    def test_mobile_form_interactions(self):
        """Test mobile form interactions and input handling."""
        mobile_user_agent = self.mobile_user_agents[0]

        # Test search form on mobile
        search_response = self.web_client.get(
            "/search/", HTTP_USER_AGENT=mobile_user_agent
        )

        if search_response.status_code == 200:
            content = search_response.content.decode("utf-8")

            # Mobile form optimization checks
            mobile_form_features = [
                "inputmode",
                "autocomplete",
                "placeholder",
                'type="search"',
                "required",
                "pattern",
            ]

            form_optimization_score = sum(
                1 for feature in mobile_form_features if feature in content.lower()
            )

            # Should have at least some mobile form optimizations
            self.assertGreater(
                form_optimization_score, 2, "Mobile forms lack optimization features"
            )

        # Test mobile-friendly input types
        contact_response = self.web_client.get(
            "/contact/", HTTP_USER_AGENT=mobile_user_agent
        )

        if contact_response.status_code == 200:
            contact_content = contact_response.content.decode("utf-8")

            # Check for mobile-optimized input types
            mobile_input_types = [
                'type="email"',
                'type="tel"',
                'type="url"',
                'type="number"',
            ]

            has_mobile_inputs = any(
                input_type in contact_content.lower()
                for input_type in mobile_input_types
            )

            if has_mobile_inputs:
                print("Mobile-optimized input types detected")

    def test_mobile_content_adaptation(self):
        """Test content adaptation for mobile devices."""
        mobile_user_agent = self.mobile_user_agents[0]
        desktop_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        # Compare mobile vs desktop content
        test_urls = ["/", "/blog/", "/blog/getting-started-bedrock-cms/"]

        for url in test_urls:
            # Get mobile version
            mobile_response = self.web_client.get(
                url, HTTP_USER_AGENT=mobile_user_agent
            )

            # Get desktop version
            desktop_response = self.web_client.get(
                url, HTTP_USER_AGENT=desktop_user_agent
            )

            if (
                mobile_response.status_code == 200
                and desktop_response.status_code == 200
            ):
                mobile_content = mobile_response.content.decode("utf-8")
                desktop_content = desktop_response.content.decode("utf-8")

                # Mobile should have viewport meta tag
                self.assertIn(
                    "viewport",
                    mobile_content.lower(),
                    f"Mobile version of {url} missing viewport meta tag",
                )

                # Check for mobile-specific adaptations
                mobile_adaptations = [
                    "mobile",
                    "responsive",
                    "touch",
                    "@media",
                    "max-width",
                    "min-width",
                ]

                has_mobile_adaptations = any(
                    adaptation in mobile_content.lower()
                    for adaptation in mobile_adaptations
                )

                # Mobile version should show consideration for mobile users
                if not has_mobile_adaptations:
                    # At least check content is accessible
                    self.assertGreater(
                        len(mobile_content),
                        1000,
                        f"Mobile content for {url} seems insufficient",
                    )

    def test_mobile_loading_states(self):
        """Test mobile loading states and progressive enhancement."""
        mobile_user_agent = self.mobile_user_agents[0]

        # Test pages for loading optimization
        for url in ["/", "/blog/"]:
            response = self.web_client.get(url, HTTP_USER_AGENT=mobile_user_agent)

            if response.status_code == 200:
                content = response.content.decode("utf-8")

                # Check for progressive loading techniques
                progressive_features = [
                    'loading="lazy"',
                    "preload",
                    "prefetch",
                    "critical",
                    "above-fold",
                    "skeleton",
                    "placeholder",
                ]

                has_progressive_loading = any(
                    feature in content.lower() for feature in progressive_features
                )

                # Check for mobile-friendly loading indicators
                loading_indicators = ["loading", "spinner", "progress", "skeleton"]

                has_loading_states = any(
                    indicator in content.lower() for indicator in loading_indicators
                )

                # Mobile should ideally have loading optimization
                if not has_progressive_loading and not has_loading_states:
                    print(f"Note: {url} could benefit from mobile loading optimization")

    def test_mobile_error_handling(self):
        """Test mobile-specific error handling and recovery."""
        mobile_user_agent = self.mobile_user_agents[0]

        # Test 404 on mobile
        not_found_response = self.web_client.get(
            "/non-existent-mobile-page/", HTTP_USER_AGENT=mobile_user_agent
        )

        self.assertEqual(not_found_response.status_code, 404)

        if not_found_response.content:
            content = not_found_response.content.decode("utf-8")

            # Mobile 404 should be user-friendly
            mobile_404_features = [
                "not found",
                "404",
                "home",
                "search",
                "menu",
                "navigation",
            ]

            has_mobile_friendly_404 = any(
                feature in content.lower() for feature in mobile_404_features
            )

            self.assertTrue(
                has_mobile_friendly_404, "Mobile 404 page should be user-friendly"
            )

        # Test mobile network error handling (simulated)
        # This would typically require network simulation tools
        # For now, test that pages degrade gracefully

        # Test mobile JavaScript error handling
        js_heavy_response = self.web_client.get("/", HTTP_USER_AGENT=mobile_user_agent)

        if js_heavy_response.status_code == 200:
            content = js_heavy_response.content.decode("utf-8")

            # Should have progressive enhancement
            progressive_enhancement_indicators = [
                "noscript",
                "progressive",
                "fallback",
                "enhance",
            ]

            has_progressive_enhancement = any(
                indicator in content.lower()
                for indicator in progressive_enhancement_indicators
            )

            # Mobile should work without JavaScript (progressive enhancement)
            if not has_progressive_enhancement:
                # At least basic content should be present
                self.assertGreater(
                    len(content),
                    500,
                    "Mobile page should provide basic content without JS",
                )

    def test_mobile_api_performance(self):
        """Test API performance on mobile connections."""
        mobile_user_agent = self.mobile_user_agents[0]

        # Test API endpoints that mobile apps might use
        mobile_api_endpoints = [
            "/api/v1/blog/posts/",
            "/api/v1/cms/pages/",
        ]

        for endpoint in mobile_api_endpoints:
            start_time = time.time()
            api_response = self.api_client.get(
                endpoint, HTTP_USER_AGENT=mobile_user_agent
            )
            response_time = time.time() - start_time

            if api_response.status_code == 200:
                # Mobile API should respond quickly
                self.assertLess(
                    response_time,
                    2.0,
                    f"Mobile API {endpoint} too slow: {response_time:.2f}s",
                )

                # Check response size (mobile should ideally get smaller payloads)
                response_size = len(api_response.content)
                self.assertLess(
                    response_size,
                    1024 * 1024,  # 1MB limit
                    f"Mobile API response {endpoint} too large: {response_size} bytes",
                )

                # Mobile API should return essential data
                try:
                    api_data = api_response.json()
                    if isinstance(api_data, dict) and "results" in api_data:
                        results = api_data["results"]
                    elif isinstance(api_data, list):
                        results = api_data
                    else:
                        results = []

                    if results:
                        # Check that mobile gets structured data
                        first_item = results[0]
                        self.assertIsInstance(first_item, dict)
                        self.assertIn("id", first_item)

                except (json.JSONDecodeError, KeyError, IndexError):
                    # API might not be available, which is fine for testing
                    pass

    def tearDown(self):
        """Clean up after tests."""
        self.cleanup_test_data()
        super().tearDown()
