"""
Global Test Configuration and Advanced Fixtures for Bedrock CMS
Provides comprehensive test setup, optimization, and shared fixtures
"""

import gc
import json
import os
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock, patch

# Setup Django before importing Django modules
import django

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")

# Django imports moved inside fixtures to avoid AppRegistryNotReady errors

# Test performance tracking
test_performance = defaultdict(list)
test_start_times = {}


@pytest.fixture(scope="session", autouse=True)
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Enhanced database setup with optimizations
    """
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group, Permission
    from django.core.management import call_command

    with django_db_blocker.unblock():
        # Only run migrations if not using test_minimal settings which disable migrations
        from django.conf import settings

        if hasattr(settings, "MIGRATION_MODULES") and not getattr(
            settings.MIGRATION_MODULES, "__contains__", lambda x: False
        )("contenttypes"):
            # Migrations are enabled, run them
            try:
                call_command("migrate", "--run-syncdb", verbosity=0, interactive=False)
            except Exception as e:
                # If migrations fail, try without syncdb
                print(f"Migration failed with --run-syncdb, trying without: {e}")
                try:
                    call_command("migrate", verbosity=0, interactive=False)
                except Exception as e2:
                    print(f"Migration still failed, skipping: {e2}")
        else:
            # Migrations are disabled, just create tables for essential models
            try:
                call_command("migrate", "--run-syncdb", verbosity=0, interactive=False)
            except Exception:
                # If even syncdb fails, continue without database setup
                pass

        # Create basic test data programmatically since fixtures may fail during setup

        # Create default locale
        try:
            from apps.i18n.models import Locale

            Locale.objects.get_or_create(
                code="en",
                defaults={
                    "name": "English",
                    "native_name": "English",
                    "is_default": True,
                    "is_active": True,
                },
            )
        except Exception:
            pass  # Ignore if model doesn't exist yet

        # Create basic users
        try:
            User = get_user_model()
            User.objects.get_or_create(
                email="admin@example.com",
                defaults={
                    "name": "Admin User",
                    "is_staff": True,
                    "is_superuser": True,
                    "role": "admin",
                },
            )
        except Exception:
            pass  # Ignore if model doesn't exist yet

        # Set up basic groups and permissions
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        member_group, _ = Group.objects.get_or_create(name="Member")
        readonly_group, _ = Group.objects.get_or_create(name="ReadOnly")


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Allow database access for all tests automatically
    This reduces boilerplate in test functions
    """
    pass


@pytest.fixture(autouse=True)
def performance_tracking(request):
    """Track test performance automatically"""
    test_name = request.node.nodeid
    start_time = time.time()
    test_start_times[test_name] = start_time

    # Track memory at test start
    import psutil

    process = psutil.Process()
    start_memory = process.memory_info().rss / 1024 / 1024  # MB

    yield

    # Calculate test duration and memory delta
    end_time = time.time()
    duration = end_time - start_time
    end_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_delta = end_memory - start_memory

    test_performance[test_name].append(
        {"duration": duration, "memory_delta_mb": memory_delta, "timestamp": end_time}
    )

    # Warn about slow tests
    if duration > 5.0:
        print(f"\n⚠️  Slow test detected: {test_name} took {duration:.2f}s")

    # Warn about memory-heavy tests
    if memory_delta > 50:  # More than 50MB increase
        print(f"\n⚠️  Memory-heavy test: {test_name} used {memory_delta:.1f}MB")


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatic cleanup after each test"""
    yield

    # Clear Django cache
    from django.core.cache import cache

    cache.clear()

    # Force garbage collection
    gc.collect()

    # Reset any global state
    try:
        from django.core.mail import outbox

        if hasattr(outbox, "clear"):
            outbox.clear()
    except ImportError:
        pass


@pytest.fixture(scope="session")
def performance_report():
    """Generate performance report at end of session"""
    yield

    if test_performance:
        # Calculate statistics
        total_tests = len(test_performance)
        slow_tests = [
            (name, max(metrics, key=lambda x: x["duration"]))
            for name, metrics in test_performance.items()
            if any(m["duration"] > 1.0 for m in metrics)
        ]

        # Sort by duration
        slow_tests.sort(key=lambda x: x[1]["duration"], reverse=True)

        print(f"\n{'='*60}")
        print(f"TEST PERFORMANCE SUMMARY")
        print(f"{'='*60}")
        print(f"Total tests: {total_tests}")
        print(f"Slow tests (>1s): {len(slow_tests)}")

        if slow_tests:
            print(f"\nTop 10 slowest tests:")
            for i, (test_name, metrics) in enumerate(slow_tests[:10], 1):
                print(f"{i:2d}. {test_name}: {metrics['duration']:.2f}s")


# Enhanced User Fixtures
@pytest.fixture
def user_factory():
    """Factory for creating test users with different attributes"""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    created_users = []

    def create_user(**kwargs):
        defaults = {
            "email": f"test{len(created_users)}@example.com",
            "password": "testpass123",
            "name": f"Test User {len(created_users)}",
            "is_active": True,
        }
        defaults.update(kwargs)

        user = User.objects.create_user(**defaults)
        created_users.append(user)
        return user

    yield create_user

    # Cleanup
    User.objects.filter(id__in=[u.id for u in created_users]).delete()


@pytest.fixture
def user(user_factory):
    """Standard test user"""
    return user_factory()


@pytest.fixture
def admin_user(user_factory):
    """Admin user with all permissions"""
    from django.contrib.auth.models import Group

    user = user_factory(
        email="admin@example.com", name="Admin User", is_staff=True, is_superuser=True
    )

    # Add to admin group
    admin_group, _ = Group.objects.get_or_create(name="Admin")
    user.groups.add(admin_group)

    return user


@pytest.fixture
def manager_user(user_factory):
    """Manager user with limited permissions"""
    from django.contrib.auth.models import Group

    user = user_factory(email="manager@example.com", name="Manager User", is_staff=True)

    # Add to manager group
    manager_group, _ = Group.objects.get_or_create(name="Manager")
    user.groups.add(manager_group)

    return user


@pytest.fixture
def member_user(user_factory):
    """Regular member user"""
    from django.contrib.auth.models import Group

    user = user_factory(email="member@example.com", name="Member User")

    # Add to member group
    member_group, _ = Group.objects.get_or_create(name="Member")
    user.groups.add(member_group)

    return user


@pytest.fixture
def readonly_user(user_factory):
    """Read-only user"""
    from django.contrib.auth.models import Group

    user = user_factory(email="readonly@example.com", name="ReadOnly User")

    # Add to readonly group
    readonly_group, _ = Group.objects.get_or_create(name="ReadOnly")
    user.groups.add(readonly_group)

    return user


# API Client Fixtures
@pytest.fixture
def api_client():
    """Unauthenticated API client"""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def auth_client(user):
    """Authenticated API client with regular user"""
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(admin_user):
    """Authenticated API client with admin user"""
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def manager_client(manager_user):
    """Authenticated API client with manager user"""
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=manager_user)
    return client


# Database and Transaction Fixtures
@pytest.fixture
def transactional_db():
    """
    Provide transactional database access
    Useful for testing database constraints and rollbacks
    """
    from django.test import TransactionTestCase

    return TransactionTestCase


@pytest.fixture
def isolated_db():
    """
    Each test gets a completely isolated database
    Slower but provides perfect isolation
    """
    from django.db import transaction

    with transaction.atomic():
        sid = transaction.savepoint()
        yield
        transaction.savepoint_rollback(sid)


# File and Media Fixtures
@pytest.fixture
def temp_media_root():
    """Temporary media root directory"""
    from django.test import override_settings

    with tempfile.TemporaryDirectory() as temp_dir:
        with override_settings(MEDIA_ROOT=temp_dir):
            yield temp_dir


@pytest.fixture
def sample_image():
    """Create a sample image file for testing"""
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile

    from PIL import Image

    # Create a simple test image
    image = Image.new("RGB", (100, 100), color="red")
    image_io = io.BytesIO()
    image.save(image_io, format="PNG")
    image_io.seek(0)

    return SimpleUploadedFile(
        "test_image.png", image_io.getvalue(), content_type="image/png"
    )


@pytest.fixture
def sample_file():
    """Create a sample text file for testing"""
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(
        "test_file.txt",
        b"This is a test file content for testing file uploads.",
        content_type="text/plain",
    )


@pytest.fixture
def sample_json_file():
    """Create a sample JSON file for testing"""
    from django.core.files.uploadedfile import SimpleUploadedFile

    data = {
        "test": True,
        "message": "This is a test JSON file",
        "items": [1, 2, 3, 4, 5],
    }

    return SimpleUploadedFile(
        "test_data.json",
        json.dumps(data).encode("utf-8"),
        content_type="application/json",
    )


# Service and Configuration Fixtures
@pytest.fixture(autouse=True)
def celery_eager(settings):
    """Configure Celery to execute tasks synchronously"""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture
def mock_external_service():
    """Mock external service calls"""
    mocks = {}

    # Common external services to mock
    services = [
        "requests.get",
        "requests.post",
        "requests.put",
        "requests.delete",
        "smtplib.SMTP",
        "boto3.client",
    ]

    for service in services:
        try:
            mock = patch(service)
            mocks[service] = mock.start()
        except ImportError:
            # Service might not be available
            pass

    yield mocks

    # Stop all mocks
    for mock in mocks.values():
        mock.stop()


@pytest.fixture
def test_settings():
    """Test-specific settings override"""
    from django.test import override_settings

    test_settings = {
        "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
        "PASSWORD_HASHERS": [
            "django.contrib.auth.hashers.MD5PasswordHasher",  # Fast for tests
        ],
        "CACHES": {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        },
        "DATABASES": {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
    }

    with override_settings(**test_settings):
        yield test_settings


# Performance and Memory Fixtures
@pytest.fixture
def memory_tracker():
    """Track memory usage during test"""
    import psutil

    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    class MemoryTracker:
        def __init__(self):
            self.initial = initial_memory
            self.samples = []

        def sample(self, label=""):
            current = process.memory_info().rss / 1024 / 1024
            self.samples.append(
                {
                    "label": label,
                    "memory_mb": current,
                    "delta_mb": current - self.initial,
                }
            )
            return current

        def report(self):
            if self.samples:
                print(f"\nMemory usage samples:")
                for sample in self.samples:
                    print(
                        f"  {sample['label']}: {sample['memory_mb']:.1f}MB (Δ{sample['delta_mb']:+.1f}MB)"
                    )

    tracker = MemoryTracker()
    yield tracker

    # Final sample
    tracker.sample("end")


@pytest.fixture
def benchmark_timer():
    """Simple benchmark timer for performance testing"""

    class Timer:
        def __init__(self):
            self.times = {}

        def start(self, label="default"):
            self.times[label] = time.time()

        def end(self, label="default"):
            if label in self.times:
                duration = time.time() - self.times[label]
                print(f"\n⏱️  {label}: {duration:.3f}s")
                return duration
            return 0

        def __enter__(self):
            self.start()
            return self

        def __exit__(self, *args):
            self.end()

    return Timer()


# Test Data Fixtures
@pytest.fixture
def groups():
    """Create default user groups with permissions"""
    from django.contrib.auth.models import Group, Permission

    admin_group, _ = Group.objects.get_or_create(name="Admin")
    manager_group, _ = Group.objects.get_or_create(name="Manager")
    member_group, _ = Group.objects.get_or_create(name="Member")
    readonly_group, _ = Group.objects.get_or_create(name="ReadOnly")

    # Add permissions to groups
    if not admin_group.permissions.exists():
        admin_group.permissions.set(Permission.objects.all())

    return {
        "admin": admin_group,
        "manager": manager_group,
        "member": member_group,
        "readonly": readonly_group,
    }


@pytest.fixture
def bulk_users(user_factory):
    """Create multiple users for bulk testing"""

    def create_bulk_users(count=10, **kwargs):
        users = []
        for i in range(count):
            user_kwargs = {
                "email": f"bulk_user_{i}@example.com",
                "name": f"Bulk User {i}",
                **kwargs,
            }
            users.append(user_factory(**user_kwargs))
        return users

    return create_bulk_users


# Async Test Support
@pytest.fixture
def async_client():
    """Async test client for testing async views"""
    try:
        from django.test import AsyncClient

        return AsyncClient()
    except ImportError:
        # AsyncClient not available in older Django versions
        return None


# Test Isolation Fixtures
@pytest.fixture
def isolated_test():
    """
    Complete test isolation - useful for tests that might
    have side effects on other tests
    """
    # Store original state
    original_cache = cache._cache.copy() if hasattr(cache._cache, "copy") else {}

    yield

    # Restore state
    cache.clear()
    if hasattr(cache._cache, "update"):
        cache._cache.update(original_cache)


# Debugging and Development Fixtures
@pytest.fixture
def debug_test():
    """Enable debug mode for specific test"""
    from django.test import override_settings

    with override_settings(DEBUG=True):
        yield


@pytest.fixture
def capture_queries():
    """Capture and analyze database queries during test"""
    from django.db import connection
    from django.test import override_settings

    with override_settings(DEBUG=True):
        queries_before = len(connection.queries)
        yield
        queries_after = len(connection.queries)

        query_count = queries_after - queries_before
        if query_count > 10:
            print(f"\n⚠️  High query count: {query_count} queries executed")

        # Show recent queries
        recent_queries = connection.queries[queries_before:]
        for i, query in enumerate(recent_queries[-5:], 1):
            print(f"Query {i}: {query['sql'][:100]}...")


# Custom markers for pytest
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "api: mark test as API test")
    config.addinivalue_line("markers", "security: mark test as security test")
    config.addinivalue_line("markers", "performance: mark test as performance test")


def pytest_runtest_setup(item):
    """Run before each test item"""
    # Skip slow tests if running fast profile
    if "slow" in item.keywords and item.config.getoption("--fast"):
        pytest.skip("skipping slow test in fast mode")


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--fast", action="store_true", default=False, help="run fast tests only"
    )
