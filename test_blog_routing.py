#!/usr/bin/env python3
"""
Test blog routing and ViewSet configuration
"""
import sys
import os
import django

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.config.settings.local')
django.setup()

from apps.blog.models import BlogPost
from apps.blog.views import BlogPostViewSet
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

def test_blog_routing():
    print("=== Testing Blog Post ViewSet ===\n")

    # Check if blog posts exist
    posts = BlogPost.objects.all()
    print(f"Total blog posts in database: {posts.count()}")
    for post in posts:
        print(f"  - ID: {post.id}, Title: {post.title}, Status: {post.status}")
    print()

    # Create a request factory
    factory = RequestFactory()

    # Test list view
    print("Testing list view:")
    request = factory.get('/api/v1/blog/posts/')
    request.user = AnonymousUser()

    viewset = BlogPostViewSet()
    viewset.setup(request, pk=None)
    viewset.action = 'list'

    queryset = viewset.get_queryset()
    print(f"  Queryset count: {queryset.count()}")
    for post in queryset:
        print(f"    - ID: {post.id}, Title: {post.title}, Status: {post.status}")
    print()

    # Test retrieve view
    print("Testing retrieve view:")
    request = factory.get('/api/v1/blog/posts/1/')
    request.user = AnonymousUser()

    viewset = BlogPostViewSet()
    viewset.setup(request, pk='1')
    viewset.action = 'retrieve'

    try:
        queryset = viewset.get_queryset()
        print(f"  Retrieve queryset count: {queryset.count()}")

        # Try to get the specific object
        obj = viewset.get_object()
        print(f"  Found object: ID {obj.id}, Title: {obj.title}")
    except Exception as e:
        print(f"  Error getting object: {e}")
    print()

    # Check permissions
    print("Testing permissions:")
    permissions = viewset.get_permissions()
    print(f"  Permissions for retrieve action: {[type(p).__name__ for p in permissions]}")

if __name__ == "__main__":
    test_blog_routing()
