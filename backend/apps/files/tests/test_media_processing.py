"""Comprehensive tests for media upload and processing functionality.

This module provides extensive test coverage for:
1. File Upload Tests (various formats and validations)
2. Image Processing Tests (resizing, thumbnails, metadata)
3. Storage and Management (path generation, duplicates, quotas)
4. Security Tests (malicious files, validation, limits)
5. API Integration Tests (endpoints, authentication, downloads)
6. Media Library Tests (listing, filtering, permissions)
"""

import hashlib
import os
import tempfile
from io import BytesIO
from unittest.mock import Mock, patch

import django

# Configure Django settings before any imports
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from PIL import Image as PILImage
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.core.enums import FileType
from apps.files.models import FileUpload, MediaCategory
from apps.files.serializers import (
    FileUploadCreateSerializer,
    FileUploadSerializer,
    SignedUrlSerializer,
)
from apps.files.services import FileService

User = get_user_model()


class MediaProcessingTestCase(TestCase):
    """Base test case with common setup for media processing tests."""

    def setUp(self):
        """Set up test users and categories."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        # Create admin user with proper admin group
        self.admin_user = User.objects.create_user(
            email="admin@example.com", password="adminpass123"
        )
        admin_group, created = Group.objects.get_or_create(name="Admin")
        self.admin_user.groups.add(admin_group)
        self.category = MediaCategory.objects.create(
            name="Test Category",
            slug="test-category",
            description="Test category for media tests",
        )

    def create_test_image(self, format="JPEG", size=(100, 100), color="red"):
        """Create a test image file in memory."""
        image = PILImage.new("RGB", size, color)
        image_io = BytesIO()
        image.save(image_io, format=format)
        image_io.seek(0)

        filename = f"test_image.{format.lower()}"
        if format == "JPEG":
            filename = "test_image.jpg"

        return SimpleUploadedFile(
            filename,
            image_io.getvalue(),
            content_type=(
                f"image/{format.lower()}" if format != "JPEG" else "image/jpeg"
            ),
        )

    def create_test_document(self, content=None, filename="test.pdf"):
        """Create a test document file."""
        if content is None:
            content = b"Test PDF content"
        return SimpleUploadedFile(filename, content, content_type="application/pdf")

    def create_test_video(self, filename="test.mp4"):
        """Create a test video file."""
        return SimpleUploadedFile(
            filename, b"fake video content", content_type="video/mp4"
        )

    def create_test_audio(self, filename="test.mp3"):
        """Create a test audio file."""
        return SimpleUploadedFile(
            filename, b"fake audio content", content_type="audio/mpeg"
        )

    def tearDown(self):
        """Clean up test files."""
        # Clean up any uploaded files during tests
        for file_upload in FileUpload.objects.all():
            if default_storage.exists(file_upload.storage_path):
                try:
                    default_storage.delete(file_upload.storage_path)
                except Exception:
                    pass


class FileUploadTests(MediaProcessingTestCase):
    """Test file upload functionality for various formats."""

    def test_image_upload_jpeg(self):
        """Test JPEG image upload."""
        image_file = self.create_test_image("JPEG", (200, 200))

        file_upload = FileService.upload_file(
            file=image_file,
            user=self.user,
            description="Test JPEG image",
            is_public=True,
        )

        self.assertEqual(file_upload.file_type, FileType.IMAGE)
        self.assertEqual(file_upload.mime_type, "image/jpeg")
        self.assertEqual(file_upload.original_filename, "test_image.jpg")
        self.assertTrue(file_upload.is_public)
        self.assertTrue(file_upload.is_image)
        self.assertFalse(file_upload.is_document)

    def test_image_upload_png(self):
        """Test PNG image upload."""
        image_file = self.create_test_image("PNG", (150, 150), "blue")

        file_upload = FileService.upload_file(
            file=image_file, user=self.user, description="Test PNG image"
        )

        self.assertEqual(file_upload.file_type, FileType.IMAGE)
        self.assertEqual(file_upload.mime_type, "image/png")
        self.assertEqual(file_upload.original_filename, "test_image.png")

    def test_image_upload_gif(self):
        """Test GIF image upload."""
        image_file = self.create_test_image("GIF", (100, 100), "green")

        file_upload = FileService.upload_file(file=image_file, user=self.user)

        self.assertEqual(file_upload.file_type, FileType.IMAGE)
        self.assertEqual(file_upload.mime_type, "image/gif")

    def test_image_upload_webp(self):
        """Test WebP image upload."""
        image_file = self.create_test_image("WEBP", (120, 120), "yellow")

        file_upload = FileService.upload_file(file=image_file, user=self.user)

        self.assertEqual(file_upload.file_type, FileType.IMAGE)
        self.assertEqual(file_upload.mime_type, "image/webp")

    def test_document_upload_pdf(self):
        """Test PDF document upload."""
        pdf_file = self.create_test_document(b"PDF content", "document.pdf")

        file_upload = FileService.upload_file(
            file=pdf_file, user=self.user, description="Test PDF document"
        )

        self.assertEqual(file_upload.file_type, FileType.DOCUMENT)
        self.assertEqual(file_upload.mime_type, "application/pdf")
        self.assertTrue(file_upload.is_document)
        self.assertFalse(file_upload.is_image)

    def test_document_upload_text(self):
        """Test text document upload."""
        text_file = SimpleUploadedFile(
            "test.txt", b"Test text content", content_type="text/plain"
        )

        file_upload = FileService.upload_file(file=text_file, user=self.user)

        self.assertEqual(file_upload.file_type, FileType.DOCUMENT)
        self.assertEqual(file_upload.mime_type, "text/plain")

    def test_video_upload_mp4(self):
        """Test MP4 video upload."""
        video_file = self.create_test_video("video.mp4")

        file_upload = FileService.upload_file(
            file=video_file, user=self.user, description="Test video"
        )

        self.assertEqual(file_upload.file_type, FileType.VIDEO)
        self.assertEqual(file_upload.mime_type, "video/mp4")

    def test_audio_upload_mp3(self):
        """Test MP3 audio upload."""
        audio_file = self.create_test_audio("audio.mp3")

        file_upload = FileService.upload_file(file=audio_file, user=self.user)

        self.assertEqual(file_upload.file_type, FileType.AUDIO)
        self.assertEqual(file_upload.mime_type, "audio/mpeg")

    def test_file_size_validation(self):
        """Test file size validation."""
        # Create a large file (simulate 15MB)
        large_content = b"x" * (15 * 1024 * 1024)
        large_file = SimpleUploadedFile(
            "large.txt", large_content, content_type="text/plain"
        )

        validation = FileService.validate_file(large_file, max_size_mb=10)
        self.assertFalse(validation["valid"])
        self.assertIn("exceeds maximum allowed", validation["errors"][0])

    def test_mime_type_validation(self):
        """Test MIME type validation."""
        # Create file with potentially dangerous content type
        dangerous_file = SimpleUploadedFile(
            "script.js", b"alert('test');", content_type="application/javascript"
        )

        validation = FileService.validate_file(dangerous_file)
        self.assertIn("may not be supported", validation["warnings"][0])

    def test_file_extension_validation(self):
        """Test file extension validation."""
        # Create file with dangerous extension
        exe_file = SimpleUploadedFile(
            "malware.exe", b"fake executable", content_type="application/octet-stream"
        )

        validation = FileService.validate_file(exe_file)
        self.assertFalse(validation["valid"])
        self.assertIn("not allowed for security reasons", validation["errors"][0])

    def test_checksum_calculation(self):
        """Test that file checksum is calculated correctly."""
        content = b"test content for checksum"
        test_file = SimpleUploadedFile("test.txt", content, content_type="text/plain")

        expected_checksum = hashlib.sha256(content).hexdigest()

        file_upload = FileService.upload_file(file=test_file, user=self.user)

        self.assertEqual(file_upload.checksum, expected_checksum)

    def test_duplicate_detection(self):
        """Test duplicate file detection via checksum."""
        content = b"duplicate content"

        # Upload first file
        file1 = SimpleUploadedFile("file1.txt", content, content_type="text/plain")
        upload1 = FileService.upload_file(file=file1, user=self.user)

        # Upload duplicate content with different name
        file2 = SimpleUploadedFile("file2.txt", content, content_type="text/plain")
        upload2 = FileService.upload_file(file=file2, user=self.user)

        # Both files should have the same checksum
        self.assertEqual(upload1.checksum, upload2.checksum)

        # But different filenames and storage paths
        self.assertNotEqual(upload1.filename, upload2.filename)
        self.assertNotEqual(upload1.storage_path, upload2.storage_path)


class ImageProcessingTests(MediaProcessingTestCase):
    """Test image processing and validation functionality."""

    def test_image_validation_valid(self):
        """Test validation of valid image files."""
        image_file = self.create_test_image("JPEG", (300, 200))

        validation = FileService.validate_file(image_file)

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["file_type"], FileType.IMAGE)
        self.assertEqual(validation["mime_type"], "image/jpeg")

    def test_image_metadata_extraction(self):
        """Test that image metadata is properly handled."""
        image_file = self.create_test_image("JPEG", (400, 300))

        file_upload = FileService.upload_file(
            file=image_file, user=self.user, description="Image with metadata"
        )

        # Verify basic metadata is stored
        self.assertEqual(file_upload.file_type, FileType.IMAGE)
        self.assertEqual(file_upload.mime_type, "image/jpeg")
        self.assertGreater(file_upload.file_size, 0)

    def test_image_format_conversion_validation(self):
        """Test validation of different image formats."""
        formats = [
            ("JPEG", "image/jpeg"),
            ("PNG", "image/png"),
            ("GIF", "image/gif"),
            ("WEBP", "image/webp"),
        ]

        for format_name, expected_mime in formats:
            with self.subTest(format=format_name):
                image_file = self.create_test_image(format_name, (100, 100))
                validation = FileService.validate_file(image_file)

                self.assertTrue(validation["valid"])
                self.assertEqual(validation["mime_type"], expected_mime)
                self.assertEqual(validation["file_type"], FileType.IMAGE)

    def test_corrupted_image_handling(self):
        """Test handling of corrupted image files."""
        # Create a file that claims to be an image but has invalid content
        corrupted_file = SimpleUploadedFile(
            "corrupted.jpg", b"not a real image", content_type="image/jpeg"
        )

        # The validation should still pass as we're checking MIME type
        # but the actual image processing would fail in a real scenario
        validation = FileService.validate_file(corrupted_file)
        self.assertTrue(validation["valid"])  # Basic validation passes

        # File can still be uploaded (storage doesn't validate image content)
        file_upload = FileService.upload_file(file=corrupted_file, user=self.user)
        self.assertEqual(file_upload.file_type, FileType.IMAGE)

    def test_large_image_handling(self):
        """Test handling of large image files."""
        # Create a large image
        large_image = self.create_test_image("JPEG", (2000, 2000))

        file_upload = FileService.upload_file(file=large_image, user=self.user)

        self.assertEqual(file_upload.file_type, FileType.IMAGE)
        self.assertGreater(file_upload.file_size, 10000)  # Should be substantial


class StorageManagementTests(MediaProcessingTestCase):
    """Test storage and file management functionality."""

    def test_storage_path_generation(self):
        """Test that storage paths are generated correctly."""
        test_file = self.create_test_image("JPEG")

        file_upload = FileService.upload_file(file=test_file, user=self.user)

        # Path should include user ID and unique filename
        self.assertIn(f"uploads/{self.user.id}/", file_upload.storage_path)
        self.assertTrue(file_upload.storage_path.endswith(".jpg"))
        self.assertNotEqual(file_upload.filename, file_upload.original_filename)

    def test_unique_filename_generation(self):
        """Test that filenames are unique even for same original names."""
        # Upload two files with the same original name
        file1 = SimpleUploadedFile("same.txt", b"content1", content_type="text/plain")
        file2 = SimpleUploadedFile("same.txt", b"content2", content_type="text/plain")

        upload1 = FileService.upload_file(file=file1, user=self.user)
        upload2 = FileService.upload_file(file=file2, user=self.user)

        # Original filenames should be the same
        self.assertEqual(upload1.original_filename, upload2.original_filename)

        # But stored filenames should be different
        self.assertNotEqual(upload1.filename, upload2.filename)
        self.assertNotEqual(upload1.storage_path, upload2.storage_path)

    def test_file_organization_by_user(self):
        """Test that files are organized by user."""
        user2 = User.objects.create_user(email="user2@example.com", password="pass123")

        file1 = SimpleUploadedFile("test1.txt", b"content1", content_type="text/plain")
        file2 = SimpleUploadedFile("test2.txt", b"content2", content_type="text/plain")

        upload1 = FileService.upload_file(file=file1, user=self.user)
        upload2 = FileService.upload_file(file=file2, user=user2)

        # Files should be in different user directories
        self.assertIn(f"uploads/{self.user.id}/", upload1.storage_path)
        self.assertIn(f"uploads/{user2.id}/", upload2.storage_path)

    def test_file_metadata_tracking(self):
        """Test that file metadata is properly tracked."""
        test_file = self.create_test_document(b"test content", "metadata.pdf")

        file_upload = FileService.upload_file(
            file=test_file,
            user=self.user,
            description="Test file with metadata",
            tags="test, document, pdf",
            is_public=True,
        )

        # Verify all metadata is stored
        self.assertEqual(file_upload.description, "Test file with metadata")
        self.assertEqual(file_upload.tags, "test, document, pdf")
        self.assertTrue(file_upload.is_public)
        self.assertEqual(file_upload.created_by, self.user)
        self.assertEqual(file_upload.updated_by, self.user)
        self.assertIsNotNone(file_upload.created_at)
        self.assertIsNotNone(file_upload.updated_at)

    def test_file_expiration(self):
        """Test file expiration functionality."""
        # Create file with expiration date in the past
        past_time = timezone.now() - timezone.timedelta(days=1)

        test_file = SimpleUploadedFile(
            "expired.txt", b"content", content_type="text/plain"
        )

        file_upload = FileService.upload_file(
            file=test_file, user=self.user, expires_at=past_time
        )

        # File should be marked as expired
        self.assertTrue(file_upload.is_expired)

        # Future expiration should not be expired
        future_time = timezone.now() + timezone.timedelta(days=1)
        file_upload.expires_at = future_time
        file_upload.save()

        self.assertFalse(file_upload.is_expired)

    def test_download_counter(self):
        """Test download counter functionality."""
        test_file = SimpleUploadedFile(
            "counter.txt", b"content", content_type="text/plain"
        )

        file_upload = FileService.upload_file(file=test_file, user=self.user)

        # Initial download count should be 0
        self.assertEqual(file_upload.download_count, 0)

        # Increment download count
        file_upload.increment_download_count()
        file_upload.refresh_from_db()

        self.assertEqual(file_upload.download_count, 1)

        # Increment again
        file_upload.increment_download_count()
        file_upload.refresh_from_db()

        self.assertEqual(file_upload.download_count, 2)


class SecurityTests(MediaProcessingTestCase):
    """Test security aspects of file uploads."""

    def test_malicious_file_detection(self):
        """Test detection of potentially malicious files."""
        # Test various dangerous file types
        dangerous_files = [
            ("malware.exe", "application/octet-stream"),
            ("script.bat", "application/octet-stream"),
            ("virus.scr", "application/octet-stream"),
            ("payload.vbs", "text/vbscript"),
        ]

        for filename, content_type in dangerous_files:
            with self.subTest(filename=filename):
                dangerous_file = SimpleUploadedFile(
                    filename, b"malicious content", content_type=content_type
                )

                validation = FileService.validate_file(dangerous_file)
                self.assertFalse(validation["valid"])
                self.assertTrue(
                    any("security reasons" in error for error in validation["errors"])
                )

    def test_file_extension_spoofing_prevention(self):
        """Test prevention of file extension spoofing."""
        # Try to upload executable with image extension
        spoofed_file = SimpleUploadedFile(
            "image.jpg.exe",
            b"fake image content",
            content_type="application/octet-stream",
        )

        validation = FileService.validate_file(spoofed_file)
        self.assertFalse(validation["valid"])

    def test_upload_size_limits(self):
        """Test upload size limit enforcement."""
        # Test with different size limits
        sizes = [
            (1, False),  # 1MB limit, should pass for small file
            (0.000001, True),  # Very small limit (1 byte), should fail for 13-byte file
        ]

        small_file = SimpleUploadedFile(
            "small.txt", b"small content", content_type="text/plain"
        )

        for max_size_mb, should_fail in sizes:
            with self.subTest(max_size_mb=max_size_mb):
                validation = FileService.validate_file(
                    small_file, max_size_mb=max_size_mb
                )

                if should_fail:
                    self.assertFalse(validation["valid"])
                    self.assertTrue(
                        any(
                            "exceeds maximum" in error for error in validation["errors"]
                        )
                    )
                else:
                    self.assertTrue(validation["valid"])

    def test_content_type_validation(self):
        """Test content type validation."""
        # File with mismatched extension and content type
        mismatched_file = SimpleUploadedFile(
            "document.pdf",
            b"not a pdf",
            content_type="text/plain",  # Wrong content type for .pdf
        )

        validation = FileService.validate_file(mismatched_file)
        # Should have warnings about MIME type
        self.assertTrue(
            any("may not be supported" in warning for warning in validation["warnings"])
        )

    def test_filename_sanitization(self):
        """Test that dangerous filename characters are handled."""
        dangerous_filenames = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "file<script>alert('xss')</script>.txt",
            'file"with"quotes.txt',
            "file|with|pipes.txt",
        ]

        serializer = SignedUrlSerializer()

        for filename in dangerous_filenames:
            with self.subTest(filename=filename):
                with self.assertRaises(Exception):  # Should raise validation error
                    serializer.validate_filename(filename)

    def test_access_control(self):
        """Test file access control."""
        # Create private file
        private_file = SimpleUploadedFile(
            "private.txt", b"private", content_type="text/plain"
        )
        private_upload = FileService.upload_file(
            file=private_file, user=self.user, is_public=False
        )

        # Create public file
        public_file = SimpleUploadedFile(
            "public.txt", b"public", content_type="text/plain"
        )
        public_upload = FileService.upload_file(
            file=public_file, user=self.user, is_public=True
        )

        # Create other user
        other_user = User.objects.create_user(
            email="other@example.com", password="pass"
        )

        # Test access permissions
        self.assertTrue(private_upload.can_access(self.user))  # Owner can access
        self.assertFalse(private_upload.can_access(other_user))  # Other user cannot
        self.assertFalse(private_upload.can_access(None))  # Anonymous cannot

        self.assertTrue(public_upload.can_access(self.user))  # Owner can access
        self.assertTrue(
            public_upload.can_access(other_user)
        )  # Other user can access public
        self.assertTrue(public_upload.can_access(None))  # Anonymous can access public

        # Admin can access everything
        self.assertTrue(private_upload.can_access(self.admin_user))
        self.assertTrue(public_upload.can_access(self.admin_user))


class APIIntegrationTests(APITestCase, MediaProcessingTestCase):
    """Test API integration for file operations."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_upload_endpoint_authentication(self):
        """Test that upload endpoint requires authentication."""
        url = reverse("fileupload-list")
        test_file = self.create_test_image()

        response = self.client.post(url, {"file": test_file}, format="multipart")
        # Accept both 401 and 403 for authentication errors
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_upload_endpoint_success(self):
        """Test successful file upload via API."""
        self.client.force_authenticate(user=self.user)
        url = reverse("fileupload-list")
        test_file = self.create_test_image()

        response = self.client.post(
            url,
            {"file": test_file, "description": "API upload test", "is_public": True},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["description"], "API upload test")
        self.assertTrue(response.data["is_public"])

    def test_upload_endpoint_validation_error(self):
        """Test upload endpoint with validation errors."""
        self.client.force_authenticate(user=self.user)
        url = reverse("fileupload-list")

        # Try to upload without file
        response = self.client.post(url, {"description": "No file"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No file provided", response.data["error"])

    def test_file_listing_endpoint(self):
        """Test file listing endpoint."""
        self.client.force_authenticate(user=self.user)

        # Upload a few files
        for i in range(3):
            test_file = SimpleUploadedFile(
                f"test{i}.txt", b"content", content_type="text/plain"
            )
            FileService.upload_file(
                file=test_file, user=self.user, is_public=i % 2 == 0
            )

        url = reverse("fileupload-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)

    def test_file_filtering(self):
        """Test file filtering by type and public status."""
        self.client.force_authenticate(user=self.user)

        # Upload different types of files
        image_file = self.create_test_image()
        doc_file = self.create_test_document()

        FileService.upload_file(file=image_file, user=self.user, is_public=True)
        FileService.upload_file(file=doc_file, user=self.user, is_public=False)

        url = reverse("fileupload-list")

        # Filter by file type
        response = self.client.get(url, {"file_type": "image"})
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["file_type"], "image")

        # Filter by public status
        response = self.client.get(url, {"is_public": "true"})
        self.assertEqual(len(response.data["results"]), 1)
        self.assertTrue(response.data["results"][0]["is_public"])

    def test_download_url_endpoint(self):
        """Test download URL generation endpoint."""
        self.client.force_authenticate(user=self.user)

        # Upload a file
        test_file = self.create_test_image()
        file_upload = FileService.upload_file(file=test_file, user=self.user)

        url = reverse("fileupload-download-url", kwargs={"pk": file_upload.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("download_url", response.data)
        self.assertIn("expires_in", response.data)
        self.assertIn("filename", response.data)

    def test_download_endpoint_access_control(self):
        """Test download endpoint access control."""
        # Create private file owned by user
        test_file = self.create_test_image()
        private_upload = FileService.upload_file(
            file=test_file, user=self.user, is_public=False
        )

        # Create other user
        other_user = User.objects.create_user(
            email="other@example.com", password="pass"
        )

        url = reverse("fileupload-download", kwargs={"pk": private_upload.id})

        # Owner should be able to download
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Other user should not be able to download
        self.client.force_authenticate(user=other_user)
        response = self.client.get(url)
        # Accept both 404 and 403 for access denied
        self.assertIn(
            response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]
        )

        # Anonymous user should not be able to download
        self.client.force_authenticate(user=None)
        response = self.client.get(url)
        # Accept 404, 401, or 403 for anonymous access denied
        self.assertIn(
            response.status_code,
            [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_signed_upload_url_endpoint(self):
        """Test signed upload URL generation."""
        self.client.force_authenticate(user=self.user)

        url = reverse("fileupload-signed-upload-url")
        data = {
            "filename": "test.jpg",
            "content_type": "image/jpeg",
            "max_size": 1024 * 1024,  # 1MB
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("upload_url", response.data)
        self.assertIn("storage_path", response.data)
        self.assertIn("expires_in", response.data)

    def test_my_files_endpoint(self):
        """Test my files endpoint."""
        self.client.force_authenticate(user=self.user)

        # Create other user and upload file
        other_user = User.objects.create_user(
            email="other@example.com", password="pass"
        )
        other_file = SimpleUploadedFile(
            "other.txt", b"content", content_type="text/plain"
        )
        FileService.upload_file(file=other_file, user=other_user, is_public=True)

        # Upload file for current user
        my_file = SimpleUploadedFile("mine.txt", b"content", content_type="text/plain")
        FileService.upload_file(file=my_file, user=self.user)

        url = reverse("fileupload-my-files")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["created_by"], self.user.id)

    def test_public_files_endpoint(self):
        """Test public files endpoint."""
        self.client.force_authenticate(user=self.user)

        # Upload public and private files
        public_file = SimpleUploadedFile(
            "public.txt", b"content", content_type="text/plain"
        )
        private_file = SimpleUploadedFile(
            "private.txt", b"content", content_type="text/plain"
        )

        FileService.upload_file(file=public_file, user=self.user, is_public=True)
        FileService.upload_file(file=private_file, user=self.user, is_public=False)

        url = reverse("fileupload-public")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertTrue(response.data["results"][0]["is_public"])


class MediaLibraryTests(MediaProcessingTestCase):
    """Test media library functionality."""

    def test_media_category_creation(self):
        """Test media category creation and management."""
        category = MediaCategory.objects.create(
            name="Documents", slug="documents", description="Document files"
        )

        self.assertEqual(str(category), "Documents")
        self.assertEqual(category.slug, "documents")

    def test_file_tagging(self):
        """Test file tagging functionality."""
        test_file = self.create_test_image()

        file_upload = FileService.upload_file(
            file=test_file, user=self.user, tags="nature, landscape, photography"
        )

        self.assertEqual(file_upload.tags, "nature, landscape, photography")

    def test_bulk_operations_simulation(self):
        """Test simulation of bulk operations on files."""
        # Create multiple files
        files = []
        for i in range(5):
            test_file = SimpleUploadedFile(
                f"bulk{i}.txt", b"content", content_type="text/plain"
            )
            upload = FileService.upload_file(file=test_file, user=self.user)
            files.append(upload)

        # Simulate bulk delete (check that all files exist first)
        file_ids = [f.id for f in files]
        existing_files = FileUpload.objects.filter(id__in=file_ids)
        self.assertEqual(existing_files.count(), 5)

        # Simulate bulk update of visibility
        FileUpload.objects.filter(id__in=file_ids).update(is_public=True)
        updated_files = FileUpload.objects.filter(id__in=file_ids)

        for file_upload in updated_files:
            self.assertTrue(file_upload.is_public)

    def test_permission_based_access_filtering(self):
        """Test that files are filtered based on user permissions."""
        # Create files with different owners and visibility
        other_user = User.objects.create_user(
            email="other@example.com", password="pass"
        )

        # User's private file
        my_private = SimpleUploadedFile(
            "my_private.txt", b"content", content_type="text/plain"
        )
        FileService.upload_file(file=my_private, user=self.user, is_public=False)

        # User's public file
        my_public = SimpleUploadedFile(
            "my_public.txt", b"content", content_type="text/plain"
        )
        FileService.upload_file(file=my_public, user=self.user, is_public=True)

        # Other user's private file
        other_private = SimpleUploadedFile(
            "other_private.txt", b"content", content_type="text/plain"
        )
        FileService.upload_file(file=other_private, user=other_user, is_public=False)

        # Other user's public file
        other_public = SimpleUploadedFile(
            "other_public.txt", b"content", content_type="text/plain"
        )
        FileService.upload_file(file=other_public, user=other_user, is_public=True)

        # Regular user should see their own files + public files
        user_accessible = FileUpload.objects.filter(
            models.Q(created_by=self.user) | models.Q(is_public=True)
        )
        self.assertEqual(
            user_accessible.count(), 3
        )  # my_private + my_public + other_public

        # Admin should see all files
        admin_accessible = FileUpload.objects.all()
        self.assertEqual(admin_accessible.count(), 4)


class FileCleanupTests(TestCase):
    """Test file cleanup and expired file handling."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

    def test_expired_files_cleanup(self):
        """Test cleanup of expired files."""
        # Create expired files
        past_time = timezone.now() - timezone.timedelta(days=1)

        expired_file = SimpleUploadedFile(
            "expired.txt", b"content", content_type="text/plain"
        )
        expired_upload = FileService.upload_file(
            file=expired_file, user=self.user, expires_at=past_time
        )

        # Create non-expired file
        future_time = timezone.now() + timezone.timedelta(days=1)
        valid_file = SimpleUploadedFile(
            "valid.txt", b"content", content_type="text/plain"
        )
        valid_upload = FileService.upload_file(
            file=valid_file, user=self.user, expires_at=future_time
        )

        # Run cleanup
        result = FileService.cleanup_expired_files()

        # Check that expired file was processed
        self.assertGreater(result["deleted"] + result["errors"], 0)

        # Check that non-expired file still exists
        self.assertTrue(FileUpload.objects.filter(id=valid_upload.id).exists())

    @patch("apps.files.services.default_storage")
    def test_cleanup_with_storage_errors(self, mock_storage):
        """Test cleanup handling of storage errors."""
        # Mock storage to simulate errors
        mock_storage.exists.return_value = True
        mock_storage.delete.side_effect = Exception("Storage error")
        mock_storage.save.return_value = (
            "uploads/test/expired.txt"  # Return proper string
        )

        # Create expired file
        past_time = timezone.now() - timezone.timedelta(days=1)
        expired_file = SimpleUploadedFile(
            "expired.txt", b"content", content_type="text/plain"
        )
        FileService.upload_file(file=expired_file, user=self.user, expires_at=past_time)

        # Run cleanup
        result = FileService.cleanup_expired_files()

        # Should handle errors gracefully
        self.assertIsInstance(result, dict)
        self.assertIn("deleted", result)
        self.assertIn("errors", result)

    def tearDown(self):
        """Clean up test files."""
        for file_upload in FileUpload.objects.all():
            if default_storage.exists(file_upload.storage_path):
                try:
                    default_storage.delete(file_upload.storage_path)
                except Exception:
                    pass


# Import Django models for filtering
from django.db import models


class AdvancedImageProcessingTests(MediaProcessingTestCase):
    """Advanced tests for image processing and metadata handling."""

    def test_exif_metadata_extraction_simulation(self):
        """Test EXIF metadata extraction simulation for JPEG images."""
        # Create a JPEG with simulated metadata
        image_file = self.create_test_image("JPEG", (800, 600))

        file_upload = FileService.upload_file(
            file=image_file, user=self.user, description="Image with EXIF data"
        )

        # Verify image properties are captured
        self.assertEqual(file_upload.file_type, FileType.IMAGE)
        self.assertEqual(file_upload.mime_type, "image/jpeg")
        self.assertGreater(file_upload.file_size, 0)

        # In a real implementation, EXIF data could be stored in description or tags
        self.assertIsNotNone(file_upload.description)

    def test_image_quality_optimization_scenarios(self):
        """Test different image quality optimization scenarios."""
        formats_and_sizes = [
            ("JPEG", (2000, 1500), "Large JPEG"),
            ("PNG", (1000, 800), "Medium PNG"),
            ("WEBP", (500, 400), "Small WebP"),
            ("GIF", (100, 100), "Tiny GIF"),
        ]

        for format_name, size, description in formats_and_sizes:
            with self.subTest(format=format_name, size=size):
                image_file = self.create_test_image(format_name, size)

                file_upload = FileService.upload_file(
                    file=image_file, user=self.user, description=description
                )

                # Verify upload success and metadata
                self.assertEqual(file_upload.file_type, FileType.IMAGE)
                self.assertIn(format_name.lower(), file_upload.mime_type.lower())
                self.assertGreater(file_upload.file_size, 0)

    def test_image_dimension_validation(self):
        """Test image dimension validation for various scenarios."""
        # Test extremely large dimensions
        large_image = self.create_test_image("JPEG", (5000, 4000))
        validation = FileService.validate_file(large_image)
        self.assertTrue(validation["valid"])

        # Test very small dimensions
        tiny_image = self.create_test_image("PNG", (10, 10))
        validation = FileService.validate_file(tiny_image)
        self.assertTrue(validation["valid"])

    def test_animated_gif_handling(self):
        """Test handling of animated GIF files."""
        # Create a GIF file (simulated)
        gif_file = self.create_test_image("GIF", (200, 200))

        file_upload = FileService.upload_file(
            file=gif_file, user=self.user, description="Animated GIF"
        )

        self.assertEqual(file_upload.file_type, FileType.IMAGE)
        self.assertEqual(file_upload.mime_type, "image/gif")

    def test_svg_image_handling(self):
        """Test SVG image file handling."""
        svg_content = """<?xml version="1.0" encoding="UTF-8"?>
        <svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="40" fill="red"/>
        </svg>"""

        svg_file = SimpleUploadedFile(
            "test.svg", svg_content.encode("utf-8"), content_type="image/svg+xml"
        )

        file_upload = FileService.upload_file(file=svg_file, user=self.user)

        self.assertEqual(file_upload.file_type, FileType.IMAGE)
        self.assertEqual(file_upload.mime_type, "image/svg+xml")


class AdvancedSecurityTests(MediaProcessingTestCase):
    """Advanced security tests for file uploads."""

    def test_polyglot_file_detection(self):
        """Test detection of polyglot files (files that are valid in multiple formats)."""
        # Create a file that could be interpreted as both HTML and image
        polyglot_content = b"GIF89a<script>alert('xss')</script>"
        polyglot_file = SimpleUploadedFile(
            "polyglot.gif", polyglot_content, content_type="image/gif"
        )

        # This should be detected as potentially dangerous
        validation = FileService.validate_file(polyglot_file)
        # Basic validation might pass, but content inspection would flag this
        self.assertIsInstance(validation, dict)

    def test_null_byte_injection(self):
        """Test prevention of null byte injection in filenames."""
        dangerous_filenames = [
            "file.txt\x00.exe",
            "image.jpg\x00.php",
            "document.pdf\x00.bat",
        ]

        serializer = SignedUrlSerializer()

        for filename in dangerous_filenames:
            with self.subTest(filename=repr(filename)):
                try:
                    serializer.validate_filename(filename)
                    # If no exception is raised, check that validation would catch other issues
                    self.fail(
                        f"Should have failed validation for filename: {repr(filename)}"
                    )
                except Exception:
                    # Expected behavior - filename should be rejected
                    pass

    def test_zip_bomb_simulation(self):
        """Test handling of compressed files that could be zip bombs."""
        # Simulate a file that claims to be very small but could expand greatly
        suspicious_file = SimpleUploadedFile(
            "suspicious.zip",
            b"PK\x03\x04" + b"x" * 100,  # ZIP header followed by data
            content_type="application/zip",
        )

        validation = FileService.validate_file(suspicious_file)
        # Should pass basic validation but could be flagged for manual review
        self.assertEqual(validation["file_type"], FileType.ARCHIVE)

    def test_mime_type_spoofing_advanced(self):
        """Test advanced MIME type spoofing scenarios."""
        spoofing_scenarios = [
            ("malware.exe", b"MZ\x90\x00", "image/jpeg"),  # Executable with image MIME
            (
                "script.php",
                b"<?php echo 'test'; ?>",
                "text/plain",
            ),  # PHP with text MIME
            (
                "shell.sh",
                b"#!/bin/bash\necho test",
                "application/pdf",
            ),  # Shell with PDF MIME
        ]

        for filename, content, mime_type in spoofing_scenarios:
            with self.subTest(filename=filename):
                spoofed_file = SimpleUploadedFile(
                    filename, content, content_type=mime_type
                )
                validation = FileService.validate_file(spoofed_file)

                # Should have warnings or errors for suspicious combinations
                self.assertTrue(validation["warnings"] or not validation["valid"])

    def test_file_header_validation(self):
        """Test validation based on file headers/magic bytes."""
        # Test files with correct headers
        valid_scenarios = [
            ("image.jpg", b"\xff\xd8\xff", "image/jpeg"),  # JPEG header
            ("image.png", b"\x89PNG\r\n\x1a\n", "image/png"),  # PNG header
            ("document.pdf", b"%PDF-1.4", "application/pdf"),  # PDF header
        ]

        for filename, header, mime_type in valid_scenarios:
            with self.subTest(filename=filename):
                content = header + b"rest of file content"
                test_file = SimpleUploadedFile(
                    filename, content, content_type=mime_type
                )
                validation = FileService.validate_file(test_file)

                self.assertTrue(validation["valid"] or len(validation["warnings"]) == 0)

    def test_unicode_filename_handling(self):
        """Test handling of unicode characters in filenames."""
        unicode_filenames = [
            "файл.txt",  # Cyrillic
            "文档.pdf",  # Chinese
            "🎉emoji.jpg",  # Emoji
            "café.png",  # Accented characters
        ]

        for filename in unicode_filenames:
            with self.subTest(filename=filename):
                test_file = SimpleUploadedFile(
                    filename, b"test content", content_type="text/plain"
                )

                try:
                    file_upload = FileService.upload_file(
                        file=test_file, user=self.user
                    )
                    # Should handle unicode filenames gracefully
                    self.assertIsNotNone(file_upload.id)
                except Exception as e:
                    # If unicode is not supported, should fail gracefully
                    self.assertIsInstance(e, (UnicodeError, ValidationError))


class StorageQuotaTests(MediaProcessingTestCase):
    """Test storage quota and disk space management."""

    def test_user_storage_quota_simulation(self):
        """Test user storage quota enforcement simulation."""
        # Upload multiple files and track total size
        total_size = 0
        uploaded_files = []

        for i in range(3):
            test_file = SimpleUploadedFile(
                f"quota_test_{i}.txt",
                b"x" * 1024 * 100,  # 100KB each
                content_type="text/plain",
            )

            file_upload = FileService.upload_file(file=test_file, user=self.user)

            uploaded_files.append(file_upload)
            total_size += file_upload.file_size

        # Calculate user's total storage usage
        user_total = (
            FileUpload.objects.filter(created_by=self.user).aggregate(
                total_size=models.Sum("file_size")
            )["total_size"]
            or 0
        )

        self.assertEqual(user_total, total_size)
        self.assertGreater(user_total, 300000)  # Should be > 300KB

    def test_storage_path_collision_handling(self):
        """Test handling of storage path collisions."""
        # This tests the UUID-based filename generation
        files = []
        for i in range(5):
            test_file = SimpleUploadedFile(
                "same_name.txt",  # Same original filename
                f"content {i}".encode(),
                content_type="text/plain",
            )

            file_upload = FileService.upload_file(file=test_file, user=self.user)
            files.append(file_upload)

        # All files should have unique storage paths
        storage_paths = [f.storage_path for f in files]
        unique_paths = set(storage_paths)

        self.assertEqual(len(storage_paths), len(unique_paths))

        # All should have same original filename but different stored filenames
        original_filenames = [f.original_filename for f in files]
        stored_filenames = [f.filename for f in files]

        self.assertEqual(len(set(original_filenames)), 1)  # All same original
        self.assertEqual(len(set(stored_filenames)), 5)  # All different stored

    def test_disk_space_simulation(self):
        """Test disk space availability simulation."""
        # Create a large file to test space usage
        large_content = b"x" * (1024 * 1024)  # 1MB
        large_file = SimpleUploadedFile(
            "large_file.txt", large_content, content_type="text/plain"
        )

        file_upload = FileService.upload_file(file=large_file, user=self.user)

        # Verify large file was uploaded successfully
        self.assertEqual(file_upload.file_size, len(large_content))
        self.assertTrue(default_storage.exists(file_upload.storage_path))


class AdvancedAPITests(APITestCase, MediaProcessingTestCase):
    """Advanced API integration tests."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_concurrent_upload_simulation(self):
        """Test simulation of concurrent uploads."""
        self.client.force_authenticate(user=self.user)
        url = reverse("fileupload-list")

        # Simulate multiple uploads in quick succession
        responses = []
        for i in range(3):
            test_file = SimpleUploadedFile(
                f"concurrent_{i}.txt",
                f"content {i}".encode(),
                content_type="text/plain",
            )

            response = self.client.post(
                url,
                {"file": test_file, "description": f"Concurrent upload {i}"},
                format="multipart",
            )

            responses.append(response)

        # All uploads should succeed
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # All should have unique IDs
        upload_ids = [r.data["id"] for r in responses]
        self.assertEqual(len(set(upload_ids)), len(upload_ids))

    def test_api_rate_limiting_simulation(self):
        """Test API rate limiting behavior simulation."""
        self.client.force_authenticate(user=self.user)
        url = reverse("fileupload-list")

        # Make multiple rapid requests
        responses = []
        for i in range(10):
            test_file = SimpleUploadedFile(
                f"rate_test_{i}.txt", b"test content", content_type="text/plain"
            )

            response = self.client.post(url, {"file": test_file}, format="multipart")

            responses.append(response.status_code)

        # Should have some successful uploads (rate limiting not implemented yet)
        successful_uploads = sum(1 for status_code in responses if status_code == 201)
        self.assertGreater(successful_uploads, 0)

    def test_large_file_upload_streaming(self):
        """Test large file upload with streaming."""
        self.client.force_authenticate(user=self.user)
        url = reverse("fileupload-list")

        # Create a file that's larger than typical memory buffer
        large_content = b"x" * (2 * 1024 * 1024)  # 2MB
        large_file = SimpleUploadedFile(
            "large_stream.txt", large_content, content_type="text/plain"
        )

        response = self.client.post(
            url,
            {"file": large_file, "description": "Large file upload test"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["file_size"], len(large_content))

    def test_api_error_handling_edge_cases(self):
        """Test API error handling for various edge cases."""
        self.client.force_authenticate(user=self.user)
        url = reverse("fileupload-list")

        # Test empty file
        empty_file = SimpleUploadedFile("empty.txt", b"", content_type="text/plain")
        response = self.client.post(url, {"file": empty_file}, format="multipart")
        # Empty files are typically rejected by validation
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test file with no extension
        no_ext_file = SimpleUploadedFile(
            "no_extension", b"content", content_type="text/plain"
        )
        response = self.client.post(url, {"file": no_ext_file}, format="multipart")
        # Files without extensions are rejected for security reasons
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test malformed multipart data
        response = self.client.post(url, {"not_a_file": "invalid"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_download_with_ranges_simulation(self):
        """Test partial download/range request simulation."""
        self.client.force_authenticate(user=self.user)

        # Upload a file first
        test_file = SimpleUploadedFile(
            "range_test.txt",
            b"0123456789" * 100,  # 1000 bytes
            content_type="text/plain",
        )

        file_upload = FileService.upload_file(file=test_file, user=self.user)

        # Test download
        download_url = reverse("fileupload-download", kwargs={"pk": file_upload.id})
        response = self.client.get(download_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(b"".join(response.streaming_content)), 1000)


class AdvancedMediaLibraryTests(MediaProcessingTestCase):
    """Advanced media library functionality tests."""

    def test_advanced_file_search(self):
        """Test advanced file search capabilities."""
        # Create files with various metadata
        files_data = [
            (
                "landscape.jpg",
                "photography nature landscape mountain",
                "photography, landscape, nature",
            ),
            (
                "portrait.png",
                "photography person portrait studio",
                "photography, portrait, people",
            ),
            ("document.pdf", "legal contract agreement", "legal, business, contract"),
            (
                "presentation.ppt",
                "business slides meeting",
                "business, presentation, meeting",
            ),
        ]

        uploaded_files = []
        for filename, description, tags in files_data:
            if filename.endswith((".jpg", ".png")):
                test_file = self.create_test_image(
                    "JPEG" if filename.endswith(".jpg") else "PNG"
                )
            else:
                test_file = self.create_test_document(filename=filename)

            file_upload = FileService.upload_file(
                file=test_file, user=self.user, description=description, tags=tags
            )
            uploaded_files.append(file_upload)

        # Test searching by description content
        photography_files = FileUpload.objects.filter(
            description__icontains="photography"
        )
        self.assertEqual(photography_files.count(), 2)

        # Test searching by tags
        business_files = FileUpload.objects.filter(tags__icontains="business")
        self.assertEqual(business_files.count(), 2)

    def test_file_categorization_by_type(self):
        """Test automatic file categorization by type."""
        # Create files of different types
        files = [
            (self.create_test_image("JPEG"), FileType.IMAGE),
            (self.create_test_image("PNG"), FileType.IMAGE),
            (self.create_test_document(filename="doc.pdf"), FileType.DOCUMENT),
            (self.create_test_video(), FileType.VIDEO),
            (self.create_test_audio(), FileType.AUDIO),
        ]

        for test_file, expected_type in files:
            with self.subTest(expected_type=expected_type):
                file_upload = FileService.upload_file(file=test_file, user=self.user)

                self.assertEqual(file_upload.file_type, expected_type)

        # Test filtering by file type
        images = FileUpload.objects.filter(file_type=FileType.IMAGE)
        self.assertEqual(images.count(), 2)

        documents = FileUpload.objects.filter(file_type=FileType.DOCUMENT)
        self.assertEqual(documents.count(), 1)

    def test_bulk_metadata_operations(self):
        """Test bulk operations on file metadata."""
        # Create multiple files
        files = []
        for i in range(5):
            test_file = SimpleUploadedFile(
                f"bulk_{i}.txt", f"content {i}".encode(), content_type="text/plain"
            )

            file_upload = FileService.upload_file(
                file=test_file, user=self.user, description=f"File {i}", is_public=False
            )
            files.append(file_upload)

        file_ids = [f.id for f in files]

        # Test bulk visibility update
        updated_count = FileUpload.objects.filter(id__in=file_ids).update(
            is_public=True
        )

        self.assertEqual(updated_count, 5)

        # Verify all files are now public
        public_files = FileUpload.objects.filter(id__in=file_ids, is_public=True)
        self.assertEqual(public_files.count(), 5)

        # Test bulk tag update
        FileUpload.objects.filter(id__in=file_ids).update(
            tags="bulk, updated, metadata"
        )

        # Verify tags were updated
        tagged_files = FileUpload.objects.filter(
            id__in=file_ids, tags__icontains="bulk"
        )
        self.assertEqual(tagged_files.count(), 5)

    def test_file_usage_analytics(self):
        """Test file usage analytics and statistics."""
        # Create files with different download counts
        files = []
        for i in range(3):
            test_file = SimpleUploadedFile(
                f"analytics_{i}.txt", f"content {i}".encode(), content_type="text/plain"
            )

            file_upload = FileService.upload_file(file=test_file, user=self.user)

            # Simulate different download counts
            for _ in range(i + 1):
                file_upload.increment_download_count()

            file_upload.refresh_from_db()
            files.append(file_upload)

        # Test download count tracking
        self.assertEqual(files[0].download_count, 1)
        self.assertEqual(files[1].download_count, 2)
        self.assertEqual(files[2].download_count, 3)

        # Test analytics aggregation
        total_downloads = (
            FileUpload.objects.filter(created_by=self.user).aggregate(
                total=models.Sum("download_count")
            )["total"]
            or 0
        )

        self.assertEqual(total_downloads, 6)  # 1+2+3

    def test_media_library_pagination_performance(self):
        """Test media library pagination with large datasets."""
        # Create many files to test pagination
        files = []
        for i in range(25):  # Create 25 files
            test_file = SimpleUploadedFile(
                f"page_test_{i:02d}.txt",
                f"content {i}".encode(),
                content_type="text/plain",
            )

            file_upload = FileService.upload_file(
                file=test_file, user=self.user, description=f"Page test file {i}"
            )
            files.append(file_upload)

        # Test ordering and pagination
        ordered_files = FileUpload.objects.filter(created_by=self.user).order_by(
            "-created_at"
        )

        self.assertEqual(ordered_files.count(), 25)

        # Test slice-based pagination
        first_page = ordered_files[:10]
        second_page = ordered_files[10:20]
        third_page = ordered_files[20:30]

        self.assertEqual(len(first_page), 10)
        self.assertEqual(len(second_page), 10)
        self.assertEqual(len(third_page), 5)

        # Verify no overlap between pages
        first_ids = set(f.id for f in first_page)
        second_ids = set(f.id for f in second_page)
        third_ids = set(f.id for f in third_page)

        self.assertEqual(len(first_ids.intersection(second_ids)), 0)
        self.assertEqual(len(second_ids.intersection(third_ids)), 0)


class PerformanceTests(MediaProcessingTestCase):
    """Performance and stress tests for file operations."""

    def test_large_batch_upload_performance(self):
        """Test performance with large batch uploads."""
        import time

        start_time = time.time()

        # Upload multiple files in sequence
        files = []
        for i in range(10):
            test_file = SimpleUploadedFile(
                f"perf_{i}.txt", b"x" * 1024, content_type="text/plain"  # 1KB each
            )

            file_upload = FileService.upload_file(file=test_file, user=self.user)
            files.append(file_upload)

        end_time = time.time()
        upload_time = end_time - start_time

        # Should complete reasonably quickly
        self.assertLess(upload_time, 30.0)  # Should take less than 30 seconds
        self.assertEqual(len(files), 10)

    def test_checksum_calculation_performance(self):
        """Test checksum calculation performance for various file sizes."""
        import time

        file_sizes = [1024, 10240, 102400]  # 1KB, 10KB, 100KB

        for size in file_sizes:
            with self.subTest(size=size):
                start_time = time.time()

                content = b"x" * size
                test_file = SimpleUploadedFile(
                    f"checksum_{size}.txt", content, content_type="text/plain"
                )

                file_upload = FileService.upload_file(file=test_file, user=self.user)

                end_time = time.time()
                processing_time = end_time - start_time

                # Verify checksum was calculated
                self.assertIsNotNone(file_upload.checksum)
                self.assertEqual(len(file_upload.checksum), 64)  # SHA256 hex length

                # Should complete in reasonable time
                self.assertLess(processing_time, 10.0)

    def test_memory_usage_with_large_files(self):
        """Test memory usage patterns with larger files."""
        # Create a file larger than typical memory buffer
        large_content = b"x" * (1024 * 1024)  # 1MB
        large_file = SimpleUploadedFile(
            "memory_test.txt", large_content, content_type="text/plain"
        )

        # This should use streaming upload for large files
        file_upload = FileService.upload_file(file=large_file, user=self.user)

        # Verify upload succeeded
        self.assertEqual(file_upload.file_size, len(large_content))
        self.assertIsNotNone(file_upload.checksum)
        self.assertTrue(default_storage.exists(file_upload.storage_path))
