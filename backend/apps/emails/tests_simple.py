"""Simple passing tests for emails app"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from apps.core.enums import EmailStatus
from apps.emails.models import EmailMessageLog, EmailTemplate

User = get_user_model()


class EmailTemplateModelTest(TestCase):
    """Test EmailTemplate model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

    def test_create_email_template(self):
        """Test creating an email template"""
        template = EmailTemplate.objects.create(
            key="test-template",
            name="Test Template",
            subject="Test Subject",
            html_content="<p>HTML content</p>",
            text_content="Text content",
            created_by=self.user,
            updated_by=self.user,
        )

        self.assertEqual(template.key, "test-template")
        self.assertEqual(template.name, "Test Template")

    def test_str_representation(self):
        """Test string representation"""
        template = EmailTemplate.objects.create(
            key="test",
            name="Test",
            subject="Subject",
            html_content="HTML",
            text_content="Text",
            created_by=self.user,
            updated_by=self.user,
        )

        self.assertEqual(str(template), "Test (test)")

    def test_cache_key_property(self):
        """Test cache key generation"""
        template = EmailTemplate.objects.create(
            key="test",
            name="Test",
            subject="Subject",
            html_content="HTML",
            text_content="Text",
            language="en",
            created_by=self.user,
            updated_by=self.user,
        )

        expected_key = "email_template:test:en"
        self.assertEqual(template.cache_key, expected_key)

    def test_render_methods(self):
        """Test render methods work"""
        template = EmailTemplate.objects.create(
            key="test",
            name="Test",
            subject="Hello {{ name }}",
            html_content="<p>Hello {{ name }}</p>",
            text_content="Hello {{ name }}",
            created_by=self.user,
            updated_by=self.user,
        )

        context = {"name": "World"}

        # Test render_subject
        rendered_subject = template.render_subject(context)
        self.assertEqual(rendered_subject, "Hello World")

        # Test render_html
        rendered_html = template.render_html(context)
        self.assertEqual(rendered_html, "<p>Hello World</p>")

        # Test render_text
        rendered_text = template.render_text(context)
        self.assertEqual(rendered_text, "Hello World")

    def test_render_all(self):
        """Test render_all method"""
        template = EmailTemplate.objects.create(
            key="test",
            name="Test",
            subject="Subject {{ var }}",
            html_content="<p>HTML {{ var }}</p>",
            text_content="Text {{ var }}",
            created_by=self.user,
            updated_by=self.user,
        )

        context = {"var": "value"}
        result = template.render_all(context)

        self.assertIn("subject", result)
        self.assertIn("html", result)
        self.assertIn("text", result)


class EmailMessageLogModelTest(TestCase):
    """Test EmailMessageLog model"""

    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com")
        self.template = EmailTemplate.objects.create(
            key="test",
            name="Test",
            subject="Subject",
            html_content="HTML",
            text_content="Text",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_create_email_log(self):
        """Test creating an email log"""
        log = EmailMessageLog.objects.create(
            template=self.template,
            template_key="test",
            to_email="recipient@example.com",
            from_email="sender@example.com",
            subject="Test Subject",
            html_content="<p>HTML</p>",
            text_content="Text",
            status=EmailStatus.PENDING,
        )

        self.assertEqual(log.to_email, "recipient@example.com")
        self.assertEqual(log.status, EmailStatus.PENDING)

    def test_str_representation(self):
        """Test string representation"""
        log = EmailMessageLog.objects.create(
            template=self.template,
            template_key="test",
            to_email="test@example.com",
            from_email="sender@example.com",
            subject="Subject",
            html_content="HTML",
            text_content="Text",
            status=EmailStatus.SENT,
        )

        expected = f"Email to test@example.com - {EmailStatus.SENT}"
        self.assertEqual(str(log), expected)

    def test_is_sent_property(self):
        """Test is_sent property"""
        log = EmailMessageLog.objects.create(
            template=self.template,
            template_key="test",
            to_email="test@example.com",
            from_email="sender@example.com",
            subject="Subject",
            html_content="HTML",
            text_content="Text",
            status=EmailStatus.PENDING,
        )

        self.assertFalse(log.is_sent)

        log.status = EmailStatus.SENT
        log.save()

        self.assertTrue(log.is_sent)

    def test_mark_as_sent(self):
        """Test marking email as sent"""
        log = EmailMessageLog.objects.create(
            template=self.template,
            template_key="test",
            to_email="test@example.com",
            from_email="sender@example.com",
            subject="Subject",
            html_content="HTML",
            text_content="Text",
            status=EmailStatus.PENDING,
        )

        log.mark_as_sent()
        log.refresh_from_db()

        self.assertEqual(log.status, EmailStatus.SENT)
        self.assertIsNotNone(log.sent_at)

    def test_mark_as_failed(self):
        """Test marking email as failed"""
        log = EmailMessageLog.objects.create(
            template=self.template,
            template_key="test",
            to_email="test@example.com",
            from_email="sender@example.com",
            subject="Subject",
            html_content="HTML",
            text_content="Text",
            status=EmailStatus.PENDING,
        )

        error_msg = "Connection refused"
        log.mark_as_failed(error_msg)
        log.refresh_from_db()

        self.assertEqual(log.status, EmailStatus.FAILED)
        self.assertEqual(log.error_message, error_msg)


class EmailUtilsTest(TestCase):
    """Test email utility functions"""

    def test_validate_email_address(self):
        """Test email validation"""
        from apps.emails.utils import validate_email_address

        # Valid emails
        self.assertTrue(validate_email_address("user@example.com"))
        self.assertTrue(validate_email_address("test.user@example.co.uk"))

        # Invalid emails
        self.assertFalse(validate_email_address("invalid"))
        self.assertFalse(validate_email_address("@example.com"))
        self.assertFalse(validate_email_address("user@"))
        self.assertFalse(validate_email_address(""))
        self.assertFalse(validate_email_address(None))

    def test_get_email_context_defaults(self):
        """Test default email context"""
        from apps.emails.utils import get_email_context_defaults

        defaults = get_email_context_defaults()

        self.assertIsInstance(defaults, dict)
        self.assertIn("site_name", defaults)
        self.assertIn("site_url", defaults)
        self.assertIn("current_year", defaults)
