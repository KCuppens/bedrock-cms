"""
Standard thumbnail presets for responsive images.

Defines breakpoints and configurations for different device sizes
following modern responsive image best practices.
"""

from typing import Dict, List

# Standard responsive breakpoints
BREAKPOINTS = {
    "mobile_sm": 640,
    "mobile_md": 750,
    "tablet": 828,
    "tablet_lg": 1080,
    "desktop": 1200,
    "desktop_lg": 1920,
    "desktop_xl": 2560,
    "desktop_xxl": 3840,
}

# Thumbnail preset configurations
THUMBNAIL_PRESETS = {
    # Ultra-small placeholder for base64 embedding
    "micro": {"width": 20, "height": 20, "quality": 40},
    # Admin thumbnail and media picker
    "thumb": {"width": 150, "quality": 85},
    # Mobile devices
    "mobile_sm": {"width": 640, "quality": 80},
    "mobile_md": {"width": 750, "quality": 80},
    # Tablet devices
    "tablet": {"width": 828, "quality": 82},
    "tablet_lg": {"width": 1080, "quality": 82},
    # Desktop
    "desktop": {"width": 1200, "quality": 85},
    "desktop_lg": {"width": 1920, "quality": 85},
    "desktop_xl": {"width": 2560, "quality": 88},
    # Retina/high-DPI support
    "desktop_xxl": {"width": 3840, "quality": 90},
}

# Default formats to generate
DEFAULT_FORMATS = ["webp", "jpeg"]

# Modern format with best compression (if supported)
MODERN_FORMATS = ["avif", "webp", "jpeg"]


def get_default_thumbnail_config() -> Dict:
    """
    Get default thumbnail configuration for new uploads.

    Returns:
        Dict with sizes, formats, and placeholder settings
    """
    return {
        "sizes": THUMBNAIL_PRESETS,
        "formats": DEFAULT_FORMATS,
        "placeholder": "blurhash",
        "generate_micro": True,  # Generate base64 micro thumbnail
    }


def get_responsive_config(
    include_retina: bool = True, formats: List[str] = None
) -> Dict:
    """
    Get configuration for responsive images.

    Args:
        include_retina: Include extra-large sizes for retina displays
        formats: List of formats to generate (defaults to webp + jpeg)

    Returns:
        Dict with responsive image configuration
    """
    sizes = {
        "mobile_sm": THUMBNAIL_PRESETS["mobile_sm"],
        "mobile_md": THUMBNAIL_PRESETS["mobile_md"],
        "tablet": THUMBNAIL_PRESETS["tablet"],
        "tablet_lg": THUMBNAIL_PRESETS["tablet_lg"],
        "desktop": THUMBNAIL_PRESETS["desktop"],
        "desktop_lg": THUMBNAIL_PRESETS["desktop_lg"],
    }

    if include_retina:
        sizes["desktop_xl"] = THUMBNAIL_PRESETS["desktop_xl"]

    return {
        "sizes": sizes,
        "formats": formats or DEFAULT_FORMATS,
        "placeholder": "blurhash",
    }


def get_thumbnail_config_for_context(
    context: str = "general", formats: List[str] = None
) -> Dict:
    """
    Get thumbnail configuration optimized for specific contexts.

    Args:
        context: Usage context (general, hero, gallery, thumbnail, og_image)
        formats: List of formats to generate

    Returns:
        Dict with context-optimized configuration
    """
    formats = formats or DEFAULT_FORMATS

    if context == "hero":
        # Hero images: larger sizes, higher quality
        return {
            "sizes": {
                "mobile_md": {"width": 750, "quality": 85},
                "tablet_lg": {"width": 1080, "quality": 88},
                "desktop_lg": {"width": 1920, "quality": 90},
                "desktop_xl": {"width": 2560, "quality": 92},
            },
            "formats": formats,
            "placeholder": "blurhash",
        }

    elif context == "gallery":
        # Gallery: balanced sizes, good quality
        return {
            "sizes": {
                "thumb": {"width": 150, "quality": 80},
                "mobile_sm": {"width": 640, "quality": 82},
                "tablet": {"width": 828, "quality": 85},
                "desktop": {"width": 1200, "quality": 88},
            },
            "formats": formats,
            "placeholder": "blurhash",
        }

    elif context == "thumbnail":
        # Thumbnails: small sizes only
        return {
            "sizes": {
                "thumb": {"width": 150, "quality": 80},
                "mobile_sm": {"width": 640, "quality": 80},
            },
            "formats": formats,
            "placeholder": "dominant-color",
        }

    elif context == "og_image":
        # Social media OG images: specific sizes
        return {
            "sizes": {
                "og_image": {"width": 1200, "height": 630, "quality": 90},
                "twitter_card": {"width": 1200, "height": 675, "quality": 90},
            },
            "formats": ["jpeg"],  # Social platforms prefer JPEG
            "placeholder": "blurhash",
        }

    else:
        # General purpose: standard responsive sizes
        return get_responsive_config(include_retina=True, formats=formats)


def get_srcset_widths() -> List[int]:
    """
    Get list of widths for srcset generation.

    Returns:
        List of widths in ascending order
    """
    return sorted(
        [preset["width"] for preset in THUMBNAIL_PRESETS.values() if "width" in preset]
    )


def get_sizes_attribute(breakpoints: Dict[str, int] = None) -> str:
    """
    Generate sizes attribute for responsive images.

    Args:
        breakpoints: Custom breakpoints dict {media_query: size}

    Returns:
        String for sizes attribute

    Example:
        "(max-width: 640px) 100vw, (max-width: 1200px) 50vw, 800px"
    """
    if not breakpoints:
        # Default sizes attribute for common layouts
        return "(max-width: 640px) 100vw, (max-width: 1024px) 80vw, 1200px"

    # Build sizes string from breakpoints
    sizes_parts = []
    for media_query, size in sorted(
        breakpoints.items(), key=lambda x: x[1], reverse=True
    ):
        if isinstance(size, int):
            sizes_parts.append(f"(max-width: {size}px) {size}px")
        else:
            sizes_parts.append(f"(max-width: {media_query}px) {size}")

    return ", ".join(sizes_parts)


# Quality presets by format
QUALITY_PRESETS = {
    "jpeg": {
        "low": 60,
        "medium": 75,
        "high": 85,
        "max": 95,
    },
    "webp": {
        "low": 50,
        "medium": 70,
        "high": 80,
        "max": 90,
    },
    "avif": {
        "low": 40,
        "medium": 60,
        "high": 70,
        "max": 80,
    },
}


def get_optimal_quality(format: str, size: int) -> int:
    """
    Get optimal quality setting based on format and size.

    Args:
        format: Image format (jpeg, webp, avif)
        size: Image width in pixels

    Returns:
        Quality value (0-100)
    """
    format_lower = format.lower()
    presets = QUALITY_PRESETS.get(format_lower, QUALITY_PRESETS["jpeg"])

    # Smaller images can use slightly lower quality
    if size <= 640:
        return presets["medium"]
    elif size <= 1200:
        return presets["high"]
    else:
        return presets["max"]
