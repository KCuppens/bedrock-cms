#!/usr/bin/env python3
"""
Debug script to print all registered blog URLs
"""
import os
import sys
import django

# Add the backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.config.settings.local')
django.setup()

from rest_framework.routers import DefaultRouter
from apps.blog import views

print("=== Blog URL Debug ===\n")

# Create router and register viewsets
router = DefaultRouter()
router.register(r"posts", views.BlogPostViewSet, basename="blogpost")
router.register(r"categories", views.BlogCategoryViewSet, basename="category")
router.register(r"tags", views.BlogTagViewSet, basename="tag")
router.register(r"settings", views.BlogSettingsViewSet, basename="blogsettings")

print("Generated URL patterns:")
for url_pattern in router.urls:
    print(f"  {url_pattern.pattern}")

print("\nBlogPostViewSet actions:")
viewset = views.BlogPostViewSet()
print(f"  Available actions: {list(viewset.get_extra_actions())}")

print("\nChecking specific ViewSet methods:")
for action_name in ['publish', 'unpublish', 'duplicate']:
    if hasattr(viewset, action_name):
        method = getattr(viewset, action_name)
        print(f"  ✅ {action_name}: {method}")
        # Check if it's decorated as an action
        if hasattr(method, 'mapping'):
            print(f"    -> HTTP methods: {method.mapping}")
        if hasattr(method, 'detail'):
            print(f"    -> Detail: {method.detail}")
        if hasattr(method, 'url_path'):
            print(f"    -> URL path: {method.url_path}")
    else:
        print(f"  ❌ {action_name}: Not found")