"""
URL configuration for i18n app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'locales', views.LocaleViewSet, basename='locales')
router.register(r'translation-units', views.TranslationUnitViewSet, basename='translation-units')
router.register(r'ui-messages', views.UiMessageViewSet, basename='ui-messages')
router.register(r'ui-message-translations', views.UiMessageTranslationViewSet, basename='ui-message-translations')
router.register(r'glossary', views.TranslationGlossaryViewSet, basename='glossary')
router.register(r'translations/queue', views.TranslationQueueViewSet, basename='translation-queue')
router.register(r'translations/history', views.TranslationHistoryViewSet, basename='translation-history')

# The bundle endpoint is now handled by the UiMessageViewSet.bundle action
# Access it via: /api/v1/i18n/ui-messages/bundle/{locale_code}/

urlpatterns = [
    path('', include(router.urls)),
    # Legacy URL for compatibility - redirect to new endpoint
    path('ui/messages/<str:locale_code>.json', 
         views.UiMessageViewSet.as_view({'get': 'bundle'}), 
         name='ui-messages-bundle'),
]