"""
Test data factories for all applications.

Provides Factory Boy factories for creating consistent test data across
all test suites with realistic, varied data generation.
"""

# Import base factories first to avoid circular dependencies
from .base import BaseFactory, UserFactory, AdminUserFactory, StaffUserFactory

# Then import other factories
try:
    from .accounts import *
except ImportError:
    pass

try:
    from .analytics import *
except ImportError:
    pass

try:
    from .cms import *
except ImportError:
    pass

try:
    from .i18n import *
except ImportError:
    pass

try:
    from .media import *
except ImportError:
    pass

__all__ = [
    "BaseFactory",
    "UserFactory",
    "PageFactory",
    "MediaItemFactory",
    "TranslationUnitFactory",
    "AnalyticsEventFactory",
]
