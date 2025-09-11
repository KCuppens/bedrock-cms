"""
Core application URLs
"""

from django.urls import path

from .views import version_info, version_simple

app_name = "core"

urlpatterns = [
    path("version/", version_info, name="version-info"),
    path("version/simple/", version_simple, name="version-simple"),
]
