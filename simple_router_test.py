#!/usr/bin/env python3
"""
Simple test to check what URLs the DefaultRouter generates
"""
import sys
sys.path.append('backend')

# Minimal imports without Django setup
from rest_framework.routers import DefaultRouter

# Create a simple router and check the patterns it generates
router = DefaultRouter()

# Let's examine what patterns would be generated for a viewset with actions
print("=== DefaultRouter Pattern Analysis ===")
print("For a ViewSet registered as 'posts' with basename 'blogpost':")
print()

# Simulate what the router would generate
base_patterns = [
    "^posts/$",                     # List/Create
    "^posts/(?P<pk>[^/.]+)/$",     # Detail
]

action_patterns = [
    "^posts/(?P<pk>[^/.]+)/publish/$",    # Custom action: publish
    "^posts/(?P<pk>[^/.]+)/unpublish/$",  # Custom action: unpublish
    "^posts/(?P<pk>[^/.]+)/duplicate/$",  # Custom action: duplicate
]

print("Expected base patterns:")
for pattern in base_patterns:
    print(f"  {pattern}")

print("\nExpected action patterns:")
for pattern in action_patterns:
    print(f"  {pattern}")

print("\nWith /api/v1/blog/ prefix, these become:")
for pattern in base_patterns + action_patterns:
    full_pattern = f"/api/v1/blog/{pattern.replace('^', '').replace('$', '')}"
    print(f"  {full_pattern}")

print("\nSo the unpublish URL should be:")
print("  /api/v1/blog/posts/1/unpublish/")
