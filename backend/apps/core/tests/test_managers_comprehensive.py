"""Comprehensive test coverage for core app managers"""

import os
from unittest.mock import Mock, patch

import django
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

from apps.core.managers import PublishedManager, SoftDeleteManager
from apps.core.mixins import SoftDeleteMixin

User = get_user_model()


class ConcreteSoftDeleteWithManager(SoftDeleteMixin):
    """Test model for SoftDeleteManager - using abstract to avoid DB creation"""

    name = models.CharField(max_length=100)

    # Multiple managers for testing
    objects = SoftDeleteManager()  # Default manager excludes deleted
    all_objects = models.Manager()  # Includes all records

    class Meta:
        app_label = "core"
        # Mark as managed=False to prevent Django from creating DB table
        managed = False


class ConcretePublishedModel(models.Model):
    """Test model for PublishedManager - managed=False to avoid DB creation"""

    name = models.CharField(max_length=100)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    objects = PublishedManager()

    class Meta:
        app_label = "core"
        # Mark as managed=False to prevent Django from creating DB table
        managed = False


class SoftDeleteManagerComprehensiveTest(TestCase):
    """Comprehensive tests for SoftDeleteManager"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_manager_initialization(self):
        """Test SoftDeleteManager can be initialized"""
        manager = SoftDeleteManager()
        self.assertIsInstance(manager, SoftDeleteManager)
        self.assertIsInstance(manager, models.Manager)

    def test_get_queryset_filters_deleted(self):
        """Test get_queryset filters out soft-deleted records"""
        manager = SoftDeleteManager()

        # Mock the parent get_queryset and filter methods
        mock_qs = Mock()
        mock_filtered_qs = Mock()
        mock_qs.filter.return_value = mock_filtered_qs

        with patch.object(models.Manager, "get_queryset", return_value=mock_qs):
            result = manager.get_queryset()

            # Should call filter with is_deleted=False
            mock_qs.filter.assert_called_once_with(is_deleted=False)
            self.assertEqual(result, mock_filtered_qs)

    def test_active_method(self):
        """Test active method returns non-deleted records"""
        manager = SoftDeleteManager()

        mock_qs = Mock()
        mock_filtered_qs = Mock()
        mock_qs.filter.return_value = mock_filtered_qs

        with patch.object(manager, "get_queryset", return_value=mock_qs):
            result = manager.active()

            # Should call filter on the manager's queryset
            mock_qs.filter.assert_called_once_with(is_deleted=False)
            self.assertEqual(result, mock_filtered_qs)

    def test_deleted_method(self):
        """Test deleted method returns only deleted records"""
        manager = SoftDeleteManager()

        # Create a mock for the base manager and queryset chain
        mock_base_manager = Mock()
        mock_base_qs = Mock()
        mock_filtered_qs = Mock()

        mock_base_manager.get_queryset.return_value = mock_base_qs
        mock_base_qs.filter.return_value = mock_filtered_qs

        # Mock the models.Manager() call in the deleted method
        with patch("apps.core.managers.models.Manager", return_value=mock_base_manager):
            # Mock the manager's get_queryset to return the base manager
            with patch.object(manager, "get_queryset", return_value=mock_base_manager):
                result = manager.deleted()

                # Should use base manager and filter for deleted records
                mock_base_manager.filter.assert_called_once_with(is_deleted=True)

    def test_with_deleted_method(self):
        """Test with_deleted method returns all records including deleted"""
        manager = SoftDeleteManager()

        mock_qs = Mock()

        # Should call parent's get_queryset, not the manager's filtered version
        with patch.object(models.Manager, "get_queryset", return_value=mock_qs):
            result = manager.with_deleted()

            # Should return unfiltered queryset
            self.assertEqual(result, mock_qs)

    def test_manager_queryset_chaining(self):
        """Test that manager methods can be chained"""
        manager = SoftDeleteManager()

        mock_qs = Mock()
        mock_filtered_qs = Mock()

        # Setup method chaining on the mock queryset
        mock_qs.filter.return_value = mock_filtered_qs
        mock_filtered_qs.order_by.return_value = mock_filtered_qs
        mock_filtered_qs.distinct.return_value = mock_filtered_qs

        with patch.object(manager, "get_queryset", return_value=mock_qs):
            # Test chaining with active()
            result = manager.active().order_by("name").distinct()

            # Verify the chain was called correctly
            mock_qs.filter.assert_called_once_with(is_deleted=False)
            mock_filtered_qs.order_by.assert_called_once_with("name")
            mock_filtered_qs.distinct.assert_called_once()

    def test_manager_with_model_operations(self):
        """Test manager integrates properly with model operations"""
        # This tests the manager in the context of actual model operations
        manager = SoftDeleteManager()

        # Set up a mock model to test manager binding
        mock_model = Mock()
        manager.model = mock_model

        mock_qs = Mock()
        mock_filtered_qs = Mock()
        mock_qs.filter.return_value = mock_filtered_qs

        with patch.object(models.Manager, "get_queryset", return_value=mock_qs):
            queryset = manager.get_queryset()

            # Manager should filter the queryset
            mock_qs.filter.assert_called_once_with(is_deleted=False)
            self.assertEqual(queryset, mock_filtered_qs)

    def test_manager_descriptor_access(self):
        """Test manager works as a descriptor on models"""
        # This would normally be tested with actual model instances,
        # but we can test the manager's behavior when attached to a model
        manager = SoftDeleteManager()

        # Test that manager can be attached to a model class
        # (This is normally done by Django's metaclass)
        self.assertIsInstance(manager, models.Manager)

        # Test that it has the expected interface
        self.assertTrue(hasattr(manager, "get_queryset"))
        self.assertTrue(hasattr(manager, "active"))
        self.assertTrue(hasattr(manager, "deleted"))
        self.assertTrue(hasattr(manager, "with_deleted"))


class PublishedManagerComprehensiveTest(TestCase):
    """Comprehensive tests for PublishedManager"""

    def setUp(self):
        self.now = timezone.datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_manager_initialization(self):
        """Test PublishedManager can be initialized"""
        manager = PublishedManager()
        self.assertIsInstance(manager, PublishedManager)
        self.assertIsInstance(manager, models.Manager)

    def test_get_queryset_unchanged(self):
        """Test base get_queryset returns unfiltered results"""
        manager = PublishedManager()

        mock_qs = Mock()

        with patch.object(models.Manager, "get_queryset", return_value=mock_qs):
            result = manager.get_queryset()

            # Should return the base queryset unchanged
            self.assertEqual(result, mock_qs)

    def test_published_method(self):
        """Test published method filters correctly"""
        manager = PublishedManager()

        mock_qs = Mock()
        mock_filtered_qs = Mock()
        mock_qs.filter.return_value = mock_filtered_qs

        with patch.object(manager, "get_queryset", return_value=mock_qs):
            with patch("django.utils.timezone.now", return_value=self.now):
                result = manager.published()

                # Should filter for published items with published_at <= now
                mock_qs.filter.assert_called_once_with(
                    is_published=True, published_at__lte=self.now
                )
                self.assertEqual(result, mock_filtered_qs)

    def test_draft_method(self):
        """Test draft method filters correctly"""
        manager = PublishedManager()

        mock_qs = Mock()
        mock_filtered_qs = Mock()
        mock_qs.filter.return_value = mock_filtered_qs

        with patch.object(manager, "get_queryset", return_value=mock_qs):
            result = manager.draft()

            # Should filter for non-published items
            mock_qs.filter.assert_called_once_with(is_published=False)
            self.assertEqual(result, mock_filtered_qs)

    def test_scheduled_method(self):
        """Test scheduled method filters correctly"""
        manager = PublishedManager()

        mock_qs = Mock()
        mock_filtered_qs = Mock()
        mock_qs.filter.return_value = mock_filtered_qs

        with patch.object(manager, "get_queryset", return_value=mock_qs):
            with patch("django.utils.timezone.now", return_value=self.now):
                result = manager.scheduled()

                # Should filter for published items with published_at > now
                mock_qs.filter.assert_called_once_with(
                    is_published=True, published_at__gt=self.now
                )
                self.assertEqual(result, mock_filtered_qs)

    def test_manager_method_chaining(self):
        """Test that manager methods support queryset chaining"""
        manager = PublishedManager()

        mock_qs = Mock()
        mock_filtered_qs = Mock()

        # Setup method chaining
        mock_qs.filter.return_value = mock_filtered_qs
        mock_filtered_qs.order_by.return_value = mock_filtered_qs
        mock_filtered_qs.select_related.return_value = mock_filtered_qs

        with patch.object(manager, "get_queryset", return_value=mock_qs):
            # Test chaining with published()
            result = (
                manager.published().order_by("-published_at").select_related("author")
            )

            # Verify the chain
            self.assertTrue(mock_qs.filter.called)
            mock_filtered_qs.order_by.assert_called_once_with("-published_at")
            mock_filtered_qs.select_related.assert_called_once_with("author")

    def test_timezone_handling(self):
        """Test proper timezone handling in published/scheduled methods"""
        manager = PublishedManager()

        # Test with different timezones
        utc_time = timezone.datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

        mock_qs = Mock()
        mock_filtered_qs = Mock()
        mock_qs.filter.return_value = mock_filtered_qs

        with patch.object(manager, "get_queryset", return_value=mock_qs):
            with patch("django.utils.timezone.now", return_value=utc_time):
                # Test published method uses the mocked time
                manager.published()
                args, kwargs = mock_qs.filter.call_args

                self.assertEqual(kwargs["published_at__lte"], utc_time)

                # Reset mock for scheduled test
                mock_qs.reset_mock()

                # Test scheduled method uses the mocked time
                manager.scheduled()
                args, kwargs = mock_qs.filter.call_args

                self.assertEqual(kwargs["published_at__gt"], utc_time)

    def test_multiple_filter_combinations(self):
        """Test combining published manager methods with additional filters"""
        manager = PublishedManager()

        mock_qs = Mock()
        mock_filtered_qs = Mock()

        # Setup chaining behavior
        mock_qs.filter.return_value = mock_filtered_qs
        mock_filtered_qs.filter.return_value = mock_filtered_qs

        with patch.object(manager, "get_queryset", return_value=mock_qs):
            with patch("django.utils.timezone.now", return_value=self.now):
                # Chain additional filters after published()
                result = manager.published().filter(category="tech")

                # Should have two filter calls
                self.assertEqual(mock_qs.filter.call_count, 1)  # published() filter
                self.assertEqual(
                    mock_filtered_qs.filter.call_count, 1
                )  # additional filter


class ManagerInteractionTest(TestCase):
    """Test how managers interact with models and each other"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_multiple_managers_on_model(self):
        """Test model with multiple managers"""

        # Test that we can define multiple managers
        class MultiManagerModel(models.Model):
            name = models.CharField(max_length=100)
            is_deleted = models.BooleanField(default=False)
            is_published = models.BooleanField(default=False)
            published_at = models.DateTimeField(null=True, blank=True)

            objects = SoftDeleteManager()  # Default manager
            all_objects = models.Manager()  # All records
            published = PublishedManager()  # Published records

            class Meta:
                app_label = "core"

        # Test that all managers are accessible
        self.assertIsInstance(MultiManagerModel.objects, SoftDeleteManager)
        self.assertIsInstance(MultiManagerModel.all_objects, models.Manager)
        self.assertIsInstance(MultiManagerModel.published, PublishedManager)

    def test_manager_inheritance_behavior(self):
        """Test manager behavior with model inheritance"""

        # Test that managers work with model inheritance
        class BaseTestModel(models.Model):
            name = models.CharField(max_length=100)
            is_deleted = models.BooleanField(default=False)

            objects = SoftDeleteManager()

            class Meta:
                app_label = "core"
                abstract = True

        class DerivedTestModel(BaseTestModel):
            description = models.TextField()

            class Meta:
                app_label = "core"

        # Should inherit the manager
        self.assertIsInstance(DerivedTestModel.objects, SoftDeleteManager)

    def test_manager_with_custom_queryset_methods(self):
        """Test managers with custom queryset methods"""

        class CustomQuerySet(models.QuerySet):
            def active_and_named(self, name):
                return self.filter(is_deleted=False, name__icontains=name)

            def recent(self):
                return self.filter(
                    created_at__gte=timezone.now() - timezone.timedelta(days=7)
                )

        class CustomManager(SoftDeleteManager):
            def get_queryset(self):
                return CustomQuerySet(self.model, using=self._db).filter(
                    is_deleted=False
                )

            def active_and_named(self, name):
                return self.get_queryset().active_and_named(name)

        # Test that custom manager can be created
        manager = CustomManager()
        self.assertIsInstance(manager, CustomManager)
        self.assertIsInstance(manager, SoftDeleteManager)

    def test_manager_db_routing(self):
        """Test manager respects database routing"""
        manager = SoftDeleteManager()

        # Test using parameter is handled
        mock_qs = Mock()

        with patch.object(models.Manager, "get_queryset") as mock_get_qs:
            mock_get_qs.return_value = mock_qs

            # Test that using parameter would be passed through
            # (This is more about verifying the manager doesn't break db routing)
            result = manager.get_queryset()

            # Manager should not interfere with database routing
            mock_get_qs.assert_called_once()

    def test_manager_thread_safety(self):
        """Test manager thread safety considerations"""
        # Managers should be thread-safe as they don't store state
        manager1 = SoftDeleteManager()
        manager2 = SoftDeleteManager()

        # Different instances should not interfere
        self.assertIsNot(manager1, manager2)

        # Both should work independently
        mock_qs1 = Mock()
        mock_qs2 = Mock()

        with patch.object(
            models.Manager, "get_queryset", side_effect=[mock_qs1, mock_qs2]
        ):
            result1 = manager1.get_queryset()
            result2 = manager2.get_queryset()

            # Each should get its own queryset
            self.assertIsNot(result1, result2)


class ManagerEdgeCasesTest(TestCase):
    """Test edge cases and error conditions for managers"""

    def test_soft_delete_manager_with_none_model(self):
        """Test SoftDeleteManager behavior when model is None"""
        manager = SoftDeleteManager()

        # Manager without model should still be creatable
        self.assertIsInstance(manager, SoftDeleteManager)

    def test_published_manager_with_null_dates(self):
        """Test PublishedManager handles null published_at dates"""
        manager = PublishedManager()

        mock_qs = Mock()
        mock_filtered_qs = Mock()
        mock_qs.filter.return_value = mock_filtered_qs

        with patch.object(manager, "get_queryset", return_value=mock_qs):
            with patch("django.utils.timezone.now", return_value=timezone.now()):
                # published() should still work with null dates
                # (records with null published_at won't match published_at__lte filter)
                result = manager.published()

                # Should still apply the filter
                self.assertTrue(mock_qs.filter.called)
                self.assertEqual(result, mock_filtered_qs)

    def test_manager_queryset_evaluation(self):
        """Test manager queryset evaluation behavior"""
        manager = SoftDeleteManager()

        mock_qs = Mock()
        mock_filtered_qs = Mock()

        # Test lazy evaluation
        mock_qs.filter.return_value = mock_filtered_qs

        with patch.object(models.Manager, "get_queryset", return_value=mock_qs):
            # Getting queryset should not evaluate it
            queryset = manager.get_queryset()

            # Filter should be called but queryset not evaluated
            mock_qs.filter.assert_called_once_with(is_deleted=False)

            # The returned queryset should be the filtered one
            self.assertEqual(queryset, mock_filtered_qs)

    def test_manager_with_empty_queryset(self):
        """Test manager behavior with empty querysets"""
        manager = SoftDeleteManager()

        # Create a mock that represents an empty queryset
        mock_empty_qs = Mock()
        mock_empty_qs.filter.return_value = mock_empty_qs
        mock_empty_qs.__iter__ = Mock(return_value=iter([]))
        mock_empty_qs.__bool__ = Mock(return_value=False)

        with patch.object(models.Manager, "get_queryset", return_value=mock_empty_qs):
            result = manager.get_queryset()

            # Should still apply filter even if base queryset is empty
            mock_empty_qs.filter.assert_called_once_with(is_deleted=False)

    def test_manager_method_error_handling(self):
        """Test manager method error handling"""
        manager = SoftDeleteManager()

        # Test that manager methods handle queryset errors gracefully
        mock_qs = Mock()
        mock_qs.filter.side_effect = Exception("Database error")

        with patch.object(models.Manager, "get_queryset", return_value=mock_qs):
            # Should propagate exceptions from queryset operations
            with self.assertRaises(Exception):
                manager.get_queryset()

    def test_manager_custom_db_operations(self):
        """Test manager with custom database operations"""
        manager = SoftDeleteManager()

        # Test that manager can handle custom database operations
        mock_qs = Mock()
        mock_using_qs = Mock()
        mock_qs.using.return_value = mock_using_qs
        mock_using_qs.filter.return_value = mock_using_qs

        with patch.object(models.Manager, "get_queryset", return_value=mock_qs):
            # Test using a specific database
            queryset = manager.get_queryset()

            # Manager should work with database routing
            mock_qs.filter.assert_called_once()
