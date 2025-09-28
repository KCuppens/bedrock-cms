import logging
import os
import uuid

from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.pagination import StandardResultsSetPagination
from apps.core.permissions import IsOwnerOrAdmin, IsOwnerOrPublic

from .image_processing import ImageProcessor
from .models import FileUpload
from .serializers import (
    FileUploadCreateSerializer,
    FileUploadSerializer,
    SignedUrlSerializer,
    ThumbnailConfigSerializer,
    ThumbnailGenerationResponseSerializer,
    ThumbnailStatusSerializer,
)
from .services import FileService
from .tasks import get_thumbnail_generation_status, queue_thumbnail_generation

logger = logging.getLogger(__name__)


class FileUploadViewSet(viewsets.ModelViewSet):
    """ViewSet for file upload management"""

    queryset = FileUpload.objects.all()
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = StandardResultsSetPagination
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
        if self.request.user.is_authenticated:
            # Check if user is admin
            if self.request.user.is_staff or (
                hasattr(self.request.user, "is_admin") and self.request.user.is_admin()
            ):
                # Admins can see all files
                pass
            else:
                # Authenticated users can see their own files and public files
                queryset = queryset.filter(
                    Q(created_by=self.request.user) | Q(is_public=True)
                )
        else:
            # Anonymous users can only see public files
            queryset = queryset.filter(is_public=True)

        # Filter by file type

        file_type = self.request.query_params.get("file_type")

        if file_type:

            queryset = queryset.filter(file_type=file_type)

        # Filter by public status

        is_public = self.request.query_params.get("is_public")

        if is_public is not None:

            queryset = queryset.filter(is_public=is_public.lower() == "true")

        # Filter by tags

        tags = self.request.query_params.get("tags")

        if tags:

            queryset = queryset.filter(tags__icontains=tags)

        return queryset

    def get_serializer_class(self):  # noqa: C901
        """Return appropriate serializer class"""

        if self.action == "create":

            return FileUploadCreateSerializer

        return FileUploadSerializer

    def list(self, request):
        """List files"""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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

        # Check permissions - only owner or admin can update
        if not self._can_modify_file(request.user, instance):
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        # For metadata updates, we only allow certain fields

        allowed_fields = ["description", "tags", "is_public"]

        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = self.get_serializer(instance, data=update_data, partial=partial)

        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific file"""
        instance = self.get_object()

        # Check if user can access this file
        if not self._can_access_file(request.user, instance):
            raise Http404("File not found")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def _can_access_file(self, user, file_instance):
        """Check if user can access the file."""
        # Public files can be accessed by anyone
        if file_instance.is_public:
            return True

        # Must be authenticated for private files
        if not user.is_authenticated:
            return False

        # File owner can access
        if file_instance.created_by == user:
            return True

        # Admin can access
        if user.is_staff or (hasattr(user, "is_admin") and user.is_admin()):
            return True

        return False

    def _can_modify_file(self, user, file_instance):
        """Check if user can modify the file."""
        if not user.is_authenticated:
            return False

        # File owner can modify
        if file_instance.created_by == user:
            return True

        # Admin can modify
        if user.is_staff or (hasattr(user, "is_admin") and user.is_admin()):
            return True

        return False

    def destroy(self, request, *args, **kwargs):
        """Delete a file"""
        instance = self.get_object()

        # Check permissions - only owner or admin can delete
        if not self._can_modify_file(request.user, instance):
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        return super().destroy(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):  # noqa: C901
        """Update file metadata (PATCH)"""

        kwargs["partial"] = True

        return self.update(request, *args, **kwargs)

    @extend_schema(
        summary="Get download URL",
        description="Get a signed download URL for the file.",
    )
    @action(
        detail=True,
        methods=["get"],
        permission_classes=[permissions.AllowAny],
        url_path="download-url",
    )
    def download_url(self, request, pk=None):  # noqa: C901
        """Get download URL for file"""

        # For download_url, we need to bypass the queryset filtering to check permissions manually
        try:
            file_upload = FileUpload.objects.get(pk=pk)
        except FileUpload.DoesNotExist:
            raise Http404("File not found")

        # Check access permissions
        if not self._can_access_file(request.user, file_upload):

            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        # Check expiration
        if file_upload.is_expired:
            return Response(
                {"error": "File has expired"}, status=status.HTTP_403_FORBIDDEN
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
        if not self._can_access_file(request.user, file_upload):

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

        except Exception as e:

            logger.error("Error serving file %s: %s", file_upload.id, str(e))

            raise Http404("Error accessing file")

    @extend_schema(
        summary="Get signed upload URL",
        description="Get a signed URL for direct upload to storage (S3/MinIO).",
    )
    @action(detail=False, methods=["post"], url_path="signed-upload-url")
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
    @action(detail=False, methods=["get"], url_path="my-files")
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
    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def public(self, request):  # noqa: C901
        """Get public files"""

        queryset = FileUpload.objects.filter(is_public=True)

        page = self.paginate_queryset(queryset)

        if page is not None:

            serializer = self.get_serializer(page, many=True)

            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)

    @extend_schema(
        summary="Generate thumbnails",
        description="Generate thumbnails for an image file based on block configuration.",
        request=ThumbnailConfigSerializer,
        responses={
            200: ThumbnailGenerationResponseSerializer,
            400: "Bad Request",
            403: "Forbidden",
            404: "Not Found",
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="generate-thumbnails",
    )
    def generate_thumbnails(self, request, pk=None):
        """Generate thumbnails for an image based on block configuration"""
        file_upload = self.get_object()

        # Check access permissions
        if not self._can_access_file(request.user, file_upload):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        # Validate that it's an image file
        if not file_upload.is_image:
            return Response(
                {"error": "File is not an image"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate request data
        serializer = ThumbnailConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        config = serializer.validated_data
        processor = ImageProcessor()
        config_hash = processor.generate_config_hash(config)

        # Check if thumbnails already exist
        if file_upload.has_thumbnails_for_config(config_hash):
            existing_urls = file_upload.get_thumbnails_for_config(config_hash)
            return Response(
                {
                    "status": "completed",
                    "config_hash": config_hash,
                    "urls": existing_urls,
                }
            )

        # Check if generation is in progress
        generation_status = get_thumbnail_generation_status(
            str(file_upload.id), config_hash
        )
        if generation_status and generation_status.get("status") == "processing":
            return Response(
                {
                    "status": "processing",
                    "config_hash": config_hash,
                    "message": "Thumbnail generation is already in progress",
                }
            )

        # Queue thumbnail generation
        try:
            task_id = queue_thumbnail_generation(
                str(file_upload.id), config, priority=config.get("priority", False)
            )

            return Response(
                {
                    "status": "processing",
                    "config_hash": config_hash,
                    "task_id": task_id,
                    "message": "Thumbnail generation queued",
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to queue thumbnail generation for file {file_upload.id}: {e}"
            )
            return Response(
                {"error": "Failed to queue thumbnail generation"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Get thumbnail status",
        description="Get the status of thumbnail generation for a specific configuration.",
        responses={
            200: ThumbnailStatusSerializer,
            404: "Not Found",
        },
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="thumbnail-status/(?P<config_hash>[a-f0-9]{8})",
    )
    def thumbnail_status(self, request, pk=None, config_hash=None):
        """Get thumbnail generation status for a specific configuration"""
        file_upload = self.get_object()

        # Check access permissions
        if not self._can_access_file(request.user, file_upload):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        # Check if thumbnails exist in database
        if file_upload.has_thumbnails_for_config(config_hash):
            urls = file_upload.get_thumbnails_for_config(config_hash)
            return Response(
                {
                    "file_id": str(file_upload.id),
                    "config_hash": config_hash,
                    "status": "completed",
                    "urls": urls,
                }
            )

        # Check generation status from cache
        generation_status = get_thumbnail_generation_status(
            str(file_upload.id), config_hash
        )

        if generation_status:
            response_data = {
                "file_id": str(file_upload.id),
                "config_hash": config_hash,
                "status": generation_status.get("status", "unknown"),
            }

            if "urls" in generation_status:
                response_data["urls"] = generation_status["urls"]

            if "error" in generation_status:
                response_data["error"] = generation_status["error"]

            return Response(response_data)

        # No status found
        return Response(
            {
                "file_id": str(file_upload.id),
                "config_hash": config_hash,
                "status": "not_found",
                "message": "No thumbnail generation found for this configuration",
            }
        )

    @extend_schema(
        summary="Get thumbnail URL",
        description="Get the URL for a specific thumbnail size.",
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="thumbnail/(?P<config_hash>[a-f0-9]{8})/(?P<size_name>[^/]+)",
    )
    def thumbnail_url(self, request, pk=None, config_hash=None, size_name=None):
        """Get URL for a specific thumbnail"""
        file_upload = self.get_object()

        # Check access permissions
        if not self._can_access_file(request.user, file_upload):
            return Response(
                {"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN
            )

        # Get thumbnails for the configuration
        thumbnails = file_upload.get_thumbnails_for_config(config_hash)

        if not thumbnails:
            return Response(
                {"error": "Thumbnails not found for this configuration"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Look for the specific size
        thumbnail_url = None
        for key, url in thumbnails.items():
            if key == size_name or key.startswith(f"{size_name}_"):
                thumbnail_url = url
                break

        if not thumbnail_url:
            return Response(
                {"error": f"Thumbnail size '{size_name}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"url": thumbnail_url, "size_name": size_name, "config_hash": config_hash}
        )

    @extend_schema(
        summary="Bulk upload files",
        description="Upload multiple files at once.",
    )
    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser],
        url_path="bulk-upload",
    )
    def bulk_upload(self, request):
        """Bulk upload multiple files"""
        files = request.FILES.getlist("files")
        if not files:
            return Response(
                {"error": "No files provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        results = []
        errors = []

        for file in files:
            try:
                # Validate file
                validation = FileService.validate_file(file)
                if not validation["valid"]:
                    errors.append(
                        {"filename": file.name, "errors": validation["errors"]}
                    )
                    continue

                # Upload file
                file_upload = FileService.upload_file(
                    file=file,
                    user=request.user,
                    description=f"Bulk uploaded: {file.name}",
                )

                serializer = FileUploadSerializer(
                    file_upload, context={"request": request}
                )
                results.append(serializer.data)

            except Exception as e:
                errors.append({"filename": file.name, "errors": [str(e)]})

        return Response(
            {
                "uploaded": results,
                "errors": errors,
                "total_files": len(files),
                "successful": len(results),
                "failed": len(errors),
            },
            status=status.HTTP_201_CREATED if results else status.HTTP_400_BAD_REQUEST,
        )


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

    except Exception as e:

        logger.error("Error serving file %s: %s", file_upload.id, str(e))

        raise Http404("Error accessing file")
