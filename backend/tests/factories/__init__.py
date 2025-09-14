"""Test data factories for all applications."""

"""Provides Factory Boy factories for creating consistent test data across"""

"""all test suites with realistic, varied data generation."""


# Import base factories first to avoid circular dependencies

from .base import AdminUserFactory, BaseFactory, StaffUserFactory, UserFactory

# Then import other factories

try:

    from .accounts import (  # noqa: F401
        EditorUserFactory,
        TranslatorUserFactory,
        UserProfileFactory,
    )

except ImportError:
    pass


try:

    from .analytics import EventFactory
    from .analytics import EventFactory as AnalyticsEventFactory
    from .analytics import SessionFactory

except ImportError:
    pass


try:

    from .cms import (
        CategoryFactory,
        DraftPageFactory,
        LocaleFactory,
        PageFactory,
        PublishedPageFactory,
        TagFactory,
    )

except ImportError:
    pass


try:

    from .i18n import LocaleFactory, TranslationUnitFactory

except ImportError:
    pass


try:

    from .media import MediaItemFactory

except ImportError:
    pass


__all__ = [
    "BaseFactory",
    "UserFactory",
    "AdminUserFactory",
    "StaffUserFactory",
    "UserProfileFactory",
    "EditorUserFactory",
    "TranslatorUserFactory",
    "PageFactory",
    "PublishedPageFactory",
    "DraftPageFactory",
    "CategoryFactory",
    "TagFactory",
    "MediaItemFactory",
    "TranslationUnitFactory",
    "AnalyticsEventFactory",
    "LocaleFactory",
    "EventFactory",
    "SessionFactory",
]
