"""
API views for Schema.org structured data management.
"""

import json
import os
from pathlib import Path

from django.http import JsonResponse

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from apps.blog.models import BlogPost
from apps.cms.models import Page
from apps.cms.schema_utils import SchemaGenerator, generate_page_schema
from apps.cms.schema_validators import SchemaValidator, validate_page_schema


class SchemaViewSet(ViewSet):
    """ViewSet for schema generation and management."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List available schema types",
        description="Get a list of supported Schema.org types with their specifications",
        responses={200: OpenApiResponse(description="List of schema types")},
    )
    @action(detail=False, methods=["get"])
    def types(self, request):
        """Get list of supported schema types."""
        schema_types = SchemaValidator.get_schema_types()
        return Response({"types": schema_types, "count": len(schema_types)})

    @extend_schema(
        summary="Get schema templates",
        description="Get JSON templates for various schema types",
        parameters=[
            OpenApiParameter(
                name="type",
                description="Schema type (e.g., article, blog_posting, webpage)",
                required=False,
                type=str,
            )
        ],
        responses={200: OpenApiResponse(description="Schema templates")},
    )
    @action(detail=False, methods=["get"])
    def templates(self, request):
        """Get schema templates."""
        schema_type = request.query_params.get("type")

        # Get templates directory
        templates_dir = Path(__file__).parent.parent / "schema_templates"

        if schema_type:
            # Return specific template
            template_file = templates_dir / f"{schema_type}.json"
            if template_file.exists():
                with open(template_file, "r") as f:
                    template = json.load(f)
                return Response({"type": schema_type, "template": template})
            else:
                return Response(
                    {"error": f"Template not found for type: {schema_type}"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # Return all templates
            templates = {}
            if templates_dir.exists():
                for template_file in templates_dir.glob("*.json"):
                    template_name = template_file.stem
                    with open(template_file, "r") as f:
                        templates[template_name] = json.load(f)

            return Response({"templates": templates, "count": len(templates)})

    @extend_schema(
        summary="Validate schema",
        description="Validate a Schema.org JSON-LD structure",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "schema": {
                        "type": "object",
                        "description": "Schema object to validate",
                    },
                    "strict": {
                        "type": "boolean",
                        "description": "Treat warnings as errors",
                        "default": False,
                    },
                },
                "required": ["schema"],
            }
        },
        responses={
            200: OpenApiResponse(description="Validation results"),
            400: OpenApiResponse(description="Invalid request"),
        },
    )
    @action(detail=False, methods=["post"])
    def validate(self, request):
        """Validate a schema object."""
        schema = request.data.get("schema")
        strict = request.data.get("strict", False)

        if not schema:
            return Response(
                {"error": "schema field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_valid, errors, warnings = SchemaValidator.validate(schema, strict=strict)

        return Response({"valid": is_valid, "errors": errors, "warnings": warnings})


class PageSchemaView(APIView):
    """API view for page-specific schema operations."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Generate schema for a page",
        description="Auto-generate appropriate Schema.org structured data for a page",
        parameters=[
            OpenApiParameter(
                name="id",
                location=OpenApiParameter.PATH,
                description="Page ID",
                required=True,
                type=int,
            )
        ],
        responses={
            200: OpenApiResponse(description="Generated schema"),
            404: OpenApiResponse(description="Page not found"),
        },
    )
    def get(self, request, id):
        """Generate schema for a specific page."""
        try:
            page = Page.objects.get(id=id)
        except Page.DoesNotExist:
            return Response(
                {"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Generate schemas
        schemas = generate_page_schema(page, request)

        # Validate generated schemas
        is_valid, errors, warnings = SchemaValidator.validate(schemas)

        return Response(
            {
                "schemas": schemas,
                "validation": {
                    "valid": is_valid,
                    "errors": errors,
                    "warnings": warnings,
                },
            }
        )

    @extend_schema(
        summary="Save generated schema to page",
        description="Generate and save schema to the page's SEO field",
        parameters=[
            OpenApiParameter(
                name="id",
                location=OpenApiParameter.PATH,
                description="Page ID",
                required=True,
                type=int,
            )
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "auto_generate": {
                        "type": "boolean",
                        "description": "Whether to auto-generate schema",
                        "default": True,
                    },
                    "schema_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Schema types to generate",
                    },
                },
            }
        },
        responses={
            200: OpenApiResponse(description="Schema saved successfully"),
            404: OpenApiResponse(description="Page not found"),
        },
    )
    def post(self, request, id):
        """Generate and save schema to page."""
        try:
            page = Page.objects.get(id=id)
        except Page.DoesNotExist:
            return Response(
                {"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Generate schemas
        schemas = generate_page_schema(page, request)

        # Convert to new format
        schema_objects = []
        for i, schema in enumerate(schemas):
            schema_objects.append(
                {
                    "id": f"schema-{i}",
                    "type": schema.get("@type", "Unknown"),
                    "auto_generated": True,
                    "data": schema,
                }
            )

        # Update page SEO field
        if not isinstance(page.seo, dict):
            page.seo = {}

        page.seo["schemas"] = schema_objects
        page.save(update_fields=["seo"])

        return Response(
            {"message": "Schema saved successfully", "schemas": schema_objects}
        )


class BlogPostSchemaView(APIView):
    """API view for blog post-specific schema operations."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Generate schema for a blog post",
        description="Auto-generate BlogPosting schema for a blog post",
        parameters=[
            OpenApiParameter(
                name="id",
                location=OpenApiParameter.PATH,
                description="Blog Post ID",
                required=True,
                type=int,
            )
        ],
        responses={
            200: OpenApiResponse(description="Generated schema"),
            404: OpenApiResponse(description="Blog post not found"),
        },
    )
    def get(self, request, id):
        """Generate schema for a specific blog post."""
        try:
            post = BlogPost.objects.get(id=id)
        except BlogPost.DoesNotExist:
            return Response(
                {"error": "Blog post not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Generate blog posting schema
        schema = SchemaGenerator.generate_blog_posting_schema(post, request)

        # Validate
        is_valid, errors, warnings = SchemaValidator.validate(schema)

        return Response(
            {
                "schema": schema,
                "validation": {
                    "valid": is_valid,
                    "errors": errors,
                    "warnings": warnings,
                },
            }
        )

    @extend_schema(
        summary="Save generated schema to blog post",
        description="Generate and save schema to the blog post's SEO field",
        parameters=[
            OpenApiParameter(
                name="id",
                location=OpenApiParameter.PATH,
                description="Blog Post ID",
                required=True,
                type=int,
            )
        ],
        responses={
            200: OpenApiResponse(description="Schema saved successfully"),
            404: OpenApiResponse(description="Blog post not found"),
        },
    )
    def post(self, request, id):
        """Generate and save schema to blog post."""
        try:
            post = BlogPost.objects.get(id=id)
        except BlogPost.DoesNotExist:
            return Response(
                {"error": "Blog post not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Generate schema
        schema = SchemaGenerator.generate_blog_posting_schema(post, request)

        # Update post SEO field
        if not isinstance(post.seo, dict):
            post.seo = {}

        post.seo["schemas"] = [
            {
                "id": "schema-0",
                "type": "BlogPosting",
                "auto_generated": True,
                "data": schema,
            }
        ]
        post.save(update_fields=["seo"])

        return Response({"message": "Schema saved successfully", "schema": schema})
