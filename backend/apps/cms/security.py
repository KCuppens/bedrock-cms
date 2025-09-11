"""
Security utilities for CMS content.
"""

from typing import Any, Dict, List, Optional

from django.conf import settings

import bleach  # type: ignore[import-untyped]

# Default allowed tags for rich text content
DEFAULT_ALLOWED_TAGS = [
    "p",
    "div",
    "span",
    "br",
    "hr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "sub",
    "sup",
    "ul",
    "ol",
    "li",
    "a",
    "img",
    "blockquote",
    "pre",
    "code",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "figure",
    "figcaption",
]

# Default allowed attributes for each tag
DEFAULT_ALLOWED_ATTRIBUTES = {
    "*": ["class", "id"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "blockquote": ["cite"],
    "table": ["cellpadding", "cellspacing", "border"],
    "th": ["scope", "rowspan", "colspan"],
    "td": ["rowspan", "colspan"],
}

# Default allowed protocols for URLs
DEFAULT_ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel"]


def get_sanitization_config():
    """
    Get HTML sanitization configuration from settings or defaults.

    Returns:
        Dict with 'allowed_tags', 'allowed_attributes', and 'allowed_protocols'
    """
    return {
        "allowed_tags": getattr(
            settings, "HTML_SANITIZER_ALLOWED_TAGS", DEFAULT_ALLOWED_TAGS
        ),
        "allowed_attributes": getattr(
            settings, "HTML_SANITIZER_ALLOWED_ATTRIBUTES", DEFAULT_ALLOWED_ATTRIBUTES
        ),
        "allowed_protocols": getattr(
            settings, "HTML_SANITIZER_ALLOWED_PROTOCOLS", DEFAULT_ALLOWED_PROTOCOLS
        ),
    }


def sanitize_html(
    html_content: str,
    allowed_tags: Optional[List[str]] = None,
    allowed_attributes: Optional[Dict[str, List[str]]] = None,
    allowed_protocols: Optional[List[str]] = None,
) -> str:
    """
    Sanitize HTML content to remove potentially dangerous elements and attributes.

    Args:
        html_content: Raw HTML string to sanitize
        allowed_tags: List of allowed HTML tags (defaults to settings/DEFAULT_ALLOWED_TAGS)
        allowed_attributes: Dict of allowed attributes per tag (defaults to settings/DEFAULT_ALLOWED_ATTRIBUTES)
        allowed_protocols: List of allowed URL protocols (defaults to settings/DEFAULT_ALLOWED_PROTOCOLS)

    Returns:
        Sanitized HTML string safe for rendering
    """
    if not html_content or not isinstance(html_content, str):
        return ""

    config = get_sanitization_config()

    return bleach.clean(
        html_content,
        tags=allowed_tags or config["allowed_tags"],
        attributes=allowed_attributes or config["allowed_attributes"],
        protocols=allowed_protocols or config["allowed_protocols"],
        strip=True,  # Remove disallowed tags completely
        strip_comments=True,  # Remove HTML comments
    )


def sanitize_rich_text_block(block_data: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize HTML content in a rich_text block.

    Args:
        block_data: Block data dictionary

    Returns:
        Block data with sanitized HTML content
    """
    if not isinstance(block_data, dict):
        return block_data

    # Make a copy to avoid mutating the original
    sanitized_block = block_data.copy()

    # Sanitize the content in props
    if "props" in sanitized_block and isinstance(sanitized_block["props"], dict):
        props = sanitized_block["props"].copy()

        # Sanitize 'content' field if present
        if "content" in props and isinstance(props["content"], str):
            props["content"] = sanitize_html(props["content"])

        sanitized_block["props"] = props

    return sanitized_block


def sanitize_block_content(block_data: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively sanitize HTML content in block data.

    This function handles different block types and sanitizes any HTML content
    found within their properties.

    Args:
        block_data: Block data dictionary

    Returns:
        Block data with sanitized HTML content
    """
    if not isinstance(block_data, dict):
        return block_data

    block_type = block_data.get("type")

    # Handle specific block types that may contain HTML
    if block_type == "rich_text":
        return sanitize_rich_text_block(block_data)

    elif block_type == "hero":
        # Sanitize hero block text content
        sanitized_block = block_data.copy()
        if "props" in sanitized_block and isinstance(sanitized_block["props"], dict):
            props = sanitized_block["props"].copy()

            # Sanitize common text fields that might contain HTML
            for field in ["title", "subtitle", "description", "content"]:
                if field in props and isinstance(props[field], str):
                    props[field] = sanitize_html(props[field])

            sanitized_block["props"] = props
        return sanitized_block

    elif block_type == "cta_band":
        # Sanitize CTA band text content
        sanitized_block = block_data.copy()
        if "props" in sanitized_block and isinstance(sanitized_block["props"], dict):
            props = sanitized_block["props"].copy()

            # Sanitize text fields
            for field in ["title", "subtitle", "cta_text"]:
                if field in props and isinstance(props[field], str):
                    props[field] = sanitize_html(props[field])

            sanitized_block["props"] = props
        return sanitized_block

    elif block_type == "faq":
        # Sanitize FAQ items
        sanitized_block = block_data.copy()
        if "props" in sanitized_block and isinstance(sanitized_block["props"], dict):
            props = sanitized_block["props"].copy()

            if "items" in props and isinstance(props["items"], list):
                sanitized_items = []
                for item in props["items"]:
                    if isinstance(item, dict):
                        sanitized_item = item.copy()
                        for field in ["question", "answer"]:
                            if field in sanitized_item and isinstance(
                                sanitized_item[field], str
                            ):
                                sanitized_item[field] = sanitize_html(
                                    sanitized_item[field]
                                )
                        sanitized_items.append(sanitized_item)
                    else:
                        sanitized_items.append(item)
                props["items"] = sanitized_items

            sanitized_block["props"] = props
        return sanitized_block

    elif block_type == "columns":
        # Recursively sanitize nested blocks in columns
        sanitized_block = block_data.copy()
        if "blocks" in sanitized_block and isinstance(sanitized_block["blocks"], list):
            sanitized_block["blocks"] = [
                sanitize_block_content(nested_block)
                for nested_block in sanitized_block["blocks"]
            ]
        return sanitized_block

    elif block_type == "image":
        # Sanitize image alt and caption
        sanitized_block = block_data.copy()
        if "props" in sanitized_block and isinstance(sanitized_block["props"], dict):
            props = sanitized_block["props"].copy()

            for field in ["alt", "caption"]:
                if field in props and isinstance(props[field], str):
                    props[field] = sanitize_html(props[field])

            sanitized_block["props"] = props
        return sanitized_block

    # For unknown block types, return as-is (could be enhanced to sanitize all string props)
    return block_data


def sanitize_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sanitize HTML content in a list of blocks.

    Args:
        blocks: List of block data dictionaries

    Returns:
        List of blocks with sanitized HTML content
    """
    if not isinstance(blocks, list):
        return blocks

    return [sanitize_block_content(block) for block in blocks]


# Settings documentation for reference
SETTINGS_HELP = """
# HTML Sanitization Settings
# Add these to your Django settings to customize HTML sanitization

# Allowed HTML tags (default: common formatting and structure tags)
HTML_SANITIZER_ALLOWED_TAGS = [
    'p', 'div', 'span', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'b', 'em', 'i', 'u', 's', 'sub', 'sup',
    'ul', 'ol', 'li',
    'a', 'img',
    'blockquote', 'pre', 'code',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'figure', 'figcaption',
]

# Allowed attributes per tag
HTML_SANITIZER_ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'blockquote': ['cite'],
    'table': ['cellpadding', 'cellspacing', 'border'],
    'th': ['scope', 'rowspan', 'colspan'],
    'td': ['rowspan', 'colspan'],
}

# Allowed URL protocols
HTML_SANITIZER_ALLOWED_PROTOCOLS = ['http', 'https', 'mailto', 'tel']
"""
