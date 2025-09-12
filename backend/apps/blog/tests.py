from django.contrib.auth import get_user_model

from django.core.exceptions import ValidationError

from django.test import TestCase



from apps.i18n.models import Locale

from apps.registry.registry import content_registry

from apps.registry.serializers import get_serializer_for_model

from apps.registry.viewsets import get_viewset_for_model



from .models import BlogPost, Category, Tag


User = get_user_model()



class BlogModelTests(TestCase):

    """Test blog models."""



    def setUp(self):

        """Set up test data."""

        self.user = User.objects.create_user(

            email="author@example.com", password="testpass123"

        )

        self.locale = Locale.objects.create(

            code="en",

            name="English",

            native_name="English",

            is_default=True,

            is_active=True,

        )



        self.category = Category.objects.create(

            name="Technology", description="Tech-related posts"

        )



        self.tag1 = Tag.objects.create(name="Python")

        self.tag2 = Tag.objects.create(name="Django")



    def test_category_creation(self):

        """Test creating a category."""

        self.assertEqual(self.category.name, "Technology")

        self.assertEqual(self.category.slug, "technology")  # Auto-generated

        self.assertTrue(self.category.is_active)

        self.assertEqual(str(self.category), "Technology")



    def test_tag_creation(self):

        """Test creating a tag."""

        self.assertEqual(self.tag1.name, "Python")

        self.assertEqual(self.tag1.slug, "python")  # Auto-generated

        self.assertTrue(self.tag1.is_active)

        self.assertEqual(str(self.tag1), "Python")



    def test_blog_post_creation(self):

        """Test creating a blog post."""

        post = BlogPost.objects.create(

            title="My First Blog Post",

            content="This is the content of my blog post.",

            author=self.user,

            locale=self.locale,

            category=self.category,

            status="draft",

        )



        self.assertEqual(post.title, "My First Blog Post")

        self.assertEqual(post.slug, "my-first-blog-post")  # Auto-generated

        self.assertEqual(post.author, self.user)

        self.assertEqual(post.status, "draft")

        self.assertEqual(str(post), "My First Blog Post")



    def test_blog_post_with_tags(self):

        """Test blog post with tags."""

        post = BlogPost.objects.create(

            title="Python Django Tutorial",

            content="Learn Django framework.",

            author=self.user,

            locale=self.locale,

        )



        post.tags.add(self.tag1, self.tag2)



        self.assertEqual(post.tags.count(), 2)

        self.assertIn(self.tag1, post.tags.all())

        self.assertIn(self.tag2, post.tags.all())



    def test_blog_post_publishing(self):

        """Test blog post publishing logic."""

        post = BlogPost.objects.create(

            title="Test Post",

            content="Test content",

            author=self.user,

            locale=self.locale,

            status="draft",

        )



        # Initially not published

        self.assertFalse(post.is_published)

        self.assertIsNone(post.published_at)



        # Publish the post

        post.status = "published"

        post.save()



        # Should now be published with timestamp

        self.assertTrue(post.is_published)

        self.assertIsNotNone(post.published_at)



    def test_scheduled_post_validation(self):

        """Test validation for scheduled posts."""

        post = BlogPost(

            title="Scheduled Post",

            content="This will be published later",

            author=self.user,

            locale=self.locale,

            status="scheduled",

            # Missing scheduled_for - should raise validation error

        )



        with self.assertRaises(ValidationError):

            post.clean()



    def test_reading_time_calculation(self):

        """Test reading time calculation."""

        content = " ".join(["word"] * 500)  # 500 words



        post = BlogPost.objects.create(

            title="Long Post", content=content, author=self.user, locale=self.locale

        )



        reading_time = post.get_reading_time()

        self.assertEqual(reading_time, 2)  # 500 words / 250 = 2 minutes



    def test_reading_time_with_blocks(self):

        """Test reading time calculation with blocks."""

        blocks = [

            {"type": "paragraph", "props": {"content": " ".join(["word"] * 100)}},

            {"type": "heading", "props": {"text": " ".join(["word"] * 50)}},

        ]



        post = BlogPost.objects.create(

            title="Post with Blocks",

            content="Some content",  # ~100 more words

            blocks=blocks,

            author=self.user,

            locale=self.locale,

        )



        reading_time = post.get_reading_time()

        # Total ~252 words (content + blocks) / 250 = ~1 minute

        self.assertEqual(reading_time, 1)



    def test_related_posts(self):

        """Test getting related posts."""

        # Create posts with same category

        post1 = BlogPost.objects.create(

            title="Post 1",

            content="Content 1",

            author=self.user,

            locale=self.locale,

            category=self.category,

            status="published",

        )



        post2 = BlogPost.objects.create(

            title="Post 2",

            content="Content 2",

            author=self.user,

            locale=self.locale,

            category=self.category,

            status="published",

        )



        post3 = BlogPost.objects.create(

            title="Post 3",

            content="Content 3",

            author=self.user,

            locale=self.locale,

            status="published",  # Different category

        )



        # post1 should find post2 as related (same category)

        # but not post3 (different category)

        related = post1.get_related_posts()

        self.assertIn(post2, related)

        self.assertNotIn(post3, related)



    def test_unique_slug_per_locale(self):

        """Test that slugs are unique per locale."""

        BlogPost.objects.create(

            title="Same Title",

            content="Content 1",

            author=self.user,

            locale=self.locale,

        )



        # Same slug in same locale should raise error

        with self.assertRaises(Exception):  # IntegrityError

            BlogPost.objects.create(

                title="Same Title",

                content="Content 2",

                author=self.user,

                locale=self.locale,

            )



    def test_category_post_count(self):

        """Test category post count functionality."""

        # Create published posts

        BlogPost.objects.create(

            title="Post 1",

            content="Content",

            author=self.user,

            locale=self.locale,

            category=self.category,

            status="published",

        )



        BlogPost.objects.create(

            title="Post 2",

            content="Content",

            author=self.user,

            locale=self.locale,

            category=self.category,

            status="draft",  # This shouldn't count

        )



        # Should only count published posts

        published_count = self.category.posts.filter(status="published").count()

        self.assertEqual(published_count, 1)



class BlogIntegrationTests(TestCase):

    """Integration tests for blog functionality."""



    def setUp(self):

        """Set up test data."""

        self.user = User.objects.create_user(

            email="author@example.com", password="testpass123"

        )

        self.locale = Locale.objects.create(

            code="en",

            name="English",

            native_name="English",

            is_default=True,

            is_active=True,

        )



    def test_content_registry_integration(self):

        """Test that blog models are registered with content registry."""



        # Check that blog models are registered

        self.assertTrue(content_registry.is_registered("blog.blogpost"))

        self.assertTrue(content_registry.is_registered("blog.category"))

        self.assertTrue(content_registry.is_registered("blog.tag"))



        # Check configurations

        blog_config = content_registry.get_config("blog.blogpost")

        self.assertEqual(blog_config.kind, "collection")

        self.assertEqual(blog_config.name, "Blog Posts")

        self.assertEqual(blog_config.slug_field, "slug")

        self.assertEqual(blog_config.locale_field, "locale")

        self.assertTrue(blog_config.can_publish)



    def test_blog_api_endpoints_exist(self):

        """Test that blog API endpoints are auto-generated."""



        # Test that serializers can be created

        blog_serializer = get_serializer_for_model("blog.blogpost")

        self.assertIsNotNone(blog_serializer)



        category_serializer = get_serializer_for_model("blog.category")

        self.assertIsNotNone(category_serializer)



        # Test that viewsets can be created

        blog_viewset = get_viewset_for_model("blog.blogpost")

        self.assertIsNotNone(blog_viewset)



        category_viewset = get_viewset_for_model("blog.category")

        self.assertIsNotNone(category_viewset)

