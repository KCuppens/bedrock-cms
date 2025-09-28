import logging
from typing import Dict, Optional

from django.core.cache import cache
from django.db import models, transaction

from celery import shared_task

from .image_processing import ImageProcessor
from .models import FileUpload

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_thumbnails_for_block(
    self, file_id: str, thumbnail_config: Dict, priority: bool = False
) -> Dict:
    """
    Generate thumbnails for a specific file based on block configuration.

    Args:
        file_id: UUID of the FileUpload instance
        thumbnail_config: Dictionary containing thumbnail configuration
        priority: Whether this is a high-priority request

    Returns:
        Dictionary with config_hash and thumbnail URLs

    Example thumbnail_config:
    {
        "sizes": {
            "mobile": {"width": 375, "quality": 80},
            "tablet": {"width": 768, "quality": 85},
            "desktop": {"width": 1200, "quality": 90}
        },
        "formats": ["webp", "jpeg"],
        "placeholder": "blurhash"
    }
    """
    try:
        logger.info(
            f"Starting thumbnail generation for file {file_id} (priority: {priority})"
        )

        # Get file upload instance
        try:
            file_upload = FileUpload.objects.get(id=file_id)
        except FileUpload.DoesNotExist:
            logger.error(f"File {file_id} not found")
            raise

        # Validate that it's an image file
        if not file_upload.is_image:
            logger.warning(
                f"File {file_id} is not an image, skipping thumbnail generation"
            )
            return {"error": "File is not an image"}

        # Initialize image processor
        processor = ImageProcessor()
        config_hash = processor.generate_config_hash(thumbnail_config)

        # Set cache key for tracking generation status
        cache_key = f"thumbnail_generation:{file_id}:{config_hash}"
        cache.set(cache_key, "processing", timeout=300)  # 5 minute timeout

        try:
            # Generate thumbnails
            config_hash, thumbnail_urls = processor.generate_thumbnails_for_file(
                file_upload, thumbnail_config
            )

            # Update cache with success status
            cache.set(
                cache_key,
                {
                    "status": "completed",
                    "config_hash": config_hash,
                    "urls": thumbnail_urls,
                },
                timeout=3600,
            )  # 1 hour cache

            logger.info(f"Successfully generated thumbnails for file {file_id}")

            return {
                "status": "completed",
                "config_hash": config_hash,
                "urls": thumbnail_urls,
                "file_id": file_id,
            }

        except Exception as exc:
            # Mark as failed in cache
            cache.set(cache_key, {"status": "failed", "error": str(exc)}, timeout=300)

            logger.error(f"Failed to generate thumbnails for file {file_id}: {exc}")

            # Retry the task with exponential backoff
            if self.request.retries < self.max_retries:
                retry_delay = 60 * (2**self.request.retries)
                logger.info(
                    f"Retrying thumbnail generation for file {file_id} in {retry_delay} seconds"
                )
                raise self.retry(exc=exc, countdown=retry_delay)
            else:
                # Max retries reached
                raise exc

    except Exception as exc:
        logger.error(
            f"Critical error in thumbnail generation task for file {file_id}: {exc}"
        )
        raise


@shared_task(bind=True, max_retries=2)
def batch_generate_thumbnails(
    self, file_ids: list, thumbnail_config: Dict, batch_size: int = 5
) -> Dict:
    """
    Batch process thumbnail generation for multiple files.

    Args:
        file_ids: List of FileUpload UUIDs
        thumbnail_config: Thumbnail configuration to apply to all files
        batch_size: Number of files to process concurrently

    Returns:
        Dictionary with processing results
    """
    logger.info(f"Starting batch thumbnail generation for {len(file_ids)} files")

    results = {"total": len(file_ids), "completed": 0, "failed": 0, "errors": []}

    # Process files in batches
    for i in range(0, len(file_ids), batch_size):
        batch = file_ids[i : i + batch_size]

        for file_id in batch:
            try:
                # Trigger individual thumbnail generation task
                result = generate_thumbnails_for_block.delay(
                    file_id, thumbnail_config, priority=False
                )

                # Don't wait for completion in batch mode
                results["completed"] += 1

            except Exception as exc:
                logger.error(
                    f"Failed to queue thumbnail generation for file {file_id}: {exc}"
                )
                results["failed"] += 1
                results["errors"].append({"file_id": file_id, "error": str(exc)})

    logger.info(
        f"Batch thumbnail generation queued: {results['completed']} successful, {results['failed']} failed"
    )
    return results


@shared_task
def cleanup_orphaned_thumbnails() -> Dict:
    """
    Clean up thumbnail files that are no longer referenced by any FileUpload.
    This task should be run periodically to manage storage costs.

    Returns:
        Dictionary with cleanup statistics
    """
    logger.info("Starting cleanup of orphaned thumbnails")

    processor = ImageProcessor()
    stats = {"files_processed": 0, "thumbnails_cleaned": 0, "errors": 0}

    try:
        # Get all files with thumbnails
        files_with_thumbnails = FileUpload.objects.exclude(thumbnails={})

        for file_upload in files_with_thumbnails:
            try:
                # Verify that original file still exists
                if not processor.verify_s3_objects_exist([file_upload.storage_path]):
                    # Original file is gone, clean up all thumbnails
                    deleted_count = processor.cleanup_thumbnails_for_file(file_upload)
                    stats["thumbnails_cleaned"] += deleted_count
                    logger.info(
                        f"Cleaned up {deleted_count} orphaned thumbnails for missing file {file_upload.id}"
                    )

                stats["files_processed"] += 1

            except Exception as exc:
                logger.error(
                    f"Error processing file {file_upload.id} during cleanup: {exc}"
                )
                stats["errors"] += 1

    except Exception as exc:
        logger.error(f"Critical error during thumbnail cleanup: {exc}")
        stats["errors"] += 1

    logger.info(f"Thumbnail cleanup completed: {stats}")
    return stats


@shared_task
def regenerate_missing_metadata() -> Dict:
    """
    Regenerate missing metadata (dimensions, BlurHash, dominant color) for existing images.
    This task is useful for populating data for images uploaded before the thumbnail system.

    Returns:
        Dictionary with processing statistics
    """
    logger.info("Starting regeneration of missing image metadata")

    processor = ImageProcessor()
    stats = {"files_processed": 0, "metadata_updated": 0, "errors": 0}

    try:
        # Find image files missing metadata
        files_needing_metadata = FileUpload.objects.filter(file_type="image").filter(
            models.Q(width__isnull=True)
            | models.Q(height__isnull=True)
            | models.Q(blurhash="")
            | models.Q(dominant_color="")
        )

        for file_upload in files_needing_metadata:
            try:
                # Download and analyze image
                image = processor.download_image_from_s3(file_upload.storage_path)

                updated_fields = []

                # Update dimensions
                if not file_upload.width or not file_upload.height:
                    file_upload.width, file_upload.height = image.size
                    updated_fields.extend(["width", "height"])

                # Generate BlurHash
                if not file_upload.blurhash:
                    file_upload.blurhash = processor.generate_blurhash(image)
                    updated_fields.append("blurhash")

                # Extract dominant color
                if not file_upload.dominant_color:
                    file_upload.dominant_color = processor.extract_dominant_color(image)
                    updated_fields.append("dominant_color")

                # Save updates
                if updated_fields:
                    file_upload.save(update_fields=updated_fields)
                    stats["metadata_updated"] += 1
                    logger.info(
                        f"Updated metadata for file {file_upload.id}: {updated_fields}"
                    )

                stats["files_processed"] += 1

            except Exception as exc:
                logger.error(
                    f"Error processing file {file_upload.id} for metadata: {exc}"
                )
                stats["errors"] += 1

    except Exception as exc:
        logger.error(f"Critical error during metadata regeneration: {exc}")
        stats["errors"] += 1

    logger.info(f"Metadata regeneration completed: {stats}")
    return stats


def get_thumbnail_generation_status(file_id: str, config_hash: str) -> Optional[Dict]:
    """
    Get the status of thumbnail generation for a specific file and configuration.

    Args:
        file_id: UUID of the FileUpload instance
        config_hash: Configuration hash

    Returns:
        Dictionary with status information or None if not found
    """
    cache_key = f"thumbnail_generation:{file_id}:{config_hash}"
    return cache.get(cache_key)


def queue_thumbnail_generation(
    file_id: str, thumbnail_config: Dict, priority: bool = False
) -> str:
    """
    Queue thumbnail generation task and return task ID.

    Args:
        file_id: UUID of the FileUpload instance
        thumbnail_config: Thumbnail configuration
        priority: Whether to process with high priority

    Returns:
        Celery task ID
    """
    task = generate_thumbnails_for_block.delay(file_id, thumbnail_config, priority)
    return task.id
