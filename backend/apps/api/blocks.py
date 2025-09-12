from rest_framework.permissions import IsAuthenticatedOrReadOnly

from rest_framework.response import Response

from rest_framework.views import APIView



Standalone blocks API endpoint.



# Force reload



class BlockTypesAPIView(APIView):



    Simple API view for getting available block types.



    permission_classes = [IsAuthenticatedOrReadOnly]



    def get(self, request):

        """Get all available block types with their metadata."""



        # Define block types with metadata (matching backend BLOCK_MODELS)

        block_types = [

            {

                "type": "hero",

                "label": "Hero Section",

                "description": "Large header with title and CTA",

                "category": "Layout",

                "icon": "layout",

            },

            {

                "type": "richtext",  # Match frontend expectation

                "label": "Rich Text",

                "description": "Formatted text content",

                "category": "Content",

                "icon": "type",

            },

            {

                "type": "image",

                "label": "Image",

                "description": "Single image with caption",

                "category": "Media",

                "icon": "image",

            },

            {

                "type": "gallery",

                "label": "Image Gallery",

                "description": "Multiple images in a grid",

                "category": "Media",

                "icon": "grid",

            },

            {

                "type": "columns",

                "label": "Columns",

                "description": "Multi-column layout",

                "category": "Layout",

                "icon": "columns",

            },

            {

                "type": "cta",  # Match frontend expectation

                "label": "Call to Action",

                "description": "Button with compelling text",

                "category": "Marketing",

                "icon": "megaphone",

            },

            {

                "type": "faq",

                "label": "FAQ",

                "description": "Accordion of questions",

                "category": "Content",

                "icon": "help-circle",

            },

            {

                "type": "content_detail",

                "label": "Content Detail",

                "description": "Dynamic content display",

                "category": "Dynamic",

                "icon": "layout-grid",

            },

            {

                "type": "collection_list",

                "label": "Collection List",

                "description": "Display list of posts or content",

                "category": "Dynamic",

                "icon": "grid",

            },

        ]



        # Sort by category then by label

        block_types.sort(key=lambda x: (x["category"], x["label"]))



        return Response({"block_types": block_types})



class BlockSchemaAPIView(APIView):



    Simple API view for getting the schema of a specific block type.



    permission_classes = [IsAuthenticatedOrReadOnly]



    def get(self, request, block_type):

        """Get the schema for a specific block type."""



        # Basic schemas for each block type

        schemas = {

            "hero": {

                "type": "object",

                "properties": {

                    "title": {"type": "string"},

                    "subtitle": {"type": "string"},

                    "cta_text": {"type": "string"},

                    "cta_url": {"type": "string"},

                    "background_image": {"type": "string"},

                },

            },

            "richtext": {

                "type": "object",

                "properties": {"content": {"type": "string"}},

            },

            "image": {

                "type": "object",

                "properties": {

                    "src": {"type": "string"},

                    "alt": {"type": "string"},

                    "caption": {"type": "string"},

                },

            },

            "gallery": {

                "type": "object",

                "properties": {

                    "images": {

                        "type": "array",

                        "items": {

                            "type": "object",

                            "properties": {

                                "src": {"type": "string"},

                                "alt": {"type": "string"},

                                "caption": {"type": "string"},

                            },

                        },

                    }

                },

            },

            "columns": {

                "type": "object",

                "properties": {

                    "columns": {

                        "type": "array",

                        "items": {

                            "type": "object",

                            "properties": {"content": {"type": "string"}},

                        },

                    },

                    "gap": {"type": "string", "enum": ["sm", "md", "lg"]},

                },

            },

            "cta": {

                "type": "object",

                "properties": {

                    "title": {"type": "string"},

                    "subtitle": {"type": "string"},

                    "cta_text": {"type": "string"},

                    "cta_url": {"type": "string"},

                    "background_color": {"type": "string"},

                },

            },

            "faq": {

                "type": "object",

                "properties": {

                    "items": {

                        "type": "array",

                        "items": {

                            "type": "object",

                            "properties": {

                                "question": {"type": "string"},

                                "answer": {"type": "string"},

                            },

                        },

                    }

                },

            },

            "content_detail": {

                "type": "object",

                "properties": {

                    "label": {"type": "string"},

                    "source": {"type": "string"},

                    "options": {"type": "object"},

                },

            },

            "collection_list": {

                "type": "object",

                "properties": {

                    "collection": {"type": "string"},

                    "limit": {"type": "number"},

                    "template": {"type": "string"},

                },

            },

        }



        if block_type not in schemas:

            return Response(

                {"error": f"Block type '{block_type}' not found"}, status=404

            )



        return Response(schemas[block_type])

