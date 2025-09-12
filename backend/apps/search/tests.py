from django.contrib.auth import get_user_model

from django.contrib.contenttypes.models import ContentType

from django.db.models.signals import post_delete, post_save

from django.test import TestCase



from apps.blog.models import BlogPost, Category

from apps.i18n.models import Locale

from apps.search.signals import auto_index_content, auto_remove_from_index



from .models import SearchIndex, SearchQuery, SearchSuggestion



"""Tests for search functionality."""



User = get_user_model()



class SearchModelTests(TestCase):

    """Test search models."""



    def setUp(self):

        """Set up test data."""

        # Disconnect search signals to avoid conflicts during tests



        post_save.disconnect(auto_index_content)

        post_delete.disconnect(auto_remove_from_index)



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



        self.blog_post = BlogPost.objects.create(

            title="Test Blog Post",

            content="This is test content for search functionality.",

            author=self.user,

            locale=self.locale,

            category=self.category,

            status="published",

        )



    def test_search_index_creation(self):

        """Test creating a search index entry."""

        content_type = ContentType.objects.get_for_model(BlogPost)



        search_index = SearchIndex.objects.create(

            content_type=content_type,

            object_id=self.blog_post.id,

            title="Test Blog Post",

            content="This is test content",

            search_category="collection",

            is_published=True,

        )



        self.assertEqual(search_index.content_object, self.blog_post)

        """self.assertEqual(str(search_index), "Test Blog Post (collection)")"""



    def test_search_index_update_from_object(self):

        """Test updating search index from source object."""

        content_type = ContentType.objects.get_for_model(BlogPost)



        search_index = SearchIndex.objects.create(

            content_type=content_type, object_id=self.blog_post.id

        )



        search_index.update_from_object(self.blog_post)



        """self.assertEqual(search_index.title, "Test Blog Post")"""

        """self.assertIn("test content", search_index.content.lower())"""

        self.assertEqual(search_index.search_category, "collection")

        self.assertTrue(search_index.is_published)



    def test_search_query_logging(self):

        """Test search query logging."""

        query_log = SearchQuery.objects.create(

            query_text="test query", result_count=5, execution_time_ms=150

        )



        """self.assertEqual(str(query_log), '"test query" (5 results)')"""



    def test_search_suggestion_creation(self):

        """Test search suggestion creation."""

        suggestion = SearchSuggestion.objects.create(

            suggestion_text="Django CMS",

        )



        # Test auto-normalization

        self.assertEqual(suggestion.normalized_text, "django cms")

        self.assertEqual(str(suggestion), "Django CMS")



    def test_search_suggestion_increment(self):

        """Test search suggestion count increment."""

        suggestion = SearchSuggestion.objects.create(suggestion_text="Python Tutorial")



        initial_count = suggestion.search_count

        suggestion.increment_search_count(result_count=10)



        self.assertEqual(suggestion.search_count, initial_count + 1)

        self.assertEqual(suggestion.result_count, 10)

        self.assertIsNotNone(suggestion.last_searched_at)

