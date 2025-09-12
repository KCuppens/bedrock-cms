

Test data factories for all applications.



Provides Factory Boy factories for creating consistent test data across

all test suites with realistic, varied data generation.



# Import base factories first to avoid circular dependencies

from .base import BaseFactory, UserFactory



# Then import other factories

try:

    from .accounts import (  # noqa: F401

        ScopedLocaleFactory,

        ScopedSectionFactory,

        UserProfileFactory,

    )

except ImportError:



try:

    from .analytics import AnalyticsEventFactory

except ImportError:



try:

    from .cms import PageFactory

except ImportError:



try:

    from .i18n import LocaleFactory, TranslationUnitFactory

except ImportError:



try:

    from .media import MediaItemFactory

except ImportError:



__all__ = [

    "BaseFactory",

    "UserFactory",

    "UserProfileFactory",

    "PageFactory",

    "MediaItemFactory",

    "TranslationUnitFactory",

    "AnalyticsEventFactory",

    "LocaleFactory",

]

