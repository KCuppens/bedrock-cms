"""
Core application views
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .version import VersionService


@extend_schema(
    summary="Get application version information",
    description="Returns version, commit, branch, and environment information",
    tags=["System"],
    responses={
        200: {
            "type": "object",
            "properties": {
                "version": {"type": "string", "example": "1.2.3"},
                "commit": {"type": "string", "example": "abc1234"},
                "branch": {"type": "string", "example": "main"},
                "environment": {"type": "string", "example": "production"},
                "dirty": {"type": "boolean", "example": False},
                "ahead": {"type": "integer", "example": 0},
                "build_date": {"type": "string", "example": "2025-01-01T00:00:00"},
                "frontend_version": {"type": "string", "example": "1.0.0"},
                "backend_version": {"type": "string", "example": "1.0.0"},
                "python_version": {"type": "string", "example": "3.9.13"},
            },
        }
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def version_info(request):
    """
    Get application version and environment information.

    This endpoint is public and can be accessed without authentication.
    It provides version tracking information from git and the environment.
    """
    info = VersionService.get_version_info()
    return Response(info, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get simple version string",
    description="Returns a simple version string for display",
    tags=["System"],
    responses={
        200: {
            "type": "object",
            "properties": {"version": {"type": "string", "example": "1.2.3+abc1234"}},
        }
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def version_simple(request):
    """
    Get a simple version string.

    Returns just the version string in a simple format,
    including commit hash if ahead of tag and dirty flag if uncommitted changes.
    """
    version = VersionService.get_simple_version()
    return Response({"version": version}, status=status.HTTP_200_OK)
