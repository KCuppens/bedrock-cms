import logging

from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.permissions import IsOwnerOrAdmin

from .models import FileUpload
from .serializers import (
from .services import FileService
            from django.db.models import Q
        import os
        import uuid
    FileUploadCreateSerializer,
    FileUploadSerializer,
    SignedUrlSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="List files",
        description="Get a list of files. Users can see their own files and public files.",
    ),
    create=extend_schema(
        summary="Upload file",
        description="Upload a new file. The authenticated user will be set as the owner.",
    ),
    retrieve=extend_schema(
        summary="Get file details",
        description="Get file metadata. Users can only access their own files or public files.",
    ),
    destroy=extend_schema(
        summary="Delete file",
        description="Delete a file. Users can only delete their own files.",
    ),
)
class FileUploadViewSet(viewsets.ModelViewSet):
    """ViewSet for file upload management"""

    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = [
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "trace",
    ]

    def get_queryset(self):  # noqa: C901
        """Get files based on user permissions"""
        queryset = FileUpload.objects.select_related("created_by", "updated_by")

        # Users can see their own files and public files
        if not self.request.user.is_admin():

            queryset = queryset.filter(
                Q(created_by=self.request.user) | Q(is_public=True)
            )

        # Filter by file type
        file_type = self.request.query_params.get("file_type")
        if file_type:
            queryset = queryset.filter(file_type=file_type)

        # Filter by public status
        is_public = self.request.query_params.get("is_public")
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public.lower() == "true")

        return queryset

    def get_serializer_class(self):  # noqa: C901
        """Return appropriate serializer class"""
        if self.action == "create":
            return FileUploadCreateSerializer
        return FileUploadSerializer

    def create(self, request, *args, **kwargs):  # noqa: C901
        """Create a new file upload"""
        if "file" not in request.FILES:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get the serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file = request.FILES["file"]

        # Validate file
        validation = FileService.validate_file(file)
        if not validation["valid"]:
            return Response(
                {"errors": validation["errors"]}, status=status.HTTP_400_BAD_REQUEST
            )

        # Upload file
        file_upload = FileService.upload_file(
            file=file,
            user=request.user,
            description=serializer.validated_data.get("description", ""),
            tags=serializer.validated_data.get("tags", ""),
            is_public=serializer.validated_data.get("is_public", False),
            expires_at=serializer.validated_data.get("expires_at"),
        )

        # Return response
        response_serializer = FileUploadSerializer(
            file_upload, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):  # noqa: C901
        """Update file metadata (PUT)"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        # For metadata updates, we only allow certain fields
        allowed_fields = ["description", "tags", "is_public"]
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = self.get_serializer(instance, data=update_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):  # noqa: C901
        """Update file metadata (PATCH)"""
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(
        summary="Get download URL",
        description="Get a signed download URL for the file.",
    )
    @action(detail=True, methods=["get"])
    def download_url(self, request, pk=None):  # noqa: C901
        """Get download URL for file"""
        file_upload = self.get_object()

        # Check access permissions
        if not file_upload.can_access(request.user):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        # Get download URL
        download_url = file_upload.get_download_url()

        return Response(
            {
                "download_url": download_url,
                "expires_in": 3600,  # 1 hour
                "filename": file_upload.original_filename,
            }
        )

    @extend_schema(summary="Download file", description="Download the file directly.")
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):  # noqa: C901
        """Download file directly"""
        file_upload = self.get_object()

        # Check access permissions
        if not file_upload.can_access(request.user):
            raise Http404("File not found")

        # Check if file exists
        if not default_storage.exists(file_upload.storage_path):
            raise Http404("File not found in storage")

        # Increment download counter
        file_upload.increment_download_count()

        try:
            # Open file from storage
            file_obj = default_storage.open(file_upload.storage_path)

            # Create response
            response = FileResponse(
                file_obj,
                content_type=file_upload.mime_type,
                filename=file_upload.original_filename,
            )

            return response

        except Exception:
            logger.error("Error serving file %s: {str(e)}", file_upload.id)
            raise Http404("Error accessing file")

    @extend_schema(
        summary="Get signed upload URL",
        description="Get a signed URL for direct upload to storage (S3/MinIO).",
    )
    @action(detail=False, methods=["post"])
    def signed_upload_url(self, request):  # noqa: C901
        """Get signed upload URL"""
        serializer = SignedUrlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        filename = serializer.validated_data["filename"]
        content_type = serializer.validated_data.get("content_type")
        max_size = serializer.validated_data.get("max_size", 10 * 1024 * 1024)  # 10MB

        # Generate storage path

        file_extension = os.path.splitext(filename)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        storage_path = f"uploads/{request.user.id}/{unique_filename}"

        # Get signed upload URL
        upload_data = FileService.get_upload_url(
            storage_path=storage_path,
            expires_in=3600,
            content_type=content_type,
            max_size=max_size,
        )

        return Response(
            {
                "upload_url": upload_data["url"],
                "fields": upload_data.get("fields", {}),
                "storage_path": storage_path,
                "expires_in": 3600,
            }
        )

    @extend_schema(
        summary="Get my files",
        description="Get all files uploaded by the current user.",
    )
    @action(detail=False, methods=["get"])
    def my_files(self, request):  # noqa: C901
        """Get files uploaded by current user"""
        queryset = self.get_queryset().filter(created_by=request.user)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Get public files", description="Get all public files.")
    @action(detail=False, methods=["get"])
    def public(self, request):  # noqa: C901
        """Get public files"""
        queryset = self.get_queryset().filter(is_public=True)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# Standalone view for direct file downloads (used in fallback URLs)
def file_download_view(request, file_id):  # noqa: C901
    """Direct file download view"""
    file_upload = get_object_or_404(FileUpload, id=file_id)

    # Check access permissions
    if not file_upload.can_access(request.user):
        raise Http404("File not found")

    # Check if file exists
    if not default_storage.exists(file_upload.storage_path):
        raise Http404("File not found in storage")

    # Increment download counter
    file_upload.increment_download_count()

    try:
        # Open file from storage
        file_obj = default_storage.open(file_upload.storage_path)

        # Create response
        response = FileResponse(
            file_obj,
            content_type=file_upload.mime_type,
            filename=file_upload.original_filename,
        )

        return response

    except Exception:
        logger.error("Error serving file %s: {str(e)}", file_upload.id)
        raise Http404("Error accessing file")
