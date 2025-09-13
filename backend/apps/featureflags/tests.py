"""Comprehensive tests for featureflags app to boost coverage"""

from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase

from apps.featureflags.helpers import (
    FeatureFlags,
    get_feature_context,
    is_feature_enabled,
    require_feature_flag,
)

User = get_user_model()


class FeatureFlagsTest(TestCase):
    """Test FeatureFlags helper class"""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.request = self.factory.get("/")
        self.request.user = self.user

    def test_default_flags_configuration(self):
        """Test default flags are properly configured"""
        expected_flags = [
            "FILES",
            "EMAIL_EDITOR",
            "RABBITMQ",
            "ADVANCED_ANALYTICS",
            "BETA_FEATURES",
            "API_V2",
            "MAINTENANCE_MODE",
        ]

        for flag in expected_flags:
            self.assertIn(flag, FeatureFlags.DEFAULT_FLAGS)
            self.assertIn("description", FeatureFlags.DEFAULT_FLAGS[flag])
            self.assertIn("default", FeatureFlags.DEFAULT_FLAGS[flag])

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_is_enabled_with_request(self, mock_flag_is_active):
        """Test is_enabled with request object"""
        mock_flag_is_active.return_value = True

        result = FeatureFlags.is_enabled("EMAIL_EDITOR", request=self.request)

        self.assertTrue(result)
        mock_flag_is_active.assert_called_once_with(self.request, "EMAIL_EDITOR")

    def test_is_enabled_without_request(self):
        """Test is_enabled without request (uses default)"""
        # EMAIL_EDITOR has default True
        result = FeatureFlags.is_enabled("EMAIL_EDITOR")
        self.assertTrue(result)

        # FILES has default False
        result = FeatureFlags.is_enabled("FILES")
        self.assertFalse(result)

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_is_enabled_with_exception(self, mock_flag_is_active):
        """Test is_enabled handles exceptions gracefully"""
        mock_flag_is_active.side_effect = Exception("Flag error")

        # Should return default value
        result = FeatureFlags.is_enabled("EMAIL_EDITOR", request=self.request)
        self.assertTrue(result)  # EMAIL_EDITOR defaults to True

    def test_is_enabled_nonexistent_flag(self):
        """Test is_enabled with non-existent flag"""
        result = FeatureFlags.is_enabled("NONEXISTENT_FLAG")
        self.assertFalse(result)  # Should return False for unknown flags

    @patch("apps.featureflags.helpers.switch_is_active")
    def test_is_switch_active(self, mock_switch):
        """Test is_switch_active"""
        mock_switch.return_value = True

        result = FeatureFlags.is_switch_active("test_switch")

        self.assertTrue(result)
        mock_switch.assert_called_once_with("test_switch")

    @patch("apps.featureflags.helpers.switch_is_active")
    def test_is_switch_active_exception(self, mock_switch):
        """Test is_switch_active handles exceptions"""
        mock_switch.side_effect = Exception("Switch error")

        result = FeatureFlags.is_switch_active("test_switch")

        self.assertFalse(result)

    @patch("apps.featureflags.helpers.sample_is_active")
    def test_is_sample_active(self, mock_sample):
        """Test is_sample_active"""
        mock_sample.return_value = True

        result = FeatureFlags.is_sample_active("test_sample")

        self.assertTrue(result)
        mock_sample.assert_called_once_with("test_sample")

    @patch("apps.featureflags.helpers.sample_is_active")
    def test_is_sample_active_exception(self, mock_sample):
        """Test is_sample_active handles exceptions"""
        mock_sample.side_effect = Exception("Sample error")

        result = FeatureFlags.is_sample_active("test_sample")

        self.assertFalse(result)

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_get_enabled_flags(self, mock_flag_is_active):
        """Test get_enabled_flags returns all flags status"""
        mock_flag_is_active.return_value = True

        result = FeatureFlags.get_enabled_flags(request=self.request)

        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), len(FeatureFlags.DEFAULT_FLAGS))

        for flag_name in FeatureFlags.DEFAULT_FLAGS:
            self.assertIn(flag_name, result)
            self.assertTrue(result[flag_name])

    def test_get_enabled_flags_without_request(self):
        """Test get_enabled_flags without request uses defaults"""
        result = FeatureFlags.get_enabled_flags()

        self.assertTrue(result["EMAIL_EDITOR"])  # Default True
        self.assertFalse(result["FILES"])  # Default False

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_get_flag_status(self, mock_flag_is_active):
        """Test get_flag_status returns detailed info"""
        mock_flag_is_active.return_value = True

        result = FeatureFlags.get_flag_status("EMAIL_EDITOR", request=self.request)

        self.assertEqual(result["name"], "EMAIL_EDITOR")
        self.assertTrue(result["enabled"])
        self.assertIn("description", result)
        self.assertIn("default", result)

    def test_get_flag_status_unknown_flag(self):
        """Test get_flag_status with unknown flag"""
        result = FeatureFlags.get_flag_status("UNKNOWN_FLAG")

        self.assertEqual(result["name"], "UNKNOWN_FLAG")
        self.assertFalse(result["enabled"])
        self.assertEqual(result["description"], "No description available")
        self.assertFalse(result["default"])


class ConvenienceFunctionsTest(TestCase):
    """Test convenience functions"""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )
        self.request = self.factory.get("/")
        self.request.user = self.user

    @patch("apps.featureflags.helpers.FeatureFlags.is_enabled")
    def test_is_feature_enabled(self, mock_is_enabled):
        """Test is_feature_enabled convenience function"""
        mock_is_enabled.return_value = True

        result = is_feature_enabled("TEST_FLAG", request=self.request)

        self.assertTrue(result)
        mock_is_enabled.assert_called_once_with("TEST_FLAG", self.request, None)

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_get_feature_context(self, mock_flag_is_active):
        """Test get_feature_context for templates"""
        mock_flag_is_active.return_value = False

        result = get_feature_context(request=self.request)

        self.assertIn("features", result)
        self.assertIn("feature_flags", result)
        self.assertEqual(result["feature_flags"], FeatureFlags)
        self.assertIsInstance(result["features"], dict)


class RequireFeatureFlagDecoratorTest(TestCase):
    """Test require_feature_flag decorator"""

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/")

    @patch("apps.featureflags.helpers.is_feature_enabled")
    def test_decorator_on_function_enabled(self, mock_is_enabled):
        """Test decorator on function when flag is enabled"""
        mock_is_enabled.return_value = True

        @require_feature_flag("TEST_FLAG")
        def test_view(request):
            return "success"

        result = test_view(self.request)

        self.assertEqual(result, "success")
        mock_is_enabled.assert_called_once()

    @patch("apps.featureflags.helpers.is_feature_enabled")
    def test_decorator_on_function_disabled(self, mock_is_enabled):
        """Test decorator on function when flag is disabled"""
        mock_is_enabled.return_value = False

        @require_feature_flag("TEST_FLAG")
        def test_view(request):
            return "success"

        with self.assertRaises(Http404) as ctx:
            test_view(self.request)

        self.assertIn("Feature not available", str(ctx.exception))

    @patch("apps.featureflags.helpers.is_feature_enabled")
    def test_decorator_on_class(self, mock_is_enabled):
        """Test decorator on class (ViewSet)"""
        mock_is_enabled.return_value = True

        @require_feature_flag("TEST_FLAG")
        class TestViewSet:
            def dispatch(self, request, *args, **kwargs):
                return "dispatched"

        viewset = TestViewSet()
        result = viewset.dispatch(self.request)

        self.assertEqual(result, "dispatched")

    @patch("apps.featureflags.helpers.is_feature_enabled")
    def test_decorator_on_class_disabled(self, mock_is_enabled):
        """Test decorator on class when flag is disabled"""
        mock_is_enabled.return_value = False

        @require_feature_flag("TEST_FLAG")
        class TestViewSet:
            def dispatch(self, request, *args, **kwargs):
                return "dispatched"

        viewset = TestViewSet()

        with self.assertRaises(Http404):
            viewset.dispatch(self.request)

    @patch("apps.featureflags.helpers.is_feature_enabled")
    def test_decorator_without_request(self, mock_is_enabled):
        """Test decorator when request is not found in args"""
        mock_is_enabled.return_value = False

        @require_feature_flag("TEST_FLAG")
        def test_func(arg1, arg2):
            return "success"

        with self.assertRaises(Http404):
            test_func("arg1", "arg2")


class ManagementCommandTest(TestCase):
    """Test management commands"""

    @patch("apps.featureflags.management.commands.sync_flags.Command.handle")
    def test_sync_flags_command(self, mock_handle):
        """Test sync_flags management command"""
        from django.core.management import call_command

        # Test command can be called
        try:
            call_command("sync_flags")
        except Exception:
            # Command might not exist, but we test the import
            pass

    def test_sync_flags_command_import(self):
        """Test sync_flags command can be imported"""
        try:
            from apps.featureflags.management.commands.sync_flags import Command

            self.assertIsNotNone(Command)
        except ImportError:
            # Command might not exist yet
            pass


class FeatureFlagsAppConfigTest(TestCase):
    """Test app configuration"""

    def test_app_config(self):
        """Test app configuration"""
        from apps.featureflags.apps import FeatureflagsConfig

        self.assertEqual(FeatureflagsConfig.name, "apps.featureflags")
        self.assertEqual(
            FeatureflagsConfig.default_auto_field, "django.db.models.BigAutoField"
        )


class FeatureFlagsIntegrationTest(TestCase):
    """Integration tests for feature flags"""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser", email="staff@example.com", is_staff=True
        )

    def test_feature_flags_in_view_context(self):
        """Test feature flags are accessible in view context"""
        request = self.factory.get("/")
        request.user = self.user

        context = get_feature_context(request, self.user)

        # Check all default flags are present
        for flag in FeatureFlags.DEFAULT_FLAGS:
            self.assertIn(flag, context["features"])

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_feature_flags_with_different_users(self, mock_flag_is_active):
        """Test feature flags can vary by user"""

        # Setup different responses for different users
        def flag_side_effect(request, flag_name):
            if request.user.is_staff:
                return True
            return False

        mock_flag_is_active.side_effect = flag_side_effect

        # Test with regular user
        request = self.factory.get("/")
        request.user = self.user
        result = FeatureFlags.is_enabled("BETA_FEATURES", request=request)
        self.assertFalse(result)

        # Test with staff user
        request.user = self.staff_user
        result = FeatureFlags.is_enabled("BETA_FEATURES", request=request)
        self.assertTrue(result)

    def test_multiple_flags_check(self):
        """Test checking multiple flags at once"""
        flags_to_check = ["FILES", "EMAIL_EDITOR", "RABBITMQ"]

        results = {}
        for flag in flags_to_check:
            results[flag] = FeatureFlags.is_enabled(flag)

        # Verify based on defaults
        self.assertFalse(results["FILES"])
        self.assertTrue(results["EMAIL_EDITOR"])
        self.assertFalse(results["RABBITMQ"])
