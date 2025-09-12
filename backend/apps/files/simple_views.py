import logging

from django.core.files.storage import default_storage

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import FileUpload
from .serializers import FileUploadSerializer

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(summary="List files"),
    create=extend_schema(summary="Upload file"),
    retrieve=extend_schema(summary="Get file details"),
    destroy=extend_schema(summary="Delete file"),
)
class SimpleFileUploadViewSet(viewsets.ModelViewSet):
    """Simple file upload ViewSet using Django best practices"""

    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """Get files for the current user"""
        return FileUpload.objects.filter(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        """Handle file upload with detailed logging"""
        logger.info("=== FILE UPLOAD REQUEST ===")
        logger.info(f"User: {request.user}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"FILES: {list(request.FILES.keys())}")
        logger.info(f"POST: {dict(request.POST)}")

        # Check if file exists in request
        if "file" not in request.FILES:
            logger.error("No file in request.FILES")
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES["file"]
        logger.info(
            f"File: name={file.name}, size={file.size}, content_type={file.content_type}"
        )

        try:
            # Basic file validation
            if file.size > 50 * 1024 * 1024:  # 50MB limit
                return Response(
                    {"error": "File too large (max 50MB)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create the file upload record
            file_upload = FileUpload.objects.create(
                original_filename=file.name,
                file_size=file.size,
                mime_type=file.content_type or "application/octet-stream",
                created_by=request.user,
                is_public=request.POST.get("is_public", "false").lower() == "true",
                description=request.POST.get("description", ""),
                tags=request.POST.get("tags", ""),
            )

            # Save the actual file
            file_path = f"uploads/{request.user.id}/{file_upload.id}_{file.name}"
            saved_path = default_storage.save(file_path, file)

            # Update the record with file path
            file_upload.file_path = saved_path
            file_upload.save()

            logger.info(
                f"File upload successful: ID={file_upload.id}, Path={saved_path}"
            )

            # Return response
            serializer = self.get_serializer(file_upload)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"File upload failed: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Upload failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
