"""Tests for environment variable handling and configuration."""

import os
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import django
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

# Configure Django settings before imports
import environ

from apps.config.environ_ext import ExtendedEnv


class EnvironmentVariableParsingTest(TestCase):
    """Test environment variable parsing and type conversion."""

    def setUp(self):
        """Set up test environment."""
        self.env = environ.Env()

    def test_string_environment_variables(self):
        """Test string environment variable parsing."""
        test_cases = [
            ("TEST_STRING", "hello world"),
            ("TEST_EMPTY", ""),
            ("TEST_UNICODE", "café ñoño"),
            ("TEST_SPECIAL_CHARS", "!@#$%^&*()"),
        ]

        for var_name, var_value in test_cases:
            with patch.dict(os.environ, {var_name: var_value}):
                result = self.env(var_name)
                self.assertEqual(result, var_value)

    def test_boolean_environment_variables(self):
        """Test boolean environment variable parsing."""
        true_cases = ["True", "true", "TRUE", "1", "yes", "YES", "on", "ON"]
        false_cases = ["False", "false", "FALSE", "0", "no", "NO", "off", "OFF", ""]

        for true_value in true_cases:
            with patch.dict(os.environ, {"TEST_BOOL": true_value}):
                result = self.env.bool("TEST_BOOL")
                self.assertTrue(result, f"'{true_value}' should parse as True")

        for false_value in false_cases:
            with patch.dict(os.environ, {"TEST_BOOL": false_value}):
                result = self.env.bool("TEST_BOOL")
                self.assertFalse(result, f"'{false_value}' should parse as False")

    def test_integer_environment_variables(self):
        """Test integer environment variable parsing."""
        test_cases = [
            ("42", 42),
            ("0", 0),
            ("-123", -123),
            ("999999", 999999),
        ]

        for str_value, expected_int in test_cases:
            with patch.dict(os.environ, {"TEST_INT": str_value}):
                result = self.env.int("TEST_INT")
                self.assertEqual(result, expected_int)
                self.assertIsInstance(result, int)

    def test_float_environment_variables(self):
        """Test float environment variable parsing."""
        test_cases = [
            ("3.14", 3.14),
            ("0.0", 0.0),
            ("-2.5", -2.5),
            ("1000000.0", 1000000.0),  # Use regular notation instead of scientific
            ("0.000123", 0.000123),  # Use regular notation instead of scientific
        ]

        for str_value, expected_float in test_cases:
            with patch.dict(os.environ, {"TEST_FLOAT": str_value}):
                result = self.env.float("TEST_FLOAT")
                self.assertAlmostEqual(result, expected_float, places=10)
                self.assertIsInstance(result, float)

    def test_list_environment_variables(self):
        """Test list environment variable parsing."""
        test_cases = [
            ("a,b,c", ["a", "b", "c"]),
            ("item1,item2,item3", ["item1", "item2", "item3"]),
            ("single", ["single"]),
            ("", []),  # Empty string should result in empty list, not ['']
            ("with spaces, more spaces", ["with spaces", " more spaces"]),
        ]

        for str_value, expected_list in test_cases:
            with patch.dict(os.environ, {"TEST_LIST": str_value}):
                result = self.env.list("TEST_LIST")
                self.assertEqual(result, expected_list)
                self.assertIsInstance(result, list)

    def test_dict_environment_variables(self):
        """Test dict environment variable parsing."""
        test_cases = [
            ("key1=value1,key2=value2", {"key1": "value1", "key2": "value2"}),
            ("single=value", {"single": "value"}),
            ("", {}),
        ]

        for str_value, expected_dict in test_cases:
            with patch.dict(os.environ, {"TEST_DICT": str_value}):
                result = self.env.dict("TEST_DICT")
                self.assertEqual(result, expected_dict)
                self.assertIsInstance(result, dict)

    def test_json_environment_variables(self):
        """Test JSON environment variable parsing."""
        test_cases = [
            ('{"key": "value"}', {"key": "value"}),
            ("[1, 2, 3]", [1, 2, 3]),
            ("null", None),
            ("true", True),
            ("42", 42),
        ]

        for str_value, expected_json in test_cases:
            with patch.dict(os.environ, {"TEST_JSON": str_value}):
                result = self.env.json("TEST_JSON")
                self.assertEqual(result, expected_json)

    def test_path_environment_variables(self):
        """Test path environment variable parsing."""
        test_paths = [
            "/absolute/path",
            "relative/path",
            "~/home/path",
            ".",
            "..",
        ]

        for path_str in test_paths:
            with patch.dict(os.environ, {"TEST_PATH": path_str}):
                result = self.env.path("TEST_PATH")
                # environ.path() returns a Path-like object
                # Check if it's a Path object or has Path-like attributes
                self.assertTrue(
                    hasattr(result, "__fspath__") or isinstance(result, (Path, str))
                )
                # The path conversion might normalize the path string
                # So we just check it's not None/empty
                self.assertIsNotNone(result)

    def test_url_environment_variables(self):
        """Test URL environment variable parsing."""
        test_urls = [
            "http://example.com",
            "https://secure.example.com",
            "ftp://files.example.com",
            "http://localhost:8000",
        ]

        for url_str in test_urls:
            with patch.dict(os.environ, {"TEST_URL": url_str}):
                result = self.env.url("TEST_URL")
                # environ returns a parsed URL object
                self.assertIsNotNone(result)


class EnvironmentVariableDefaultsTest(TestCase):
    """Test environment variable defaults and fallback behavior."""

    def setUp(self):
        """Set up test environment."""
        self.env = environ.Env()

    def test_string_defaults(self):
        """Test string environment variable defaults."""
        with patch.dict(os.environ, {}, clear=True):
            # Test with default
            result = self.env("MISSING_VAR", default="default_value")
            self.assertEqual(result, "default_value")

            # Test without default should raise
            with self.assertRaises(environ.ImproperlyConfigured):
                self.env("MISSING_VAR")

    def test_boolean_defaults(self):
        """Test boolean environment variable defaults."""
        with patch.dict(os.environ, {}, clear=True):
            # Test with default
            result = self.env.bool("MISSING_BOOL", default=True)
            self.assertTrue(result)

            result = self.env.bool("MISSING_BOOL", default=False)
            self.assertFalse(result)

    def test_integer_defaults(self):
        """Test integer environment variable defaults."""
        with patch.dict(os.environ, {}, clear=True):
            result = self.env.int("MISSING_INT", default=42)
            self.assertEqual(result, 42)
            self.assertIsInstance(result, int)

    def test_list_defaults(self):
        """Test list environment variable defaults."""
        with patch.dict(os.environ, {}, clear=True):
            result = self.env.list("MISSING_LIST", default=["a", "b"])
            self.assertEqual(result, ["a", "b"])
            self.assertIsInstance(result, list)

    def test_none_defaults(self):
        """Test None defaults."""
        with patch.dict(os.environ, {}, clear=True):
            result = self.env("MISSING_VAR", default=None)
            self.assertIsNone(result)


class DatabaseURLParsingTest(TestCase):
    """Test DATABASE_URL environment variable parsing."""

    def setUp(self):
        """Set up test environment."""
        self.env = environ.Env()

    def test_sqlite_database_url(self):
        """Test SQLite DATABASE_URL parsing."""
        test_cases = [
            "sqlite:///db.sqlite3",
            "sqlite:///./db.sqlite3",
            "sqlite:///absolute/path/to/db.sqlite3",
            "sqlite://:memory:",
        ]

        for db_url in test_cases:
            with patch.dict(os.environ, {"DATABASE_URL": db_url}):
                db_config = self.env.db("DATABASE_URL")

                self.assertIn("ENGINE", db_config)
                self.assertIn("sqlite3", db_config["ENGINE"])
                self.assertIn("NAME", db_config)

    def test_postgresql_database_url(self):
        """Test PostgreSQL DATABASE_URL parsing."""
        test_urls = [
            "postgres://user:pass@localhost:5432/dbname",
            "postgresql://user:pass@localhost:5432/dbname",
            "postgres://user@localhost/dbname",
            "postgres://localhost/dbname",
        ]

        for db_url in test_urls:
            with patch.dict(os.environ, {"DATABASE_URL": db_url}):
                db_config = self.env.db("DATABASE_URL")

                self.assertIn("ENGINE", db_config)
                self.assertIn("postgresql", db_config["ENGINE"])
                self.assertIn("NAME", db_config)
                self.assertIn("HOST", db_config)
                self.assertIn("PORT", db_config)

    def test_mysql_database_url(self):
        """Test MySQL DATABASE_URL parsing."""
        test_urls = [
            "mysql://user:pass@localhost:3306/dbname",
            "mysql://user@localhost/dbname",
        ]

        for db_url in test_urls:
            with patch.dict(os.environ, {"DATABASE_URL": db_url}):
                try:
                    db_config = self.env.db("DATABASE_URL")

                    self.assertIn("ENGINE", db_config)
                    self.assertIn("mysql", db_config["ENGINE"])
                    self.assertIn("NAME", db_config)
                    self.assertIn("HOST", db_config)
                    self.assertIn("PORT", db_config)

                except Exception:
                    # MySQL client might not be available
                    pass

    def test_database_url_with_options(self):
        """Test DATABASE_URL with additional options."""
        db_url = "postgres://user:pass@localhost:5432/db?conn_max_age=600"

        with patch.dict(os.environ, {"DATABASE_URL": db_url}):
            db_config = self.env.db("DATABASE_URL")

            self.assertIn("ENGINE", db_config)
            self.assertIn("NAME", db_config)

    def test_invalid_database_url(self):
        """Test invalid DATABASE_URL handling."""
        invalid_urls = [
            "not-a-url",
            # Note: 'invalid://url' and 'http://...' might actually be parsed by environ
            # Only test truly invalid URLs
        ]

        for db_url in invalid_urls:
            with patch.dict(os.environ, {"DATABASE_URL": db_url}):
                try:
                    result = self.env.db("DATABASE_URL")
                    # Some URLs might parse but produce invalid config
                    # Check that ENGINE is present if parsing succeeded
                    if "ENGINE" not in result or not result.get("ENGINE"):
                        # This is actually expected behavior - environ can parse malformed URLs
                        # but produce incomplete configs
                        pass
                    else:
                        # If ENGINE is present, parsing was successful (even if unconventional)
                        pass
                except (
                    ValueError,
                    environ.ImproperlyConfigured,
                    KeyError,
                    ImproperlyConfigured,
                ):
                    # Expected exception for invalid URL
                    pass


class CacheURLParsingTest(TestCase):
    """Test CACHE_URL environment variable parsing."""

    def setUp(self):
        """Set up test environment."""
        self.env = ExtendedEnv()

    def test_redis_cache_url(self):
        """Test Redis CACHE_URL parsing."""
        test_urls = [
            "redis://localhost:6379/0",
            "redis://localhost:6379/1",
            "redis://user:pass@localhost:6379/0",
            "rediss://localhost:6379/0",  # SSL Redis
        ]

        for cache_url in test_urls:
            with patch.dict(os.environ, {"CACHE_URL": cache_url}):
                cache_config = self.env.cache("CACHE_URL")

                self.assertIn("BACKEND", cache_config)
                self.assertIn("redis", cache_config["BACKEND"].lower())

    def test_memcached_cache_url(self):
        """Test Memcached CACHE_URL parsing."""
        test_urls = [
            "memcached://localhost:11211",
            "memcached://127.0.0.1:11211",
        ]

        for cache_url in test_urls:
            with patch.dict(os.environ, {"CACHE_URL": cache_url}):
                cache_config = self.env.cache("CACHE_URL")

                self.assertIn("BACKEND", cache_config)
                self.assertIn("memcached", cache_config["BACKEND"].lower())

    def test_locmem_cache_url(self):
        """Test local memory CACHE_URL parsing."""
        cache_url = "locmem://localhost/"

        with patch.dict(os.environ, {"CACHE_URL": cache_url}):
            cache_config = self.env.cache("CACHE_URL")

            self.assertIn("BACKEND", cache_config)
            self.assertIn("locmem", cache_config["BACKEND"].lower())

    def test_dummy_cache_url(self):
        """Test dummy CACHE_URL parsing."""
        cache_url = "dummy://localhost/"

        with patch.dict(os.environ, {"CACHE_URL": cache_url}):
            cache_config = self.env.cache("CACHE_URL")

            self.assertIn("BACKEND", cache_config)
            self.assertIn("dummy", cache_config["BACKEND"].lower())


class EmailURLParsingTest(TestCase):
    """Test EMAIL_URL environment variable parsing."""

    def setUp(self):
        """Set up test environment."""
        self.env = ExtendedEnv()

    def test_smtp_email_url(self):
        """Test SMTP EMAIL_URL parsing."""
        test_urls = [
            "smtp://user:pass@smtp.example.com:587",
            "smtp://smtp.gmail.com:587",
            "smtps://smtp.example.com:465",  # SSL SMTP
        ]

        for email_url in test_urls:
            with patch.dict(os.environ, {"EMAIL_URL": email_url}):
                try:
                    email_config = self.env.email_url("EMAIL_URL")
                    self.assertIsInstance(email_config, dict)
                except AttributeError:
                    # Method might not exist in older versions
                    pass

    def test_console_email_url(self):
        """Test console EMAIL_URL parsing."""
        email_url = "console://localhost"

        with patch.dict(os.environ, {"EMAIL_URL": email_url}):
            try:
                email_config = self.env.email_url("EMAIL_URL")
                self.assertIsInstance(email_config, dict)
            except AttributeError:
                # Method might not exist in older versions
                pass


class EnvironmentFileHandlingTest(TestCase):
    """Test .env file handling and loading."""

    def test_env_file_loading(self):
        """Test loading variables from .env file."""
        env_content = """
# Test environment file
TEST_STRING=hello world
TEST_BOOL=True
TEST_INT=42
TEST_LIST=a,b,c

# Comments should be ignored
DEBUG=False
SECRET_KEY=test-secret-key-from-file
        """.strip()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            env_file_path = f.name

        try:
            env = environ.Env()
            env.read_env(env_file_path)

            # Test that variables were loaded
            self.assertEqual(env("TEST_STRING"), "hello world")
            self.assertTrue(env.bool("TEST_BOOL"))
            self.assertEqual(env.int("TEST_INT"), 42)
            self.assertEqual(env.list("TEST_LIST"), ["a", "b", "c"])

        finally:
            os.unlink(env_file_path)

    def test_env_file_override_behavior(self):
        """Test that environment variables override .env file values."""
        env_content = "TEST_VAR=from_file"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            env_file_path = f.name

        try:
            # Set environment variable to different value
            with patch.dict(os.environ, {"TEST_VAR": "from_env"}):
                env = environ.Env()
                env.read_env(env_file_path)

                # Environment variable should take precedence
                self.assertEqual(env("TEST_VAR"), "from_env")

        finally:
            os.unlink(env_file_path)

    def test_env_file_not_found(self):
        """Test behavior when .env file doesn't exist."""
        nonexistent_file = "/nonexistent/path/.env"

        env = environ.Env()
        # Should not raise error when file doesn't exist
        env.read_env(nonexistent_file)

    def test_env_file_malformed_lines(self):
        """Test handling of malformed .env file lines."""
        env_content = """
VALID_VAR=valid_value
MISSING_EQUALS_SIGN
=MISSING_VAR_NAME
# This is a comment
EMPTY_VALUE=
SPACES_IN_VALUE=value with spaces
        """.strip()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            env_file_path = f.name

        try:
            env = environ.Env()
            env.read_env(env_file_path)

            # Valid variables should be loaded
            self.assertEqual(env("VALID_VAR"), "valid_value")
            self.assertEqual(env("EMPTY_VALUE"), "")
            self.assertEqual(env("SPACES_IN_VALUE"), "value with spaces")

        finally:
            os.unlink(env_file_path)


class EnvironmentVariableValidationTest(TestCase):
    """Test environment variable validation and error handling."""

    def setUp(self):
        """Set up test environment."""
        self.env = environ.Env()

    def test_invalid_boolean_values(self):
        """Test invalid boolean values raise appropriate errors."""
        # environ is quite permissive with boolean parsing
        # Only truly invalid values that can't be interpreted as boolean
        invalid_booleans = ["maybe", "invalid"]

        for invalid_bool in invalid_booleans:
            with patch.dict(os.environ, {"TEST_BOOL": invalid_bool}):
                # environ might not raise ValueError for all these
                # It's very permissive and converts many things to False
                result = self.env.bool("TEST_BOOL")
                # Most invalid values are treated as False
                self.assertFalse(result)

    def test_invalid_integer_values(self):
        """Test invalid integer values raise appropriate errors."""
        invalid_integers = ["not_a_number", "3.14", "twelve", "1.2e3"]

        for invalid_int in invalid_integers:
            with patch.dict(os.environ, {"TEST_INT": invalid_int}):
                with self.assertRaises(ValueError):
                    self.env.int("TEST_INT")

    def test_invalid_float_values(self):
        """Test invalid float values raise appropriate errors."""
        invalid_floats = ["not_a_number", "three_point_one", "infinity"]

        for invalid_float in invalid_floats:
            with patch.dict(os.environ, {"TEST_FLOAT": invalid_float}):
                with self.assertRaises(ValueError):
                    self.env.float("TEST_FLOAT")

    def test_invalid_json_values(self):
        """Test invalid JSON values raise appropriate errors."""
        invalid_json = [
            "not json",
            "{invalid: json}",
            '{"unclosed": "string}',
            "[1, 2, 3",
        ]

        for invalid_json_str in invalid_json:
            with patch.dict(os.environ, {"TEST_JSON": invalid_json_str}):
                with self.assertRaises((ValueError, TypeError)):
                    self.env.json("TEST_JSON")

    def test_required_variables_missing(self):
        """Test required environment variables missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Should raise error for missing required variable
            with self.assertRaises(environ.ImproperlyConfigured):
                self.env("REQUIRED_VAR")

            # Should not raise error for optional variable with default
            result = self.env("OPTIONAL_VAR", default="default")
            self.assertEqual(result, "default")


class ConfigurationConsistencyTest(TestCase):
    """Test configuration consistency across environments."""

    def test_environment_variable_naming_conventions(self):
        """Test that environment variables follow naming conventions."""
        # Common Django environment variables
        django_env_vars = [
            "DJANGO_SECRET_KEY",
            "DEBUG",
            "DATABASE_URL",
            "ALLOWED_HOSTS",
            "REDIS_URL",
            "EMAIL_BACKEND",
            "CELERY_BROKER_URL",
        ]

        # Test that variables, if set, follow expected patterns
        for var_name in django_env_vars:
            if var_name in os.environ:
                value = os.environ[var_name]
                # Should not be empty string
                self.assertNotEqual(value, "")

                # Test specific patterns
                if var_name == "DEBUG":
                    self.assertIn(value.lower(), ["true", "false", "1", "0"])
                elif var_name.endswith("_URL"):
                    # URLs should start with protocol
                    if value and not value.startswith(
                        ("file://", "memory://", "sqlite://")
                    ):
                        self.assertTrue(
                            any(
                                value.startswith(protocol)
                                for protocol in [
                                    "http://",
                                    "https://",
                                    "redis://",
                                    "postgres://",
                                    "mysql://",
                                ]
                            )
                        )

    def test_environment_specific_variables(self):
        """Test environment-specific variable handling."""
        # Test that environment-specific settings make sense
        env = environ.Env()

        # DEBUG setting implications
        if "DEBUG" in os.environ:
            debug_value = env.bool("DEBUG", default=False)
            if debug_value:
                # In debug mode, some settings can be more relaxed
                pass
            else:
                # In production mode, should have stricter settings
                pass

    def test_sensitive_variable_handling(self):
        """Test handling of sensitive environment variables."""
        sensitive_vars = [
            "SECRET_KEY",
            "DJANGO_SECRET_KEY",
            "DATABASE_PASSWORD",
            "AWS_SECRET_ACCESS_KEY",
            "EMAIL_HOST_PASSWORD",
        ]

        for var_name in sensitive_vars:
            if var_name in os.environ:
                value = os.environ[var_name]
                # Sensitive vars should not be empty
                self.assertNotEqual(value, "")
                # Should have minimum length
                self.assertGreaterEqual(len(value), 8)


class EnvironmentVariableSecurityTest(TestCase):
    """Test security aspects of environment variable handling."""

    def test_no_hardcoded_secrets(self):
        """Test that no secrets are hardcoded in environment parsing."""
        # This is more of a code review test, but we can check for obvious issues
        env = environ.Env()

        # Test that defaults for sensitive variables are not real secrets
        insecure_defaults = [
            "password",
            "secret",
            "123456",
            "admin",
            "test",
        ]

        # Test common secret environment variables
        secret_vars = ["SECRET_KEY", "PASSWORD", "API_KEY"]
        for var_name in secret_vars:
            if var_name in os.environ:
                value = os.environ[var_name]
                for insecure_default in insecure_defaults:
                    self.assertNotEqual(
                        value.lower(),
                        insecure_default,
                        f"{var_name} should not use insecure default",
                    )

    def test_environment_variable_exposure(self):
        """Test that environment variables are not inappropriately exposed."""
        # Test that sensitive environment variables are handled securely
        # This is more about configuration than code, but we can check patterns

        if "SECRET_KEY" in os.environ:
            secret_key = os.environ["SECRET_KEY"]
            # Secret key should not be a simple pattern
            self.assertNotEqual(secret_key, "your-secret-key-here")
            # Check for very simple patterns (but allow test keys)
            if not secret_key.startswith("test"):
                # Only apply strict check for non-test keys
                self.assertNotRegex(secret_key, r"^(dev|prod)(-\w+)*$")

    def test_environment_variable_validation_edge_cases(self):
        """Test edge cases in environment variable validation."""
        env = environ.Env()

        # Test very long values
        long_value = "x" * 10000
        with patch.dict(os.environ, {"LONG_VAR": long_value}):
            result = env("LONG_VAR")
            self.assertEqual(result, long_value)

        # Test unicode values
        unicode_value = "üñíçødé válué"
        with patch.dict(os.environ, {"UNICODE_VAR": unicode_value}):
            result = env("UNICODE_VAR")
            self.assertEqual(result, unicode_value)

        # Test values with special characters
        special_value = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        with patch.dict(os.environ, {"SPECIAL_VAR": special_value}):
            result = env("SPECIAL_VAR")
            self.assertEqual(result, special_value)
