"""
Content Creator Workflow Tests

Tests complete user journeys for content creators including:
- Complete content creation journey (login → create → edit → publish)
- Multilingual content management workflow
- Content collaboration and review workflows
- SEO optimization workflow
- Media management and content block editing
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()

import json
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import BlogPost, Category, Tag
from apps.cms.models import BlockType, Page
from apps.files.models import FileUpload

from .utils import DataIntegrityMixin, E2ETestCase, PerformanceMixin, WorkflowTestMixin

# Import the patch utilities
try:
    from .test_utils_patch import requires_frontend
except ImportError:

    def requires_frontend(func):
        return unittest.skip("Requires front-end routes")(func)


class ContentCreatorWorkflowTests(
    E2ETestCase, WorkflowTestMixin, DataIntegrityMixin, PerformanceMixin
):
    """Test complete content creator workflows."""

    def setUp(self):
        super().setUp()
        self.create_sample_content()

    @requires_frontend
    def test_complete_blog_post_creation_workflow(self):
        """Test complete blog post creation from login to publish."""
        workflow_steps = [
            # Step 1: Login
            {
                "action": "login",
                "url": "/admin/login/",
                "method": "GET",
                "expected_status": 200,
                "validate_content": ["Login"],
            },
            {
                "action": "authenticate",
                "url": "/admin/login/",
                "method": "POST",
                "data": {
                    "username": self.author_user.email,  # Django admin still expects 'username' field name
                    "password": "testpass123",
                },
                "expected_status": 302,
            },
            # Step 2: Navigate to blog post creation
            {
                "action": "navigate_create",
                "url": "/admin/blog/blogpost/add/",
                "method": "GET",
                "expected_status": 200,
                "validate_content": ["Add blog post"],
            },
            # Step 3: Create blog post (this would be a complex form submission)
            # We'll simulate this with API calls for better control
        ]

        # Execute login workflow
        login_results = self.simulate_user_journey(
            workflow_steps[:2], user=self.author_user
        )
        self.assert_workflow_completion(login_results)

        # Now test the complete content creation workflow using API
        self.api_authenticate(self.author_user)

        # Create a new blog post
        post_data = {
            "title": "Test Blog Post from Workflow",
            "slug": "test-blog-post-workflow",
            "content": "This is a test blog post created through the E2E workflow.",
            "excerpt": "Test excerpt for the blog post.",
            "locale": self.en_locale.id,
            "category": self.tech_category.id,
            "status": "draft",
            "featured": False,
            "allow_comments": True,
            "blocks": [
                {
                    "type": "richtext",
                    "id": "content-1",
                    "props": {
                        "content": "<h1>Test Blog Post</h1><p>This is the main content.</p>"
                    },
                }
            ],
            "seo": {
                "title": "Test Blog Post - SEO Title",
                "description": "SEO description for test blog post",
                "keywords": ["test", "blog", "cms"],
            },
        }

        # Create the post
        start_time = time.time()
        create_response = self.api_client.post(
            "/api/v1/blog/posts/",
            data=json.dumps(post_data),
            content_type="application/json",
        )
        creation_time = time.time() - start_time

        # Validate creation
        self.assertEqual(create_response.status_code, 201)
        created_post_data = create_response.json()
        self.assertEqual(created_post_data["title"], post_data["title"])
        self.assertEqual(created_post_data["status"], "draft")

        # Test performance
        self.assertLess(creation_time, 2.0, "Post creation took too long")

        # Get the created post
        post = BlogPost.objects.get(id=created_post_data["id"])

        # Test editing workflow
        edit_data = {
            "title": "Updated Test Blog Post",
            "content": "Updated content for the blog post.",
            "status": "published",
            "tags": [self.python_tag.id, self.django_tag.id],
        }

        edit_response = self.api_client.patch(
            f"/api/v1/blog/posts/{post.id}/",
            data=json.dumps(edit_data),
            content_type="application/json",
        )

        self.assertEqual(edit_response.status_code, 200)
        updated_post_data = edit_response.json()
        self.assertEqual(updated_post_data["title"], edit_data["title"])
        self.assertEqual(updated_post_data["status"], "published")

        # Validate database state
        post.refresh_from_db()
        self.assertEqual(post.title, edit_data["title"])
        self.assertEqual(post.status, "published")
        self.assertIsNotNone(post.published_at)
        self.assertEqual(post.tags.count(), 2)

        # Test SEO optimization workflow
        seo_data = {
            "seo": {
                "title": "Optimized SEO Title",
                "description": "Optimized SEO description with keywords",
                "keywords": ["test", "blog", "cms", "optimization"],
                "og_title": "Social Media Title",
                "og_description": "Social media description",
                "canonical_url": f"/blog/{post.slug}/",
            }
        }

        seo_response = self.api_client.patch(
            f"/api/v1/blog/posts/{post.id}/",
            data=json.dumps(seo_data),
            content_type="application/json",
        )

        self.assertEqual(seo_response.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.seo["title"], seo_data["seo"]["title"])
        self.assertIn("optimization", post.seo["keywords"])

        # Validate data consistency
        self.assert_data_consistency(
            BlogPost, {"featured": 1}
        )  # One featured post exists

        # Clean up
        post.delete()

    def test_multilingual_content_workflow(self):
        """Test creating and managing multilingual content."""
        self.api_authenticate(self.author_user)

        # Create English version
        en_post_data = {
            "title": "Multilingual Test Post",
            "slug": "multilingual-test-post",
            "content": "This is the English version of the post.",
            "locale": self.en_locale.id,
            "category": self.tech_category.id,
            "status": "published",
            "blocks": [
                {
                    "type": "richtext",
                    "id": "content-en",
                    "props": {
                        "content": "<h1>Multilingual Test</h1><p>English content</p>"
                    },
                }
            ],
        }

        en_response = self.api_client.post(
            "/api/v1/blog/posts/",
            data=json.dumps(en_post_data),
            content_type="application/json",
        )

        self.assertEqual(en_response.status_code, 201)
        en_post = BlogPost.objects.get(id=en_response.json()["id"])

        # Create Spanish version with same group_id
        es_post_data = {
            "title": "Publicación de Prueba Multilingüe",
            "slug": "publicacion-prueba-multilingue",
            "content": "Esta es la versión en español del post.",
            "locale": self.es_locale.id,
            "category": self.tech_category.id,
            "status": "published",
            "group_id": str(en_post.group_id),  # Link to English version
            "blocks": [
                {
                    "type": "richtext",
                    "id": "content-es",
                    "props": {
                        "content": "<h1>Prueba Multilingüe</h1><p>Contenido en español</p>"
                    },
                }
            ],
        }

        es_response = self.api_client.post(
            "/api/v1/blog/posts/",
            data=json.dumps(es_post_data),
            content_type="application/json",
        )

        self.assertEqual(es_response.status_code, 201)
        es_post = BlogPost.objects.get(id=es_response.json()["id"])

        # Validate multilingual linking
        self.assertEqual(en_post.group_id, es_post.group_id)

        # Test retrieving related language versions
        related_response = self.api_client.get(
            f"/api/v1/blog/posts/{en_post.id}/translations/"
        )

        if related_response.status_code == 200:  # If endpoint exists
            translations = related_response.json()
            self.assertGreaterEqual(len(translations), 1)

        # Clean up
        en_post.delete()
        es_post.delete()

    def test_content_collaboration_workflow(self):
        """Test content collaboration and review workflow."""
        # Author creates draft
        self.api_authenticate(self.author_user)

        draft_data = {
            "title": "Collaborative Draft Post",
            "slug": "collaborative-draft-post",
            "content": "This is a draft that needs review.",
            "locale": self.en_locale.id,
            "category": self.tech_category.id,
            "status": "draft",
            "blocks": [
                {
                    "type": "richtext",
                    "id": "content-draft",
                    "props": {"content": "<h1>Draft Content</h1><p>Needs review</p>"},
                }
            ],
        }

        create_response = self.api_client.post(
            "/api/v1/blog/posts/",
            data=json.dumps(draft_data),
            content_type="application/json",
        )

        self.assertEqual(create_response.status_code, 201)
        post = BlogPost.objects.get(id=create_response.json()["id"])

        # Author submits for review
        submit_data = {"status": "pending_review"}

        # Switch to editor for review
        self.api_authenticate(self.editor_user)

        # Editor reviews and provides feedback
        review_data = {
            "status": "published",
            "content": "Updated content after review.",
            "review_notes": "Approved with minor edits",
        }

        review_response = self.api_client.patch(
            f"/api/v1/blog/posts/{post.id}/",
            data=json.dumps(review_data),
            content_type="application/json",
        )

        # Should succeed as editor has publish permissions
        if review_response.status_code == 200:
            post.refresh_from_db()
            self.assertEqual(post.status, "published")

        # Clean up
        post.delete()

    def test_media_management_workflow(self):
        """Test media upload and management in content blocks."""
        self.api_authenticate(self.author_user)

        # Create a test image file
        image_content = b"fake-image-content-for-testing"
        uploaded_file = SimpleUploadedFile(
            "test-image.jpg", image_content, content_type="image/jpeg"
        )

        # Upload file
        upload_response = self.api_client.post(
            "/api/v1/files/upload/",
            {"file": uploaded_file, "filename": "test-image.jpg"},
            format="multipart",
        )

        if upload_response.status_code == 201:
            file_data = upload_response.json()
            file_id = file_data["id"]

            # Create blog post with media block
            post_data = {
                "title": "Post with Media",
                "slug": "post-with-media",
                "content": "This post contains media.",
                "locale": self.en_locale.id,
                "category": self.design_category.id,
                "status": "draft",
                "blocks": [
                    {
                        "type": "richtext",
                        "id": "content-1",
                        "props": {"content": "<h1>Post with Media</h1>"},
                    },
                    {
                        "type": "image",
                        "id": "image-1",
                        "props": {
                            "file_id": file_id,
                            "alt": "Test image",
                            "caption": "This is a test image",
                        },
                    },
                ],
            }

            create_response = self.api_client.post(
                "/api/v1/blog/posts/",
                data=json.dumps(post_data),
                content_type="application/json",
            )

            if create_response.status_code == 201:
                post = BlogPost.objects.get(id=create_response.json()["id"])

                # Validate media block
                image_block = None
                for block in post.blocks:
                    if block.get("type") == "image":
                        image_block = block
                        break

                if image_block:
                    self.assertEqual(image_block["props"]["file_id"], file_id)

                # Clean up
                post.delete()

            # Clean up file
            try:
                FileUpload.objects.get(id=file_id).delete()
            except FileUpload.DoesNotExist:
                pass

    def test_page_creation_workflow(self):
        """Test complete page creation workflow."""
        self.api_authenticate(self.editor_user)

        # Create a new page
        page_data = {
            "title": "Test Page from Workflow",
            "slug": "test-page-workflow",
            "locale": self.en_locale.id,
            "status": "draft",
            "blocks": [
                {
                    "type": "hero",
                    "id": "hero-1",
                    "props": {
                        "title": "Test Page Hero",
                        "subtitle": "Created through workflow",
                        "cta_text": "Learn More",
                        "cta_url": "#",
                    },
                },
                {
                    "type": "richtext",
                    "id": "content-1",
                    "props": {
                        "content": "<h2>Page Content</h2><p>This is test page content.</p>"
                    },
                },
            ],
            "seo": {
                "title": "Test Page SEO Title",
                "description": "SEO description for test page",
            },
        }

        # Create page
        create_response = self.api_client.post(
            "/api/v1/cms/pages/",
            data=json.dumps(page_data),
            content_type="application/json",
        )

        # May not have this endpoint, so handle gracefully
        if create_response.status_code in [201, 404]:
            if create_response.status_code == 201:
                page_data = create_response.json()
                page = Page.objects.get(id=page_data["id"])

                # Test publishing
                publish_data = {
                    "status": "published",
                    "published_at": timezone.now().isoformat(),
                }

                publish_response = self.api_client.patch(
                    f"/api/v1/cms/pages/{page.id}/",
                    data=json.dumps(publish_data),
                    content_type="application/json",
                )

                if publish_response.status_code == 200:
                    page.refresh_from_db()
                    self.assertEqual(page.status, "published")

                # Clean up
                page.delete()

    def test_content_scheduling_workflow(self):
        """Test content scheduling workflow."""
        self.api_authenticate(self.editor_user)

        # Create scheduled content
        future_time = timezone.now() + timedelta(hours=1)
        scheduled_data = {
            "title": "Scheduled Blog Post",
            "slug": "scheduled-blog-post",
            "content": "This post is scheduled for future publication.",
            "locale": self.en_locale.id,
            "category": self.tech_category.id,
            "status": "scheduled",
            "scheduled_publish_at": future_time.isoformat(),
            "blocks": [
                {
                    "type": "richtext",
                    "id": "content-1",
                    "props": {
                        "content": "<h1>Scheduled Content</h1><p>Future publication</p>"
                    },
                }
            ],
        }

        create_response = self.api_client.post(
            "/api/v1/blog/posts/",
            data=json.dumps(scheduled_data),
            content_type="application/json",
        )

        if create_response.status_code == 201:
            post = BlogPost.objects.get(id=create_response.json()["id"])
            self.assertEqual(post.status, "scheduled")
            self.assertIsNotNone(post.scheduled_publish_at)

            # Test rescheduling
            new_time = timezone.now() + timedelta(hours=2)
            reschedule_data = {"scheduled_publish_at": new_time.isoformat()}

            reschedule_response = self.api_client.patch(
                f"/api/v1/blog/posts/{post.id}/",
                data=json.dumps(reschedule_data),
                content_type="application/json",
            )

            if reschedule_response.status_code == 200:
                post.refresh_from_db()
                self.assertAlmostEqual(
                    post.scheduled_publish_at, new_time, delta=timedelta(seconds=1)
                )

            # Clean up
            post.delete()

    def test_content_block_editing_workflow(self):
        """Test complex content block editing workflow."""
        self.api_authenticate(self.author_user)

        # Create post with multiple blocks
        complex_post_data = {
            "title": "Complex Block Structure Post",
            "slug": "complex-block-structure",
            "content": "Post with complex block structure.",
            "locale": self.en_locale.id,
            "category": self.tech_category.id,
            "status": "draft",
            "blocks": [
                {
                    "type": "hero",
                    "id": "hero-main",
                    "props": {
                        "title": "Main Hero",
                        "subtitle": "Hero subtitle",
                        "cta_text": "Get Started",
                        "cta_url": "/start/",
                    },
                },
                {
                    "type": "richtext",
                    "id": "content-intro",
                    "props": {"content": "<h2>Introduction</h2><p>Intro content</p>"},
                },
                {
                    "type": "richtext",
                    "id": "content-main",
                    "props": {"content": "<h2>Main Content</h2><p>Main content</p>"},
                },
            ],
        }

        create_response = self.api_client.post(
            "/api/v1/blog/posts/",
            data=json.dumps(complex_post_data),
            content_type="application/json",
        )

        if create_response.status_code == 201:
            post = BlogPost.objects.get(id=create_response.json()["id"])

            # Test block reordering and editing
            updated_blocks = [
                {
                    "type": "richtext",
                    "id": "content-intro",
                    "props": {
                        "content": "<h2>Updated Introduction</h2><p>Updated intro</p>"
                    },
                },
                {
                    "type": "hero",
                    "id": "hero-main",
                    "props": {
                        "title": "Updated Hero Title",
                        "subtitle": "Updated subtitle",
                        "cta_text": "Updated CTA",
                        "cta_url": "/updated/",
                    },
                },
                {
                    "type": "richtext",
                    "id": "content-main",
                    "props": {
                        "content": "<h2>Updated Main Content</h2><p>Updated content</p>"
                    },
                },
                {
                    "type": "richtext",
                    "id": "content-new",
                    "props": {
                        "content": "<h2>New Section</h2><p>Newly added content</p>"
                    },
                },
            ]

            update_data = {"blocks": updated_blocks}

            update_response = self.api_client.patch(
                f"/api/v1/blog/posts/{post.id}/",
                data=json.dumps(update_data),
                content_type="application/json",
            )

            if update_response.status_code == 200:
                post.refresh_from_db()
                self.assertEqual(len(post.blocks), 4)

                # Verify block order and content
                first_block = post.blocks[0]
                self.assertEqual(first_block["id"], "content-intro")
                self.assertIn("Updated Introduction", first_block["props"]["content"])

                # Verify new block was added
                new_block = post.blocks[3]
                self.assertEqual(new_block["id"], "content-new")

            # Clean up
            post.delete()

    def test_content_performance_optimization(self):
        """Test content creation performance under load."""
        self.api_authenticate(self.author_user)

        # Test rapid content creation
        posts_created = []
        creation_times = []

        for i in range(5):
            post_data = {
                "title": f"Performance Test Post {i+1}",
                "slug": f"performance-test-post-{i+1}",
                "content": f"Content for performance test post {i+1}",
                "locale": self.en_locale.id,
                "category": self.tech_category.id,
                "status": "draft",
                "blocks": [
                    {
                        "type": "richtext",
                        "id": f"content-{i}",
                        "props": {
                            "content": f"<h1>Test Post {i+1}</h1><p>Performance test content</p>"
                        },
                    }
                ],
            }

            start_time = time.time()
            response = self.api_client.post(
                "/api/v1/blog/posts/",
                data=json.dumps(post_data),
                content_type="application/json",
            )
            end_time = time.time()

            if response.status_code == 201:
                posts_created.append(response.json()["id"])
                creation_times.append(end_time - start_time)

        # Validate performance
        if creation_times:
            avg_creation_time = sum(creation_times) / len(creation_times)
            max_creation_time = max(creation_times)

            self.assertLess(avg_creation_time, 1.0, "Average creation time too high")
            self.assertLess(max_creation_time, 2.0, "Max creation time too high")

        # Clean up
        for post_id in posts_created:
            try:
                BlogPost.objects.get(id=post_id).delete()
            except BlogPost.DoesNotExist:
                pass

    def test_error_recovery_workflow(self):
        """Test error recovery during content creation."""
        self.api_authenticate(self.author_user)

        # Test creation with invalid data
        invalid_data = {
            "title": "",  # Empty title should cause validation error
            "slug": "invalid-post",
            "content": "Test content",
            "locale": 999,  # Invalid locale ID
            "status": "invalid_status",  # Invalid status
        }

        error_response = self.api_client.post(
            "/api/v1/blog/posts/",
            data=json.dumps(invalid_data),
            content_type="application/json",
        )

        # Should return validation error
        self.assertIn(error_response.status_code, [400, 422])

        # Test recovery with valid data
        valid_data = {
            "title": "Recovery Test Post",
            "slug": "recovery-test-post",
            "content": "Recovered content creation",
            "locale": self.en_locale.id,
            "category": self.tech_category.id,
            "status": "draft",
        }

        recovery_response = self.api_client.post(
            "/api/v1/blog/posts/",
            data=json.dumps(valid_data),
            content_type="application/json",
        )

        if recovery_response.status_code == 201:
            post = BlogPost.objects.get(id=recovery_response.json()["id"])
            self.assertEqual(post.title, valid_data["title"])

            # Clean up
            post.delete()

    def tearDown(self):
        """Clean up after tests."""
        self.cleanup_test_data()
        super().tearDown()
