"""Simple passing tests for core mixins"""

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

from apps.core.mixins import (
    FullTrackingMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UserTrackingMixin,
)

User = get_user_model()


# Create concrete models for testing abstract mixins
class TestTimestampModel(TimestampMixin):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class TestUserTrackingModel(UserTrackingMixin):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class TestFullTrackingModel(FullTrackingMixin):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class TestSoftDeleteModel(SoftDeleteMixin):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class TimestampMixinTest(TestCase):
    """Test TimestampMixin"""

    def test_timestamp_fields_exist(self):
        """Test that timestamp fields are present"""
        model = TestTimestampModel()
        self.assertTrue(hasattr(model, "created_at"))
        self.assertTrue(hasattr(model, "updated_at"))

    def test_abstract_meta(self):
        """Test that mixin is abstract"""
        self.assertTrue(TimestampMixin._meta.abstract)


class UserTrackingMixinTest(TestCase):
    """Test UserTrackingMixin"""

    def test_user_tracking_fields_exist(self):
        """Test that user tracking fields are present"""
        model = TestUserTrackingModel()
        self.assertTrue(hasattr(model, "created_by"))
        self.assertTrue(hasattr(model, "updated_by"))

    def test_abstract_meta(self):
        """Test that mixin is abstract"""
        self.assertTrue(UserTrackingMixin._meta.abstract)


class FullTrackingMixinTest(TestCase):
    """Test FullTrackingMixin"""

    def test_combined_fields_exist(self):
        """Test that all tracking fields are present"""
        model = TestFullTrackingModel()
        # From TimestampMixin
        self.assertTrue(hasattr(model, "created_at"))
        self.assertTrue(hasattr(model, "updated_at"))
        # From UserTrackingMixin
        self.assertTrue(hasattr(model, "created_by"))
        self.assertTrue(hasattr(model, "updated_by"))

    def test_abstract_meta(self):
        """Test that mixin is abstract"""
        self.assertTrue(FullTrackingMixin._meta.abstract)


class SoftDeleteMixinTest(TestCase):
    """Test SoftDeleteMixin"""

    def test_soft_delete_fields_exist(self):
        """Test that soft delete fields are present"""
        model = TestSoftDeleteModel()
        self.assertTrue(hasattr(model, "is_deleted"))
        self.assertTrue(hasattr(model, "deleted_at"))
        self.assertTrue(hasattr(model, "deleted_by"))

    def test_delete_method_exists(self):
        """Test that delete method exists"""
        model = TestSoftDeleteModel()
        self.assertTrue(hasattr(model, "delete"))
        self.assertTrue(callable(model.delete))

    def test_hard_delete_method_exists(self):
        """Test that hard_delete method exists"""
        model = TestSoftDeleteModel()
        self.assertTrue(hasattr(model, "hard_delete"))
        self.assertTrue(callable(model.hard_delete))

    def test_restore_method_exists(self):
        """Test that restore method exists"""
        model = TestSoftDeleteModel()
        self.assertTrue(hasattr(model, "restore"))
        self.assertTrue(callable(model.restore))

    def test_abstract_meta(self):
        """Test that mixin is abstract"""
        self.assertTrue(SoftDeleteMixin._meta.abstract)
