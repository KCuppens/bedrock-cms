from django.core.management.base import BaseCommand



from apps.cms.models import BlockType, BlockTypeCategory



Management command to register blog-related block types.



class Command(BaseCommand):

    help = "Register blog-related block types in the database"



    def handle(self, *args, **options):

        blog_blocks = [

            {

                "type": "blog_list",

                "component": "BlogListBlock",

                "label": "Blog List",

                "description": "Display a list of blog posts with filtering options",

                "category": BlockTypeCategory.DYNAMIC,

                "icon": "newspaper",

                "editing_mode": "modal",

                "model_name": "blog.BlogPost",

                "data_source": "list",

                "api_endpoint": "/api/v1/blog/posts/",

                "query_schema": {

                    "filters": ["category", "tags", "featured", "status"],

                    "ordering": ["published_at", "created_at", "title"],

                    "search_fields": ["title", "excerpt", "content"],

                },

                "schema": {

                    "type": "object",

                    "properties": {

                        "title": {"type": "string", "description": "Section title"},

                        "subtitle": {

                            "type": "string",

                            "description": "Section subtitle",

                        },

                        "layout": {

                            "type": "string",

                            "enum": ["list", "grid", "cards", "minimal"],

                            "default": "grid",

                        },

                        "columns": {

                            "type": "integer",

                            "minimum": 1,

                            "maximum": 4,

                            "default": 3,

                        },

                        "limit": {

                            "type": "integer",

                            "minimum": 1,

                            "maximum": 50,

                            "default": 9,

                        },

                        "category": {

                            "type": "string",

                            "description": "Filter by category slug",

                        },

                        "tags": {

                            "type": "array",

                            "items": {"type": "string"},

                            "description": "Filter by tag slugs",

                        },

                        "featured_only": {

                            "type": "boolean",

                            "default": False,

                            "description": "Show only featured posts",

                        },

                        "order_by": {

                            "type": "string",

                            "enum": ["published_at", "created_at", "title", "random"],

                            "default": "published_at",

                        },

                        "show_excerpt": {"type": "boolean", "default": True},

                        "show_author": {"type": "boolean", "default": True},

                        "show_date": {"type": "boolean", "default": True},

                        "show_category": {"type": "boolean", "default": True},

                        "show_tags": {"type": "boolean", "default": False},

                        "show_read_more": {"type": "boolean", "default": True},

                        "read_more_text": {"type": "string", "default": "Read more"},

                        "show_pagination": {"type": "boolean", "default": True},

                    },

                },

                "default_props": {

                    "layout": "grid",

                    "columns": 3,

                    "limit": 9,

                    "featured_only": False,

                    "order_by": "published_at",

                    "show_excerpt": True,

                    "show_author": True,

                    "show_date": True,

                    "show_category": True,

                    "show_tags": False,

                    "show_read_more": True,

                    "read_more_text": "Read more",

                    "show_pagination": True,

                },

            },

            {

                "type": "blog_featured",

                "component": "BlogFeaturedBlock",

                "label": "Featured Blog Posts",

                "description": "Showcase featured blog posts in a hero section",

                "category": BlockTypeCategory.MARKETING,

                "icon": "star",

                "editing_mode": "modal",

                "model_name": "blog.BlogPost",

                "data_source": "list",

                "api_endpoint": "/api/v1/blog/posts/",

                "query_schema": {

                    "filters": ["featured"],

                    "ordering": ["published_at"],

                    "default_filters": {"featured": True},

                },

                "schema": {

                    "type": "object",

                    "properties": {

                        "title": {"type": "string", "description": "Section title"},

                        "layout": {

                            "type": "string",

                            "enum": ["hero", "carousel", "split"],

                            "default": "hero",

                        },

                        "limit": {

                            "type": "integer",

                            "minimum": 1,

                            "maximum": 5,

                            "default": 3,

                        },

                        "auto_rotate": {

                            "type": "boolean",

                            "default": False,

                            "description": "Auto-rotate featured posts (carousel only)",

                        },

                        "interval": {

                            "type": "integer",

                            "minimum": 3,

                            "maximum": 10,

                            "default": 5,

                            "description": "Rotation interval in seconds",

                        },

                    },

                },

                "default_props": {

                    "layout": "hero",

                    "limit": 3,

                    "auto_rotate": False,

                    "interval": 5,

                },

            },

            {

                "type": "blog_categories",

                "component": "BlogCategoriesBlock",

                "label": "Blog Categories",

                "description": "Display blog categories as cards or list",

                "category": BlockTypeCategory.DYNAMIC,

                "icon": "folder",

                "editing_mode": "inline",

                "model_name": "blog.Category",

                "data_source": "list",

                "api_endpoint": "/api/v1/blog/categories/",

                "schema": {

                    "type": "object",

                    "properties": {

                        "title": {"type": "string", "description": "Section title"},

                        "layout": {

                            "type": "string",

                            "enum": ["cards", "list", "chips"],

                            "default": "cards",

                        },

                        "show_count": {

                            "type": "boolean",

                            "default": True,

                            "description": "Show post count per category",

                        },

                        "show_description": {"type": "boolean", "default": True},

                    },

                },

                "default_props": {

                    "layout": "cards",

                    "show_count": True,

                    "show_description": True,

                },

            },

            {

                "type": "blog_single",

                "component": "BlogSingleBlock",

                "label": "Single Blog Post",

                "description": "Display a specific blog post",

                "category": BlockTypeCategory.CONTENT,

                "icon": "file-text",

                "editing_mode": "modal",

                "model_name": "blog.BlogPost",

                "data_source": "single",

                "api_endpoint": "/api/v1/blog/posts/",

                "schema": {

                    "type": "object",

                    "properties": {

                        "post_id": {

                            "type": "integer",

                            "description": "ID of the blog post to display",

                        },

                        "post_slug": {

                            "type": "string",

                            "description": "Slug of the blog post (alternative to ID)",

                        },

                        "show_title": {"type": "boolean", "default": True},

                        "show_meta": {

                            "type": "boolean",

                            "default": True,

                            "description": "Show author, date, category",

                        },

                        "show_social_share": {"type": "boolean", "default": True},

                        "show_related": {

                            "type": "boolean",

                            "default": False,

                            "description": "Show related posts section",

                        },

                        "related_limit": {

                            "type": "integer",

                            "minimum": 2,

                            "maximum": 6,

                            "default": 3,

                        },

                    },

                    "required": [],

                },

                "default_props": {

                    "show_title": True,

                    "show_meta": True,

                    "show_social_share": True,

                    "show_related": False,

                    "related_limit": 3,

                },

            },

            {

                "type": "blog_search",

                "component": "BlogSearchBlock",

                "label": "Blog Search",

                "description": "Search bar for blog posts",

                "category": BlockTypeCategory.DYNAMIC,

                "icon": "search",

                "editing_mode": "inline",

                "model_name": "blog.BlogPost",

                "data_source": "list",

                "api_endpoint": "/api/v1/blog/posts/",

                "query_schema": {

                    "search_fields": ["title", "excerpt", "content"],

                    "filters": ["category", "tags"],

                },

                "schema": {

                    "type": "object",

                    "properties": {

                        "placeholder": {

                            "type": "string",

                            "default": "Search blog posts...",

                        },

                        "show_filters": {

                            "type": "boolean",

                            "default": True,

                            "description": "Show category and tag filters",

                        },

                        "show_results_count": {"type": "boolean", "default": True},

                    },

                },

                "default_props": {

                    "placeholder": "Search blog posts...",

                    "show_filters": True,

                    "show_results_count": True,

                },

            },

        ]



        for block_data in blog_blocks:

            block_type, created = BlockType.objects.update_or_create(

                type=block_data["type"], defaults=block_data

            )



            if created:

                self.stdout.write(

                    self.style.SUCCESS(f"Created block type: {block_type.label}")

                )

            else:

                self.stdout.write(

                    self.style.WARNING(f"Updated block type: {block_type.label}")

                )



        self.stdout.write(

            self.style.SUCCESS("Successfully registered all blog block types")

        )

