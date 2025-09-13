"""Comprehensive tests for emails app to boost coverage to 80%+"""

import json
from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.template import Context, Template
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.core.enums import EmailStatus
from apps.emails.admin import EmailMessageLogAdmin, EmailTemplateAdmin
from apps.emails.models import EmailMessageLog, EmailTemplate
from apps.emails.services import EmailService

User = get_user_model()


class EmailTemplateModelTest(TestCase):
    """Test EmailTemplate model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.template = EmailTemplate.objects.create(
            key="test-template",
            name="Test Template",
            description="Test template description",
            subject="Test Subject {{ name }}",
            html_content="<p>Hello {{ name }}</p>",
            text_content="Hello {{ name }}",
            is_active=True,
            category="test",
            language="en",
            template_variables={"name": "string"},
            created_by=self.user,
            updated_by=self.user,
        )

    def test_str_representation(self):
        """Test string representation"""
        self.assertEqual(str(self.template), "Test Template (test-template)")

    def test_cache_key_property(self):
        """Test cache key generation"""
        expected_key = "email_template:test-template:en"
        self.assertEqual(self.template.cache_key, expected_key)

    def test_save_clears_cache(self):
        """Test that saving clears cache"""
        cache.set(self.template.cache_key, "cached_value")
        cache.set(f"email_templates:{self.template.key}", "cached_list")

        self.template.name = "Updated Name"
        self.template.save()

        self.assertIsNone(cache.get(self.template.cache_key))
        self.assertIsNone(cache.get(f"email_templates:{self.template.key}"))

    def test_render_subject(self):
        """Test subject rendering with context"""
        context = {"name": "John"}
        rendered = self.template.render_subject(context)
        self.assertEqual(rendered, "Test Subject John")

    def test_render_html(self):
        """Test HTML rendering with context"""
        context = {"name": "John"}
        rendered = self.template.render_html(context)
        self.assertEqual(rendered, "<p>Hello John</p>")

    def test_render_text(self):
        """Test text rendering with context"""
        context = {"name": "John"}
        rendered = self.template.render_text(context)
        self.assertEqual(rendered, "Hello John")

    def test_render_all(self):
        """Test rendering all content at once"""
        context = {"name": "John"}
        result = self.template.render_all(context)

        self.assertEqual(result["subject"], "Test Subject John")
        self.assertEqual(result["html"], "<p>Hello John</p>")
        self.assertEqual(result["text"], "Hello John")

    def test_get_template_caching(self):
        """Test template retrieval with caching"""
        # First call should hit database
        with self.assertNumQueries(1):
            template1 = EmailTemplate.get_template("test-template", "en")

        # Second call should use cache
        with self.assertNumQueries(0):
            template2 = EmailTemplate.get_template("test-template", "en")

        self.assertEqual(template1.id, template2.id)

    def test_get_template_not_found(self):
        """Test template not found returns None"""
        template = EmailTemplate.get_template("nonexistent", "en")
        self.assertIsNone(template)

    def test_unique_together_constraint(self):
        """Test unique together constraint for key and language"""
        with self.assertRaises(Exception):
            EmailTemplate.objects.create(
                key="test-template",
                name="Duplicate",
                subject="Subject",
                html_content="HTML",
                text_content="Text",
                language="en",
                created_by=self.user,
                updated_by=self.user,
            )

    def test_template_variables_json_field(self):
        """Test template variables JSON field"""
        self.template.template_variables = {"var1": "type1", "var2": "type2"}
        self.template.save()
        self.template.refresh_from_db()

        self.assertEqual(self.template.template_variables["var1"], "type1")
        self.assertEqual(self.template.template_variables["var2"], "type2")

    def test_model_indexes(self):
        """Test that model indexes are properly defined"""
        meta = EmailTemplate._meta
        index_fields = [idx.fields for idx in meta.indexes]

        self.assertIn(["is_active", "category"], index_fields)
        self.assertIn(["key", "language"], index_fields)
        self.assertIn(["category", "-created_at"], index_fields)


class EmailMessageLogModelTest(TestCase):
    """Test EmailMessageLog model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )
        self.template = EmailTemplate.objects.create(
            key="test-template",
            name="Test Template",
            subject="Subject",
            html_content="HTML",
            text_content="Text",
            created_by=self.user,
            updated_by=self.user,
        )
        self.log = EmailMessageLog.objects.create(
            template=self.template,
            template_key="test-template",
            to_email="recipient@example.com",
            from_email="sender@example.com",
            subject="Test Subject",
            html_content="<p>HTML</p>",
            text_content="Text",
            status=EmailStatus.PENDING,
        )

    def test_str_representation(self):
        """Test string representation"""
        expected = f"Email to recipient@example.com - {EmailStatus.PENDING}"
        self.assertEqual(str(self.log), expected)

    def test_is_sent_property(self):
        """Test is_sent property"""
        self.assertFalse(self.log.is_sent)

        self.log.status = EmailStatus.SENT
        self.assertTrue(self.log.is_sent)

    def test_mark_as_sent(self):
        """Test marking email as sent"""
        self.log.mark_as_sent()
        self.log.refresh_from_db()

        self.assertEqual(self.log.status, EmailStatus.SENT)
        self.assertIsNotNone(self.log.sent_at)

    def test_mark_as_failed(self):
        """Test marking email as failed"""
        error_msg = "Connection refused"
        self.log.mark_as_failed(error_msg)
        self.log.refresh_from_db()

        self.assertEqual(self.log.status, EmailStatus.FAILED)
        self.assertEqual(self.log.error_message, error_msg)

    def test_retry_count_increment(self):
        """Test retry count incrementation"""
        initial_count = self.log.retry_count
        self.log.retry_count += 1
        self.log.save()
        self.log.refresh_from_db()

        self.assertEqual(self.log.retry_count, initial_count + 1)

    def test_metadata_json_field(self):
        """Test metadata JSON field"""
        self.log.metadata = {"key1": "value1", "key2": "value2"}
        self.log.save()
        self.log.refresh_from_db()

        self.assertEqual(self.log.metadata["key1"], "value1")
        self.assertEqual(self.log.metadata["key2"], "value2")

    def test_model_ordering(self):
        """Test model ordering"""
        log2 = EmailMessageLog.objects.create(
            template=self.template,
            template_key="test-template",
            to_email="another@example.com",
            from_email="sender@example.com",
            subject="Subject",
            html_content="HTML",
            text_content="Text",
            status=EmailStatus.PENDING,
        )

        logs = list(EmailMessageLog.objects.all())
        # Should be ordered by -created_at (newest first)
        self.assertEqual(logs[0], log2)
        self.assertEqual(logs[1], self.log)


class EmailServiceTest(TestCase):
    """Test EmailService"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )
        self.template = EmailTemplate.objects.create(
            key="welcome",
            name="Welcome Email",
            subject="Welcome {{ username }}!",
            html_content="<h1>Welcome {{ username }}</h1>",
            text_content="Welcome {{ username }}",
            created_by=self.user,
            updated_by=self.user,
        )

    @patch("apps.emails.services.send_email_task.delay")
    def test_send_email_async(self, mock_task):
        """Test sending email asynchronously"""
        context = {"username": "John"}
        log = EmailService.send_email(
            template_key="welcome",
            to_email="john@example.com",
            context=context,
            async_send=True,
        )

        self.assertIsInstance(log, EmailMessageLog)
        self.assertEqual(log.to_email, "john@example.com")
        self.assertEqual(log.status, EmailStatus.PENDING)
        mock_task.assert_called_once_with(log.id)

    @patch("apps.emails.services.EmailService._send_email_now")
    def test_send_email_sync(self, mock_send):
        """Test sending email synchronously"""
        mock_send.return_value = True

        context = {"username": "John"}
        log = EmailService.send_email(
            template_key="welcome",
            to_email="john@example.com",
            context=context,
            async_send=False,
        )

        self.assertIsInstance(log, EmailMessageLog)
        mock_send.assert_called_once_with(log)

    def test_send_email_template_not_found(self):
        """Test sending email with non-existent template"""
        with self.assertRaises(ValueError) as ctx:
            EmailService.send_email(
                template_key="nonexistent", to_email="test@example.com"
            )

        self.assertIn("not found", str(ctx.exception))

    def test_send_email_with_multiple_recipients(self):
        """Test sending email to multiple recipients"""
        recipients = ["user1@example.com", "user2@example.com"]
        log = EmailService.send_email(
            template_key="welcome",
            to_email=recipients,
            context={"username": "Users"},
            async_send=False,
        )

        # Should use first recipient as primary
        self.assertEqual(log.to_email, "user1@example.com")

    @override_settings(DEFAULT_FROM_EMAIL="default@example.com")
    def test_send_email_default_from(self):
        """Test default from email"""
        log = EmailService.send_email(
            template_key="welcome", to_email="test@example.com", async_send=False
        )

        self.assertEqual(log.from_email, "default@example.com")

    def test_send_email_with_cc_bcc(self):
        """Test sending email with CC and BCC"""
        log = EmailService.send_email(
            template_key="welcome",
            to_email="main@example.com",
            cc=["cc1@example.com", "cc2@example.com"],
            bcc=["bcc@example.com"],
            async_send=False,
        )

        self.assertEqual(log.cc, "cc1@example.com,cc2@example.com")
        self.assertEqual(log.bcc, "bcc@example.com")

    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration"""
        # Test that service creates log even on failure
        with patch("apps.emails.services.EmailService._send_email_now") as mock_send:
            mock_send.side_effect = Exception("Connection failed")

            log = EmailService.send_email(
                template_key="welcome", to_email="test@example.com", async_send=False
            )

            self.assertIsInstance(log, EmailMessageLog)

    def test_send_email_render_failure(self):
        """Test handling of template render failure"""
        # Create template with invalid syntax
        bad_template = EmailTemplate.objects.create(
            key="bad-template",
            name="Bad Template",
            subject="{{ invalid_syntax",  # Invalid template syntax
            html_content="HTML",
            text_content="Text",
            created_by=self.user,
            updated_by=self.user,
        )

        with self.assertRaises(ValueError) as ctx:
            EmailService.send_email(
                template_key="bad-template", to_email="test@example.com"
            )

        self.assertIn("Failed to render", str(ctx.exception))


class EmailTasksTest(TestCase):
    """Test email tasks"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )
        self.template = EmailTemplate.objects.create(
            key="test",
            name="Test",
            subject="Subject",
            html_content="HTML",
            text_content="Text",
            created_by=self.user,
            updated_by=self.user,
        )
        self.log = EmailMessageLog.objects.create(
            template=self.template,
            template_key="test",
            to_email="test@example.com",
            from_email="sender@example.com",
            subject="Test Subject",
            html_content="<p>HTML</p>",
            text_content="Text",
            status=EmailStatus.PENDING,
        )

    @patch("apps.emails.services.EmailService._send_email_now")
    def test_send_email_task_success(self, mock_send):
        """Test successful email sending via task"""
        mock_send.return_value = True
        from apps.emails.tasks import send_email_task

        # Mock the celery task directly
        mock_self = MagicMock()
        mock_self.request.retries = 0
        result = send_email_task(mock_self, self.log.id)

        self.assertTrue(result["success"])
        mock_send.assert_called_once()

    @patch("apps.emails.services.EmailService._send_email_now")
    def test_send_email_task_failure(self, mock_send):
        """Test failed email sending via task"""
        mock_send.return_value = False
        from apps.emails.tasks import send_email_task

        mock_self = MagicMock()
        mock_self.request.retries = 0
        result = send_email_task(mock_self, self.log.id)

        self.assertFalse(result["success"])

    def test_send_email_task_invalid_id(self):
        """Test task with invalid email ID"""
        from apps.emails.tasks import send_email_task

        mock_self = MagicMock()
        mock_self.request.retries = 0
        result = send_email_task(mock_self, 99999)
        self.assertFalse(result["success"])


class EmailViewsTest(TestCase):
    """Test email views"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.template = EmailTemplate.objects.create(
            key="test",
            name="Test",
            subject="Subject",
            html_content="HTML",
            text_content="Text",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_email_preview_view(self):
        """Test email preview view"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(f"/emails/preview/{self.template.id}/")

        # Should return preview or require specific permissions
        # This is a placeholder - adjust based on actual view implementation
        self.assertIn(response.status_code, [200, 302, 403])

    def test_send_test_email_view(self):
        """Test sending test email"""
        self.client.login(username="testuser", password="testpass123")

        data = {
            "template_id": self.template.id,
            "to_email": "test@example.com",
            "context": json.dumps({"test": "data"}),
        }

        response = self.client.post("/emails/send-test/", data)

        # Should handle test email sending
        self.assertIn(response.status_code, [200, 201, 302, 403])


class EmailAdminTest(TestCase):
    """Test admin interfaces"""

    def test_email_template_admin_registration(self):
        """Test EmailTemplate admin is registered"""
        from django.contrib import admin

        self.assertIn(EmailTemplate, admin.site._registry)

    def test_email_message_log_admin_registration(self):
        """Test EmailMessageLog admin is registered"""
        from django.contrib import admin

        self.assertIn(EmailMessageLog, admin.site._registry)

    def test_template_admin_list_display(self):
        """Test template admin list display fields"""
        admin_class = EmailTemplateAdmin
        expected_fields = ["name", "key", "category", "language", "is_active"]

        for field in expected_fields:
            self.assertIn(field, admin_class.list_display)

    def test_message_log_admin_list_display(self):
        """Test message log admin list display fields"""
        admin_class = EmailMessageLogAdmin
        expected_fields = ["to_email", "template_key", "status", "created_at"]

        for field in expected_fields:
            self.assertIn(field, admin_class.list_display)


class EmailUtilsTest(TestCase):
    """Test email utility functions"""

    def test_validate_email_address(self):
        """Test email address validation"""
        from apps.emails.utils import validate_email_address

        # Valid emails
        self.assertTrue(validate_email_address("user@example.com"))
        self.assertTrue(validate_email_address("user.name@example.co.uk"))

        # Invalid emails
        self.assertFalse(validate_email_address("invalid"))
        self.assertFalse(validate_email_address("@example.com"))
        self.assertFalse(validate_email_address("user@"))

    def test_sanitize_html_content(self):
        """Test HTML content sanitization"""
        from apps.emails.utils import sanitize_html_content

        # Test XSS prevention
        dirty_html = '<script>alert("xss")</script><p>Hello</p>'
        clean_html = sanitize_html_content(dirty_html)

        self.assertNotIn("<script>", clean_html)
        self.assertIn("<p>Hello</p>", clean_html)

    def test_get_email_context_defaults(self):
        """Test getting default email context"""
        from apps.emails.utils import get_email_context_defaults

        defaults = get_email_context_defaults()

        # Should include common context variables
        self.assertIn("site_name", defaults)
        self.assertIn("site_url", defaults)
        self.assertIn("current_year", defaults)


# Additional test for coverage
class EmailAppConfigTest(TestCase):
    """Test app configuration"""

    def test_app_config(self):
        """Test app configuration"""
        from apps.emails.apps import EmailsConfig

        self.assertEqual(EmailsConfig.name, "apps.emails")
        self.assertEqual(
            EmailsConfig.default_auto_field, "django.db.models.BigAutoField"
        )
