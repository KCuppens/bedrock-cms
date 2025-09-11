"""
API views for CMS blocks registry.
"""

from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from drf_spectacular.utils import extend_schema, extend_schema_view
from ..blocks.validation import BLOCK_MODELS
from ..models import BlockType


class BlockTypesView(views.APIView):
    """
    API view for getting available block types and their schemas.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    @extend_schema(
        summary="List available block types",
        description="Get a list of all available block types with their metadata and schemas.",
        responses={
            200: {
                "description": "List of available block types",
                "type": "object",
                "properties": {
                    "block_types": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "label": {"type": "string"},
                                "description": {"type": "string"},
                                "category": {"type": "string"},
                                "icon": {"type": "string"},
                                "schema": {"type": "object"}
                            }
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        """Get all available block types with their metadata from database."""
        
        # Get active block types from database
        db_block_types = BlockType.objects.filter(is_active=True).values(
            'type', 'component', 'label', 'description', 'category', 'icon', 
            'preload', 'editing_mode', 'schema', 'default_props'
        )
        
        block_types = []
        
        for db_block_type in db_block_types:
            block_type = db_block_type['type']
            
            # Get the Pydantic model schema for validation (fallback to empty schema)
            model_schema = {}
            if block_type in BLOCK_MODELS:
                try:
                    model_class = BLOCK_MODELS[block_type]
                    model_schema = model_class.schema()
                except Exception:
                    pass
            
            # Use database schema if available, otherwise fallback to model schema
            schema = db_block_type['schema'] if db_block_type['schema'] else model_schema
            
            block_types.append({
                "type": block_type,
                "component": db_block_type['component'],
                "label": db_block_type['label'],
                "description": db_block_type['description'],
                "category": db_block_type['category'].title(),  # Capitalize for consistency
                "icon": db_block_type['icon'],
                "preload": db_block_type['preload'],
                "editing_mode": db_block_type['editing_mode'],
                "schema": schema,
                "default_props": db_block_type['default_props'] or {}
            })
        
        # Sort by category then by label
        block_types.sort(key=lambda x: (x["category"], x["label"]))
        
        return Response({
            "block_types": block_types
        })


class BlockSchemaView(views.APIView):
    """
    API view for getting the schema of a specific block type.
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    @extend_schema(
        summary="Get block type schema",
        description="Get the JSON schema for a specific block type.",
        responses={
            200: {
                "description": "Block type schema",
                "type": "object"
            },
            404: {
                "description": "Block type not found",
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            }
        }
    )
    def get(self, request, block_type):
        """Get the schema for a specific block type from database."""
        try:
            db_block_type = BlockType.objects.get(type=block_type, is_active=True)
            
            # Use database schema if available, otherwise fallback to model schema
            schema = db_block_type.schema
            if not schema and block_type in BLOCK_MODELS:
                try:
                    model_class = BLOCK_MODELS[block_type]
                    schema = model_class.schema()
                except Exception:
                    schema = {}
            
            return Response(schema or {})
            
        except BlockType.DoesNotExist:
            return Response(
                {"error": f"Block type '{block_type}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )