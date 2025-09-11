"""
Blog URL configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'blog'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'posts', views.BlogPostViewSet, basename='blogpost')
router.register(r'categories', views.BlogCategoryViewSet, basename='category')
router.register(r'tags', views.BlogTagViewSet, basename='tag')
router.register(r'settings', views.BlogSettingsViewSet, basename='blogsettings')

urlpatterns = [
    # ViewSet URLs - Note: prefix is handled by main urls.py
    path('', include(router.urls)),
    
    # Legacy function-based view URLs for backwards compatibility
    path('settings/', views.blog_settings_list, name='settings-list'),
    path('settings/<str:locale_code>/', views.blog_settings_api, name='settings-detail'),
]

# Alternative URL patterns for different API structures
# You can uncomment these if you prefer a flatter URL structure:

# urlpatterns += [
#     # Alternative flat structure
#     path('api/v1/blog-posts/', include(router.urls)),
#     path('api/v1/blog-categories/', views.BlogCategoryViewSet.as_view({'get': 'list', 'post': 'create'})),
#     path('api/v1/blog-tags/', views.BlogTagViewSet.as_view({'get': 'list', 'post': 'create'})),
# ]