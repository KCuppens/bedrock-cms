"""
Block registry utilities for the CMS.
Provides helper functions to work with block types and metadata.
"""

from apps.cms.models import BlockType


def get_block_metadata():
    """
    Get metadata for all active block types for API responses.
    
    This function delegates to the BlockType model's class method
    to maintain consistency and avoid code duplication.
    
    Returns:
        QuerySet: Block type metadata for active blocks
    """
    return BlockType.get_block_metadata()


def get_block_registry():
    """
    Get the full block registry for all active block types.
    
    Returns:
        QuerySet: Full block registry data
    """
    return BlockType.get_registry()


def get_block_by_type(block_type):
    """
    Get a specific block type by its type identifier.
    
    Args:
        block_type (str): The block type identifier
        
    Returns:
        BlockType: The block type instance or None if not found
    """
    try:
        return BlockType.objects.get(type=block_type, is_active=True)
    except BlockType.DoesNotExist:
        return None


def is_block_type_active(block_type):
    """
    Check if a block type is active.
    
    Args:
        block_type (str): The block type identifier
        
    Returns:
        bool: True if the block type is active, False otherwise
    """
    return BlockType.objects.filter(type=block_type, is_active=True).exists()