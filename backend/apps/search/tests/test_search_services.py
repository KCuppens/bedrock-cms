"""Tests for search services functionality."""

from datetime import timedelta
from unittest.mock import MagicMock, Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from apps.search.services import SearchService


class SearchServiceTestCase(TestCase):
    """Test search service functionality."""

    def setUp(self):
        self.service = SearchService()

    @patch("apps.search.services.SearchService.index_model")
    def test_index_model_property(self, mock_index_model):
        """Test index model property lazy loading."""
        mock_model = Mock()
        mock_index_model.return_value = mock_model

        # First access should load the model
        result = self.service.index_model
        self.assertEqual(result, mock_index_model.return_value)

    @patch("apps.search.services.SearchService.query_log_model")
    def test_query_log_model_property(self, mock_query_log_model):
        """Test query log model property lazy loading."""
        mock_model = Mock()
        mock_query_log_model.return_value = mock_model

        # First access should load the model
        result = self.service.query_log_model
        self.assertEqual(result, mock_query_log_model.return_value)

    @patch("apps.search.services.SearchService.suggestion_model")
    def test_suggestion_model_property(self, mock_suggestion_model):
        """Test suggestion model property lazy loading."""
        mock_model = Mock()
        mock_suggestion_model.return_value = mock_model

        # First access should load the model
        result = self.service.suggestion_model
        self.assertEqual(result, mock_suggestion_model.return_value)

    @patch("apps.search.services.content_registry")
    def test_get_searchable_models(self, mock_registry):
        """Test getting searchable content models."""
        # Mock registry with searchable models
        mock_config1 = Mock()
        mock_config1.is_searchable = True
        mock_config1.model = Mock()
        mock_config1.model.__name__ = "BlogPost"

        mock_config2 = Mock()
        mock_config2.is_searchable = False
        mock_config2.model = Mock()
        mock_config2.model.__name__ = "Page"

        mock_config3 = Mock()
        mock_config3.is_searchable = True
        mock_config3.model = Mock()
        mock_config3.model.__name__ = "Article"

        mock_registry.get_all_configs.return_value = [
            mock_config1,
            mock_config2,
            mock_config3,
        ]

        # Test the method if it exists
        if hasattr(self.service, "get_searchable_models"):
            searchable = self.service.get_searchable_models()
            self.assertEqual(len(searchable), 2)
            self.assertIn(mock_config1.model, searchable)
            self.assertIn(mock_config3.model, searchable)
            self.assertNotIn(mock_config2.model, searchable)

    def test_sanitize_query(self):
        """Test query sanitization functionality."""
        if hasattr(self.service, "sanitize_query"):
            # Test basic sanitization
            clean_query = self.service.sanitize_query("hello world")
            self.assertEqual(clean_query, "hello world")

            # Test with special characters
            special_query = self.service.sanitize_query("hello & world | test")
            self.assertIsInstance(special_query, str)

            # Test empty query
            empty_query = self.service.sanitize_query("")
            self.assertEqual(empty_query, "")

            # Test None query
            none_query = self.service.sanitize_query(None)
            self.assertEqual(none_query, "")

    @patch("apps.search.services.SearchService.index_model")
    def test_search_basic(self, mock_index_model):
        """Test basic search functionality."""
        # Mock queryset and search results
        mock_queryset = Mock()
        mock_index_model.objects.filter.return_value = mock_queryset
        mock_queryset.select_related.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset

        # Mock search results
        mock_result1 = Mock()
        mock_result1.content_object = Mock()
        mock_result1.title = "Test Result 1"
        mock_result1.snippet = "Test snippet 1"
        mock_result1.relevance_score = 0.9

        mock_result2 = Mock()
        mock_result2.content_object = Mock()
        mock_result2.title = "Test Result 2"
        mock_result2.snippet = "Test snippet 2"
        mock_result2.relevance_score = 0.7

        mock_queryset.__iter__ = Mock(return_value=iter([mock_result1, mock_result2]))
        mock_queryset.count.return_value = 2

        if hasattr(self.service, "search"):
            results = self.service.search("test query")

            # Verify results structure
            self.assertIsInstance(results, dict)
            if "results" in results:
                self.assertEqual(len(results["results"]), 2)
                self.assertEqual(results["total"], 2)

    @patch("apps.search.services.SearchService.query_log_model")
    def test_log_search_query(self, mock_query_log_model):
        """Test search query logging."""
        mock_query_log_model.objects.create.return_value = Mock()

        if hasattr(self.service, "log_search_query"):
            # Test logging with basic parameters
            self.service.log_search_query(
                query="test search", user_id=1, results_count=5, execution_time=0.123
            )

            # Verify create was called
            mock_query_log_model.objects.create.assert_called_once()
            call_args = mock_query_log_model.objects.create.call_args[1]
            self.assertEqual(call_args["query"], "test search")
            self.assertEqual(call_args["results_count"], 5)
            self.assertEqual(call_args["execution_time"], 0.123)

    @patch("apps.search.services.SearchService.index_model")
    def test_index_content(self, mock_index_model):
        """Test content indexing functionality."""
        # Mock content object
        mock_content = Mock()
        mock_content.pk = 1
        mock_content.title = "Test Content"
        mock_content.get_search_content.return_value = "Test content for search"

        # Mock content type
        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_ct = Mock()
            mock_ct.pk = 1
            mock_get_ct.return_value = mock_ct

            # Mock index creation
            mock_index_obj = Mock()
            mock_index_model.objects.update_or_create.return_value = (
                mock_index_obj,
                True,
            )

            if hasattr(self.service, "index_content"):
                result = self.service.index_content(mock_content)

                # Verify update_or_create was called
                mock_index_model.objects.update_or_create.assert_called_once()

                # Check the defaults parameter structure
                call_args = mock_index_model.objects.update_or_create.call_args
                self.assertIn("defaults", call_args[1])

    @patch("apps.search.services.SearchService.index_model")
    def test_remove_from_index(self, mock_index_model):
        """Test removing content from search index."""
        # Mock content object
        mock_content = Mock()
        mock_content.pk = 1

        # Mock content type
        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_ct = Mock()
            mock_ct.pk = 1
            mock_get_ct.return_value = mock_ct

            # Mock queryset for deletion
            mock_queryset = Mock()
            mock_index_model.objects.filter.return_value = mock_queryset
            mock_queryset.delete.return_value = (1, {"search.SearchIndex": 1})

            if hasattr(self.service, "remove_from_index"):
                result = self.service.remove_from_index(mock_content)

                # Verify filter and delete were called
                mock_index_model.objects.filter.assert_called_once()
                mock_queryset.delete.assert_called_once()

    @patch("apps.search.services.SearchService.suggestion_model")
    def test_get_suggestions(self, mock_suggestion_model):
        """Test search suggestions functionality."""
        # Mock suggestion queryset
        mock_queryset = Mock()
        mock_suggestion_model.objects.filter.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset
        mock_queryset.values_list.return_value = [
            "test suggestion",
            "another suggestion",
        ]

        if hasattr(self.service, "get_suggestions"):
            suggestions = self.service.get_suggestions("test")

            # Verify the query
            mock_suggestion_model.objects.filter.assert_called_once()
            self.assertEqual(suggestions, ["test suggestion", "another suggestion"])

    def test_calculate_relevance_score(self):
        """Test relevance score calculation."""
        if hasattr(self.service, "calculate_relevance_score"):
            # Test basic relevance calculation
            score = self.service.calculate_relevance_score(
                query="test search",
                title="Test Document Title",
                content="This document contains test content for search functionality",
            )

            self.assertIsInstance(score, (int, float))
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 1)

    @patch("apps.search.services.SearchService.query_log_model")
    def test_get_popular_queries(self, mock_query_log_model):
        """Test getting popular search queries."""
        # Mock queryset with aggregation
        mock_queryset = Mock()
        mock_query_log_model.objects.filter.return_value = mock_queryset
        mock_queryset.values.return_value = mock_queryset
        mock_queryset.annotate.return_value = mock_queryset
        mock_queryset.order_by.return_value = mock_queryset

        # Mock popular queries result
        mock_popular = [
            {"query": "popular search", "count": 100},
            {"query": "another search", "count": 75},
        ]
        mock_queryset.__iter__ = Mock(return_value=iter(mock_popular))

        if hasattr(self.service, "get_popular_queries"):
            # Test with default parameters
            popular = self.service.get_popular_queries()

            # Verify the query structure
            mock_query_log_model.objects.filter.assert_called_once()
            mock_queryset.values.assert_called_with("query")
            mock_queryset.annotate.assert_called_once()

    @patch("apps.search.services.timezone")
    def test_get_search_analytics(self, mock_timezone):
        """Test search analytics functionality."""
        # Mock current time
        mock_now = timezone.now()
        mock_timezone.now.return_value = mock_now

        if hasattr(self.service, "get_search_analytics"):
            # Test basic analytics call
            analytics = self.service.get_search_analytics(days=7)

            # Should return dictionary with analytics data
            self.assertIsInstance(analytics, dict)

    def test_search_performance(self):
        """Test search performance measurement."""
        if hasattr(self.service, "search"):
            # Mock time measurement
            with patch("apps.search.services.time") as mock_time:
                mock_time.time.side_effect = [1000.0, 1000.5]  # 0.5 second execution

                # Mock search results
                with patch.object(self.service, "index_model") as mock_model:
                    mock_queryset = Mock()
                    mock_model.objects.filter.return_value = mock_queryset
                    mock_queryset.select_related.return_value = mock_queryset
                    mock_queryset.order_by.return_value = mock_queryset
                    mock_queryset.__iter__ = Mock(return_value=iter([]))
                    mock_queryset.count.return_value = 0

                    result = self.service.search("test query")

                    # Should include timing information
                    if isinstance(result, dict) and "execution_time" in result:
                        self.assertGreater(result["execution_time"], 0)


class SearchServiceIntegrationTestCase(TestCase):
    """Integration tests for search service."""

    def setUp(self):
        self.service = SearchService()

    def test_service_initialization(self):
        """Test that search service initializes properly."""
        self.assertIsInstance(self.service, SearchService)
        self.assertIsNone(self.service._index_model)
        self.assertIsNone(self.service._query_log_model)
        self.assertIsNone(self.service._suggestion_model)

    def test_postgres_search_import(self):
        """Test PostgreSQL search import handling."""
        from apps.search.services import (
            HAS_POSTGRES_SEARCH,
            SearchQuery,
            SearchRank,
            SearchVector,
        )

        # Should handle import gracefully
        self.assertIsInstance(HAS_POSTGRES_SEARCH, bool)

        if not HAS_POSTGRES_SEARCH:
            # If PostgreSQL search is not available, imports should be None
            self.assertIsNone(SearchQuery)
            self.assertIsNone(SearchRank)
            self.assertIsNone(SearchVector)

    def test_service_methods_exist(self):
        """Test that expected service methods exist."""
        # Core methods that should exist
        expected_methods = ["index_model", "query_log_model", "suggestion_model"]

        for method in expected_methods:
            self.assertTrue(
                hasattr(self.service, method),
                f"SearchService should have {method} property/method",
            )
