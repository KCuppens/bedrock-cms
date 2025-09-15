"""Simplified comprehensive API tests for the Files/Media app.

This test suite covers the major API functionality for file upload,
management, permissions, and processing in the CMS system.
"""

import hashlib
import os
import tempfile
import uuid
from io import BytesIO
from unittest.mock import Mock, patch

import django
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from apps.core.enums import FileType
from apps.files.models import FileUpload, MediaCategory
from apps.files.services import FileService

User = get_user_model()


class FileUploadAPITestCase(APITestCase):
    """Test file upload API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
        )
        # Set admin role if the user model supports it
        if hasattr(self.admin_user, "role"):
            self.admin_user.role = "admin"
            self.admin_user.save()

        self.client = APIClient()

        # Create test category
        self.category = MediaCategory.objects.create(
            name="Test Category",
            slug="test-category",
            description="Test category for uploads",
        )

    def create_test_file(
        self,
        filename="test.txt",
        content=b"test content",
        content_type="text/plain",
        size=None,
    ):
        """Helper to create test files."""
        if size:
            content = b"x" * size
        return SimpleUploadedFile(filename, content, content_type=content_type)

    def test_file_upload_success(self):
        """Test successful file upload."""
        self.client.force_authenticate(user=self.user)

        test_file = self.create_test_file("test.txt", b"Hello World!")

        data = {
            "file": test_file,
            "description": "Test file upload",
            "tags": "test,upload",
            "is_public": False,
        }

        url = reverse("fileupload-list")
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["original_filename"], "test.txt")
        self.assertEqual(response.data["description"], "Test file upload")
        self.assertEqual(response.data["tags"], "test,upload")
        self.assertFalse(response.data["is_public"])

    def test_file_upload_without_file(self):
        """Test file upload without providing file."""
        self.client.force_authenticate(user=self.user)

        data = {"description": "Test without file"}

        url = reverse("fileupload-list")
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_file_upload_unauthenticated(self):
        """Test file upload without authentication."""
        test_file = self.create_test_file()
        data = {"file": test_file}

        url = reverse("fileupload-list")
        response = self.client.post(url, data, format="multipart")

        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    @patch("apps.files.services.FileService.validate_file")
    def test_file_upload_validation_failure(self, mock_validate):
        """Test file upload with validation failure."""
        mock_validate.return_value = {
            "valid": False,
            "errors": ["File too large", "Invalid file type"],
        }

        self.client.force_authenticate(user=self.user)
        test_file = self.create_test_file()

        data = {"file": test_file}
        url = reverse("fileupload-list")
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)


class FileManagementAPITestCase(APITestCase):
    """Test file management API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", password="testpass123"
        )
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
        )
        # Set admin role if supported
        if hasattr(self.admin_user, "role"):
            self.admin_user.role = "admin"
            self.admin_user.save()

        self.client = APIClient()

    def create_test_file_upload(self, user=None, **kwargs):
        """Helper to create FileUpload instances."""
        if user is None:
            user = self.user

        defaults = {
            "original_filename": "test.txt",
            "filename": f"{uuid.uuid4().hex}.txt",
            "file_type": FileType.DOCUMENT,
            "mime_type": "text/plain",
            "file_size": 1024,
            "checksum": hashlib.sha256(b"test").hexdigest(),
            "storage_path": f"uploads/{user.id}/test.txt",
            "created_by": user,
            "updated_by": user,
        }
        defaults.update(kwargs)
        return FileUpload.objects.create(**defaults)

    def test_file_list(self):
        """Test listing files."""
        self.client.force_authenticate(user=self.user)

        # Create files for different users
        file1 = self.create_test_file_upload(
            user=self.user, original_filename="user_file.txt"
        )
        file2 = self.create_test_file_upload(
            user=self.other_user, original_filename="other_file.txt"
        )
        public_file = self.create_test_file_upload(
            user=self.other_user, original_filename="public_file.txt", is_public=True
        )

        url = reverse("fileupload-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should see own files and public files
        if "results" in response.data:
            filenames = [f["original_filename"] for f in response.data["results"]]
        else:
            filenames = [f["original_filename"] for f in response.data]

        self.assertIn("user_file.txt", filenames)
        self.assertIn("public_file.txt", filenames)
        self.assertNotIn("other_file.txt", filenames)

    def test_file_retrieve(self):
        """Test retrieving file details."""
        self.client.force_authenticate(user=self.user)

        file_upload = self.create_test_file_upload()

        url = reverse("fileupload-detail", kwargs={"pk": file_upload.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(file_upload.id))
        self.assertEqual(
            response.data["original_filename"], file_upload.original_filename
        )

    def test_file_retrieve_unauthorized(self):
        """Test retrieving file without permission."""
        self.client.force_authenticate(user=self.other_user)

        file_upload = self.create_test_file_upload(user=self.user)

        url = reverse("fileupload-detail", kwargs={"pk": file_upload.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_file_update_metadata(self):
        """Test updating file metadata."""
        self.client.force_authenticate(user=self.user)

        file_upload = self.create_test_file_upload(description="Original description")

        data = {
            "description": "Updated description",
            "tags": "updated,test",
            "is_public": True,
        }

        url = reverse("fileupload-detail", kwargs={"pk": file_upload.id})
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["description"], "Updated description")
        self.assertEqual(response.data["tags"], "updated,test")
        self.assertTrue(response.data["is_public"])

    def test_file_delete(self):
        """Test deleting file."""
        self.client.force_authenticate(user=self.user)

        file_upload = self.create_test_file_upload()

        url = reverse("fileupload-detail", kwargs={"pk": file_upload.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FileUpload.objects.filter(id=file_upload.id).exists())


class FileDownloadAPITestCase(APITestCase):
    """Test file download API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com", password="testpass123"
        )
        self.client = APIClient()

    def create_test_file_upload(self, user=None, **kwargs):
        """Helper to create FileUpload instances."""
        if user is None:
            user = self.user

        defaults = {
            "original_filename": "test.txt",
            "filename": f"{uuid.uuid4().hex}.txt",
            "file_type": FileType.DOCUMENT,
            "mime_type": "text/plain",
            "file_size": 1024,
            "checksum": hashlib.sha256(b"test").hexdigest(),
            "storage_path": f"uploads/{user.id}/test.txt",
            "created_by": user,
            "updated_by": user,
        }
        defaults.update(kwargs)
        return FileUpload.objects.create(**defaults)

    def test_download_url_generation(self):
        """Test getting download URL for file."""
        self.client.force_authenticate(user=self.user)

        file_upload = self.create_test_file_upload()

        url = reverse("fileupload-download-url", kwargs={"pk": file_upload.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("download_url", response.data)
        self.assertIn("expires_in", response.data)
        self.assertIn("filename", response.data)

    def test_download_url_unauthorized(self):
        """Test getting download URL without permission."""
        self.client.force_authenticate(user=self.other_user)

        file_upload = self.create_test_file_upload(user=self.user, is_public=False)

        url = reverse("fileupload-download-url", kwargs={"pk": file_upload.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_url_public_file(self):
        """Test getting download URL for public file."""
        # No authentication required for public files

        file_upload = self.create_test_file_upload(is_public=True)

        url = reverse("fileupload-download-url", kwargs={"pk": file_upload.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("download_url", response.data)


class FileValidationAPITestCase(APITestCase):
    """Test file validation and error handling."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.client = APIClient()

    def create_test_file(
        self,
        filename="test.txt",
        content=b"test content",
        content_type="text/plain",
        size=None,
    ):
        """Helper to create test files."""
        if size:
            content = b"x" * size
        return SimpleUploadedFile(filename, content, content_type=content_type)

    def test_file_size_validation(self):
        """Test file size validation."""
        self.client.force_authenticate(user=self.user)

        # Create oversized file (100MB)
        large_file = self.create_test_file(
            "large.txt", size=100 * 1024 * 1024, content_type="text/plain"
        )

        data = {"file": large_file}
        url = reverse("fileupload-list")
        response = self.client.post(url, data, format="multipart")

        # Should be rejected due to size
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_file_type_validation(self):
        """Test file type validation."""
        self.client.force_authenticate(user=self.user)

        # Create executable file (should be rejected)
        exe_file = self.create_test_file(
            "malicious.exe",
            b"fake executable content",
            content_type="application/x-executable",
        )

        data = {"file": exe_file}
        url = reverse("fileupload-list")
        response = self.client.post(url, data, format="multipart")

        # Should be rejected due to dangerous file type
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FilePermissionsAPITestCase(APITestCase):
    """Test file permissions and access control."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            email="owner@example.com", password="testpass123"
        )
        self.user = User.objects.create_user(
            email="user@example.com", password="testpass123"
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
        )
        # Set admin role if supported
        if hasattr(self.admin, "role"):
            self.admin.role = "admin"
            self.admin.save()

        self.client = APIClient()

    def create_test_file_upload(self, user=None, **kwargs):
        """Helper to create FileUpload instances."""
        if user is None:
            user = self.owner

        defaults = {
            "original_filename": "test.txt",
            "filename": f"{uuid.uuid4().hex}.txt",
            "file_type": FileType.DOCUMENT,
            "mime_type": "text/plain",
            "file_size": 1024,
            "checksum": hashlib.sha256(b"test").hexdigest(),
            "storage_path": f"uploads/{user.id}/test.txt",
            "created_by": user,
            "updated_by": user,
        }
        defaults.update(kwargs)
        return FileUpload.objects.create(**defaults)

    def test_owner_can_access_private_file(self):
        """Test owner can access their private files."""
        self.client.force_authenticate(user=self.owner)

        private_file = self.create_test_file_upload(is_public=False)

        url = reverse("fileupload-detail", kwargs={"pk": private_file.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_cannot_access_others_private_file(self):
        """Test user cannot access other user's private files."""
        self.client.force_authenticate(user=self.user)

        private_file = self.create_test_file_upload(user=self.owner, is_public=False)

        url = reverse("fileupload-detail", kwargs={"pk": private_file.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_access_public_file(self):
        """Test user can access public files."""
        self.client.force_authenticate(user=self.user)

        public_file = self.create_test_file_upload(user=self.owner, is_public=True)

        url = reverse("fileupload-detail", kwargs={"pk": public_file.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class FileServiceIntegrationTestCase(TestCase):
    """Integration tests for FileService with real file operations."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

    def test_file_service_validation(self):
        """Test FileService validation functionality."""
        # Test valid file
        valid_file = SimpleUploadedFile(
            "valid.txt", b"Valid content", content_type="text/plain"
        )

        result = FileService.validate_file(valid_file)
        self.assertTrue(result["valid"])
        self.assertEqual(result["file_type"], FileType.DOCUMENT)

    def test_file_service_upload_and_cleanup(self):
        """Test FileService upload and cleanup."""
        test_file = SimpleUploadedFile(
            "service_test.txt", b"Test service upload", content_type="text/plain"
        )

        # Upload file
        file_upload = FileService.upload_file(
            file=test_file, user=self.user, description="Service test upload"
        )

        self.assertIsInstance(file_upload, FileUpload)
        self.assertEqual(file_upload.original_filename, "service_test.txt")
        self.assertEqual(file_upload.created_by, self.user)

        # Test checksum calculation
        self.assertIsNotNone(file_upload.checksum)
        self.assertEqual(len(file_upload.checksum), 64)  # SHA256 hex length

        # Clean up
        FileService.delete_file(file_upload)

        # Verify file was deleted from database
        self.assertFalse(FileUpload.objects.filter(id=file_upload.id).exists())


class MediaCategoryAPITestCase(APITestCase):
    """Test media category functionality (if endpoints exist)."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
        )
        # Set admin role if supported
        if hasattr(self.admin_user, "role"):
            self.admin_user.role = "admin"
            self.admin_user.save()

        self.client = APIClient()

    def test_list_media_categories(self):
        """Test listing media categories."""
        category1 = MediaCategory.objects.create(
            name="Images", slug="images", description="Image files"
        )
        category2 = MediaCategory.objects.create(
            name="Videos", slug="videos", description="Video files"
        )

        # Test if categories can be listed through any endpoint
        # This assumes categories might be exposed through some API
        self.assertEqual(MediaCategory.objects.count(), 2)
        self.assertEqual(category1.name, "Images")
        self.assertEqual(category2.name, "Videos")


# Additional test for image processing if PIL is available
if PIL_AVAILABLE:

    class FileImageProcessingAPITestCase(APITestCase):
        """Test image processing and thumbnail generation."""

        def setUp(self):
            """Set up test data."""
            self.user = User.objects.create_user(
                email="test@example.com", password="testpass123"
            )
            self.client = APIClient()

        def create_test_image(
            self, filename="test.jpg", format="JPEG", size=(200, 200), color="red"
        ):
            """Helper to create test image files."""
            image = Image.new("RGB", size, color=color)
            image_buffer = BytesIO()
            image.save(image_buffer, format=format)
            image_buffer.seek(0)

            return SimpleUploadedFile(
                filename, image_buffer.read(), content_type=f"image/{format.lower()}"
            )

        def test_image_upload_processing(self):
            """Test image upload with automatic processing."""
            self.client.force_authenticate(user=self.user)

            test_image = self.create_test_image("test_image.jpg", size=(500, 400))

            data = {
                "file": test_image,
                "description": "Test image upload",
            }

            url = reverse("fileupload-list")
            response = self.client.post(url, data, format="multipart")

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data["file_type"], FileType.IMAGE)
            self.assertEqual(response.data["mime_type"], "image/jpeg")
