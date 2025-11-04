"""
File magic number validation for security.
Validates file types by checking magic bytes (file signatures) instead of just extensions.
"""

import io


class MagicBytesValidator:
    """Validate files by checking magic bytes (file signatures)"""

    # File signatures (magic bytes) for common file types
    MAGIC_SIGNATURES = {
        # Images
        "image/jpeg": [
            b'\xFF\xD8\xFF\xE0',  # JPEG/JFIF
            b'\xFF\xD8\xFF\xE1',  # JPEG/Exif
            b'\xFF\xD8\xFF\xE2',  # JPEG/Canon
            b'\xFF\xD8\xFF\xDB',  # JPEG raw
        ],
        "image/png": [b'\x89PNG\r\n\x1a\n'],
        "image/gif": [b'GIF87a', b'GIF89a'],
        "image/webp": [b'RIFF'],  # Followed by WEBP at offset 8
        "image/bmp": [b'BM'],

        # Documents
        "application/pdf": [b'%PDF-'],
        "application/zip": [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],  # Also DOCX, XLSX
        "text/plain": None,  # No magic bytes for plain text
        "text/csv": None,  # No magic bytes for CSV

        # Office Documents (ZIP-based, check for specific internals)
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [b'PK\x03\x04'],  # DOCX
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [b'PK\x03\x04'],  # XLSX

        # Legacy Office
        "application/msword": [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'],  # DOC

        # Video
        "video/mp4": [b'\x00\x00\x00\x18ftypmp4', b'\x00\x00\x00\x20ftypmp4'],
        "video/webm": [b'\x1A\x45\xDF\xA3'],

        # Audio
        "audio/mpeg": [b'ID3', b'\xFF\xFB', b'\xFF\xF3', b'\xFF\xF2'],  # MP3
        "audio/wav": [b'RIFF'],  # Followed by WAVE
    }

    @classmethod
    def validate_magic_bytes(cls, file, expected_mime_type: str) -> dict:
        """
        Validate file by checking magic bytes against expected MIME type.

        Args:
            file: Django UploadedFile object
            expected_mime_type: Expected MIME type based on extension

        Returns:
            dict with 'valid', 'error', and 'actual_type' keys
        """
        # Save current position
        original_position = file.tell()

        try:
            # Read first 512 bytes for signature check
            file.seek(0)
            header = file.read(512)

            # Reset file position
            file.seek(original_position)

            if len(header) == 0:
                return {
                    'valid': False,
                    'error': 'Empty file',
                    'actual_type': None
                }

            # Get expected signatures
            expected_signatures = cls.MAGIC_SIGNATURES.get(expected_mime_type)

            # Text files have no magic bytes - allow them
            if expected_signatures is None:
                return {
                    'valid': True,
                    'error': None,
                    'actual_type': expected_mime_type
                }

            # Check if file starts with expected signature
            for signature in expected_signatures:
                if header.startswith(signature):
                    # Special handling for WEBP
                    if expected_mime_type == 'image/webp':
                        if b'WEBP' in header[:16]:
                            return {'valid': True, 'error': None, 'actual_type': expected_mime_type}
                    # Special handling for WAV
                    elif expected_mime_type == 'audio/wav':
                        if b'WAVE' in header[:16]:
                            return {'valid': True, 'error': None, 'actual_type': expected_mime_type}
                    else:
                        return {'valid': True, 'error': None, 'actual_type': expected_mime_type}

            # Try to detect actual file type
            detected_type = cls._detect_file_type(header)

            return {
                'valid': False,
                'error': f'File content does not match expected type {expected_mime_type}. Detected: {detected_type or "unknown"}',
                'actual_type': detected_type
            }

        except Exception as e:
            return {
                'valid': False,
                'error': f'Error validating file: {str(e)}',
                'actual_type': None
            }
        finally:
            # Ensure file position is reset
            try:
                file.seek(original_position)
            except:
                pass

    @classmethod
    def _detect_file_type(cls, header: bytes) -> str:
        """Detect file type from magic bytes"""
        for mime_type, signatures in cls.MAGIC_SIGNATURES.items():
            if signatures is None:
                continue
            for signature in signatures:
                if header.startswith(signature):
                    # Additional checks for specific types
                    if mime_type == 'image/webp' and b'WEBP' not in header[:16]:
                        continue
                    if mime_type == 'audio/wav' and b'WAVE' not in header[:16]:
                        continue
                    return mime_type
        return "unknown"
