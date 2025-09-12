"""
Background tasks for CMS operations.
"""

import logging
import re
from typing import Any
from urllib.parse import urljoin

import requests
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Page
from .scheduling import ScheduledTask

logger = logging.getLogger(__name__)


class LinkExtractor:
    """Extract and validate internal links from content blocks."""

    # Regex patterns for finding links
    LINK_PATTERNS = [
        r'href=["\']([^"\']+)["\']',  # HTML href attributes
        r'src=["\']([^"\']+)["\']',  # HTML src attributes
        r'"url":\s*["\']([^"\']+)["\']',  # JSON url properties
        r'"link":\s*["\']([^"\']+)["\']',  # JSON link properties
        r'"href":\s*["\']([^"\']+)["\']',  # JSON href properties
    ]

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Bedrock-CMS-LinkChecker/1.0"})

    def extract_links_from_blocks(
        self, blocks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract all links from page blocks."""
        links = []

        if not blocks:
            return links

        for block_index, block in enumerate(blocks):
            block_links = self._extract_links_from_block(block, block_index)
            links.extend(block_links)

        return links

    def _extract_links_from_block(
        self, block: dict[str, Any], block_index: int, parent_path: str = ""
    ) -> list[dict[str, Any]]:
        """Extract links from a single block recursively."""
        links = []

        if not isinstance(block, dict):
            return links

        block_type = block.get("type", "unknown")
        block_path = (
            f"{parent_path}blocks[{block_index}]"
            if parent_path
            else f"blocks[{block_index}]"
        )

        # Extract links from block content
        content_str = str(block)
        found_urls = self._find_urls_in_text(content_str)

        for url in found_urls:
            if self._is_internal_link(url):
                links.append(
                    {
                        "url": url,
                        "block_path": block_path,
                        "block_type": block_type,
                        "context": self._get_link_context(block, url),
                    }
                )

        # Handle nested blocks (like in columns)
        if "blocks" in block and isinstance(block["blocks"], list):
            for nested_index, nested_block in enumerate(block["blocks"]):
                nested_links = self._extract_links_from_block(
                    nested_block, nested_index, f"{block_path}.blocks."
                )
                links.extend(nested_links)

        return links

    def _find_urls_in_text(self, text: str) -> list[str]:
        """Find URLs in text using regex patterns."""
        urls = set()

        for pattern in self.LINK_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            urls.update(matches)

        return list(urls)

    def _is_internal_link(self, url: str) -> bool:
        """Check if URL is an internal link that should be checked."""
        if not url:
            return False

        # Skip external URLs
        if url.startswith(("http://", "https://")) and not url.startswith(
            self.base_url
        ):
            return False

        # Skip non-HTTP protocols
        if url.startswith(("mailto:", "tel:", "ftp:", "javascript:")):
            return False

        # Skip fragments and query-only URLs
        if url.startswith(("#", "?")):
            return False

        return True

    def _get_link_context(self, block: dict[str, Any], url: str) -> str:
        """Get context information about where the link appears."""
        props = block.get("props", {})

        # Try to find text context around the link
        context_fields = ["content", "text", "title", "description"]

        for field in context_fields:
            if field in props and url in str(props[field]):
                text = str(props[field])
                # Find text around the URL
                url_index = text.find(url)
                start = max(0, url_index - 50)
                end = min(len(text), url_index + len(url) + 50)
                return text[start:end].strip()

        return f"Found in {block.get('type', 'unknown')} block"

    def check_link_status(self, url: str, timeout: int = 10) -> dict[str, Any]:
        """Check if a link is accessible."""
        # Convert relative URLs to absolute
        if not url.startswith(("http://", "https://")):
            url = urljoin(self.base_url, url)

        result = {
            "url": url,
            "status_code": None,
            "is_broken": True,
            "error": None,
            "checked_at": timezone.now(),
        }

        try:
            # Use HEAD request first for efficiency
            response = self.session.head(url, timeout=timeout, allow_redirects=True)

            # If HEAD not supported, try GET
            if response.status_code == 405:
                response = self.session.get(url, timeout=timeout, allow_redirects=True)

            result["status_code"] = response.status_code
            result["is_broken"] = response.status_code >= 400

            if response.status_code >= 400:
                result["error"] = f"HTTP {response.status_code}: {response.reason}"

        except requests.exceptions.Timeout:
            result["error"] = "Request timeout"
        except requests.exceptions.ConnectionError:
            result["error"] = "Connection error"
        except requests.exceptions.RequestException as e:
            result["error"] = str(e)
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"

        return result


@shared_task(bind=True)
def check_internal_links(self, page_ids: list[int] | None = None) -> dict[str, Any]:
    """
    Check internal links in pages and report broken ones.

    Args:
        page_ids: Optional list of page IDs to check. If None, checks all published pages.

    Returns:
        Dict with broken links report
    """
    try:
        # Initialize link extractor
        extractor = LinkExtractor()

        # Get pages to check
        if page_ids:
            pages = Page.objects.filter(id__in=page_ids, status="published")
        else:
            pages = Page.objects.filter(status="published")

        total_pages = pages.count()
        results = {
            "total_pages_checked": 0,
            "total_links_found": 0,
            "total_links_checked": 0,
            "broken_links": [],
            "errors": [],
        }

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": total_pages,
                "status": f"Starting link check for {total_pages} pages",
            },
        )

        for page_index, page in enumerate(pages):
            try:
                # Extract links from page blocks
                links = extractor.extract_links_from_blocks(page.blocks or [])
                results["total_links_found"] += len(links)

                # Check each link
                for link_info in links:
                    link_status = extractor.check_link_status(link_info["url"])
                    results["total_links_checked"] += 1

                    if link_status["is_broken"]:
                        broken_link = {
                            "page_id": page.id,
                            "page_title": page.title,
                            "page_path": page.path,
                            "page_locale": page.locale.code,
                            "url": link_info["url"],
                            "block_path": link_info["block_path"],
                            "block_type": link_info["block_type"],
                            "context": link_info["context"],
                            "status_code": link_status["status_code"],
                            "error": link_status["error"],
                            "checked_at": link_status["checked_at"],
                        }
                        results["broken_links"].append(broken_link)

                results["total_pages_checked"] += 1

                # Update progress
                if page_index % 10 == 0 or page_index == total_pages - 1:
                    int((page_index + 1) / total_pages * 100)
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current": page_index + 1,
                            "total": total_pages,
                            "status": f"Checked {page_index + 1} pages, found {len(results['broken_links'])} broken links",
                        },
                    )

            except Exception as e:
                error_msg = f"Error checking page {page.id}: {str(e)}"
                logger.warning(error_msg)
                results["errors"].append(error_msg)

        # Final summary
        self.update_state(
            state="SUCCESS",
            meta={
                "current": total_pages,
                "total": total_pages,
                "status": f"Completed: {len(results['broken_links'])} broken links found",
            },
        )

        logger.info(
            "Link check completed: %s links checked, {len(results['broken_links'])} broken",
            results["total_links_checked"],
        )
        return results

    except Exception as e:
        error_msg = f"Failed to check internal links: {str(e)}"
        logger.error(error_msg)
        self.update_state(state="FAILURE", meta={"error": error_msg})
        raise


@shared_task
def nightly_link_check():
    """
    Nightly task to check all internal links.
    """
    logger.info("Starting nightly internal link check")
    result = check_internal_links.delay()
    return result.id


@shared_task(bind=True)
def check_single_page_links(self, page_id: int) -> dict[str, Any]:
    """Check links for a single page."""
    return check_internal_links(self, page_ids=[page_id])


@shared_task
def publish_scheduled_content():
    """
    Publish scheduled content that's ready to be published.
    This task should run every minute to check for content ready to publish.
    """
    from apps.blog.models import BlogPost

    now = timezone.now()
    published_count = 0
    unpublished_count = 0
    errors = []

    try:
        # Publish scheduled pages
        scheduled_pages = Page.objects.filter(
            status="scheduled", published_at__lte=now, published_at__isnull=False
        )

        for page in scheduled_pages:
            try:
                with transaction.atomic():
                    page.status = "published"
                    page.save(update_fields=["status"])
                    published_count += 1
                    logger.info(
                        f"Published scheduled page: {page.title} (ID: {page.id})"
                    )
            except Exception as e:
                error_msg = f"Failed to publish page {page.id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Publish scheduled blog posts (if they exist and have scheduled status)
        try:
            scheduled_posts = BlogPost.objects.filter(
                status="scheduled", published_at__lte=now, published_at__isnull=False
            )

            for post in scheduled_posts:
                try:
                    with transaction.atomic():
                        post.status = "published"
                        post.save(update_fields=["status"])
                        published_count += 1
                        logger.info(
                            f"Published scheduled blog post: {post.title} (ID: {post.id})"
                        )
                except Exception as e:
                    error_msg = f"Failed to publish blog post {post.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

        except Exception as e:
            # Blog app might not be installed or have different structure
            logger.warning(f"Could not check scheduled blog posts: {str(e)}")

        # Log summary
        if published_count > 0 or errors:
            logger.info(
                f"Scheduled publishing completed: {published_count} items published, {len(errors)} errors"
            )

        return {
            "published_count": published_count,
            "unpublished_count": unpublished_count,
            "errors": errors,
            "checked_at": now,
        }

    except Exception as e:
        error_msg = f"Critical error in scheduled publishing: {str(e)}"
        logger.error(error_msg)
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Retry after 1 minute
    autoretry_for=(Exception,),
)
def process_scheduled_publishing(self):
    """
    Process all pending scheduled publishing tasks.
    This task should be run periodically (e.g., every minute) via Celery Beat.
    """
    now = timezone.now()
    processed_count = 0
    failed_count = 0
    errors = []

    logger.info("Starting scheduled publishing task processing")

    try:
        # Get all pending tasks that should run now
        # Using select_for_update with skip_locked for concurrent safety
        pending_tasks = ScheduledTask.objects.filter(
            status="pending", scheduled_for__lte=now
        ).select_for_update(skip_locked=True)[:50]  # Process max 50 at a time

        for task in pending_tasks:
            try:
                # Execute the task
                success = task.execute()
                if success:
                    processed_count += 1
                    logger.info(
                        f"Successfully executed task {task.id}: {task.task_type} for {task.content_object}"
                    )
                else:
                    failed_count += 1
                    errors.append(f"Task {task.id} failed: {task.error_message}")
                    logger.error(
                        f"Failed to execute task {task.id}: {task.error_message}"
                    )

            except Exception as e:
                failed_count += 1
                error_msg = f"Error processing task {task.id}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)

                # Re-raise if this is a retry-able error and we haven't exceeded max retries
                if task.attempts < 3:
                    raise

        logger.info(
            f"Scheduled publishing completed: {processed_count} processed, {failed_count} failed"
        )

        return {
            "processed_count": processed_count,
            "failed_count": failed_count,
            "errors": errors,
            "checked_at": now,
        }

    except Exception as e:
        error_msg = f"Critical error in scheduled publishing: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise self.retry(exc=e)
