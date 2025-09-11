"""
Test data factories for all applications.

Provides Factory Boy factories for creating consistent test data across
all test suites with realistic, varied data generation.
"""

try:
    from .base import *
    from .accounts import *
    from .cms import *
    from .i18n import *
    from .media import *
    from .analytics import *
except ImportError:
    # Handle missing dependencies gracefully
    pass

__all__ = [
    "UserFactory",
    "LocaleFactory",
    "PageFactory",
    "MediaItemFactory",
    "TranslationUnitFactory",
    "AnalyticsEventFactory",
]
