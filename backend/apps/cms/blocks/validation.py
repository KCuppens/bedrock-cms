# mypy: ignore-errors
from typing import List, Dict, Any, Literal, Union, Optional
from pydantic import BaseModel, ValidationError, Field, HttpUrl
from rest_framework.exceptions import ValidationError as DRFValidationError
from ..security import sanitize_blocks


class BaseBlockModel(BaseModel):
    """Base model for all block types."""

    type: str
    schema_version: int = Field(default=1)


class HeroBlockModel(BaseBlockModel):
    """Hero section block."""

    type: Literal["hero"]
    props: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class RichTextBlockModel(BaseBlockModel):
    """Rich text content block."""

    type: Literal["richtext", "rich_text"]  # Accept both
    props: Dict[str, Any] = Field(default_factory=lambda: {"content": ""})


class ImageBlockModel(BaseBlockModel):
    """Single image block."""

    type: Literal["image"]
    props: Dict[str, Any] = Field(
        default_factory=lambda: {"src": "", "alt": "", "caption": ""}
    )


class GalleryBlockModel(BaseBlockModel):
    """Image gallery block."""

    type: Literal["gallery"]
    props: Dict[str, Any] = Field(default_factory=lambda: {"images": []})


class ColumnsBlockModel(BaseBlockModel):
    """Multi-column layout block with nested blocks."""

    type: Literal["columns"]
    props: Dict[str, Any] = Field(default_factory=lambda: {"columns": [], "gap": "md"})
    blocks: List[Dict[str, Any]] = Field(default_factory=list)


class CTABandBlockModel(BaseBlockModel):
    """Call-to-action band block."""

    type: Literal["cta", "cta_band"]  # Accept both
    props: Dict[str, Any] = Field(
        default_factory=lambda: {
            "title": "",
            "subtitle": "",
            "cta_text": "",
            "cta_url": "",
            "background_color": "#f8f9fa",
        }
    )


class FAQBlockModel(BaseBlockModel):
    """Frequently Asked Questions block."""

    type: Literal["faq"]
    props: Dict[str, Any] = Field(default_factory=lambda: {"items": []})


class ContentDetailSource(BaseModel):
    """Source configuration for content_detail block."""

    id: Optional[int] = None


class ContentDetailOptions(BaseModel):
    """Display options for content_detail block."""

    show_toc: bool = True
    show_author: bool = True
    show_dates: bool = True
    show_share: bool = True
    show_reading_time: bool = True


class ContentDetailBlockModel(BaseBlockModel):
    """Content detail block for rendering registered model details."""

    type: Literal["content_detail"]
    props: Dict[str, Any] = Field(
        default_factory=lambda: {
            "label": "",  # e.g., "blog.blogpost"
            "source": "route",  # "route" or {"id": int}
            "options": {
                "show_toc": True,
                "show_author": True,
                "show_dates": True,
                "show_share": True,
                "show_reading_time": True,
            },
        }
    )


class CollectionListBlockModel(BaseBlockModel):
    """Collection list block for displaying lists of content."""

    type: Literal["collection_list"]
    props: Dict[str, Any] = Field(
        default_factory=lambda: {
            "source": "blog.blogpost",
            "mode": "query",
            "filters": {},
            "limit": 10,
            "layout": "grid",
            "emptyStateText": "",
        }
    )


# Registry of all block models
BLOCK_MODELS: Dict[str, type[BaseBlockModel]] = {
    "hero": HeroBlockModel,
    "richtext": RichTextBlockModel,  # Match API response
    "rich_text": RichTextBlockModel,  # Keep for backwards compatibility
    "image": ImageBlockModel,
    "gallery": GalleryBlockModel,
    "columns": ColumnsBlockModel,
    "cta": CTABandBlockModel,  # Match API response
    "cta_band": CTABandBlockModel,  # Keep for backwards compatibility
    "faq": FAQBlockModel,
    "content_detail": ContentDetailBlockModel,
    "collection_list": CollectionListBlockModel,  # Use proper model
}


def validate_blocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate a list of blocks using database-driven block types and Pydantic models.
    Returns validated and sanitized blocks or raises DRF ValidationError.
    """
    if not isinstance(blocks, list):
        raise DRFValidationError(
            {"errors": [{"path": "blocks", "msg": "Must be a list"}]}
        )

    # Import here to avoid circular imports
    from ..models import BlockType
    from django.db import connection

    # Check if database is available and BlockType table exists
    db_block_types = {}
    try:
        if (
            connection.introspection.table_names()
            and "cms_blocktype" in connection.introspection.table_names()
        ):
            # Get active block types from database
            db_block_types = {
                bt.type: bt for bt in BlockType.objects.filter(is_active=True)
            }
    except Exception:
        # Database not ready or table doesn't exist, continue with static validation
        pass

    # First pass: Sanitize HTML content in blocks
    sanitized_blocks = sanitize_blocks(blocks)

    validated_blocks = []
    errors = []

    for index, block_data in enumerate(sanitized_blocks):
        if not isinstance(block_data, dict):
            errors.append(
                {"path": f"blocks[{index}]", "msg": "Block must be an object"}
            )
            continue

        block_type = block_data.get("type")
        if not block_type:
            errors.append(
                {"path": f"blocks[{index}].type", "msg": "Block type is required"}
            )
            continue

        # Check if block type exists in database (primary validation)
        if block_type not in db_block_types:
            # Fallback to hardcoded models for backwards compatibility
            if block_type not in BLOCK_MODELS:
                errors.append(
                    {
                        "path": f"blocks[{index}].type",
                        "msg": f"Unknown block type: {block_type}",
                    }
                )
                continue

        # Validate block using appropriate Pydantic model (if available)
        validated_block_dict = block_data.copy()

        if block_type in BLOCK_MODELS:
            try:
                model_class = BLOCK_MODELS[block_type]
                validated_block = model_class(**block_data)
                validated_block_dict = validated_block.dict()

                # Handle nested blocks (for columns)
                if block_type == "columns" and "blocks" in block_data:
                    try:
                        validated_nested = validate_blocks(block_data["blocks"])
                        validated_block_dict["blocks"] = validated_nested
                    except DRFValidationError as nested_error:
                        # Re-path nested errors
                        for error in nested_error.detail.get("errors", []):
                            errors.append(
                                {
                                    "path": f"blocks[{index}].{error['path']}",
                                    "msg": error["msg"],
                                }
                            )
                        continue

            except ValidationError as e:
                # Convert Pydantic errors to DRF format
                for error in e.errors():
                    field_path = ".".join([str(loc) for loc in error["loc"]])
                    errors.append(
                        {"path": f"blocks[{index}].{field_path}", "msg": error["msg"]}
                    )
                continue

        # Basic validation for database-only block types
        elif block_type in db_block_types:
            # Ensure required fields exist
            if "props" not in validated_block_dict:
                validated_block_dict["props"] = {}

            # Validate against database schema if available
            db_block_type = db_block_types[block_type]
            if db_block_type.schema:
                # TODO: Add JSON schema validation here if needed
                # For now, we trust the frontend to send valid data
                pass

        validated_blocks.append(validated_block_dict)

    if errors:
        raise DRFValidationError({"errors": errors})

    return validated_blocks
