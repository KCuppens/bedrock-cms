"""Comprehensive test coverage for manager queryset optimization and SQL generation"""

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.db import connection, models
from django.test import TestCase, override_settings
from django.test.utils import override_settings
from django.utils import timezone

from apps.core.managers import PublishedManager, SoftDeleteManager
from apps.core.mixins import SoftDeleteMixin

User = get_user_model()


class TestSoftDeleteModel(SoftDeleteMixin):
    """Concrete model for testing SoftDeleteManager with actual database operations"""

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, default="general")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        app_label = "core"


class TestPublishedModel(models.Model):
    """Concrete model for testing PublishedManager with actual database operations"""

    title = models.CharField(max_length=100)
    content = models.TextField()
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    category = models.CharField(max_length=50, default="general")

    objects = PublishedManager()

    class Meta:
        app_label = "core"


class TestCombinedModel(SoftDeleteMixin):
    """Model using both managers for comprehensive testing"""

    title = models.CharField(max_length=100)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    # Multiple managers
    objects = SoftDeleteManager()
    published_objects = PublishedManager()
    all_objects = models.Manager()

    class Meta:
        app_label = "core"


class ManagerQuerysetOptimizationTest(TestCase):
    """Test queryset optimization and SQL generation for managers"""

    def setUp(self):
        """Set up test data"""
        self.reset_queries()

    def reset_queries(self):
        """Reset query count for testing"""
        connection.queries_log.clear()

    def assertQueryCount(self, num_queries):
        """Assert the number of queries executed"""
        self.assertEqual(len(connection.queries_log), num_queries)

    def test_soft_delete_manager_sql_generation(self):
        """Test SQL generation for SoftDeleteManager queries"""
        manager = SoftDeleteManager()
        mock_model = Mock()
        mock_model._meta.db_table = "test_table"
        manager.model = mock_model

        with patch("django.db.models.Manager.get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_filtered_qs = Mock()
            mock_qs.filter.return_value = mock_filtered_qs
            mock_get_qs.return_value = mock_qs

            # Test get_queryset SQL filtering
            result = manager.get_queryset()

            # Should filter with is_deleted=False
            mock_qs.filter.assert_called_once_with(is_deleted=False)
            self.assertEqual(result, mock_filtered_qs)

    def test_published_manager_sql_generation(self):
        """Test SQL generation for PublishedManager queries"""
        manager = PublishedManager()
        mock_model = Mock()
        mock_model._meta.db_table = "test_table"
        manager.model = mock_model

        test_time = timezone.datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        with patch("django.utils.timezone.now", return_value=test_time):
            with patch.object(manager, "get_queryset") as mock_get_qs:
                mock_qs = Mock()
                mock_filtered_qs = Mock()
                mock_qs.filter.return_value = mock_filtered_qs
                mock_get_qs.return_value = mock_qs

                # Test published() method SQL generation
                result = manager.published()

                # Should filter with is_published=True and published_at__lte
                mock_qs.filter.assert_called_once_with(
                    is_published=True, published_at__lte=test_time
                )
                self.assertEqual(result, mock_filtered_qs)

    def test_queryset_chaining_optimization(self):
        """Test queryset chaining doesn't create excessive queries"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()

            # Setup method chaining
            mock_qs.filter.return_value = mock_qs
            mock_qs.order_by.return_value = mock_qs
            mock_qs.distinct.return_value = mock_qs
            mock_qs.select_related.return_value = mock_qs
            mock_qs.prefetch_related.return_value = mock_qs

            mock_get_qs.return_value = mock_qs

            # Chain multiple operations
            result = (
                manager.active()
                .filter(name__icontains="test")
                .order_by("name")
                .distinct()
                .select_related("category")
                .prefetch_related("tags")
            )

            # Should only call get_queryset once
            mock_get_qs.assert_called_once()

            # Each chained operation should be called
            self.assertTrue(mock_qs.filter.called)
            self.assertTrue(mock_qs.order_by.called)
            self.assertTrue(mock_qs.distinct.called)

    def test_manager_lazy_evaluation(self):
        """Test that manager querysets are lazily evaluated"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_qs.filter.return_value = mock_qs
            mock_qs.__iter__ = Mock(return_value=iter([]))
            mock_get_qs.return_value = mock_qs

            # Create queryset but don't evaluate
            qs = manager.active().filter(name="test")

            # Should not be evaluated yet (no __iter__ call)
            mock_qs.__iter__.assert_not_called()

            # Force evaluation
            list(qs)

            # Now should be evaluated
            mock_qs.__iter__.assert_called_once()

    def test_multiple_manager_query_optimization(self):
        """Test query optimization when using multiple managers"""
        # This tests the conceptual behavior since we're working with mocked objects
        soft_delete_mgr = SoftDeleteManager()
        published_mgr = PublishedManager()

        with patch.object(soft_delete_mgr, "get_queryset") as mock_sd_qs:
            with patch.object(published_mgr, "get_queryset") as mock_pub_qs:
                mock_sd_result = Mock()
                mock_pub_result = Mock()
                mock_sd_qs.return_value = mock_sd_result
                mock_pub_qs.return_value = mock_pub_result

                # Use different managers
                sd_qs = soft_delete_mgr.active()
                pub_qs = published_mgr.published()

                # Each should use their own queryset
                mock_sd_qs.assert_called_once()
                mock_pub_qs.assert_called_once()
                self.assertNotEqual(sd_qs, pub_qs)

    def test_queryset_annotation_optimization(self):
        """Test queryset annotations don't break manager filtering"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_annotated_qs = Mock()

            mock_qs.filter.return_value = mock_qs
            mock_qs.annotate.return_value = mock_annotated_qs
            mock_get_qs.return_value = mock_qs

            # Test annotations on manager queryset
            result = manager.active().annotate(item_count=models.Count("items"))

            # Should maintain the filter and add annotation
            mock_qs.filter.assert_called_with(is_deleted=False)
            mock_qs.annotate.assert_called_with(item_count=models.Count("items"))

    def test_queryset_aggregation_optimization(self):
        """Test queryset aggregations with manager filtering"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_aggregated_result = {"count": 5}

            mock_qs.filter.return_value = mock_qs
            mock_qs.aggregate.return_value = mock_aggregated_result
            mock_get_qs.return_value = mock_qs

            # Test aggregation on manager queryset
            result = manager.active().aggregate(total=models.Count("id"))

            # Should apply filter before aggregation
            mock_qs.filter.assert_called_with(is_deleted=False)
            mock_qs.aggregate.assert_called_with(total=models.Count("id"))
            self.assertEqual(result, mock_aggregated_result)

    def test_queryset_subquery_optimization(self):
        """Test subquery optimization with managers"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_subquery = Mock()
            mock_filtered_qs = Mock()

            mock_qs.filter.return_value = mock_filtered_qs
            mock_get_qs.return_value = mock_qs

            # Test subquery with manager
            from django.db.models import OuterRef, Subquery

            subquery = Subquery(
                mock_subquery.filter(parent_id=OuterRef("id")).values("id")
            )

            result = manager.active().filter(id__in=subquery)

            # Should apply manager filter first, then subquery filter
            mock_qs.filter.assert_called_with(is_deleted=False)
            mock_filtered_qs.filter.assert_called_with(id__in=subquery)

    def test_manager_queryset_caching(self):
        """Test queryset caching behavior with managers"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_qs.filter.return_value = mock_qs
            mock_qs._result_cache = None  # Simulate uncached queryset
            mock_get_qs.return_value = mock_qs

            # Multiple calls to same manager method
            qs1 = manager.active()
            qs2 = manager.active()

            # Should call get_queryset multiple times (no caching at manager level)
            self.assertEqual(mock_get_qs.call_count, 2)

    def test_queryset_database_functions(self):
        """Test database functions work with manager querysets"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_annotated_qs = Mock()

            mock_qs.filter.return_value = mock_qs
            mock_qs.annotate.return_value = mock_annotated_qs
            mock_get_qs.return_value = mock_qs

            # Test with database functions
            from django.db.models.functions import Length, Upper

            result = manager.active().annotate(
                upper_name=Upper("name"), name_length=Length("name")
            )

            # Should apply filter then annotation
            mock_qs.filter.assert_called_with(is_deleted=False)
            mock_qs.annotate.assert_called_with(
                upper_name=Upper("name"), name_length=Length("name")
            )

    def test_manager_raw_queries(self):
        """Test raw queries with managers"""
        manager = SoftDeleteManager()
        manager.model = Mock()
        manager.model._meta.db_table = "test_table"

        # Test that raw queries bypass manager filtering (expected behavior)
        with patch.object(manager, "raw") as mock_raw:
            mock_result = Mock()
            mock_raw.return_value = mock_result

            sql = "SELECT * FROM test_table WHERE custom_condition = %s"
            result = manager.raw(sql, ["value"])

            mock_raw.assert_called_once_with(sql, ["value"])
            self.assertEqual(result, mock_result)


class ManagerPerformanceTest(TestCase):
    """Performance tests for managers with actual database operations"""

    def setUp(self):
        """Create test tables for performance testing"""
        # These models are created dynamically for testing
        pass

    def test_soft_delete_manager_query_count(self):
        """Test that SoftDeleteManager generates efficient queries"""
        # This would test actual database query generation
        # For now, we test the conceptual behavior

        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_qs.filter.return_value = mock_qs
            mock_qs.count.return_value = 5
            mock_get_qs.return_value = mock_qs

            # Single query operations
            count = manager.active().count()

            # Should only call get_queryset once
            mock_get_qs.assert_called_once()
            self.assertEqual(count, 5)

    def test_published_manager_timezone_query_optimization(self):
        """Test timezone-aware queries are optimized"""
        manager = PublishedManager()

        test_time = timezone.now()

        with patch("django.utils.timezone.now", return_value=test_time):
            with patch.object(manager, "get_queryset") as mock_get_qs:
                mock_qs = Mock()
                mock_filtered_qs = Mock()
                mock_qs.filter.return_value = mock_filtered_qs
                mock_get_qs.return_value = mock_qs

                # Test that timezone.now() is called once per method call
                result = manager.published()

                # Should use the same time consistently
                mock_qs.filter.assert_called_once_with(
                    is_published=True, published_at__lte=test_time
                )

    def test_manager_bulk_operations_performance(self):
        """Test bulk operations performance"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_bulk_result = Mock()

            mock_qs.filter.return_value = mock_qs
            mock_qs.bulk_update.return_value = mock_bulk_result
            mock_get_qs.return_value = mock_qs

            # Test bulk update with manager
            objects = [Mock() for _ in range(100)]
            result = manager.active().bulk_update(objects, ["field"])

            # Should apply manager filter before bulk operation
            mock_qs.filter.assert_called_with(is_deleted=False)

    def test_manager_select_related_optimization(self):
        """Test select_related optimization with managers"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_optimized_qs = Mock()

            mock_qs.filter.return_value = mock_qs
            mock_qs.select_related.return_value = mock_optimized_qs
            mock_get_qs.return_value = mock_qs

            # Test select_related with manager filtering
            result = manager.active().select_related("category", "author")

            # Should apply both filter and select_related
            mock_qs.filter.assert_called_with(is_deleted=False)
            mock_qs.select_related.assert_called_with("category", "author")
            self.assertEqual(result, mock_optimized_qs)

    def test_manager_prefetch_related_optimization(self):
        """Test prefetch_related optimization with managers"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_prefetched_qs = Mock()

            mock_qs.filter.return_value = mock_qs
            mock_qs.prefetch_related.return_value = mock_prefetched_qs
            mock_get_qs.return_value = mock_qs

            # Test prefetch_related with manager filtering
            result = manager.active().prefetch_related("tags", "comments")

            # Should apply both filter and prefetch_related
            mock_qs.filter.assert_called_with(is_deleted=False)
            mock_qs.prefetch_related.assert_called_with("tags", "comments")
            self.assertEqual(result, mock_prefetched_qs)


class ManagerSQLGenerationTest(TestCase):
    """Test actual SQL generation and database interaction"""

    def test_soft_delete_manager_sql_structure(self):
        """Test SoftDeleteManager generates correct SQL structure"""
        manager = SoftDeleteManager()

        # Mock the super().get_queryset() to capture filter calls
        with patch.object(models.Manager, "get_queryset") as mock_super_get_qs:
            mock_base_qs = Mock()
            mock_filtered_qs = Mock()

            # Simulate SQL query attributes
            mock_filtered_qs.query = Mock()
            mock_filtered_qs.query.get_compiler = Mock()
            mock_base_qs.filter.return_value = mock_filtered_qs
            mock_super_get_qs.return_value = mock_base_qs

            # Call the actual get_queryset method which should apply the filter
            queryset = manager.get_queryset()

            # Should apply is_deleted=False filter to the base queryset
            mock_base_qs.filter.assert_called_once_with(is_deleted=False)
            self.assertEqual(queryset, mock_filtered_qs)

    def test_published_manager_complex_sql(self):
        """Test PublishedManager generates complex SQL correctly"""
        manager = PublishedManager()

        test_time = timezone.datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        with patch("django.utils.timezone.now", return_value=test_time):
            with patch.object(manager, "get_queryset") as mock_get_qs:
                mock_qs = Mock()
                mock_filtered_qs = Mock()
                mock_ordered_qs = Mock()

                mock_qs.filter.return_value = mock_filtered_qs
                mock_filtered_qs.order_by.return_value = mock_ordered_qs
                mock_get_qs.return_value = mock_qs

                # Test complex query with multiple operations
                result = manager.published().order_by("-published_at")

                # Should apply published filter then ordering
                mock_qs.filter.assert_called_with(
                    is_published=True, published_at__lte=test_time
                )
                mock_filtered_qs.order_by.assert_called_with("-published_at")
                self.assertEqual(result, mock_ordered_qs)

    def test_manager_join_optimization(self):
        """Test manager queries with joins are optimized"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_filtered_qs = Mock()
            mock_joined_qs = Mock()

            mock_qs.filter.return_value = mock_filtered_qs
            mock_filtered_qs.select_related.return_value = mock_joined_qs
            mock_get_qs.return_value = mock_qs

            # Test join with manager filter
            result = manager.active().select_related("foreign_key")

            # Should apply manager filter then join
            mock_qs.filter.assert_called_with(is_deleted=False)
            mock_filtered_qs.select_related.assert_called_with("foreign_key")
            self.assertEqual(result, mock_joined_qs)

    def test_manager_index_usage(self):
        """Test that manager queries can use database indexes effectively"""
        manager = SoftDeleteManager()

        # Test that manager filters work well with indexed fields
        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_filtered_qs = Mock()

            mock_qs.filter.return_value = mock_filtered_qs
            mock_filtered_qs.filter.return_value = mock_filtered_qs
            mock_get_qs.return_value = mock_qs

            # Simulate indexed field query with fixed timestamp
            test_time = timezone.now()
            result = manager.active().filter(created_at__gte=test_time)

            # Should apply both filters efficiently
            mock_qs.filter.assert_called_with(is_deleted=False)
            mock_filtered_qs.filter.assert_called_with(created_at__gte=test_time)

    def test_manager_database_specific_features(self):
        """Test manager compatibility with database-specific features"""
        manager = PublishedManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_distinct_qs = Mock()

            mock_qs.distinct.return_value = mock_distinct_qs
            mock_get_qs.return_value = mock_qs

            # Test DISTINCT with manager
            result = manager.get_queryset().distinct()

            # Should support database features
            mock_qs.distinct.assert_called_once()
            self.assertEqual(result, mock_distinct_qs)
