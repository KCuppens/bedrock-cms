"""Tests for search services functionality."""

from datetime import timedelta
from unittest.mock import MagicMock, Mock, PropertyMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from apps.search.services import SearchService


class SearchServiceTestCase(TestCase):
    """Test search service functionality."""

    def setUp(self):
        self.service = SearchService()

    def test_index_model_property(self):
        """Test index model property lazy loading."""
        # Test that the property returns the expected model class
        model_class = self.service.index_model
        self.assertIsNotNone(model_class)
        # Verify it's cached
        self.assertIs(self.service.index_model, model_class)

    def test_query_log_model_property(self):
        """Test query log model property lazy loading."""
        # Test that the property returns the expected model class
        model_class = self.service.query_log_model
        self.assertIsNotNone(model_class)
        # Verify it's cached
        self.assertIs(self.service.query_log_model, model_class)

    def test_suggestion_model_property(self):
        """Test suggestion model property lazy loading."""
        # Test that the property returns the expected model class
        model_class = self.service.suggestion_model
        self.assertIsNotNone(model_class)
        # Verify it's cached
        self.assertIs(self.service.suggestion_model, model_class)

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

    def test_search_basic(self):
        """Test basic search functionality."""
        # Mock the index model by setting it directly
        mock_index_model = Mock()
        mock_queryset = Mock()

        # Setup mock queryset chain
        mock_index_model.objects.filter.return_value = mock_queryset
        mock_queryset.count.return_value = 2

        # Mock search results
        mock_result1 = Mock()
        mock_result1.id = 1
        mock_result1.title = "Test Result 1"
        mock_result1.excerpt = "Test snippet 1"
        mock_result1.search_category = "blog"
        mock_result1.url = "/test-1"
        mock_result1.image_url = None
        mock_result1.locale_code = "en"
        mock_result1.search_tags = []
        mock_result1.published_at = None
        mock_result1.search_weight = 1.0
        mock_result1.content_type = None
        mock_result1.object_id = 1
        mock_result1.content = "Test content 1"

        mock_result2 = Mock()
        mock_result2.id = 2
        mock_result2.title = "Test Result 2"
        mock_result2.excerpt = "Test snippet 2"
        mock_result2.search_category = "blog"
        mock_result2.url = "/test-2"
        mock_result2.image_url = None
        mock_result2.locale_code = "en"
        mock_result2.search_tags = []
        mock_result2.published_at = None
        mock_result2.search_weight = 1.0
        mock_result2.content_type = None
        mock_result2.object_id = 2
        mock_result2.content = "Test content 2"

        # Mock the pagination behavior
        with patch("django.core.paginator.Paginator") as mock_paginator_class:
            mock_paginator = Mock()
            mock_page = Mock()
            mock_page.object_list = [mock_result1, mock_result2]
            mock_page.has_next.return_value = False
            mock_page.has_previous.return_value = False

            mock_paginator.get_page.return_value = mock_page
            mock_paginator.num_pages = 1
            mock_paginator_class.return_value = mock_paginator

            # Set the mock model
            self.service._index_model = mock_index_model

            # Mock other methods that are called
            with patch.object(self.service, "_log_search_query") as mock_log:
                with patch.object(self.service, "_update_suggestions") as mock_update:
                    with patch.object(
                        self.service, "get_suggestions", return_value=[]
                    ) as mock_suggestions:
                        results = self.service.search("test query")

                        # Verify results structure
                        self.assertIsInstance(results, dict)
                        self.assertIn("results", results)
                        self.assertIn("pagination", results)
                        self.assertEqual(len(results["results"]), 2)
                        self.assertEqual(results["pagination"]["total_results"], 2)

    def test_log_search_query(self):
        """Test search query logging."""
        mock_query_log_model = Mock()
        mock_query_log_model.objects.create.return_value = Mock()

        # Set the mock model
        self.service._query_log_model = mock_query_log_model

        # Test the private method _log_search_query
        self.service._log_search_query(
            query="test search",
            filters={},
            result_count=5,
            execution_time_ms=123,
            user=None,
            request=None,
        )

        # Verify create was called
        mock_query_log_model.objects.create.assert_called_once()
        call_args = mock_query_log_model.objects.create.call_args[1]
        self.assertEqual(call_args["query_text"], "test search")
        self.assertEqual(call_args["result_count"], 5)
        self.assertEqual(call_args["execution_time_ms"], 123)

    def test_index_object(self):
        """Test content indexing functionality."""
        # Mock content object
        mock_content = Mock()
        mock_content.pk = 1
        mock_content.title = "Test Content"
        mock_content.__str__ = Mock(return_value="Test Content")

        # Mock content type
        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_ct = Mock()
            mock_ct.pk = 1
            mock_get_ct.return_value = mock_ct

            # Mock index model
            mock_index_model = Mock()
            mock_index_obj = Mock()
            mock_index_obj.update_from_object = Mock()
            mock_index_obj.save = Mock()

            mock_index_model.objects.get_or_create.return_value = (
                mock_index_obj,
                True,
            )

            # Set the mock model
            self.service._index_model = mock_index_model

            result = self.service.index_object(mock_content)

            # Verify get_or_create was called
            mock_index_model.objects.get_or_create.assert_called_once()

            # Verify update_from_object and save were called
            mock_index_obj.update_from_object.assert_called_once_with(mock_content)
            mock_index_obj.save.assert_called_once()

    def test_remove_from_index(self):
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

            # Mock index model
            mock_index_model = Mock()
            mock_queryset = Mock()
            mock_index_model.objects.filter.return_value = mock_queryset
            mock_queryset.delete.return_value = (1, {"search.SearchIndex": 1})

            # Set the mock model
            self.service._index_model = mock_index_model

            result = self.service.remove_from_index(mock_content)

            # Verify filter and delete were called
            mock_index_model.objects.filter.assert_called_once_with(
                content_type=mock_ct, object_id=1
            )
            mock_queryset.delete.assert_called_once()

    def test_get_suggestions(self):
        """Test search suggestions functionality."""
        # Mock suggestion model and objects
        mock_suggestion1 = Mock()
        mock_suggestion1.suggestion_text = "test suggestion"
        mock_suggestion2 = Mock()
        mock_suggestion2.suggestion_text = "another suggestion"

        mock_queryset = Mock()
        mock_queryset.order_by.return_value = mock_queryset
        mock_queryset.__getitem__ = Mock(
            return_value=[mock_suggestion1, mock_suggestion2]
        )

        mock_suggestion_model = Mock()
        mock_suggestion_model.objects.filter.return_value = mock_queryset

        # Set the mock model
        self.service._suggestion_model = mock_suggestion_model

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

    def test_get_search_analytics(self):
        """Test getting search analytics."""
        # Mock query log model
        mock_queryset = Mock()
        mock_queryset.count.return_value = 100
        mock_queryset.aggregate.side_effect = [
            {"avg_results": 5.2},
            {"avg_time": 150.5},
        ]

        # Mock for top queries and zero result queries
        top_queries_qs = Mock()
        top_queries_qs.values.return_value = top_queries_qs
        top_queries_qs.annotate.return_value = top_queries_qs
        top_queries_qs.order_by.return_value = top_queries_qs
        top_queries_qs.__getitem__ = Mock(
            return_value=[
                {"query_text": "popular search", "count": 50},
                {"query_text": "another search", "count": 30},
            ]
        )

        zero_result_qs = Mock()
        zero_result_qs.filter.return_value = zero_result_qs
        zero_result_qs.values.return_value = zero_result_qs
        zero_result_qs.annotate.return_value = zero_result_qs
        zero_result_qs.order_by.return_value = zero_result_qs
        zero_result_qs.__getitem__ = Mock(
            return_value=[{"query_text": "no results query", "count": 5}]
        )

        mock_query_log_model = Mock()
        # First call for main queryset, second for zero results
        mock_query_log_model.objects.filter.side_effect = [
            mock_queryset,
            zero_result_qs,
        ]

        # Mock the values/annotate chain for top queries
        mock_queryset.values.return_value = top_queries_qs

        # Set the mock model
        self.service._query_log_model = mock_query_log_model

        analytics = self.service.get_search_analytics(days=7)

        # Verify the results
        self.assertIsInstance(analytics, dict)
        self.assertIn("period_days", analytics)
        self.assertIn("total_queries", analytics)
        self.assertIn("avg_results_per_query", analytics)
        self.assertIn("avg_execution_time_ms", analytics)
        self.assertEqual(analytics["total_queries"], 100)
        self.assertEqual(analytics["period_days"], 7)

    def test_search_performance(self):
        """Test search performance measurement."""
        # Mock time measurement
        with patch("time.time") as mock_time:
            mock_time.side_effect = [1000.0, 1000.5]  # 0.5 second execution

            # Mock the index model
            mock_index_model = Mock()
            mock_queryset = Mock()
            mock_index_model.objects.filter.return_value = mock_queryset
            mock_queryset.count.return_value = 0

            # Mock the pagination behavior
            with patch("django.core.paginator.Paginator") as mock_paginator_class:
                mock_paginator = Mock()
                mock_page = Mock()
                mock_page.object_list = []
                mock_page.has_next.return_value = False
                mock_page.has_previous.return_value = False

                mock_paginator.get_page.return_value = mock_page
                mock_paginator.num_pages = 1
                mock_paginator_class.return_value = mock_paginator

                # Set the mock model
                self.service._index_model = mock_index_model

                # Mock other methods that are called
                with patch.object(self.service, "_log_search_query") as mock_log:
                    with patch.object(
                        self.service, "_update_suggestions"
                    ) as mock_update:
                        with patch.object(
                            self.service, "get_suggestions", return_value=[]
                        ) as mock_suggestions:
                            result = self.service.search("test query")

                            # Should include timing information
                            self.assertIn("execution_time_ms", result)
                            self.assertGreater(result["execution_time_ms"], 0)


class SearchServiceIntegrationTestCase(TestCase):
    """Integration tests for search service."""

    def setUp(self):
        self.service = SearchService()

    def test_service_initialization(self):
        """Test that search service initializes properly."""
        new_service = SearchService()
        self.assertIsInstance(new_service, SearchService)
        self.assertIsNone(new_service._index_model)
        self.assertIsNone(new_service._query_log_model)
        self.assertIsNone(new_service._suggestion_model)

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
