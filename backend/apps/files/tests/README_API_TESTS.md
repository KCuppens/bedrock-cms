# Files/Media API Tests

This document describes the comprehensive API test suite created for the Files/Media app in the Bedrock CMS system.

## Overview

Two comprehensive test files have been created for the Files/Media app:

1. **`test_api.py`** - Full comprehensive test suite with extensive coverage
2. **`test_api_simplified.py`** - Streamlined version focusing on core functionality

## Test Coverage

### 1. File Upload API Tests (`FileUploadAPITest`)

**Endpoints Tested:**
- `POST /api/v1/files/` - File upload

**Test Scenarios:**
- ✅ Successful file upload with metadata
- ✅ File upload without file (error case)
- ✅ Unauthenticated file upload (401 error)
- ✅ File upload with expiration date
- ✅ File upload validation failure
- ✅ Large file upload handling
- ✅ Batch file upload (if endpoint exists)

**Key Features Tested:**
- File metadata (description, tags, public/private status)
- File expiration handling
- Validation error responses
- Authentication requirements
- File size limits

### 2. File Management API Tests (`FileManagementAPITest`)

**Endpoints Tested:**
- `GET /api/v1/files/` - List files
- `GET /api/v1/files/{id}/` - Get file details
- `PATCH /api/v1/files/{id}/` - Update file metadata
- `DELETE /api/v1/files/{id}/` - Delete file

**Test Scenarios:**
- ✅ File listing with permission filtering
- ✅ Admin users can see all files
- ✅ File filtering by type and public status
- ✅ File detail retrieval
- ✅ Unauthorized file access (404 error)
- ✅ File metadata updates
- ✅ File deletion with permission checks

**Key Features Tested:**
- Permission-based file visibility
- Query parameter filtering
- Metadata update restrictions
- Access control enforcement

### 3. File Download API Tests (`FileDownloadAPITest`)

**Endpoints Tested:**
- `GET /api/v1/files/{id}/download_url/` - Get signed download URL
- `GET /api/v1/files/{id}/download/` - Direct file download

**Test Scenarios:**
- ✅ Download URL generation for authorized users
- ✅ Download URL rejection for unauthorized users
- ✅ Public file download access
- ✅ Direct file download with counter increment
- ✅ Expired file download prevention

**Key Features Tested:**
- Signed URL generation
- Access permission validation
- Download counter tracking
- File expiration handling

### 4. Signed Upload URL API Tests (`SignedUploadURLAPITest`)

**Endpoints Tested:**
- `POST /api/v1/files/signed_upload_url/` - Get signed upload URL

**Test Scenarios:**
- ✅ Signed upload URL generation
- ✅ Invalid filename rejection (security)
- ✅ Filename extension validation
- ✅ Unauthenticated access denial

**Key Features Tested:**
- Path traversal prevention
- File extension requirements
- Content type validation
- Security-first filename handling

### 5. Media Category API Tests (`MediaCategoryAPITest`)

**Endpoints Tested:**
- `GET /api/v1/mediacategory/` - List categories (if exists)
- `POST /api/v1/mediacategory/` - Create category (if exists)

**Test Scenarios:**
- ✅ Category creation (admin only)
- ✅ Category listing
- ✅ Category management permissions

**Key Features Tested:**
- Category CRUD operations
- Admin-only category management
- Category-file relationships

### 6. File Validation API Tests (`FileValidationAPITest`)

**Test Scenarios:**
- ✅ File size validation and rejection
- ✅ File type security validation
- ✅ Empty file handling
- ✅ Filename security validation
- ✅ MIME type validation

**Key Security Features Tested:**
- Executable file rejection
- Path traversal prevention
- Reserved filename blocking
- Size limit enforcement
- MIME type verification

### 7. File Permissions API Tests (`FilePermissionsAPITest`)

**Test Scenarios:**
- ✅ Owner access to private files
- ✅ User blocked from others' private files
- ✅ Public file access for all users
- ✅ Admin access to all files
- ✅ Anonymous user access patterns
- ✅ Expired file access denial

**Key Features Tested:**
- Ownership-based access control
- Public/private file handling
- Admin privilege escalation
- File expiration enforcement

### 8. File Bulk Operations API Tests (`FileBulkOperationsAPITest`)

**Endpoints Tested:**
- `GET /api/v1/files/my_files/` - Get user's files
- `GET /api/v1/files/public/` - Get public files
- `POST /api/v1/files/bulk_upload/` - Bulk upload (if exists)

**Test Scenarios:**
- ✅ Bulk file upload
- ✅ User-specific file listing
- ✅ Public file filtering
- ✅ Tag-based file organization

**Key Features Tested:**
- Multi-file operations
- User-scoped queries
- Tag-based filtering
- Bulk processing

### 9. Image Processing API Tests (`FileImageProcessingAPITest`)

**Test Scenarios:**
- ✅ Image upload with metadata extraction
- ✅ Thumbnail generation on upload
- ✅ Image format validation
- ✅ Invalid image file handling

**Key Features Tested:**
- Automatic image processing
- Metadata extraction (dimensions, format)
- Thumbnail creation
- Image format validation

### 10. File Service Integration Tests (`FileServiceIntegrationTest`)

**Test Scenarios:**
- ✅ FileService validation functionality
- ✅ File upload and cleanup workflow
- ✅ Large file handling
- ✅ Expired file cleanup
- ✅ Checksum calculation
- ✅ Storage path management

**Key Features Tested:**
- Service layer functionality
- File storage operations
- Cleanup procedures
- Hash generation
- Memory-efficient processing

## Running the Tests

### Prerequisites

Ensure you have the following dependencies installed:
```bash
pip install Pillow  # For image processing tests
```

### Run All File API Tests
```bash
python manage.py test apps.files.tests.test_api --verbosity=2
```

### Run Simplified Test Suite
```bash
python manage.py test apps.files.tests.test_api_simplified --verbosity=2
```

### Run Specific Test Classes
```bash
# File upload tests only
python manage.py test apps.files.tests.test_api.FileUploadAPITest

# Permission tests only
python manage.py test apps.files.tests.test_api.FilePermissionsAPITest

# Service integration tests
python manage.py test apps.files.tests.test_api.FileServiceIntegrationTest
```

### Run Individual Tests
```bash
python manage.py test apps.files.tests.test_api.FileUploadAPITest.test_file_upload_success
```

## Test Configuration

### Settings Override
Tests use the following settings overrides for consistency:
```python
@override_settings(
    FILE_UPLOAD_MAX_MEMORY_SIZE=1024 * 1024,  # 1MB
    ALLOWED_FILE_EXTENSIONS=['.txt', '.pdf', '.jpg', '.png'],
    ALLOWED_MIME_TYPES=['text/plain', 'application/pdf', 'image/jpeg', 'image/png']
)
```

### Test Data
Each test class creates its own isolated test data:
- Test users (regular, admin, other)
- Test files with various properties
- Media categories for organization
- Mock storage operations where needed

## Security Test Coverage

The test suite includes comprehensive security testing:

### File Upload Security
- ✅ Path traversal prevention (`../../../etc/passwd`)
- ✅ Executable file rejection (`.exe`, `.bat`, `.js`)
- ✅ MIME type validation
- ✅ File size limits
- ✅ Filename sanitization

### Access Control Security
- ✅ Authentication requirements
- ✅ Authorization checks
- ✅ Owner-based permissions
- ✅ Admin privilege separation
- ✅ Public/private file isolation

### API Security
- ✅ Input validation
- ✅ SQL injection prevention (through Django ORM)
- ✅ Cross-user data access prevention
- ✅ Expired resource access denial

## Mock Objects and Patches

The tests use mocking strategically for:
- File storage operations
- External service calls
- Time-sensitive operations
- Resource-intensive operations

Example mocking patterns:
```python
@patch('apps.files.services.FileService.validate_file')
def test_upload_validation(self, mock_validate):
    mock_validate.return_value = {"valid": False, "errors": ["Test error"]}
    # Test validation failure handling
```

## Performance Considerations

The test suite is designed for performance:
- Uses in-memory SQLite database
- Mocks expensive operations
- Creates minimal test data
- Cleans up after each test

## Error Handling Coverage

Tests cover all major error scenarios:
- HTTP 400 (Bad Request) - Invalid input
- HTTP 401 (Unauthorized) - Missing authentication
- HTTP 403 (Forbidden) - Insufficient permissions
- HTTP 404 (Not Found) - Resource not found
- HTTP 413 (Payload Too Large) - File too large

## API Response Validation

Each test validates:
- Correct HTTP status codes
- Response data structure
- Required fields presence
- Data type consistency
- Error message clarity

## Integration Points

Tests verify integration with:
- Django REST Framework serializers
- File storage backends (S3, local)
- Authentication system
- Permission system
- Database models
- File processing services

## Maintenance Notes

When adding new API endpoints or features:

1. Add corresponding test class
2. Cover success and error scenarios
3. Test permission boundaries
4. Validate security implications
5. Update this documentation

## Test Data Examples

### Sample File Upload Request
```python
data = {
    "file": test_file,
    "description": "Test file upload",
    "tags": "test,upload",
    "is_public": False,
    "expires_at": "2024-12-31T23:59:59Z"
}
```

### Sample Response Validation
```python
self.assertEqual(response.status_code, status.HTTP_201_CREATED)
self.assertIn("id", response.data)
self.assertEqual(response.data["original_filename"], "test.txt")
self.assertTrue("download_url" in response.data)
```

This comprehensive test suite ensures the Files/Media API is robust, secure, and handles all edge cases appropriately for a production CMS system.
