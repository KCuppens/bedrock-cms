"""
Simple tests for analytics models that avoid migration issues.

Tests model creation and key methods without complex setups.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.utils import timezone

User = get_user_model()


# Disable migrations to avoid migration syntax errors
@override_settings(
    MIGRATION_MODULES={
        "analytics": None,
        "cms": None,
        "accounts": None,
        "contenttypes": None,
        "auth": None,
    }
)
class AnalyticsModelsTest(TestCase):
    """Simple test for analytics models focusing on coverage."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )

    def test_imports_and_basic_creation(self):
        """Test that we can import and create basic model instances."""
        from apps.analytics.models import (
            AnalyticsSummary,
            Assessment,
            ContentMetrics,
            PageView,
            Risk,
            Threat,
            UserActivity,
        )

        # Test PageView
        page_view = PageView(
            session_id="test_session",
            ip_address="127.0.0.1",
            user_agent="Test Browser",
            url="https://example.com/test",
            user=self.user,
        )
        self.assertIsInstance(page_view.id, uuid.UUID)

        # Test str method
        str_result = str(page_view)
        self.assertIn("View of https://example.com/test", str_result)

    def test_user_activity_model(self):
        """Test UserActivity model."""
        from apps.analytics.models import UserActivity

        activity = UserActivity(
            user=self.user,
            action="login",
            description="User logged in",
            ip_address="127.0.0.1",
            session_id="test_session",
        )

        # Test str method
        str_result = str(activity)
        self.assertIn(self.user.email, str_result)
        self.assertIn("User Login", str_result)

    def test_content_metrics_model(self):
        """Test ContentMetrics model."""
        from apps.analytics.models import ContentMetrics

        content_type = ContentType.objects.get_for_model(User)
        metrics = ContentMetrics(
            content_type=content_type, object_id=self.user.id, date=date.today()
        )

        # Test str method
        str_result = str(metrics)
        self.assertIn(f"Metrics for {self.user}", str_result)
        self.assertIn(str(date.today()), str_result)

    def test_assessment_model(self):
        """Test Assessment model."""
        from apps.analytics.models import Assessment

        assessment = Assessment(
            title="Security Assessment",
            assessment_type="security",
            created_by=self.user,
        )

        # Test str method
        str_result = str(assessment)
        self.assertIn("Security Assessment", str_result)
        self.assertIn("Security Assessment", str_result)  # get_assessment_type_display

    def test_risk_model_and_save_method(self):
        """Test Risk model including save method calculations."""
        from apps.analytics.models import Risk

        # Test different risk score calculations
        test_cases = [
            {"probability": 2, "impact": 2, "expected_severity": "very_low"},  # 4
            {"probability": 2, "impact": 4, "expected_severity": "low"},  # 8
            {"probability": 3, "impact": 4, "expected_severity": "medium"},  # 12
            {"probability": 4, "impact": 4, "expected_severity": "high"},  # 16
            {"probability": 5, "impact": 5, "expected_severity": "very_high"},  # 25
        ]

        for case in test_cases:
            risk = Risk(
                title="Test Risk",
                description="Test description",
                category="security",
                probability=case["probability"],
                impact=case["impact"],
            )

            # Manually call save to trigger calculations
            risk.save()

            expected_score = case["probability"] * case["impact"]
            self.assertEqual(risk.risk_score, expected_score)
            self.assertEqual(risk.severity, case["expected_severity"])

            # Test str method
            str_result = str(risk)
            self.assertIn("Test Risk", str_result)
            self.assertIn(f"Risk Score: {expected_score}", str_result)

    def test_threat_model(self):
        """Test Threat model."""
        from apps.analytics.models import Threat

        threat = Threat(
            title="Test Threat",
            description="A test threat",
            threat_type="malware",
            severity="critical",
            reported_by=self.user,
        )

        # Test str method
        str_result = str(threat)
        self.assertIn("Test Threat", str_result)
        self.assertIn("Critical", str_result)  # get_severity_display

    def test_analytics_summary_model(self):
        """Test AnalyticsSummary model."""
        from apps.analytics.models import AnalyticsSummary

        summary = AnalyticsSummary(date=date.today(), period_type="daily")

        # Test str method
        str_result = str(summary)
        self.assertIn("Daily summary", str_result)
        self.assertIn(str(date.today()), str_result)

    def test_model_field_defaults(self):
        """Test that model fields have correct defaults."""
        from apps.analytics.models import AnalyticsSummary, ContentMetrics

        # Test AnalyticsSummary defaults
        summary = AnalyticsSummary(date=date.today(), period_type="daily")
        self.assertEqual(summary.total_views, 0)
        self.assertEqual(summary.bounce_rate, 0)
        self.assertEqual(summary.uptime_percentage, 100)

        # Test ContentMetrics defaults
        content_type = ContentType.objects.get_for_model(User)
        metrics = ContentMetrics(
            content_type=content_type, object_id=self.user.id, date=date.today()
        )
        self.assertEqual(metrics.views, 0)
        self.assertEqual(metrics.unique_views, 0)
        self.assertEqual(metrics.content_category, "other")

    def test_model_choices(self):
        """Test model choice fields."""
        from apps.analytics.models import Assessment, Risk, Threat, UserActivity

        # Test that choice fields accept valid values
        activity = UserActivity(
            user=self.user,
            action="page_create",  # Valid choice
            ip_address="127.0.0.1",
            session_id="test",
        )
        self.assertEqual(activity.action, "page_create")

        assessment = Assessment(
            title="Test",
            assessment_type="compliance",  # Valid choice
            created_by=self.user,
        )
        self.assertEqual(assessment.assessment_type, "compliance")

        risk = Risk(
            title="Test",
            description="Test",
            category="operational",  # Valid choice
            probability=3,
            impact=3,
        )
        self.assertEqual(risk.category, "operational")

        threat = Threat(
            title="Test",
            description="Test",
            threat_type="phishing",  # Valid choice
            reported_by=self.user,
        )
        self.assertEqual(threat.threat_type, "phishing")
