"""Advanced feature flag tests for comprehensive coverage."""

import os
from unittest.mock import Mock, patch

import django

# Configure Django settings before any imports
from django.contrib.auth import get_user_model
from django.http import Http404, HttpRequest
from django.test import RequestFactory, TestCase
from django.views import View

from apps.featureflags.helpers import (
    FeatureFlags,
    get_feature_context,
    is_feature_enabled,
    require_feature_flag,
)

User = get_user_model()


class AdvancedFeatureFlagsTestCase(TestCase):
    """Advanced tests for FeatureFlags functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="testuser@example.com", password="testpass123"
        )

    def test_default_flags_configuration_completeness(self):
        """Test that all default flags have required configuration."""
        for flag_name, config in FeatureFlags.DEFAULT_FLAGS.items():
            with self.subTest(flag=flag_name):
                self.assertIsInstance(flag_name, str)
                self.assertIn("description", config)
                self.assertIn("default", config)
                self.assertIsInstance(config["description"], str)
                self.assertIsInstance(config["default"], bool)
                self.assertTrue(len(config["description"]) > 0)

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_is_enabled_with_request_active(self, mock_flag_is_active):
        """Test is_enabled returns True when waffle flag is active."""
        mock_flag_is_active.return_value = True
        request = self.factory.get("/")
        request.user = self.user

        result = FeatureFlags.is_enabled("FILES", request)

        self.assertTrue(result)
        mock_flag_is_active.assert_called_once_with(request, "FILES")

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_is_enabled_with_request_inactive(self, mock_flag_is_active):
        """Test is_enabled returns False when waffle flag is inactive."""
        mock_flag_is_active.return_value = False
        request = self.factory.get("/")
        request.user = self.user

        result = FeatureFlags.is_enabled("FILES", request)

        self.assertFalse(result)
        mock_flag_is_active.assert_called_once_with(request, "FILES")

    def test_is_enabled_without_request_uses_default(self):
        """Test is_enabled uses default value when no request provided."""
        # Test flag with default True
        result = FeatureFlags.is_enabled("EMAIL_EDITOR")
        self.assertTrue(result)  # EMAIL_EDITOR defaults to True

        # Test flag with default False
        result = FeatureFlags.is_enabled("FILES")
        self.assertFalse(result)  # FILES defaults to False

    def test_is_enabled_nonexistent_flag(self):
        """Test is_enabled with non-existent flag returns False."""
        result = FeatureFlags.is_enabled("NONEXISTENT_FLAG")
        self.assertFalse(result)

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_is_enabled_exception_handling(self, mock_flag_is_active):
        """Test is_enabled handles exceptions gracefully."""
        mock_flag_is_active.side_effect = Exception("Waffle error")
        request = self.factory.get("/")
        request.user = self.user

        # Should return default value when exception occurs
        result = FeatureFlags.is_enabled("EMAIL_EDITOR", request)
        self.assertTrue(result)  # Should fall back to default (True)

        result = FeatureFlags.is_enabled("FILES", request)
        self.assertFalse(result)  # Should fall back to default (False)

    @patch("apps.featureflags.helpers.switch_is_active")
    def test_is_switch_active_true(self, mock_switch_is_active):
        """Test is_switch_active returns True when switch is active."""
        mock_switch_is_active.return_value = True

        result = FeatureFlags.is_switch_active("TEST_SWITCH")

        self.assertTrue(result)
        mock_switch_is_active.assert_called_once_with("TEST_SWITCH")

    @patch("apps.featureflags.helpers.switch_is_active")
    def test_is_switch_active_false(self, mock_switch_is_active):
        """Test is_switch_active returns False when switch is inactive."""
        mock_switch_is_active.return_value = False

        result = FeatureFlags.is_switch_active("TEST_SWITCH")

        self.assertFalse(result)
        mock_switch_is_active.assert_called_once_with("TEST_SWITCH")

    @patch("apps.featureflags.helpers.switch_is_active")
    def test_is_switch_active_exception_handling(self, mock_switch_is_active):
        """Test is_switch_active handles exceptions gracefully."""
        mock_switch_is_active.side_effect = Exception("Switch error")

        result = FeatureFlags.is_switch_active("TEST_SWITCH")

        self.assertFalse(result)

    @patch("apps.featureflags.helpers.sample_is_active")
    def test_is_sample_active_true(self, mock_sample_is_active):
        """Test is_sample_active returns True when sample is active."""
        mock_sample_is_active.return_value = True

        result = FeatureFlags.is_sample_active("TEST_SAMPLE")

        self.assertTrue(result)
        mock_sample_is_active.assert_called_once_with("TEST_SAMPLE")

    @patch("apps.featureflags.helpers.sample_is_active")
    def test_is_sample_active_false(self, mock_sample_is_active):
        """Test is_sample_active returns False when sample is inactive."""
        mock_sample_is_active.return_value = False

        result = FeatureFlags.is_sample_active("TEST_SAMPLE")

        self.assertFalse(result)
        mock_sample_is_active.assert_called_once_with("TEST_SAMPLE")

    @patch("apps.featureflags.helpers.sample_is_active")
    def test_is_sample_active_exception_handling(self, mock_sample_is_active):
        """Test is_sample_active handles exceptions gracefully."""
        mock_sample_is_active.side_effect = Exception("Sample error")

        result = FeatureFlags.is_sample_active("TEST_SAMPLE")

        self.assertFalse(result)

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_get_enabled_flags_with_request(self, mock_flag_is_active):
        """Test get_enabled_flags with request object."""

        # Mock different flag states
        def flag_side_effect(request, flag_name):
            return flag_name in ["EMAIL_EDITOR", "API_V2"]

        mock_flag_is_active.side_effect = flag_side_effect
        request = self.factory.get("/")
        request.user = self.user

        result = FeatureFlags.get_enabled_flags(request)

        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), len(FeatureFlags.DEFAULT_FLAGS))
        self.assertTrue(result["EMAIL_EDITOR"])
        self.assertTrue(result["API_V2"])
        self.assertFalse(result["FILES"])

    def test_get_enabled_flags_without_request(self):
        """Test get_enabled_flags without request uses defaults."""
        result = FeatureFlags.get_enabled_flags()

        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), len(FeatureFlags.DEFAULT_FLAGS))

        # Should match default values
        for flag_name, config in FeatureFlags.DEFAULT_FLAGS.items():
            self.assertEqual(result[flag_name], config["default"])

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_get_flag_status_with_request(self, mock_flag_is_active):
        """Test get_flag_status with request object."""
        mock_flag_is_active.return_value = True
        request = self.factory.get("/")
        request.user = self.user

        result = FeatureFlags.get_flag_status("FILES", request)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], "FILES")
        self.assertTrue(result["enabled"])
        self.assertIn("description", result)
        self.assertIn("default", result)
        self.assertEqual(
            result["description"], FeatureFlags.DEFAULT_FLAGS["FILES"]["description"]
        )
        self.assertEqual(
            result["default"], FeatureFlags.DEFAULT_FLAGS["FILES"]["default"]
        )

    def test_get_flag_status_nonexistent_flag(self):
        """Test get_flag_status with non-existent flag."""
        result = FeatureFlags.get_flag_status("NONEXISTENT_FLAG")

        self.assertEqual(result["name"], "NONEXISTENT_FLAG")
        self.assertFalse(result["enabled"])
        self.assertEqual(result["description"], "No description available")
        self.assertFalse(result["default"])

    def test_convenience_function_is_feature_enabled(self):
        """Test convenience function is_feature_enabled."""
        result = is_feature_enabled("EMAIL_EDITOR")
        self.assertTrue(result)  # EMAIL_EDITOR defaults to True

        result = is_feature_enabled("FILES")
        self.assertFalse(result)  # FILES defaults to False

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_convenience_function_with_request(self, mock_flag_is_active):
        """Test convenience function with request object."""
        mock_flag_is_active.return_value = True
        request = self.factory.get("/")
        request.user = self.user

        result = is_feature_enabled("FILES", request)
        self.assertTrue(result)

    def test_get_feature_context_without_request(self):
        """Test get_feature_context without request."""
        result = get_feature_context()

        self.assertIn("features", result)
        self.assertIn("feature_flags", result)
        self.assertEqual(result["feature_flags"], FeatureFlags)
        self.assertIsInstance(result["features"], dict)

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_get_feature_context_with_request(self, mock_flag_is_active):
        """Test get_feature_context with request object."""
        mock_flag_is_active.return_value = True
        request = self.factory.get("/")
        request.user = self.user

        result = get_feature_context(request, self.user)

        self.assertIn("features", result)
        self.assertIn("feature_flags", result)
        self.assertIsInstance(result["features"], dict)


class FeatureFlagDecoratorTestCase(TestCase):
    """Test feature flag decorators."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="testuser@example.com", password="testpass123"
        )

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_require_feature_flag_function_decorator_enabled(self, mock_flag_is_active):
        """Test require_feature_flag decorator on function when flag is enabled."""
        mock_flag_is_active.return_value = True

        @require_feature_flag("FILES")
        def test_view(request):
            return "Success"

        request = self.factory.get("/")
        request.user = self.user

        result = test_view(request)
        self.assertEqual(result, "Success")

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_require_feature_flag_function_decorator_disabled(
        self, mock_flag_is_active
    ):
        """Test require_feature_flag decorator on function when flag is disabled."""
        mock_flag_is_active.return_value = False

        @require_feature_flag("FILES")
        def test_view(request):
            return "Success"

        request = self.factory.get("/")
        request.user = self.user

        with self.assertRaises(Http404):
            test_view(request)

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_require_feature_flag_class_decorator_enabled(self, mock_flag_is_active):
        """Test require_feature_flag decorator on class when flag is enabled."""
        mock_flag_is_active.return_value = True

        @require_feature_flag("FILES")
        class TestView(View):
            def get(self, request):
                return "Success"

        request = self.factory.get("/")
        request.user = self.user

        view = TestView()
        result = view.dispatch(request)
        self.assertEqual(result, "Success")

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_require_feature_flag_class_decorator_disabled(self, mock_flag_is_active):
        """Test require_feature_flag decorator on class when flag is disabled."""
        mock_flag_is_active.return_value = False

        @require_feature_flag("FILES")
        class TestView(View):
            def get(self, request):
                return "Success"

        request = self.factory.get("/")
        request.user = self.user

        view = TestView()
        with self.assertRaises(Http404):
            view.dispatch(request)

    def test_require_feature_flag_function_no_request(self):
        """Test require_feature_flag decorator on function without request."""

        @require_feature_flag("EMAIL_EDITOR")  # Default is True
        def test_view():
            return "Success"

        # Should succeed because EMAIL_EDITOR defaults to True
        result = test_view()
        self.assertEqual(result, "Success")

        @require_feature_flag("FILES")  # Default is False
        def test_view_disabled():
            return "Success"

        # Should fail because FILES defaults to False
        with self.assertRaises(Http404):
            test_view_disabled()

    def test_require_feature_flag_function_with_non_request_args(self):
        """Test require_feature_flag decorator handles non-request arguments."""

        @require_feature_flag("EMAIL_EDITOR")  # Default is True
        def test_view(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = test_view("a", "b", kwarg1="c")
        self.assertEqual(result, "a-b-c")

    @patch("apps.featureflags.helpers.flag_is_active")
    def test_require_feature_flag_detects_request_in_args(self, mock_flag_is_active):
        """Test require_feature_flag decorator detects request object in args."""
        mock_flag_is_active.return_value = True

        @require_feature_flag("FILES")
        def test_view(self, request, extra_arg):
            return f"Success-{extra_arg}"

        request = self.factory.get("/")
        request.user = self.user

        result = test_view("self_placeholder", request, "extra")
        self.assertEqual(result, "Success-extra")
        mock_flag_is_active.assert_called_once_with(request, "FILES")


class FeatureFlagEdgeCasesTestCase(TestCase):
    """Test edge cases and error conditions."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()

    def test_is_enabled_with_none_request(self):
        """Test is_enabled handles None request gracefully."""
        result = FeatureFlags.is_enabled("FILES", None)
        self.assertFalse(result)  # Should use default

    def test_is_enabled_with_invalid_request(self):
        """Test is_enabled handles invalid request object."""
        invalid_request = "not_a_request"

        # Should not crash and fall back to default
        result = FeatureFlags.is_enabled("FILES", invalid_request)
        self.assertFalse(result)

    def test_get_enabled_flags_with_none_user(self):
        """Test get_enabled_flags handles None user."""
        request = self.factory.get("/")
        request.user = None

        result = FeatureFlags.get_enabled_flags(request, None)
        self.assertIsInstance(result, dict)

    def test_get_flag_status_with_empty_string_flag(self):
        """Test get_flag_status handles empty string flag name."""
        result = FeatureFlags.get_flag_status("")

        self.assertEqual(result["name"], "")
        self.assertFalse(result["enabled"])
        self.assertEqual(result["description"], "No description available")

    def test_feature_context_consistency(self):
        """Test that feature context is consistent across calls."""
        context1 = get_feature_context()
        context2 = get_feature_context()

        # Should have same structure
        self.assertEqual(set(context1.keys()), set(context2.keys()))
        self.assertEqual(context1["feature_flags"], context2["feature_flags"])

    @patch("apps.featureflags.helpers.is_feature_enabled")
    def test_multiple_decorator_applications(self, mock_is_feature_enabled):
        """Test multiple feature flag decorators on same function."""
        mock_is_feature_enabled.return_value = True

        @require_feature_flag("FILES")
        @require_feature_flag("EMAIL_EDITOR")
        def test_view(request):
            return "Success"

        request = self.factory.get("/")
        # Both flags need to be enabled
        result = test_view(request)
        self.assertEqual(result, "Success")

        # Test with one flag disabled
        def flag_side_effect(flag_name, request):
            return flag_name != "FILES"  # FILES is disabled

        mock_is_feature_enabled.side_effect = flag_side_effect

        with self.assertRaises(Http404):
            test_view(request)

    def test_feature_flag_naming_conventions(self):
        """Test that feature flags follow naming conventions."""
        for flag_name in FeatureFlags.DEFAULT_FLAGS.keys():
            # Should be uppercase
            self.assertEqual(flag_name, flag_name.upper())
            # Should use underscores, not hyphens
            self.assertNotIn("-", flag_name)
            # Should not be empty
            self.assertTrue(len(flag_name) > 0)

    def test_all_flags_have_reasonable_defaults(self):
        """Test that all flags have reasonable default values."""
        # Most flags should default to False for safety
        false_defaults = sum(
            1 for config in FeatureFlags.DEFAULT_FLAGS.values() if not config["default"]
        )
        true_defaults = sum(
            1 for config in FeatureFlags.DEFAULT_FLAGS.values() if config["default"]
        )

        # Should have more False defaults than True (safety-first approach)
        self.assertGreaterEqual(false_defaults, true_defaults)
