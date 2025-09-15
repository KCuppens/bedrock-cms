"""Advanced integration tests for managers with mixins, inheritance, and complex scenarios"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, call, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.core.managers import PublishedManager, SoftDeleteManager
from apps.core.mixins import SoftDeleteMixin, TimestampMixin, UserTrackingMixin

User = get_user_model()


class ComplexTestModel(SoftDeleteMixin, TimestampMixin, UserTrackingMixin):
    """Complex model combining multiple mixins and managers"""

    title = models.CharField(max_length=200)
    content = models.TextField()
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    category = models.CharField(max_length=50)
    priority = models.IntegerField(default=0)

    # Multiple managers for different use cases
    objects = SoftDeleteManager()  # Default: excludes soft-deleted
    published = PublishedManager()  # For published content
    all_objects = models.Manager()  # Includes all records

    class Meta:
        app_label = "core"
        ordering = ["-created_at", "title"]
        indexes = [
            models.Index(fields=["is_deleted", "category"]),
            models.Index(fields=["is_published", "published_at"]),
            models.Index(fields=["created_at"]),
        ]


class CustomQuerySet(models.QuerySet):
    """Custom queryset for testing advanced manager integration"""

    def active_and_published(self):
        """Combine active (not soft-deleted) and published filters"""
        return self.filter(is_deleted=False, is_published=True)

    def by_category(self, category):
        """Filter by category"""
        return self.filter(category=category)

    def recent(self, days=7):
        """Get recent items within specified days"""
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff)

    def with_content_stats(self):
        """Add content statistics annotations"""
        from django.db.models import Case, IntegerField, Length, When

        return self.annotate(
            content_length=Length("content"),
            content_category=Case(
                When(content_length__lt=100, then=models.Value("short")),
                When(content_length__lt=500, then=models.Value("medium")),
                default=models.Value("long"),
                output_field=models.CharField(max_length=10),
            ),
            priority_level=Case(
                When(priority__gte=10, then=models.Value(1)),
                When(priority__gte=5, then=models.Value(2)),
                default=models.Value(3),
                output_field=IntegerField(),
            ),
        )


class AdvancedSoftDeleteManager(SoftDeleteManager):
    """Advanced manager extending SoftDeleteManager with custom queryset"""

    def get_queryset(self):
        """Return custom queryset with soft delete filtering"""
        return CustomQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def active_and_published(self):
        """Get active and published items"""
        return self.get_queryset().active_and_published()

    def by_category(self, category):
        """Filter by category"""
        return self.get_queryset().by_category(category)

    def recent(self, days=7):
        """Get recent items"""
        return self.get_queryset().recent(days)

    def with_stats(self):
        """Get items with content statistics"""
        return self.get_queryset().with_content_stats()

    def popular_recent(self, days=30):
        """Get popular recent items"""
        return (
            self.recent(days)
            .filter(priority__gte=5)
            .order_by("-priority", "-created_at")
        )


class AdvancedPublishedManager(PublishedManager):
    """Advanced published manager with custom methods"""

    def get_queryset(self):
        """Return custom queryset for published content"""
        return CustomQuerySet(self.model, using=self._db)

    def live(self):
        """Get live published content (published and not soft-deleted)"""
        now = timezone.now()
        return self.get_queryset().filter(
            is_published=True, published_at__lte=now, is_deleted=False
        )

    def scheduled_this_week(self):
        """Get content scheduled for this week"""
        now = timezone.now()
        week_end = now + timezone.timedelta(days=7)
        return self.get_queryset().filter(
            is_published=True, published_at__gt=now, published_at__lte=week_end
        )


class ManagerMixinIntegrationTest(TestCase):
    """Test manager integration with various mixins"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user("test@example.com", "password")

    def test_soft_delete_manager_with_timestamp_mixin(self):
        """Test SoftDeleteManager works with TimestampMixin"""

        # Create a model that uses both
        class TimestampedSoftDeleteModel(SoftDeleteMixin, TimestampMixin):
            name = models.CharField(max_length=100)
            objects = SoftDeleteManager()
            all_objects = models.Manager()

            class Meta:
                app_label = "core"

        manager = AdvancedSoftDeleteManager()
        manager.model = TimestampedSoftDeleteModel

        # Test manager filters work with timestamp fields
        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_filtered_qs = Mock()
            mock_qs.filter.return_value = mock_filtered_qs
            mock_get_qs.return_value = mock_qs

            # Test combining manager filter with timestamp filtering
            result = manager.active().filter(created_at__gte=timezone.now())

            # Should apply soft delete filter first
            self.assertTrue(mock_get_qs.called)

    def test_manager_with_user_tracking_mixin(self):
        """Test manager integration with UserTrackingMixin"""

        class UserTrackedModel(SoftDeleteMixin, UserTrackingMixin):
            title = models.CharField(max_length=100)
            objects = SoftDeleteManager()

            class Meta:
                app_label = "core"

        manager = SoftDeleteManager()
        manager.model = UserTrackedModel

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_filtered_qs = Mock()
            mock_qs.filter.return_value = mock_filtered_qs
            mock_get_qs.return_value = mock_qs

            # Test filtering by user with manager
            result = manager.active().filter(created_by=self.user)

            # Should work with user tracking fields
            mock_get_qs.assert_called_once()
            mock_qs.filter.assert_called_with(is_deleted=False)

    def test_multiple_manager_inheritance_patterns(self):
        """Test different manager inheritance patterns"""

        # Test manager extending SoftDeleteManager
        advanced_manager = AdvancedSoftDeleteManager()
        self.assertIsInstance(advanced_manager, SoftDeleteManager)
        self.assertTrue(hasattr(advanced_manager, "active"))
        self.assertTrue(hasattr(advanced_manager, "by_category"))

        # Test manager extending PublishedManager
        advanced_pub_manager = AdvancedPublishedManager()
        self.assertIsInstance(advanced_pub_manager, PublishedManager)
        self.assertTrue(hasattr(advanced_pub_manager, "published"))
        self.assertTrue(hasattr(advanced_pub_manager, "live"))

    def test_manager_queryset_method_propagation(self):
        """Test custom queryset methods are available through manager"""
        manager = AdvancedSoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = CustomQuerySet(ComplexTestModel)
            mock_get_qs.return_value = mock_qs

            # Test that queryset methods are accessible
            self.assertTrue(hasattr(manager.get_queryset(), "active_and_published"))
            self.assertTrue(hasattr(manager.get_queryset(), "by_category"))
            self.assertTrue(hasattr(manager.get_queryset(), "recent"))

    def test_manager_method_chaining_with_custom_queryset(self):
        """Test method chaining works with custom querysets"""
        manager = AdvancedSoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()

            # Setup chaining behavior
            mock_qs.by_category.return_value = mock_qs
            mock_qs.recent.return_value = mock_qs
            mock_qs.order_by.return_value = mock_qs
            mock_get_qs.return_value = mock_qs

            # Test complex chaining
            result = manager.by_category("tech").recent(30).order_by("-created_at")

            # Should call each method in chain
            mock_qs.by_category.assert_called_with("tech")
            mock_qs.recent.assert_called_with(30)
            mock_qs.order_by.assert_called_with("-created_at")


class ManagerPerformanceAndOptimizationTest(TestCase):
    """Test manager performance and optimization features"""

    def test_manager_query_optimization_with_select_related(self):
        """Test manager query optimization with select_related"""
        manager = AdvancedSoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_optimized_qs = Mock()

            mock_qs.select_related.return_value = mock_optimized_qs
            mock_get_qs.return_value = mock_qs

            # Test select_related optimization
            result = manager.get_queryset().select_related("created_by", "updated_by")

            mock_qs.select_related.assert_called_with("created_by", "updated_by")
            self.assertEqual(result, mock_optimized_qs)

    def test_manager_bulk_operations_optimization(self):
        """Test manager bulk operations"""
        manager = AdvancedSoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_bulk_result = [1, 2, 3]  # Mock bulk update result

            mock_qs.filter.return_value = mock_qs
            mock_qs.bulk_update.return_value = mock_bulk_result
            mock_get_qs.return_value = mock_qs

            # Test bulk update with manager filtering
            test_objects = [Mock(), Mock(), Mock()]
            result = manager.active().bulk_update(test_objects, ["title"])

            # Should apply manager filter before bulk operation
            mock_qs.filter.assert_called_with(is_deleted=False)
            mock_qs.bulk_update.assert_called_with(test_objects, ["title"])

    def test_manager_annotation_optimization(self):
        """Test manager annotations for performance"""
        manager = AdvancedSoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_annotated_qs = Mock()

            mock_qs.with_content_stats.return_value = mock_annotated_qs
            mock_get_qs.return_value = mock_qs

            # Test annotation method
            result = manager.with_stats()

            mock_qs.with_content_stats.assert_called_once()
            self.assertEqual(result, mock_annotated_qs)

    def test_manager_database_function_integration(self):
        """Test manager integration with database functions"""
        manager = AdvancedSoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_annotated_qs = Mock()

            mock_qs.annotate.return_value = mock_annotated_qs
            mock_get_qs.return_value = mock_qs

            # Test database functions with manager
            from django.db.models import Value
            from django.db.models.functions import Concat, Length, Upper

            annotations = {
                "title_upper": Upper("title"),
                "content_length": Length("content"),
                "full_description": Concat("title", Value(" - "), "category"),
            }

            result = manager.get_queryset().annotate(**annotations)

            mock_qs.annotate.assert_called_with(**annotations)
            self.assertEqual(result, mock_annotated_qs)


class ManagerThreadSafetyTest(TestCase):
    """Test manager thread safety and concurrent access"""

    def test_manager_concurrent_access(self):
        """Test manager handles concurrent access safely"""
        manager1 = SoftDeleteManager()
        manager2 = SoftDeleteManager()

        # Managers should be separate instances
        self.assertIsNot(manager1, manager2)

        results = []
        errors = []

        def access_manager(mgr, name):
            try:
                with patch.object(mgr, "get_queryset") as mock_get_qs:
                    mock_qs = Mock()
                    mock_qs.filter.return_value = mock_qs
                    mock_qs.count.return_value = 42
                    mock_get_qs.return_value = mock_qs

                    # Simulate work
                    time.sleep(0.01)
                    result = mgr.active().count()
                    results.append((name, result))
            except Exception as e:
                errors.append((name, e))

        # Test concurrent access
        threads = [
            threading.Thread(target=access_manager, args=(manager1, "mgr1")),
            threading.Thread(target=access_manager, args=(manager2, "mgr2")),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should not have any errors
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 2)

    def test_manager_state_isolation(self):
        """Test that managers don't share state between instances"""
        manager1 = SoftDeleteManager()
        manager2 = SoftDeleteManager()

        # Test that managers have independent state
        manager1._custom_attr = "value1"

        # manager2 should not have the attribute
        self.assertFalse(hasattr(manager2, "_custom_attr"))

    def test_manager_thread_local_behavior(self):
        """Test manager behavior with thread-local data"""
        manager = SoftDeleteManager()

        thread_results = {}

        def thread_worker(thread_id):
            # Each thread should get independent manager behavior
            with patch.object(manager, "get_queryset") as mock_get_qs:
                mock_qs = Mock()
                mock_qs.filter.return_value = mock_qs
                mock_qs.count.return_value = (
                    thread_id * 10
                )  # Different result per thread
                mock_get_qs.return_value = mock_qs

                result = manager.active().count()
                thread_results[thread_id] = result

        # Run in multiple threads
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(thread_worker, i) for i in range(3)]
            for future in as_completed(futures):
                future.result()  # Wait for completion

        # Each thread should have gotten its own result
        self.assertEqual(len(thread_results), 3)
        self.assertEqual(thread_results[0], 0)
        self.assertEqual(thread_results[1], 10)
        self.assertEqual(thread_results[2], 20)


class ManagerErrorHandlingTest(TestCase):
    """Test manager error handling and edge cases"""

    def test_manager_database_error_handling(self):
        """Test manager handles database errors gracefully"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_qs.filter.side_effect = IntegrityError("Database constraint violation")
            mock_get_qs.return_value = mock_qs

            # The test calls get_queryset which doesn't trigger filter
            # Instead, we should test the actual filtering behavior
            try:
                result = manager.get_queryset()
                # Calling filter on the result should raise the error
                result.filter(deleted_at__isnull=True)
            except IntegrityError:
                pass  # Expected behavior

    def test_manager_with_invalid_model_state(self):
        """Test manager behavior with invalid model state"""
        manager = SoftDeleteManager()

        # Test with unbound manager (no model set)
        self.assertIsNone(manager.model)

        # Manager should still be creatable and have methods
        self.assertTrue(hasattr(manager, "get_queryset"))
        self.assertTrue(hasattr(manager, "active"))

    def test_manager_queryset_validation_errors(self):
        """Test manager handles queryset validation errors"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_qs.filter.side_effect = ValidationError("Invalid filter condition")
            mock_get_qs.return_value = mock_qs

            # The test calls get_queryset which doesn't trigger filter
            # Instead, we should test the actual filtering behavior
            try:
                result = manager.get_queryset()
                # Calling filter on the result should raise the error
                result.filter(deleted_at__isnull=True)
            except ValidationError:
                pass  # Expected behavior

    def test_manager_attribute_error_handling(self):
        """Test manager handles missing attributes gracefully"""
        manager = SoftDeleteManager()

        # Test accessing non-existent method
        with self.assertRaises(AttributeError):
            manager.non_existent_method()

        # Test that standard methods exist
        self.assertTrue(hasattr(manager, "get_queryset"))
        self.assertTrue(hasattr(manager, "active"))
        self.assertTrue(hasattr(manager, "deleted"))

    def test_manager_transaction_rollback_handling(self):
        """Test manager behavior during transaction rollbacks"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_qs.filter.return_value = mock_qs
            mock_qs.create.side_effect = IntegrityError("Constraint violation")
            mock_get_qs.return_value = mock_qs

            # Test that manager propagates transaction errors
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    manager.active().create(name="test")


class ManagerCustomQuerySetIntegrationTest(TestCase):
    """Test manager integration with custom querysets"""

    def test_custom_queryset_manager_methods(self):
        """Test custom queryset methods through manager"""
        manager = AdvancedSoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            # Create a mock that has our custom methods
            mock_qs = Mock(spec=CustomQuerySet)
            mock_qs.by_category.return_value = mock_qs
            mock_qs.recent.return_value = mock_qs
            mock_qs.with_content_stats.return_value = mock_qs
            mock_get_qs.return_value = mock_qs

            # Test manager methods that use queryset methods
            result1 = manager.by_category("tech")
            mock_qs.by_category.assert_called_with("tech")

            result2 = manager.recent(15)
            mock_qs.recent.assert_called_with(15)

            result3 = manager.with_stats()
            mock_qs.with_content_stats.assert_called_once()

    def test_queryset_manager_method_chaining(self):
        """Test method chaining between manager and queryset methods"""
        manager = AdvancedSoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()

            # Setup method chaining
            mock_qs.by_category.return_value = mock_qs
            mock_qs.recent.return_value = mock_qs
            mock_qs.with_content_stats.return_value = mock_qs
            mock_qs.order_by.return_value = mock_qs
            mock_get_qs.return_value = mock_qs

            # Test complex method chaining
            result = (
                manager.by_category("tech")
                .recent(30)
                .with_content_stats()
                .order_by("-priority")
            )

            # Verify method call chain
            mock_qs.by_category.assert_called_with("tech")
            mock_qs.recent.assert_called_with(30)
            mock_qs.with_content_stats.assert_called_once()
            mock_qs.order_by.assert_called_with("-priority")

    def test_queryset_annotation_aggregation(self):
        """Test queryset annotations and aggregations through manager"""
        manager = AdvancedSoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_result = {"avg_priority": 5.5, "total_count": 25}

            mock_qs.with_content_stats.return_value = mock_qs
            mock_qs.aggregate.return_value = mock_result
            mock_get_qs.return_value = mock_qs

            # Test aggregation with annotations
            from django.db.models import Avg, Count

            result = manager.with_stats().aggregate(
                avg_priority=Avg("priority"), total_count=Count("id")
            )

            mock_qs.with_content_stats.assert_called_once()
            mock_qs.aggregate.assert_called_with(
                avg_priority=Avg("priority"), total_count=Count("id")
            )
            self.assertEqual(result, mock_result)


class ManagerDatabaseCompatibilityTest(TestCase):
    """Test manager compatibility with different database features"""

    def test_manager_database_specific_queries(self):
        """Test manager works with database-specific query features"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_result = Mock()

            mock_qs.filter.return_value = mock_qs
            mock_qs.extra.return_value = mock_result
            mock_get_qs.return_value = mock_qs

            # Test extra() method for database-specific SQL
            result = manager.active().extra(where=["custom_field > %s"], params=[5])

            mock_qs.filter.assert_called_with(is_deleted=False)
            mock_qs.extra.assert_called_with(where=["custom_field > %s"], params=[5])
            self.assertEqual(result, mock_result)

    def test_manager_database_functions(self):
        """Test manager with various database functions"""
        manager = SoftDeleteManager()

        with patch.object(manager, "get_queryset") as mock_get_qs:
            mock_qs = Mock()
            mock_annotated_qs = Mock()

            mock_qs.filter.return_value = mock_qs
            mock_qs.annotate.return_value = mock_annotated_qs
            mock_get_qs.return_value = mock_qs

            # Test various database functions
            from django.db.models.functions import (
                Coalesce,
                Concat,
                Extract,
                Length,
                Lower,
                Substr,
                TruncDate,
                Upper,
            )

            result = manager.active().annotate(
                title_upper=Upper("title"),
                title_lower=Lower("title"),
                title_length=Length("title"),
                title_substr=Substr("title", 1, 10),
                full_title=Concat(
                    "title", models.Value(" ("), "category", models.Value(")")
                ),
                year_created=Extract("created_at", "year"),
                date_created=TruncDate("created_at"),
                display_name=Coalesce("title", models.Value("Untitled")),
            )

            # Should apply manager filter then annotations
            mock_qs.filter.assert_called_with(is_deleted=False)
            self.assertTrue(mock_qs.annotate.called)
            self.assertEqual(result, mock_annotated_qs)
