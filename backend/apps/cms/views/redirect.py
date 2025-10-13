import csv
import io

from django.db.models import Q
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.cms.models import Redirect
from apps.cms.serializers.redirect import RedirectSerializer


@extend_schema_view(
    list=extend_schema(summary="List redirects", tags=["Redirects"]),
    create=extend_schema(summary="Create redirect", tags=["Redirects"]),
    retrieve=extend_schema(summary="Get redirect details", tags=["Redirects"]),
    update=extend_schema(summary="Update redirect", tags=["Redirects"]),
    partial_update=extend_schema(
        summary="Partially update redirect", tags=["Redirects"]
    ),
    destroy=extend_schema(summary="Delete redirect", tags=["Redirects"]),
)
class RedirectViewSet(viewsets.ModelViewSet):
    """ViewSet for managing SEO redirects"""

    queryset = Redirect.objects.all()

    serializer_class = RedirectSerializer

    # Default permission for write operations
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        Allow public read access, require auth for write operations.
        """
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def list(self, request, *args, **kwargs):
        """List redirects with caching"""
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def retrieve(self, request, *args, **kwargs):
        """Retrieve redirect with caching"""
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        """Filter redirects based on query parameters"""

        queryset = self.queryset

        # Search in paths

        search = self.request.query_params.get("search")

        if search:

            queryset = queryset.filter(
                Q(from_path__icontains=search) | Q(to_path__icontains=search)
            )

        # Filter by redirect type

        redirect_type = self.request.query_params.get("type")

        if redirect_type:

            queryset = queryset.filter(status=redirect_type)

        return queryset

    def perform_create(self, serializer):
        """Create redirect instance"""

        serializer.save()

    @extend_schema(
        summary="Lookup redirect by path",
        description="Public endpoint to lookup a redirect for a given path. Heavily cached for performance.",
        parameters=[
            {
                "name": "path",
                "in": "query",
                "description": "The path to lookup (e.g., /old-page)",
                "required": True,
                "schema": {"type": "string"},
            }
        ],
        responses={
            200: {
                "description": "Redirect found",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "from_path": {"type": "string"},
                                "to_path": {"type": "string"},
                                "status": {"type": "integer"},
                            },
                        }
                    }
                },
            },
            404: {"description": "No redirect found for this path"},
        },
    )
    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    @method_decorator(cache_page(60 * 30))  # Cache for 30 minutes
    def lookup(self, request):
        """
        Public endpoint to lookup redirects by path.
        Optimized for performance with heavy caching and minimal database queries.
        """
        path = request.query_params.get("path")

        if not path:
            return Response(
                {"error": "path parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optimize query: only fetch necessary fields and filter for active redirects
        redirect = (
            Redirect.objects.only("from_path", "to_path", "status")
            .filter(from_path=path, is_active=True)
            .first()
        )

        if not redirect:
            # Return 404 but with cache headers so 404s are also cached
            response = Response(
                {"error": "No redirect found"},
                status=status.HTTP_404_NOT_FOUND,
            )
            # Cache 404s for a shorter duration (5 minutes)
            response["Cache-Control"] = "public, max-age=300"
            return response

        # Return minimal response
        response = Response(
            {
                "from_path": redirect.from_path,
                "to_path": redirect.to_path,
                "status": redirect.status,
            }
        )

        # Add CDN-friendly cache headers
        response["Cache-Control"] = "public, max-age=1800"  # 30 minutes

        return response

    @extend_schema(
        summary="Test redirect",
        description="Test if a redirect is working correctly",
        responses={200: {"description": "Test result", "type": "object"}},
    )
    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """Test redirect functionality"""

        redirect = self.get_object()

        result = redirect.test()

        return Response(result)

    @extend_schema(
        summary="Import redirects from CSV",
        description="Import multiple redirects from CSV file",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"file": {"type": "string", "format": "binary"}},
            }
        },
        responses={201: {"description": "Import started"}},
    )
    @action(detail=False, methods=["post"])
    def import_csv(self, request):
        """Import redirects from CSV file"""

        if "file" not in request.FILES:

            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES["file"]

        if not file.name.endswith(".csv"):

            return Response(
                {"error": "File must be a CSV"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:

            # Read and validate CSV

            content = file.read().decode("utf-8")

            csv_reader = csv.DictReader(io.StringIO(content))

            # Expected columns: from_path, to_path, status, notes

            required_columns = ["from_path", "to_path"]

            if not csv_reader.fieldnames or not all(
                col in csv_reader.fieldnames for col in required_columns
            ):

                return Response(
                    {
                        "error": f"CSV must contain columns: {', '.join(required_columns)}"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Track import statistics

            sum(1 for row in csv.DictReader(io.StringIO(content)))

            # Process rows

            successful_imports = 0

            failed_imports = 0

            errors = []

            csv_reader = csv.DictReader(io.StringIO(content))

            for row_num, row in enumerate(csv_reader, 1):

                try:

                    # Create redirect from CSV row

                    redirect_data = {
                        "from_path": row.get(
                            "from_path", row.get("source_path", "")
                        ).strip(),
                        "to_path": row.get(
                            "to_path", row.get("destination_url", "")
                        ).strip(),
                        "status": int(row.get("status", row.get("redirect_type", 301))),
                        "notes": row.get("notes", ""),
                        "is_active": row.get("is_active", "true").lower() == "true",
                    }

                    # Validate and create redirect

                    serializer = RedirectSerializer(data=redirect_data)

                    if serializer.is_valid():

                        serializer.save()

                        successful_imports += 1

                    else:

                        failed_imports += 1

                        """errors.append(f"Row {row_num}: {serializer.errors}")"""

                except Exception as e:

                    failed_imports += 1

                    """errors.append(f"Row {row_num}: {str(e)}")"""

            # Import completed

            return Response(
                {
                    "message": "Import completed",
                    "successful_imports": successful_imports,
                    "failed_imports": failed_imports,
                    "errors": errors[:10],  # Return first 10 errors
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:

            return Response(
                {"error": f"Failed to process CSV: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Export redirects to CSV",
        description="Export all redirects as CSV file",
        responses={
            200: {
                "description": "CSV file",
                "content": {"text/csv": {"schema": {"type": "string"}}},
            }
        },
    )
    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        """Export redirects to CSV file"""

        response = HttpResponse(content_type="text/csv")

        response["Content-Disposition"] = 'attachment; filename="redirects.csv"'

        writer = csv.writer(response)

        writer.writerow(
            [
                "from_path",
                "to_path",
                "status",
                "is_active",
                "hits",
                "notes",
                "created_at",
            ]
        )

        for redirect in self.get_queryset():

            writer.writerow(
                [
                    redirect.from_path,
                    redirect.to_path,
                    redirect.status,
                    redirect.is_active,
                    redirect.hits,
                    redirect.notes,
                    redirect.created_at.isoformat(),
                ]
            )

        return response

    @extend_schema(
        summary="Validate redirect rules",
        description="Validate redirect rules for conflicts and loops",
        responses={200: {"description": "Validation results"}},
    )
    @action(detail=False, methods=["post"])
    def validate(self, request):
        """Validate redirect rules for conflicts and loops"""

        redirects = self.get_queryset()

        issues = []

        # Check for duplicate source paths

        source_paths = {}

        for redirect in redirects:

            if redirect.source_path in source_paths:
                issues.append(
                    {
                        "type": "duplicate_source",
                        "message": f"Duplicate source path: {redirect.source_path}",
                        "redirects": [source_paths[redirect.source_path], redirect.id],
                    }
                )

            else:

                source_paths[redirect.source_path] = redirect.id

        # Check for potential redirect loops (simplified check)

        for redirect in redirects:

            if redirect.source_path == redirect.destination_url:
                issues.append(
                    {
                        "type": "self_loop",
                        "message": f"Redirect loops to itself: {redirect.source_path}",
                        "redirect_id": redirect.id,
                    }
                )

        return Response(
            {
                "total_redirects": redirects.count(),
                "issues_found": len(issues),
                "issues": issues,
            }
        )
