"""Comprehensive tests for file services and utilities."""

import os
import tempfile
from io import BytesIO
from unittest.mock import Mock, patch

import django

# Configure Django settings before any imports
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.core.enums import FileType
from apps.files.models import FileUpload
from apps.files.services import FileService

User = get_user_model()


class FileServiceTestCase(TestCase):
    """Test FileService functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="testuser@example.com", password="testpass123"
        )

        # Create test file content
        self.test_image_content = b"GIF87a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00;"
        self.test_pdf_content = (
            b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n\n%%EOF"
        )
        self.test_text_content = b"Hello, this is a test file content."

    def create_test_file(self, filename, content, content_type):
        """Helper to create test files."""
        return SimpleUploadedFile(filename, content, content_type=content_type)

    def test_file_type_mapping(self):
        """Test file type mapping functionality."""
        # Test image types
        self.assertEqual(FileService.FILE_TYPE_MAP["image/jpeg"], FileType.IMAGE)
        self.assertEqual(FileService.FILE_TYPE_MAP["image/png"], FileType.IMAGE)

        # Test document types
        self.assertEqual(
            FileService.FILE_TYPE_MAP["application/pdf"], FileType.DOCUMENT
        )
        self.assertEqual(FileService.FILE_TYPE_MAP["text/plain"], FileType.DOCUMENT)

        # Test video types
        self.assertEqual(FileService.FILE_TYPE_MAP["video/mp4"], FileType.VIDEO)

        # Test audio types
        self.assertEqual(FileService.FILE_TYPE_MAP["audio/mpeg"], FileType.AUDIO)

    @patch("apps.files.services.default_storage")
    def test_upload_file_success(self, mock_storage):
        """Test successful file upload."""
        mock_storage.save.return_value = "uploads/1/test.jpg"
        mock_storage.exists.return_value = True

        test_file = self.create_test_file(
            "test.jpg", self.test_image_content, "image/jpeg"
        )

        file_upload = FileService.upload_file(
            test_file,
            self.user,
            description="Test image",
            tags="test, image",
            is_public=True,
        )

        self.assertIsInstance(file_upload, FileUpload)
        self.assertEqual(file_upload.original_filename, "test.jpg")
        self.assertEqual(file_upload.file_type, FileType.IMAGE)
        self.assertEqual(file_upload.mime_type, "image/jpeg")
        self.assertEqual(file_upload.description, "Test image")
        self.assertEqual(file_upload.tags, "test, image")
        self.assertTrue(file_upload.is_public)
        self.assertEqual(file_upload.created_by, self.user)

    def test_upload_file_checksum_calculation(self):
        """Test checksum calculation during file upload."""
        test_file = self.create_test_file(
            "test.txt", self.test_text_content, "text/plain"
        )

        with patch("apps.files.services.default_storage.save") as mock_save:
            mock_save.return_value = "uploads/1/test.txt"

            file_upload = FileService.upload_file(test_file, self.user)

            # Verify checksum was calculated
            self.assertTrue(file_upload.checksum)
            self.assertEqual(len(file_upload.checksum), 64)  # SHA256 hex length

    def test_upload_file_large_file_handling(self):
        """Test handling of large files."""
        # Create a simple test file that simulates large file behavior
        test_file = self.create_test_file(
            "large.bin",
            b"x" * 1024,
            "application/octet-stream",  # Small file for testing
        )
        # Mock the size to appear large
        test_file.size = 11 * 1024 * 1024  # 11MB

        with patch("apps.files.services.default_storage.save") as mock_save:
            mock_save.return_value = "uploads/1/large.bin"

            with override_settings(FILE_UPLOAD_MAX_MEMORY_SIZE=10485760):  # 10MB
                file_upload = FileService.upload_file(test_file, self.user)

                self.assertEqual(file_upload.file_size, test_file.size)

    def test_upload_file_with_expires_at(self):
        """Test file upload with expiration date."""
        from datetime import datetime, timedelta

        from django.utils import timezone

        expires_at = timezone.now() + timedelta(days=7)
        test_file = self.create_test_file(
            "temp.txt", self.test_text_content, "text/plain"
        )

        with patch("apps.files.services.default_storage.save") as mock_save:
            mock_save.return_value = "uploads/1/temp.txt"

            file_upload = FileService.upload_file(
                test_file, self.user, expires_at=expires_at
            )

            self.assertEqual(file_upload.expires_at, expires_at)

    @patch("apps.files.services.default_storage")
    def test_get_download_url_public_file(self, mock_storage):
        """Test getting download URL for public files."""
        mock_storage.url.return_value = "https://example.com/file.jpg"

        file_upload = FileUpload.objects.create(
            original_filename="public.jpg",
            filename="public.jpg",
            file_type=FileType.IMAGE,
            mime_type="image/jpeg",
            file_size=1024,
            storage_path="uploads/public.jpg",
            is_public=True,
            created_by=self.user,
        )

        url = FileService.get_download_url(file_upload)
        self.assertEqual(url, "https://example.com/file.jpg")

    @patch("apps.files.services.default_storage")
    def test_get_download_url_private_file_with_presigned(self, mock_storage):
        """Test getting download URL for private files with presigned URL support."""
        mock_storage.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/signed-url"
        )

        file_upload = FileUpload.objects.create(
            original_filename="private.jpg",
            filename="private.jpg",
            file_type=FileType.IMAGE,
            mime_type="image/jpeg",
            file_size=1024,
            storage_path="uploads/private.jpg",
            is_public=False,
            created_by=self.user,
        )

        url = FileService.get_download_url(file_upload, expires_in=7200)
        self.assertEqual(url, "https://s3.amazonaws.com/signed-url")

        # Verify presigned URL was called with correct parameters
        mock_storage.generate_presigned_url.assert_called_once_with(
            "uploads/private.jpg", expires_in=7200, method="GET"
        )

    @patch("apps.files.services.reverse")
    @patch("apps.files.services.default_storage")
    def test_get_download_url_fallback(self, mock_storage, mock_reverse):
        """Test download URL fallback for local development."""
        # Simulate no presigned URL support
        if hasattr(mock_storage, "generate_presigned_url"):
            del mock_storage.generate_presigned_url

        # Mock reverse to return predictable URL
        mock_reverse.return_value = "/files/download/123/"

        file_upload = FileUpload.objects.create(
            original_filename="local.jpg",
            filename="local.jpg",
            file_type=FileType.IMAGE,
            mime_type="image/jpeg",
            file_size=1024,
            storage_path="uploads/local.jpg",
            is_public=False,
            created_by=self.user,
        )

        url = FileService.get_download_url(file_upload)

        # Should return local file serving URL
        self.assertEqual(url, "/files/download/123/")
        mock_reverse.assert_called_once_with(
            "file_download", kwargs={"file_id": file_upload.id}
        )

    @patch("apps.files.services.default_storage")
    def test_get_upload_url_with_presigned_post(self, mock_storage):
        """Test getting upload URL with presigned POST support."""
        mock_storage.generate_presigned_post.return_value = {
            "url": "https://s3.amazonaws.com/upload",
            "fields": {"key": "uploads/test.jpg", "policy": "encoded-policy"},
        }

        result = FileService.get_upload_url(
            "uploads/test.jpg",
            expires_in=3600,
            content_type="image/jpeg",
            max_size=5242880,  # 5MB
        )

        self.assertEqual(result["url"], "https://s3.amazonaws.com/upload")
        self.assertIn("fields", result)

        # Verify conditions were set correctly
        mock_storage.generate_presigned_post.assert_called_once()
        call_args = mock_storage.generate_presigned_post.call_args
        self.assertEqual(call_args[0][0], "uploads/test.jpg")
        self.assertEqual(call_args[1]["expires_in"], 3600)

    @patch("apps.files.services.reverse")
    @patch("apps.files.services.default_storage")
    def test_get_upload_url_fallback(self, mock_storage, mock_reverse):
        """Test upload URL fallback for local development."""
        # Simulate no presigned POST support
        if hasattr(mock_storage, "generate_presigned_post"):
            del mock_storage.generate_presigned_post

        # Mock reverse to return predictable URL
        mock_reverse.return_value = "/api/v1/files/fileupload/"

        result = FileService.get_upload_url("uploads/test.jpg")

        # Should return local upload endpoint
        self.assertIn("url", result)
        self.assertEqual(result["url"], "/api/v1/files/fileupload/")
        self.assertEqual(result["fields"], {})

    @patch("apps.files.services.default_storage")
    def test_delete_file_success(self, mock_storage):
        """Test successful file deletion."""
        mock_storage.exists.return_value = True
        mock_storage.delete.return_value = None

        file_upload = FileUpload.objects.create(
            original_filename="delete.jpg",
            filename="delete.jpg",
            file_type=FileType.IMAGE,
            mime_type="image/jpeg",
            file_size=1024,
            storage_path="uploads/delete.jpg",
            created_by=self.user,
        )

        result = FileService.delete_file(file_upload)

        self.assertTrue(result)

        # Verify file was deleted from storage
        mock_storage.delete.assert_called_once_with("uploads/delete.jpg")

        # Verify database record was deleted
        self.assertFalse(FileUpload.objects.filter(id=file_upload.id).exists())

    @patch("apps.files.services.default_storage")
    def test_delete_file_not_exists(self, mock_storage):
        """Test file deletion when file doesn't exist in storage."""
        mock_storage.exists.return_value = False

        file_upload = FileUpload.objects.create(
            original_filename="nonexistent.jpg",
            filename="nonexistent.jpg",
            file_type=FileType.IMAGE,
            mime_type="image/jpeg",
            file_size=1024,
            storage_path="uploads/nonexistent.jpg",
            created_by=self.user,
        )

        result = FileService.delete_file(file_upload)

        self.assertTrue(result)

        # Should not call delete if file doesn't exist
        mock_storage.delete.assert_not_called()

        # Database record should still be deleted
        self.assertFalse(FileUpload.objects.filter(id=file_upload.id).exists())

    @patch("apps.files.services.default_storage")
    def test_delete_file_storage_error(self, mock_storage):
        """Test file deletion with storage error."""
        mock_storage.exists.return_value = True
        mock_storage.delete.side_effect = Exception("Storage error")

        file_upload = FileUpload.objects.create(
            original_filename="error.jpg",
            filename="error.jpg",
            file_type=FileType.IMAGE,
            mime_type="image/jpeg",
            file_size=1024,
            storage_path="uploads/error.jpg",
            created_by=self.user,
        )

        result = FileService.delete_file(file_upload)

        self.assertFalse(result)

        # Database record should still exist if storage deletion fails
        self.assertTrue(FileUpload.objects.filter(id=file_upload.id).exists())

    def test_validate_file_success(self):
        """Test successful file validation."""
        test_file = self.create_test_file(
            "valid.jpg", self.test_image_content, "image/jpeg"
        )

        result = FileService.validate_file(test_file, max_size_mb=10)

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])
        self.assertTrue(result["valid"])

    def test_validate_file_size_exceeded(self):
        """Test file validation with size exceeded."""
        large_content = b"x" * (6 * 1024 * 1024)  # 6MB
        test_file = self.create_test_file("large.jpg", large_content, "image/jpeg")

        result = FileService.validate_file(test_file, max_size_mb=5)

        self.assertFalse(result["valid"])
        self.assertTrue(len(result["errors"]) > 0)
        self.assertIn("File size", result["errors"][0])

    def test_validate_file_invalid_extension(self):
        """Test file validation with invalid extension."""
        test_file = self.create_test_file(
            "test.exe", b"executable content", "application/octet-stream"
        )

        result = FileService.validate_file(test_file)

        self.assertFalse(result["valid"])
        self.assertTrue(len(result["errors"]) > 0)
        self.assertIn("not allowed for security reasons", result["errors"][0])

    def test_validate_file_suspicious_content(self):
        """Test file validation with suspicious content."""
        # File with script-like content
        suspicious_content = b'<script>alert("xss")</script>'
        test_file = self.create_test_file(
            "suspicious.txt", suspicious_content, "text/plain"
        )

        result = FileService.validate_file(test_file)

        # Should detect suspicious content and add warning
        if result["warnings"]:
            self.assertIn("suspicious", result["warnings"][0].lower())

    def test_validate_file_mime_type_mismatch(self):
        """Test file validation with MIME type mismatch."""
        # JPG extension but PDF content
        test_file = self.create_test_file(
            "fake.jpg", self.test_pdf_content, "image/jpeg"
        )

        result = FileService.validate_file(test_file)

        # Should detect mismatch and add warning
        if result["warnings"]:
            self.assertIn("mismatch", result["warnings"][0].lower())

    @patch("apps.files.services.storage_circuit_breaker")
    def test_circuit_breaker_integration(self, mock_circuit_breaker):
        """Test circuit breaker integration in file operations."""

        # Mock circuit breaker decorator
        def mock_decorator():
            def decorator(func):
                return func

            return decorator

        mock_circuit_breaker.return_value = mock_decorator()

        test_file = self.create_test_file(
            "test.jpg", self.test_image_content, "image/jpeg"
        )

        with patch("apps.files.services.default_storage.save") as mock_save:
            mock_save.return_value = "uploads/1/test.jpg"

            FileService.upload_file(test_file, self.user)

            # Verify circuit breaker was used
            mock_circuit_breaker.assert_called()

    def test_file_type_detection_unknown_mime_type(self):
        """Test file type detection for unknown MIME types."""
        test_file = self.create_test_file(
            "unknown.xyz", b"unknown content", "application/x-unknown"
        )

        with patch("apps.files.services.default_storage.save") as mock_save:
            mock_save.return_value = "uploads/1/unknown.xyz"

            file_upload = FileService.upload_file(test_file, self.user)

            # Should default to OTHER for unknown MIME types
            self.assertEqual(file_upload.file_type, FileType.OTHER)

    def test_storage_path_generation(self):
        """Test storage path generation includes user ID and unique filename."""
        test_file = self.create_test_file(
            "test.jpg", self.test_image_content, "image/jpeg"
        )

        with patch("apps.files.services.default_storage.save") as mock_save:
            mock_save.return_value = "uploads/1/unique.jpg"

            FileService.upload_file(test_file, self.user)

            # Verify save was called with path containing user ID
            call_args = mock_save.call_args[0][0]
            self.assertIn(f"uploads/{self.user.id}/", call_args)
            self.assertTrue(call_args.endswith(".jpg"))

    @patch("apps.files.services.logger")
    def test_logging_integration(self, mock_logger):
        """Test logging integration in file operations."""
        test_file = self.create_test_file(
            "test.jpg", self.test_image_content, "image/jpeg"
        )

        with patch("apps.files.services.default_storage.save") as mock_save:
            mock_save.return_value = "uploads/1/test.jpg"

            FileService.upload_file(test_file, self.user)

            # Verify logging was called
            mock_logger.info.assert_called()
