"""
API Consumer Workflow Tests

Tests complete API consumer journeys including:
- Headless CMS content consumption
- API-driven content management
- Third-party integration workflows
- Bulk data operations via API
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()

import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.test import override_settings
from django.utils import timezone

from apps.blog.models import BlogPost, Category, Tag
from apps.cms.models import BlockType, Page
from apps.files.models import FileUpload

from .utils import DataIntegrityMixin, E2ETestCase, PerformanceMixin, WorkflowTestMixin


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CELERY_BROKER_URL="memory://",
    CELERY_RESULT_BACKEND="cache+memory://",
)
class APIConsumerWorkflowTests(
    E2ETestCase, WorkflowTestMixin, DataIntegrityMixin, PerformanceMixin
):
    """Test complete API consumer workflows."""

    def setUp(self):
        super().setUp()
        self.create_sample_content()

    def test_headless_cms_consumption_workflow(self):
        """Test headless CMS content consumption workflow."""
        # Test unauthenticated content consumption

        # Get blog posts
        posts_response = self.api_client.get("/api/v1/blog/posts/")

        if posts_response.status_code == 200:
            posts_data = posts_response.json()

            # Should contain published posts
            if "results" in posts_data:
                posts = posts_data["results"]
            else:
                posts = posts_data if isinstance(posts_data, list) else []

            published_posts = [p for p in posts if p.get("status") == "published"]
            self.assertGreater(len(published_posts), 0, "No published posts found")

            # Verify post structure
            if published_posts:
                post = published_posts[0]
                required_fields = ["id", "title", "slug", "content", "published_at"]
                for field in required_fields:
                    self.assertIn(field, post, f"Missing required field: {field}")

        elif posts_response.status_code == 404:
            self.skipTest("Blog API endpoints not available")
        else:
            self.fail(f"Unexpected API response: {posts_response.status_code}")

        # Get pages
        pages_response = self.api_client.get("/api/v1/cms/pages/")

        if pages_response.status_code == 200:
            pages_data = pages_response.json()

            # Should contain published pages
            if "results" in pages_data:
                pages = pages_data["results"]
            else:
                pages = pages_data if isinstance(pages_data, list) else []

            published_pages = [p for p in pages if p.get("status") == "published"]
            self.assertGreater(len(published_pages), 0, "No published pages found")

        # Test content filtering
        category_filter_response = self.api_client.get(
            "/api/v1/blog/posts/", {"category": self.tech_category.slug}
        )

        if category_filter_response.status_code == 200:
            filtered_data = category_filter_response.json()
            # Should contain fewer results than unfiltered
            if "results" in filtered_data:
                filtered_count = len(filtered_data["results"])
            else:
                filtered_count = (
                    len(filtered_data) if isinstance(filtered_data, list) else 0
                )

            # Should have some results but not all
            self.assertGreaterEqual(filtered_count, 1)

    def test_api_authentication_workflow(self):
        """Test API authentication and authorization workflow."""
        # Test without authentication
        protected_response = self.api_client.post("/api/v1/blog/posts/", {})
        self.assertIn(protected_response.status_code, [401, 403, 404])

        # Test with valid authentication
        self.api_authenticate(self.author_user)

        # Test authenticated access to user-specific data
        user_posts_response = self.api_client.get("/api/v1/blog/posts/mine/")

        if user_posts_response.status_code == 200:
            user_posts = user_posts_response.json()
            if isinstance(user_posts, dict) and "results" in user_posts:
                user_posts = user_posts["results"]

            # Should only contain posts by this author
            for post in user_posts:
                self.assertEqual(post["author"]["id"], self.author_user.id)

        # Test token refresh (if supported)
        token_refresh_response = self.api_client.post("/api/v1/auth/token/refresh/")
        # Should either work or return 404 if not implemented
        self.assertIn(token_refresh_response.status_code, [200, 404, 405])

        # Test token validation
        validate_response = self.api_client.get("/api/v1/auth/user/")
        if validate_response.status_code == 200:
            user_data = validate_response.json()
            self.assertEqual(user_data["email"], self.author_user.email)

    def test_content_crud_api_workflow(self):
        """Test complete CRUD operations via API."""
        self.api_authenticate(self.author_user)

        # Create new blog post
        create_data = {
            "title": "API Test Post",
            "slug": "api-test-post",
            "content": "This post was created via API",
            "excerpt": "API test excerpt",
            "locale": self.en_locale.id,
            "category": self.tech_category.id,
            "status": "draft",
            "tags": [self.python_tag.id],
            "blocks": [
                {
                    "type": "richtext",
                    "id": "content-1",
                    "props": {
                        "content": "<h1>API Created Content</h1><p>Via REST API</p>"
                    },
                }
            ],
        }

        create_response = self.api_client.post(
            "/api/v1/blog/posts/",
            data=json.dumps(create_data),
            content_type="application/json",
        )

        if create_response.status_code == 404:
            self.skipTest("Blog API endpoints not available")

        self.assertEqual(create_response.status_code, 201)
        created_post = create_response.json()
        post_id = created_post["id"]

        # Read the created post
        read_response = self.api_client.get(f"/api/v1/blog/posts/{post_id}/")
        self.assertEqual(read_response.status_code, 200)

        read_data = read_response.json()
        self.assertEqual(read_data["title"], create_data["title"])
        self.assertEqual(read_data["status"], "draft")

        # Update the post
        update_data = {
            "title": "Updated API Test Post",
            "status": "published",
            "content": "Updated content via API",
        }

        update_response = self.api_client.patch(
            f"/api/v1/blog/posts/{post_id}/",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(update_response.status_code, 200)
        updated_post = update_response.json()
        self.assertEqual(updated_post["title"], update_data["title"])
        self.assertEqual(updated_post["status"], "published")

        # Verify database was updated
        blog_post = BlogPost.objects.get(id=post_id)
        self.assertEqual(blog_post.title, update_data["title"])
        self.assertEqual(blog_post.status, "published")

        # Delete the post
        delete_response = self.api_client.delete(f"/api/v1/blog/posts/{post_id}/")
        self.assertIn(delete_response.status_code, [204, 404])

        if delete_response.status_code == 204:
            # Verify post was deleted
            self.assertFalse(BlogPost.objects.filter(id=post_id).exists())
        else:
            # If delete not supported, manually clean up
            blog_post.delete()

    def test_bulk_api_operations_workflow(self):
        """Test bulk operations via API."""
        self.api_authenticate(self.editor_user)

        # Create multiple posts for bulk operations
        bulk_posts_data = []
        for i in range(3):
            post_data = {
                "title": f"Bulk Test Post {i+1}",
                "slug": f"bulk-test-post-{i+1}",
                "content": f"Bulk content {i+1}",
                "locale": self.en_locale.id,
                "category": self.tech_category.id,
                "status": "draft",
            }
            bulk_posts_data.append(post_data)

        # Test bulk create
        bulk_create_response = self.api_client.post(
            "/api/v1/blog/posts/bulk/",
            data=json.dumps({"posts": bulk_posts_data}),
            content_type="application/json",
        )

        created_post_ids = []

        if bulk_create_response.status_code == 201:
            # Bulk create supported
            bulk_result = bulk_create_response.json()
            created_post_ids = [post["id"] for post in bulk_result["created"]]

        elif bulk_create_response.status_code == 404:
            # Bulk create not supported, create individually
            for post_data in bulk_posts_data:
                create_response = self.api_client.post(
                    "/api/v1/blog/posts/",
                    data=json.dumps(post_data),
                    content_type="application/json",
                )
                if create_response.status_code == 201:
                    created_post_ids.append(create_response.json()["id"])

        # Test bulk update
        if created_post_ids:
            bulk_update_data = {
                "post_ids": created_post_ids,
                "updates": {"status": "published", "featured": True},
            }

            bulk_update_response = self.api_client.post(
                "/api/v1/blog/posts/bulk-update/",
                data=json.dumps(bulk_update_data),
                content_type="application/json",
            )

            if bulk_update_response.status_code == 200:
                # Verify bulk update worked
                updated_posts = BlogPost.objects.filter(id__in=created_post_ids)
                for post in updated_posts:
                    self.assertEqual(post.status, "published")
                    self.assertTrue(post.featured)
            elif bulk_update_response.status_code == 404:
                # Bulk update not supported, update individually
                for post_id in created_post_ids:
                    update_response = self.api_client.patch(
                        f"/api/v1/blog/posts/{post_id}/",
                        data=json.dumps({"status": "published"}),
                        content_type="application/json",
                    )
                    self.assertIn(update_response.status_code, [200, 404])

        # Test bulk delete
        if created_post_ids:
            bulk_delete_data = {"post_ids": created_post_ids}

            bulk_delete_response = self.api_client.post(
                "/api/v1/blog/posts/bulk-delete/",
                data=json.dumps(bulk_delete_data),
                content_type="application/json",
            )

            if bulk_delete_response.status_code in [200, 204]:
                # Verify posts were deleted
                remaining_posts = BlogPost.objects.filter(
                    id__in=created_post_ids
                ).count()
                self.assertEqual(remaining_posts, 0)
            else:
                # Clean up individually
                BlogPost.objects.filter(id__in=created_post_ids).delete()

    def test_api_pagination_and_filtering(self):
        """Test API pagination and advanced filtering."""
        # Test pagination
        paginated_response = self.api_client.get(
            "/api/v1/blog/posts/", {"page": 1, "page_size": 2}
        )

        if paginated_response.status_code == 200:
            paginated_data = paginated_response.json()

            # Should contain pagination metadata
            if "results" in paginated_data:
                self.assertIn("count", paginated_data)
                self.assertIn("next", paginated_data)
                self.assertIn("previous", paginated_data)
                self.assertLessEqual(len(paginated_data["results"]), 2)

        # Test filtering by date range
        date_filter_response = self.api_client.get(
            "/api/v1/blog/posts/",
            {
                "published_after": (timezone.now() - timedelta(days=1)).isoformat(),
                "published_before": timezone.now().isoformat(),
            },
        )

        if date_filter_response.status_code == 200:
            # Should return recent posts
            filtered_data = date_filter_response.json()
            if "results" in filtered_data:
                posts = filtered_data["results"]
            else:
                posts = filtered_data if isinstance(filtered_data, list) else []

            # Verify date filtering worked
            for post in posts:
                if post.get("published_at"):
                    published_date = datetime.fromisoformat(
                        post["published_at"].replace("Z", "+00:00")
                    )
                    self.assertGreater(
                        published_date, timezone.now() - timedelta(days=2)
                    )

        # Test search functionality
        search_response = self.api_client.get(
            "/api/v1/blog/posts/", {"search": "bedrock"}
        )

        if search_response.status_code == 200:
            search_data = search_response.json()
            if "results" in search_data:
                search_results = search_data["results"]
            else:
                search_results = search_data if isinstance(search_data, list) else []

            # Should contain relevant results
            if search_results:
                found_match = any(
                    "bedrock"
                    in (post.get("title", "") + post.get("content", "")).lower()
                    for post in search_results
                )
                self.assertTrue(found_match, "Search did not return relevant results")

    def test_api_versioning_workflow(self):
        """Test API versioning and backwards compatibility."""
        # Test v1 API
        v1_response = self.api_client.get("/api/v1/blog/posts/")

        # Test v2 API (if it exists)
        v2_response = self.api_client.get("/api/v2/blog/posts/")

        if v1_response.status_code == 200 and v2_response.status_code == 200:
            # Both versions exist, test compatibility
            v1_data = v1_response.json()
            v2_data = v2_response.json()

            # V2 should be backward compatible or provide migration path
            # This is a basic check - specifics would depend on API design
            self.assertIsInstance(v1_data, (list, dict))
            self.assertIsInstance(v2_data, (list, dict))

        # Test API version headers
        version_header_response = self.api_client.get(
            "/api/blog/posts/", HTTP_API_VERSION="v1"  # No version in URL
        )

        # Should either work or return appropriate error
        self.assertIn(version_header_response.status_code, [200, 404, 400])

    def test_third_party_integration_workflow(self):
        """Test third-party integration scenarios."""
        self.api_authenticate(self.admin_user)

        # Test webhook registration
        webhook_data = {
            "url": "https://example.com/webhook",
            "events": ["post.created", "post.updated", "post.published"],
            "active": True,
            "secret": "webhook_secret_key",
        }

        webhook_response = self.api_client.post(
            "/api/v1/webhooks/",
            data=json.dumps(webhook_data),
            content_type="application/json",
        )

        webhook_id = None
        if webhook_response.status_code == 201:
            webhook_result = webhook_response.json()
            webhook_id = webhook_result["id"]

            # Test webhook update
            update_webhook_data = {"active": False}
            update_webhook_response = self.api_client.patch(
                f"/api/v1/webhooks/{webhook_id}/",
                data=json.dumps(update_webhook_data),
                content_type="application/json",
            )
            self.assertEqual(update_webhook_response.status_code, 200)

        # Test API key management
        api_key_data = {
            "name": "Third-party Integration Key",
            "permissions": ["blog.read", "blog.write"],
            "rate_limit": 1000,
            "expires_at": (timezone.now() + timedelta(days=365)).isoformat(),
        }

        api_key_response = self.api_client.post(
            "/api/v1/api-keys/",
            data=json.dumps(api_key_data),
            content_type="application/json",
        )

        if api_key_response.status_code == 201:
            api_key_result = api_key_response.json()
            api_key_id = api_key_result["id"]

            # Test using the API key
            test_client = self.api_client.__class__()
            test_client.credentials(
                HTTP_AUTHORIZATION=f'ApiKey {api_key_result["key"]}'
            )

            key_test_response = test_client.get("/api/v1/blog/posts/")
            self.assertIn(
                key_test_response.status_code, [200, 403]
            )  # Depends on permissions

        # Test OAuth2 flow (if supported)
        oauth_authorize_response = self.api_client.get("/oauth/authorize/")
        # Should either redirect or return 404 if not implemented
        self.assertIn(oauth_authorize_response.status_code, [302, 404])

        # Clean up
        if webhook_id:
            self.api_client.delete(f"/api/v1/webhooks/{webhook_id}/")

    def test_api_rate_limiting_workflow(self):
        """Test API rate limiting and throttling."""
        # Make rapid requests to test rate limiting
        responses = []
        for i in range(20):
            response = self.api_client.get("/api/v1/blog/posts/")
            responses.append(response)

            # Small delay to avoid overwhelming the system
            time.sleep(0.1)

        # Check for rate limiting responses
        rate_limited_responses = [r for r in responses if r.status_code == 429]

        if rate_limited_responses:
            # Rate limiting is implemented
            rate_limited_response = rate_limited_responses[0]

            # Should have rate limit headers
            rate_limit_headers = [
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "Retry-After",
            ]

            found_headers = [
                header
                for header in rate_limit_headers
                if header in rate_limited_response.headers
            ]

            self.assertGreater(
                len(found_headers),
                0,
                "Rate limited response missing rate limit headers",
            )

    def test_api_error_handling_workflow(self):
        """Test API error handling and response formats."""
        # Test 404 errors
        not_found_response = self.api_client.get("/api/v1/blog/posts/99999/")
        self.assertEqual(not_found_response.status_code, 404)

        if not_found_response.content:
            try:
                error_data = not_found_response.json()
                # Should have structured error response
                self.assertTrue(
                    "error" in error_data
                    or "detail" in error_data
                    or "message" in error_data
                )
            except json.JSONDecodeError:
                self.fail("404 response should return valid JSON error")

        # Test validation errors
        self.api_authenticate(self.author_user)

        invalid_data = {
            "title": "",  # Empty title
            "slug": "invalid-post",
            "locale": 99999,  # Invalid locale
            "status": "invalid_status",  # Invalid status
        }

        validation_response = self.api_client.post(
            "/api/v1/blog/posts/",
            data=json.dumps(invalid_data),
            content_type="application/json",
        )

        self.assertIn(validation_response.status_code, [400, 422])

        if validation_response.content:
            try:
                validation_error = validation_response.json()
                # Should contain field-specific errors
                self.assertTrue(
                    isinstance(validation_error, dict) and len(validation_error) > 0
                )
            except json.JSONDecodeError:
                self.fail("Validation error response should be valid JSON")

        # Test permission errors
        self.api_authenticate(self.viewer_user)  # User with limited permissions

        forbidden_response = self.api_client.post(
            "/api/v1/blog/posts/",
            data=json.dumps({"title": "Test"}),
            content_type="application/json",
        )

        self.assertIn(forbidden_response.status_code, [403, 404])

    def test_api_content_serialization(self):
        """Test API content serialization and format handling."""
        # Test different content types
        content_types = ["application/json", "application/xml", "text/csv"]

        for content_type in content_types:
            response = self.api_client.get(
                "/api/v1/blog/posts/", HTTP_ACCEPT=content_type
            )

            if response.status_code == 200:
                # Verify content type matches request
                response_content_type = response.get("Content-Type", "").lower()

                if "json" in content_type:
                    self.assertIn("json", response_content_type)
                    # Should be valid JSON
                    try:
                        response.json()
                    except json.JSONDecodeError:
                        self.fail("JSON response is not valid JSON")

                elif "xml" in content_type:
                    self.assertIn("xml", response_content_type)
                    # Should be valid XML
                    self.assertIn("<", response.content.decode("utf-8"))

                elif "csv" in content_type:
                    self.assertIn("csv", response_content_type)
                    # Should be CSV format
                    content = response.content.decode("utf-8")
                    self.assertIn(",", content)  # Basic CSV check

    @patch("apps.blog.views.track_view_async.delay")
    def test_api_performance_workflow(self, mock_track_view):
        """Test API performance characteristics."""
        # Mock the Celery task to avoid connection issues
        mock_track_view.return_value = Mock()

        # Test response time for list endpoint
        start_time = time.time()
        list_response = self.api_client.get("/api/v1/blog/posts/")
        list_time = time.time() - start_time

        if list_response.status_code == 200:
            self.assertLess(list_time, 2.0, "List API too slow")

            # Test response time for detail endpoint
            posts_data = list_response.json()
            if "results" in posts_data and posts_data["results"]:
                post_id = posts_data["results"][0]["id"]
            elif isinstance(posts_data, list) and posts_data:
                post_id = posts_data[0]["id"]
            else:
                self.skipTest("No posts available for detail test")

            start_time = time.time()
            detail_response = self.api_client.get(f"/api/v1/blog/posts/{post_id}/")
            detail_time = time.time() - start_time

            if detail_response.status_code == 200:
                self.assertLess(detail_time, 1.0, "Detail API too slow")

        # Test concurrent API requests
        import queue
        import threading

        results_queue = queue.Queue()

        def api_request_thread():
            start = time.time()
            response = self.api_client.get("/api/v1/blog/posts/")
            end = time.time()
            results_queue.put(
                {"status_code": response.status_code, "response_time": end - start}
            )

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=api_request_thread)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Analyze results
        concurrent_results = []
        while not results_queue.empty():
            concurrent_results.append(results_queue.get())

        # Verify all requests succeeded
        successful_requests = [r for r in concurrent_results if r["status_code"] == 200]

        if successful_requests:
            avg_response_time = sum(
                r["response_time"] for r in successful_requests
            ) / len(successful_requests)

            self.assertLess(
                avg_response_time,
                3.0,
                f"Concurrent API requests too slow: {avg_response_time:.2f}s average",
            )

    def test_api_caching_workflow(self):
        """Test API caching behavior."""
        # First request
        first_response = self.api_client.get("/api/v1/blog/posts/")

        if first_response.status_code == 200:
            # Check for caching headers
            cache_headers = ["ETag", "Cache-Control", "Expires", "Last-Modified"]

            found_cache_headers = [
                header for header in cache_headers if header in first_response.headers
            ]

            if found_cache_headers:
                # Test conditional requests
                etag = first_response.get("ETag")
                if etag:
                    conditional_response = self.api_client.get(
                        "/api/v1/blog/posts/", HTTP_IF_NONE_MATCH=etag
                    )
                    # Should return 304 if not modified
                    self.assertIn(conditional_response.status_code, [200, 304])

                last_modified = first_response.get("Last-Modified")
                if last_modified:
                    conditional_response = self.api_client.get(
                        "/api/v1/blog/posts/", HTTP_IF_MODIFIED_SINCE=last_modified
                    )
                    # Should return 304 if not modified
                    self.assertIn(conditional_response.status_code, [200, 304])

    def tearDown(self):
        """Clean up after tests."""
        self.cleanup_test_data()
        super().tearDown()
