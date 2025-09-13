"""Email utility functions"""

import re
from datetime import datetime
from typing import Any, Dict

from django.conf import settings
from django.utils.html import strip_tags

import bleach


def validate_email_address(email: str) -> bool:
    """Validate email address format

    Args:
        email: Email address to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not email:
        return False

    # Basic email regex pattern
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def sanitize_html_content(html_content: str) -> str:
    """Sanitize HTML content to prevent XSS attacks

    Args:
        html_content: HTML content to sanitize

    Returns:
        str: Sanitized HTML content
    """
    # Define allowed tags and attributes
    allowed_tags = [
        "p",
        "br",
        "span",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "strong",
        "em",
        "u",
        "i",
        "b",
        "a",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tr",
        "td",
        "th",
        "img",
    ]

    allowed_attributes = {
        "a": ["href", "title", "target"],
        "img": ["src", "alt", "width", "height"],
        "*": ["class", "style"],
    }

    # Clean the HTML
    cleaned = bleach.clean(
        html_content, tags=allowed_tags, attributes=allowed_attributes, strip=True
    )

    return cleaned


def get_email_context_defaults() -> Dict[str, Any]:
    """Get default context variables for email templates

    Returns:
        Dict: Default context variables
    """
    return {
        "site_name": getattr(settings, "SITE_NAME", "Django Site"),
        "site_url": getattr(settings, "SITE_URL", "http://localhost:8000"),
        "current_year": datetime.now().year,
        "support_email": getattr(settings, "SUPPORT_EMAIL", "support@example.com"),
        "company_name": getattr(settings, "COMPANY_NAME", "Company"),
        "company_address": getattr(settings, "COMPANY_ADDRESS", ""),
    }


def extract_plain_text_from_html(html_content: str) -> str:
    """Extract plain text from HTML content

    Args:
        html_content: HTML content

    Returns:
        str: Plain text extracted from HTML
    """
    # Strip HTML tags
    text = strip_tags(html_content)

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def format_recipient_list(recipients: list) -> str:
    """Format a list of recipients for display

    Args:
        recipients: List of email addresses

    Returns:
        str: Formatted recipient string
    """
    if not recipients:
        return ""

    if len(recipients) == 1:
        return recipients[0]
    elif len(recipients) == 2:
        return f"{recipients[0]} and {recipients[1]}"
    else:
        return f'{", ".join(recipients[:-1])}, and {recipients[-1]}'


def parse_email_headers(headers_dict: dict) -> str:
    """Parse email headers dictionary into string format

    Args:
        headers_dict: Dictionary of email headers

    Returns:
        str: Formatted headers string
    """
    if not headers_dict:
        return ""

    lines = []
    for key, value in headers_dict.items():
        lines.append(f"{key}: {value}")

    return "\n".join(lines)
