from django.core.cache import cache



from drf_spectacular.utils import extend_schema

from rest_framework import views

from rest_framework.permissions import AllowAny

from rest_framework.response import Response



from apps.cms.models import Page

from apps.i18n.models import Locale





class NavigationView(views.APIView):



    API view for getting navigation menu items.

    Returns pages marked as in_main_menu.



    permission_classes = [AllowAny]



    @extend_schema(

        summary="Get navigation menu items",

        description="Get all pages marked for main navigation menu.",

        responses={

            200: {

                "description": "Navigation menu items",

                "type": "object",

                "properties": {

                    "menu_items": {

                        "type": "array",

                        "items": {

                            "type": "object",

                            "properties": {

                                "id": {"type": "integer"},

                                "title": {"type": "string"},

                                "slug": {"type": "string"},

                                "path": {"type": "string"},

                                "position": {"type": "integer"},

                                "parent": {"type": "integer", "nullable": True},

                                "children": {

                                    "type": "array",

                                    "items": {"$ref": "#/components/schemas/MenuItem"},

                                },

                            },

                        },

                    }

                },

            }

        },

    )

    def get(self, request):

        """Get navigation menu items."""



        # Get locale from request

        locale_code = request.GET.get("locale", "en")



        # Try to get from cache first

        cache_key = f"navigation_menu_{locale_code}"

        menu_items = cache.get(cache_key)



        if menu_items is None:

            # Get all pages marked for main menu, ordered by position

            # Filter by locale if provided



            filters = {"in_main_menu": True, "status": "published"}



            # Add locale filter if specified

            if locale_code:

                try:

                    locale = Locale.objects.get(code=locale_code)

                    filters["locale"] = locale

                except Locale.DoesNotExist:

                    pass  # Fall back to all locales if locale not found



            pages = (

                Page.objects.filter(**filters)

                .select_related("locale")

                .order_by("position", "title")

            )



            # Build hierarchical menu structure

            menu_items = []

            page_map = {}



            # First pass: create all items

            for page in pages:

                item = {

                    "id": page.id,

                    "title": page.title,

                    "slug": page.slug,

                    "path": page.path,

                    "position": page.position,

                    "parent": page.parent_id,

                    "children": [],

                }

                page_map[page.id] = item



                # Add to root level if no parent

                if not page.parent_id:

                    """menu_items.append(item)"""



            # Second pass: organize children

            for page in pages:

                if page.parent_id and page.parent_id in page_map:

                    parent_item = page_map[page.parent_id]

                    """parent_item["children"].append(page_map[page.id])"""



            # Remove items that became children from root level

            menu_items = [item for item in menu_items if not item["parent"]]



            # Cache for 5 minutes

            cache.set(cache_key, menu_items, timeout=300)



        return Response({"menu_items": menu_items})



class FooterView(views.APIView):



    API view for getting footer menu items.

    Returns pages marked as in_footer.



    permission_classes = [AllowAny]



    @extend_schema(

        summary="Get footer menu items",

        description="Get all pages marked for footer quick links.",

        responses={

            200: {

                "description": "Footer menu items",

                "type": "object",

                "properties": {

                    "footer_items": {

                        "type": "array",

                        "items": {

                            "type": "object",

                            "properties": {

                                "id": {"type": "integer"},

                                "title": {"type": "string"},

                                "slug": {"type": "string"},

                                "path": {"type": "string"},

                                "position": {"type": "integer"},

                            },

                        },

                    }

                },

            }

        },

    )

    def get(self, request):

        """Get footer menu items."""



        # Get locale from request

        locale_code = request.GET.get("locale", "en")



        # Try to get from cache first

        cache_key = f"footer_menu_{locale_code}"

        footer_items = cache.get(cache_key)



        if footer_items is None:

            # Get all pages marked for footer, ordered by position

            # Filter by locale if provided



            filters = {"in_footer": True, "status": "published"}



            # Add locale filter if specified

            if locale_code:

                try:

                    locale = Locale.objects.get(code=locale_code)

                    filters["locale"] = locale

                except Locale.DoesNotExist:

                    pass  # Fall back to all locales if locale not found



            pages = (

                Page.objects.filter(**filters)

                .select_related("locale")

                .order_by("position", "title")

            )



            footer_items = [

                {

                    "id": page.id,

                    "title": page.title,

                    "slug": page.slug,

                    "path": page.path,

                    "position": page.position,

                }

                for page in pages

            ]



            # Cache for 5 minutes

            cache.set(cache_key, footer_items, timeout=300)



        return Response({"footer_items": footer_items})



class SiteSettingsView(views.APIView):



    API view for getting site-wide settings like homepage, navigation, and footer.



    permission_classes = [AllowAny]



    @extend_schema(

        summary="Get site settings",

        description="Get site-wide configuration including homepage and menu items.",

        responses={

            200: {

                "description": "Site settings",

                "type": "object",

                "properties": {

                    "homepage": {

                        "type": "object",

                        "properties": {

                            "id": {"type": "integer"},

                            "title": {"type": "string"},

                            "slug": {"type": "string"},

                            "path": {"type": "string"},

                        },

                    },

                    "navigation": {

                        "type": "array",

                        "items": {"$ref": "#/components/schemas/MenuItem"},

                    },

                    "footer": {

                        "type": "array",

                        "items": {"$ref": "#/components/schemas/MenuItem"},

                    },

                },

            }

        },

    )

    def get(self, request):

        """Get site settings including homepage, navigation, and footer."""



        locale_code = request.GET.get("locale", "en")

        cache_key = f"site_settings_{locale_code}"

        settings = cache.get(cache_key)



        if settings is None:

            # Get homepage

            homepage = None

            try:



                homepage_filters = {"is_homepage": True, "status": "published"}



                # Add locale filter if specified

                if locale_code:

                    try:

                        locale = Locale.objects.get(code=locale_code)

                        homepage_filters["locale"] = locale

                    except Locale.DoesNotExist:

                        pass  # Fall back to all locales if locale not found



                homepage_page = (

                    Page.objects.filter(**homepage_filters)

                    .select_related("locale")

                    .first()

                )



                if homepage_page:

                    homepage = {

                        "id": homepage_page.id,

                        "title": homepage_page.title,

                        "slug": homepage_page.slug,

                        "path": homepage_page.path,

                    }

            except Page.DoesNotExist:
                pass



            # Get navigation items (reuse logic from NavigationView)

            nav_filters = {"in_main_menu": True, "status": "published"}



            # Add locale filter if specified

            if locale_code:

                try:

                    locale = Locale.objects.get(code=locale_code)

                    nav_filters["locale"] = locale

                except Locale.DoesNotExist:

                    pass  # Fall back to all locales if locale not found



            nav_pages = (

                Page.objects.filter(**nav_filters)

                .select_related("locale")

                .order_by("position", "title")

            )



            navigation = []

            page_map = {}



            for page in nav_pages:

                item = {

                    "id": page.id,

                    "title": page.title,

                    "slug": page.slug,

                    "path": page.path,

                    "position": page.position,

                    "parent": page.parent_id,

                    "children": [],

                }

                page_map[page.id] = item



                if not page.parent_id:

                    """navigation.append(item)"""



            for page in nav_pages:

                if page.parent_id and page.parent_id in page_map:

                    parent_item = page_map[page.parent_id]

                    """parent_item["children"].append(page_map[page.id])"""



            navigation = [item for item in navigation if not item["parent"]]



            # Get footer items

            footer_filters = {"in_footer": True, "status": "published"}



            # Add locale filter if specified

            if locale_code:

                try:

                    locale = Locale.objects.get(code=locale_code)

                    footer_filters["locale"] = locale

                except Locale.DoesNotExist:

                    pass  # Fall back to all locales if locale not found



            footer_pages = (

                Page.objects.filter(**footer_filters)

                .select_related("locale")

                .order_by("position", "title")

            )



            footer = [

                {

                    "id": page.id,

                    "title": page.title,

                    "slug": page.slug,

                    "path": page.path,

                    "position": page.position,

                }

                for page in footer_pages

            ]



            settings = {

                "homepage": homepage,

                "navigation": navigation,

                "footer": footer,

            }



            # Cache for 5 minutes

            cache.set(cache_key, settings, timeout=300)



        return Response(settings)

