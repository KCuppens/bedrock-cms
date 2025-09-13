"""
Test suite for analytics models.

Tests all models in the analytics app to achieve high coverage.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import (
    AnalyticsSummary,
    Assessment,
    ContentMetrics,
    PageView,
    Risk,
    Threat,
    UserActivity,
)

User = get_user_model()


class PageViewModelTest(TestCase):
    """Test cases for PageView model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_page_view_creation(self):
        """Test creating a PageView instance."""
        page_view = PageView.objects.create(
            session_id="test_session_123",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0 Test Browser",
            url="https://example.com/test",
            title="Test Page",
            user=self.user,
            device_type="desktop",
            browser="Chrome",
            os="Windows",
        )

        self.assertIsInstance(page_view.id, uuid.UUID)
        self.assertEqual(page_view.session_id, "test_session_123")
        self.assertEqual(page_view.ip_address, "127.0.0.1")
        self.assertEqual(page_view.device_type, "desktop")
        self.assertEqual(page_view.user, self.user)

    def test_page_view_str_method(self):
        """Test PageView __str__ method."""
        page_view = PageView.objects.create(
            session_id="test_session",
            ip_address="127.0.0.1",
            user_agent="Test Browser",
            url="https://example.com/test",
        )

        expected_str = f"View of https://example.com/test at {page_view.viewed_at}"
        self.assertEqual(str(page_view), expected_str)

    def test_page_view_optional_fields(self):
        """Test PageView with optional fields."""
        page_view = PageView.objects.create(
            session_id="test_session",
            ip_address="127.0.0.1",
            user_agent="Test Browser",
            url="https://example.com/test",
            referrer="https://google.com",
            load_time=250,
            time_on_page=30,
            country="US",
            city="New York",
        )

        self.assertEqual(page_view.referrer, "https://google.com")
        self.assertEqual(page_view.load_time, 250)
        self.assertEqual(page_view.time_on_page, 30)
        self.assertEqual(page_view.country, "US")
        self.assertEqual(page_view.city, "New York")


class UserActivityModelTest(TestCase):
    """Test cases for UserActivity model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_user_activity_creation(self):
        """Test creating a UserActivity instance."""
        activity = UserActivity.objects.create(
            user=self.user,
            action="login",
            description="User logged in",
            ip_address="127.0.0.1",
            user_agent="Test Browser",
            session_id="test_session",
            metadata={"source": "web"},
        )

        self.assertIsInstance(activity.id, uuid.UUID)
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.action, "login")
        self.assertEqual(activity.description, "User logged in")
        self.assertEqual(activity.metadata, {"source": "web"})

    def test_user_activity_str_method(self):
        """Test UserActivity __str__ method."""
        activity = UserActivity.objects.create(
            user=self.user,
            action="page_create",
            ip_address="127.0.0.1",
            session_id="test_session",
        )

        expected_str = f"{self.user.email} - Page Created at {activity.created_at}"
        self.assertEqual(str(activity), expected_str)

    def test_user_activity_with_content_object(self):
        """Test UserActivity with generic foreign key."""
        # Create a content type for testing
        content_type = ContentType.objects.get_for_model(User)

        activity = UserActivity.objects.create(
            user=self.user,
            action="other",
            ip_address="127.0.0.1",
            session_id="test_session",
            content_type=content_type,
            object_id=self.user.id,
        )

        self.assertEqual(activity.content_object, self.user)
        self.assertEqual(activity.content_type, content_type)
        self.assertEqual(activity.object_id, self.user.id)


class ContentMetricsModelTest(TestCase):
    """Test cases for ContentMetrics model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.content_type = ContentType.objects.get_for_model(User)

    def test_content_metrics_creation(self):
        """Test creating a ContentMetrics instance."""
        metrics = ContentMetrics.objects.create(
            content_type=self.content_type,
            object_id=self.user.id,
            date=date.today(),
            content_category="page",
            views=100,
            unique_views=75,
            avg_time_on_content=120,
            bounce_rate=Decimal("25.50"),
        )

        self.assertEqual(metrics.content_type, self.content_type)
        self.assertEqual(metrics.object_id, self.user.id)
        self.assertEqual(metrics.content_category, "page")
        self.assertEqual(metrics.views, 100)
        self.assertEqual(metrics.unique_views, 75)
        self.assertEqual(metrics.bounce_rate, Decimal("25.50"))

    def test_content_metrics_str_method(self):
        """Test ContentMetrics __str__ method."""
        metrics = ContentMetrics.objects.create(
            content_type=self.content_type,
            object_id=self.user.id,
            date=date.today(),
            content_category="page",
        )

        expected_str = f"Metrics for {self.user} on {date.today()}"
        self.assertEqual(str(metrics), expected_str)

    def test_content_metrics_engagement_fields(self):
        """Test ContentMetrics engagement fields."""
        metrics = ContentMetrics.objects.create(
            content_type=self.content_type,
            object_id=self.user.id,
            date=date.today(),
            shares=5,
            comments=10,
            downloads=2,
            search_impressions=500,
            search_clicks=25,
            avg_position=Decimal("3.5"),
        )

        self.assertEqual(metrics.shares, 5)
        self.assertEqual(metrics.comments, 10)
        self.assertEqual(metrics.downloads, 2)
        self.assertEqual(metrics.search_impressions, 500)
        self.assertEqual(metrics.search_clicks, 25)
        self.assertEqual(metrics.avg_position, Decimal("3.5"))


class AssessmentModelTest(TestCase):
    """Test cases for Assessment model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_assessment_creation(self):
        """Test creating an Assessment instance."""
        assessment = Assessment.objects.create(
            title="Security Assessment",
            description="Test security assessment",
            assessment_type="security",
            status="scheduled",
            created_by=self.user,
        )

        self.assertIsInstance(assessment.id, uuid.UUID)
        self.assertEqual(assessment.title, "Security Assessment")
        self.assertEqual(assessment.assessment_type, "security")
        self.assertEqual(assessment.status, "scheduled")
        self.assertEqual(assessment.created_by, self.user)

    def test_assessment_str_method(self):
        """Test Assessment __str__ method."""
        assessment = Assessment.objects.create(
            title="Test Assessment", assessment_type="compliance", created_by=self.user
        )

        expected_str = "Test Assessment (Compliance Audit)"
        self.assertEqual(str(assessment), expected_str)

    def test_assessment_with_optional_fields(self):
        """Test Assessment with optional fields."""
        assessment = Assessment.objects.create(
            title="Full Assessment",
            assessment_type="security",
            target_url="https://example.com",
            scope={"pages": ["home", "about"]},
            score=85,
            severity="medium",
            findings=["issue1", "issue2"],
            recommendations="Fix the issues",
            assigned_to=self.user,
            created_by=self.user,
            scheduled_for=timezone.now() + timedelta(days=1),
        )

        self.assertEqual(assessment.target_url, "https://example.com")
        self.assertEqual(assessment.scope, {"pages": ["home", "about"]})
        self.assertEqual(assessment.score, 85)
        self.assertEqual(assessment.severity, "medium")
        self.assertEqual(assessment.findings, ["issue1", "issue2"])
        self.assertEqual(assessment.assigned_to, self.user)


class RiskModelTest(TestCase):
    """Test cases for Risk model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.assessment = Assessment.objects.create(
            title="Test Assessment", assessment_type="security", created_by=self.user
        )

    def test_risk_creation_and_save_method(self):
        """Test creating a Risk instance and automatic calculations."""
        risk = Risk.objects.create(
            title="Test Risk",
            description="A test security risk",
            category="security",
            probability=3,
            impact=4,
            owner=self.user,
        )

        # Test automatic calculations in save method
        self.assertEqual(risk.risk_score, 12)  # 3 * 4
        self.assertEqual(risk.severity, "medium")  # 12 falls in medium range

    def test_risk_severity_calculations(self):
        """Test different severity calculations based on risk score."""
        # Test very_low (score <= 4)
        risk_low = Risk.objects.create(
            title="Low Risk",
            description="Low risk test",
            category="technical",
            probability=2,
            impact=2,
        )
        self.assertEqual(risk_low.severity, "very_low")

        # Test low (score <= 8)
        risk_low_med = Risk.objects.create(
            title="Low-Med Risk",
            description="Low-medium risk test",
            category="technical",
            probability=2,
            impact=4,
        )
        self.assertEqual(risk_low_med.severity, "low")

        # Test high (score <= 16)
        risk_high = Risk.objects.create(
            title="High Risk",
            description="High risk test",
            category="security",
            probability=4,
            impact=4,
        )
        self.assertEqual(risk_high.severity, "high")

        # Test very_high (score > 16)
        risk_very_high = Risk.objects.create(
            title="Very High Risk",
            description="Very high risk test",
            category="security",
            probability=5,
            impact=5,
        )
        self.assertEqual(risk_very_high.severity, "very_high")

    def test_risk_str_method(self):
        """Test Risk __str__ method."""
        risk = Risk.objects.create(
            title="Critical Risk",
            description="A critical security risk",
            category="security",
            probability=4,
            impact=5,
        )

        expected_str = f"Critical Risk (Risk Score: {risk.risk_score})"
        self.assertEqual(str(risk), expected_str)

    def test_risk_with_optional_fields(self):
        """Test Risk with all optional fields."""
        risk = Risk.objects.create(
            title="Complex Risk",
            description="A complex risk scenario",
            category="operational",
            probability=3,
            impact=4,
            mitigation_plan="Implement controls",
            mitigation_deadline=date.today() + timedelta(days=30),
            mitigation_cost=Decimal("5000.00"),
            owner=self.user,
            assigned_to=self.user,
            assessment=self.assessment,
        )

        self.assertEqual(risk.mitigation_plan, "Implement controls")
        self.assertEqual(risk.mitigation_cost, Decimal("5000.00"))
        self.assertEqual(risk.owner, self.user)
        self.assertEqual(risk.assigned_to, self.user)
        self.assertEqual(risk.assessment, self.assessment)


class ThreatModelTest(TestCase):
    """Test cases for Threat model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_threat_creation(self):
        """Test creating a Threat instance."""
        threat = Threat.objects.create(
            title="DDoS Attack",
            description="Distributed denial of service attack",
            threat_type="ddos",
            severity="high",
            reported_by=self.user,
        )

        self.assertIsInstance(threat.id, uuid.UUID)
        self.assertEqual(threat.title, "DDoS Attack")
        self.assertEqual(threat.threat_type, "ddos")
        self.assertEqual(threat.severity, "high")
        self.assertEqual(threat.status, "detected")  # default
        self.assertEqual(threat.reported_by, self.user)

    def test_threat_str_method(self):
        """Test Threat __str__ method."""
        threat = Threat.objects.create(
            title="Test Threat",
            description="A test threat",
            threat_type="malware",
            severity="critical",
            reported_by=self.user,
        )

        expected_str = "Test Threat (Critical)"
        self.assertEqual(str(threat), expected_str)

    def test_threat_with_detailed_fields(self):
        """Test Threat with detailed threat information."""
        threat = Threat.objects.create(
            title="Advanced Threat",
            description="Sophisticated attack",
            threat_type="phishing",
            severity="medium",
            source_ip="192.168.1.100",
            target_url="https://example.com/admin",
            attack_vector="Email phishing",
            indicators=["suspicious_email.pdf", "fake_domain.com"],
            affected_systems=["web_server", "database"],
            data_compromised=True,
            service_disrupted=False,
            estimated_damage=Decimal("10000.00"),
            response_actions="Blocked IP, informed users",
            lessons_learned="Need better email filtering",
            assigned_to=self.user,
            reported_by=self.user,
        )

        self.assertEqual(threat.source_ip, "192.168.1.100")
        self.assertEqual(threat.target_url, "https://example.com/admin")
        self.assertEqual(threat.attack_vector, "Email phishing")
        self.assertEqual(threat.indicators, ["suspicious_email.pdf", "fake_domain.com"])
        self.assertEqual(threat.affected_systems, ["web_server", "database"])
        self.assertTrue(threat.data_compromised)
        self.assertFalse(threat.service_disrupted)
        self.assertEqual(threat.estimated_damage, Decimal("10000.00"))


class AnalyticsSummaryModelTest(TestCase):
    """Test cases for AnalyticsSummary model."""

    def test_analytics_summary_creation(self):
        """Test creating an AnalyticsSummary instance."""
        summary = AnalyticsSummary.objects.create(
            date=date.today(),
            period_type="daily",
            total_views=1000,
            unique_visitors=750,
            returning_visitors=250,
            avg_session_duration=180,
            bounce_rate=Decimal("35.5"),
        )

        self.assertEqual(summary.date, date.today())
        self.assertEqual(summary.period_type, "daily")
        self.assertEqual(summary.total_views, 1000)
        self.assertEqual(summary.unique_visitors, 750)
        self.assertEqual(summary.bounce_rate, Decimal("35.5"))

    def test_analytics_summary_str_method(self):
        """Test AnalyticsSummary __str__ method."""
        summary = AnalyticsSummary.objects.create(
            date=date.today(), period_type="weekly"
        )

        expected_str = f"Weekly summary for {date.today()}"
        self.assertEqual(str(summary), expected_str)

    def test_analytics_summary_all_fields(self):
        """Test AnalyticsSummary with all fields populated."""
        summary = AnalyticsSummary.objects.create(
            date=date.today(),
            period_type="monthly",
            total_views=50000,
            unique_visitors=30000,
            returning_visitors=15000,
            avg_session_duration=240,
            bounce_rate=Decimal("42.5"),
            new_users=500,
            active_users=2000,
            user_actions=75000,
            pages_published=25,
            files_uploaded=100,
            content_updates=150,
            threats_detected=3,
            risks_identified=8,
            assessments_completed=2,
            avg_load_time=450,
            uptime_percentage=Decimal("99.8"),
        )

        # Test all fields are set correctly
        self.assertEqual(summary.total_views, 50000)
        self.assertEqual(summary.new_users, 500)
        self.assertEqual(summary.pages_published, 25)
        self.assertEqual(summary.threats_detected, 3)
        self.assertEqual(summary.avg_load_time, 450)
        self.assertEqual(summary.uptime_percentage, Decimal("99.8"))

    def test_analytics_summary_validation(self):
        """Test validation constraints on AnalyticsSummary fields."""
        # Test that we can create with valid bounce rate
        summary = AnalyticsSummary.objects.create(
            date=date.today(), period_type="daily", bounce_rate=Decimal("50.0")
        )
        self.assertEqual(summary.bounce_rate, Decimal("50.0"))

        # Test that we can create with valid uptime percentage
        summary2 = AnalyticsSummary.objects.create(
            date=date.today() - timedelta(days=1),
            period_type="daily",
            uptime_percentage=Decimal("95.5"),
        )
        self.assertEqual(summary2.uptime_percentage, Decimal("95.5"))


class AnalyticsModelsIntegrationTest(TestCase):
    """Integration tests across analytics models."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_assessment_risk_relationship(self):
        """Test the relationship between Assessment and Risk models."""
        assessment = Assessment.objects.create(
            title="Security Assessment",
            assessment_type="security",
            created_by=self.user,
        )

        risk = Risk.objects.create(
            title="SQL Injection Risk",
            description="Potential SQL injection vulnerability",
            category="security",
            probability=4,
            impact=5,
            assessment=assessment,
        )

        # Test relationship
        self.assertEqual(risk.assessment, assessment)
        self.assertIn(risk, assessment.risks.all())

    def test_model_ordering(self):
        """Test default ordering of models."""
        # Create multiple PageViews
        pv1 = PageView.objects.create(
            session_id="session1",
            ip_address="127.0.0.1",
            user_agent="Browser1",
            url="https://example.com/1",
        )
        pv2 = PageView.objects.create(
            session_id="session2",
            ip_address="127.0.0.1",
            user_agent="Browser2",
            url="https://example.com/2",
        )

        # Should be ordered by -viewed_at (newest first)
        page_views = list(PageView.objects.all())
        self.assertEqual(page_views[0], pv2)
        self.assertEqual(page_views[1], pv1)
