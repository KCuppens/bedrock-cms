import hashlib
import json
import logging
import os
import tempfile
from io import BytesIO
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.core.cache import cache

import boto3
from botocore.exceptions import ClientError
from PIL import Image, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    S3-optimized image processing service for thumbnail generation.

    Features:
    - Generate multiple thumbnail sizes
    - Create WebP and JPEG variants
    - Generate BlurHash placeholders
    - Extract dominant colors
    - Upload directly to S3 with optimized paths
    - CloudFront-compatible URLs
    """

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
            region_name=getattr(settings, "AWS_S3_REGION_NAME", "us-east-1"),
        )
        self.bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "bedrock-cms")
        self.cloudfront_domain = getattr(settings, "CLOUDFRONT_DOMAIN", "")

    def generate_config_hash(self, thumbnail_config: Dict) -> str:
        """Generate a hash for thumbnail configuration to enable caching"""
        config_str = json.dumps(thumbnail_config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]

    def download_image_from_s3(self, s3_key: str) -> Image.Image:
        """Download image from S3 and return PIL Image object"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            image_data = response["Body"].read()
            return Image.open(BytesIO(image_data))
        except ClientError as e:
            logger.error(f"Failed to download image from S3: {s3_key} - {e}")
            raise

    def upload_image_to_s3(
        self, image: Image.Image, s3_key: str, format: str = "JPEG", quality: int = 85
    ) -> str:
        """Upload PIL Image to S3 and return the URL"""
        try:
            # Convert image to bytes
            output = BytesIO()

            # Handle format-specific options
            save_kwargs = {"format": format}
            if format in ["JPEG", "WEBP"]:
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True

            if format == "JPEG" and image.mode in ("RGBA", "LA", "P"):
                # Convert to RGB for JPEG
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(
                    image, mask=image.split()[-1] if image.mode == "RGBA" else None
                )
                image = background

            image.save(output, **save_kwargs)
            output.seek(0)

            # Upload to S3
            content_type = f"image/{format.lower()}"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=output.getvalue(),
                ContentType=content_type,
                CacheControl="public, max-age=31536000",  # 1 year cache
                Metadata={
                    "quality": str(quality),
                    "format": format.lower(),
                    "generated_by": "bedrock-cms-thumbnail-processor",
                },
            )

            # Return CloudFront URL if configured, otherwise S3 URL
            if self.cloudfront_domain:
                return f"{self.cloudfront_domain.rstrip('/')}/{s3_key}"
            else:
                return f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"

        except Exception as e:
            logger.error(f"Failed to upload image to S3: {s3_key} - {e}")
            raise

    def create_thumbnail(
        self,
        image: Image.Image,
        width: int,
        height: Optional[int] = None,
        quality: int = 85,
    ) -> Image.Image:
        """Create a thumbnail maintaining aspect ratio"""
        original_width, original_height = image.size

        if height is None:
            # Calculate height maintaining aspect ratio
            aspect_ratio = original_width / original_height
            height = int(width / aspect_ratio)

        # Use high-quality resampling
        thumbnail = image.resize((width, height), Image.Resampling.LANCZOS)

        # Apply subtle sharpening for better quality at small sizes
        if width < 500:
            thumbnail = thumbnail.filter(
                ImageFilter.UnsharpMask(radius=0.5, percent=50, threshold=0)
            )

        return thumbnail

    def extract_dominant_color(self, image: Image.Image) -> str:
        """Extract dominant color from image as hex value"""
        try:
            # Resize to small size for faster processing
            small_image = image.resize((50, 50), Image.Resampling.LANCZOS)

            # Convert to RGB if necessary
            if small_image.mode != "RGB":
                small_image = small_image.convert("RGB")

            # Get color histogram
            colors = small_image.getcolors(50 * 50)
            if not colors:
                return "#CCCCCC"  # Default gray

            # Find most common color
            most_common_color = max(colors, key=lambda x: x[0])[1]

            # Convert to hex
            return f"#{most_common_color[0]:02x}{most_common_color[1]:02x}{most_common_color[2]:02x}"

        except Exception as e:
            logger.warning(f"Failed to extract dominant color: {e}")
            return "#CCCCCC"

    def generate_blurhash(self, image: Image.Image) -> str:
        """Generate BlurHash for ultra-fast placeholders"""
        try:
            # Try to import blurhash
            from blurhash import encode

            # Resize to small size for BlurHash processing
            small_image = image.resize((32, 32), Image.Resampling.LANCZOS)

            # Convert to RGB if necessary
            if small_image.mode != "RGB":
                small_image = small_image.convert("RGB")

            # Convert to numpy array format expected by blurhash
            import numpy as np

            image_array = np.array(small_image)

            # Generate BlurHash
            blurhash = encode(image_array, x_components=4, y_components=3)
            return blurhash

        except ImportError:
            logger.warning(
                "BlurHash library not installed, skipping BlurHash generation"
            )
            return ""
        except Exception as e:
            logger.warning(f"Failed to generate BlurHash: {e}")
            return ""

    def generate_thumbnails_for_file(
        self, file_upload, thumbnail_config: Dict
    ) -> Tuple[str, Dict[str, str]]:
        """
        Generate thumbnails for a file based on configuration.

        Args:
            file_upload: FileUpload instance
            thumbnail_config: Configuration dict with sizes, formats, etc.

        Returns:
            Tuple of (config_hash, thumbnail_urls_dict)
        """
        config_hash = self.generate_config_hash(thumbnail_config)

        # Check if thumbnails already exist
        if file_upload.has_thumbnails_for_config(config_hash):
            logger.info(f"Thumbnails already exist for config {config_hash}")
            return config_hash, file_upload.get_thumbnails_for_config(config_hash)

        try:
            # Download original image from S3
            original_image = self.download_image_from_s3(file_upload.storage_path)

            # Update file dimensions if not set
            if not file_upload.width or not file_upload.height:
                file_upload.width, file_upload.height = original_image.size
                file_upload.save(update_fields=["width", "height"])

            # Generate dominant color if not set
            if not file_upload.dominant_color:
                file_upload.dominant_color = self.extract_dominant_color(original_image)
                file_upload.save(update_fields=["dominant_color"])

            # Generate BlurHash if not set
            if not file_upload.blurhash:
                file_upload.blurhash = self.generate_blurhash(original_image)
                file_upload.save(update_fields=["blurhash"])

            thumbnail_urls = {}
            sizes_config = thumbnail_config.get("sizes", {})
            formats = thumbnail_config.get("formats", ["webp", "jpeg"])

            for size_name, size_config in sizes_config.items():
                width = size_config["width"]
                height = size_config.get("height")
                quality = size_config.get("quality", 85)

                # Create thumbnail
                thumbnail = self.create_thumbnail(
                    original_image, width, height, quality
                )

                # Generate thumbnails in requested formats
                for format in formats:
                    format_upper = format.upper()
                    if format_upper == "WEBP":
                        # Generate WebP version
                        s3_key = f"thumbnails/{file_upload.id}/{config_hash}/{size_name}.webp"
                        webp_url = self.upload_image_to_s3(
                            thumbnail, s3_key, "WEBP", quality
                        )
                        thumbnail_urls[f"{size_name}_webp"] = webp_url

                    elif format_upper == "JPEG":
                        # Generate JPEG version
                        s3_key = (
                            f"thumbnails/{file_upload.id}/{config_hash}/{size_name}.jpg"
                        )
                        jpeg_url = self.upload_image_to_s3(
                            thumbnail, s3_key, "JPEG", quality
                        )
                        thumbnail_urls[f"{size_name}_jpeg"] = jpeg_url

                        # Default format (for backward compatibility)
                        if size_name not in thumbnail_urls:
                            thumbnail_urls[size_name] = jpeg_url

            # Store thumbnail URLs in database
            file_upload.add_thumbnails_for_config(config_hash, thumbnail_urls)

            logger.info(
                f"Generated {len(thumbnail_urls)} thumbnails for file {file_upload.id}"
            )
            return config_hash, thumbnail_urls

        except Exception as e:
            logger.error(
                f"Failed to generate thumbnails for file {file_upload.id}: {e}"
            )
            raise

    def verify_s3_objects_exist(self, s3_keys: List[str]) -> bool:
        """Verify that S3 objects exist"""
        try:
            for s3_key in s3_keys:
                # Extract S3 key from URL if it's a full URL
                if s3_key.startswith("http"):
                    s3_key = s3_key.split(f"{self.bucket_name}/")[-1]

                self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def cleanup_thumbnails_for_file(self, file_upload) -> int:
        """Clean up all thumbnails for a file"""
        deleted_count = 0

        try:
            all_urls = file_upload.get_all_thumbnail_urls()

            for url in all_urls:
                # Extract S3 key from URL
                if url.startswith("http"):
                    s3_key = url.split(f"{self.bucket_name}/")[-1]
                else:
                    s3_key = url

                try:
                    self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                    deleted_count += 1
                except ClientError as e:
                    logger.warning(f"Failed to delete S3 object {s3_key}: {e}")

            # Clear thumbnails from database
            file_upload.thumbnails = {}
            file_upload.save(update_fields=["thumbnails"])

            logger.info(
                f"Cleaned up {deleted_count} thumbnails for file {file_upload.id}"
            )

        except Exception as e:
            logger.error(f"Failed to cleanup thumbnails for file {file_upload.id}: {e}")

        return deleted_count
