from typing import Any



from django.db.models import Q

from django.shortcuts import get_object_or_404



from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import OpenApiParameter, extend_schema

from rest_framework import filters, permissions, status, viewsets

from rest_framework.decorators import action

from rest_framework.response import Response



from apps.i18n.models import Locale



from .config import ContentConfig

from .registry import content_registry

from .serializers import (  # models

    Auto-generated,

    RegistrySerializer,

    RegistrySummarySerializer,

    ViewSets,

    content,

    get_serializer_for_config,

    registered,

)





class ContentViewSetFactory:



    Factory for creating ViewSets for registered content models.



    @classmethod

    def create_viewset(cls, config: ContentConfig) -> type[viewsets.ModelViewSet]:



        Create a ViewSet class for a content configuration.



        Args:

            config: ContentConfig instance



        Returns:

            ModelViewSet class



        model = config.model

        serializer_class = get_serializer_for_config(config)



        # Create the ViewSet class dynamically

        viewset_class = type(

            f"{model.__name__}ViewSet",

            (viewsets.ModelViewSet,),

            {

                "queryset": model.objects.all(),

                "serializer_class": serializer_class,

                "permission_classes": [permissions.IsAuthenticatedOrReadOnly],

                "filter_backends": [

                    DjangoFilterBackend,

                    filters.SearchFilter,

                    filters.OrderingFilter,

                ],

                "filterset_fields": cls._get_filterset_fields(config),

                "search_fields": cls._get_search_fields(config),

                "ordering_fields": cls._get_ordering_fields(config),

                "ordering": config.ordering,

                **cls._get_custom_methods(config),

            },

        )



        return viewset_class



    @classmethod

    def _get_filterset_fields(cls, config: ContentConfig) -> list[str]:

        """Get filterset fields for the ViewSet."""

        fields = []



        # Add locale filtering if applicable

        if config.locale_field:

            fields.append(config.locale_field)



        # Add status filtering if model supports publishing

        if config.supports_publishing():

            fields.append("status")



        # Add common fields that are usually filterable

        model_fields = {f.name for f in config.model._meta.get_fields()}



        for field in ["category", "tags", "author", "created_at", "updated_at"]:

            if field in model_fields:

                fields.append(field)



        return fields



    @classmethod

    def _get_search_fields(cls, config: ContentConfig) -> list[str]:

        """Get search fields for the ViewSet."""

        # Use configured searchable fields, but flatten nested fields for Django filter

        search_fields = []



        for field in config.searchable_fields:

            if "." in field:

                # Handle nested JSON fields differently

                if field.endswith(".title") or field.endswith(".description"):

                    # For SEO fields, we'll handle these in custom search



                else:

                    search_fields.append(field.split(".")[0])

            else:

                search_fields.append(field)



        return search_fields



    @classmethod

    def _get_ordering_fields(cls, config: ContentConfig) -> list[str]:

        """Get ordering fields for the ViewSet."""

        model_fields = {f.name for f in config.model._meta.get_fields()}



        ordering_fields = []

        for field in config.ordering:

            clean_field = field.lstrip("-+")

            if clean_field in model_fields:

                ordering_fields.append(clean_field)



        # Add common ordering fields

        for field in ["created_at", "updated_at", "published_at", "title", "name"]:

            if field in model_fields and field not in ordering_fields:

                ordering_fields.append(field)



        return ordering_fields



    @classmethod

    def _get_custom_methods(cls, config: ContentConfig) -> dict[str, Any]:

        """Get custom methods for the ViewSet."""

        methods = {}



        # Add by-slug action if applicable

        if config.slug_field:



            @extend_schema(

                summary=f"Get {config.name} by slug",

                description=f"Retrieve a {config.name.lower()} by its slug and optional locale.",

                parameters=[

                    OpenApiParameter("slug", str, description="Content slug"),

                    OpenApiParameter(

                        "locale", str, description="Locale code (optional)"

                    ),

                ],

            )

            @action(detail=False, methods=["get"], url_path="by-slug")

            def by_slug(self, request):

                slug = request.query_params.get("slug")

                locale_code = request.query_params.get("locale")



                if not slug:

                    return Response(

                        {"error": "slug parameter is required"},

                        status=status.HTTP_400_BAD_REQUEST,

                    )



                queryset = self.get_queryset()



                # Filter by slug

                queryset = queryset.filter(**{config.slug_field: slug})



                # Filter by locale if specified and model supports localization

                if locale_code and config.locale_field:

                    try:

                        locale = Locale.objects.get(code=locale_code, is_active=True)

                        queryset = queryset.filter(**{config.locale_field: locale})

                    except Locale.DoesNotExist:

                        return Response(

                            {"error": "Invalid locale code"},

                            status=status.HTTP_400_BAD_REQUEST,

                        )



                # Get the object

                obj = get_object_or_404(queryset)

                serializer = self.get_serializer(obj)

                return Response(serializer.data)



            methods["by_slug"] = by_slug



        # Add custom filtering method for complex searches

        def make_get_queryset(model_class, config_obj):

            def get_queryset(self):

                queryset = model_class.objects.all()



                # Custom search across JSON fields (only if request exists)

                if hasattr(self, "request") and self.request:

                    q = self.request.query_params.get("q")

                else:

                    q = None



                if q:

                    q_objects = Q()



                    # Search in configured searchable fields

                    for field in config_obj.searchable_fields:

                        if "." in field:

                            # Handle nested JSON field searches

                            root_field, nested_key = field.split(".", 1)

                            if hasattr(model_class, root_field):

                                # Use JSONField contains search

                                q_objects |= Q(**{f"{root_field}__icontains": q})

                        else:

                            # Regular field search

                            if hasattr(model_class, field):

                                q_objects |= Q(**{f"{field}__icontains": q})



                    if q_objects:

                        queryset = queryset.filter(q_objects)



                return queryset



            return get_queryset



        methods["get_queryset"] = make_get_queryset(config.model, config)



        # Add locale filtering for localized content

        if config.locale_field:



            def make_filter_queryset(locale_field_name):

                def filter_queryset(self, queryset):

                    # Use base filter_queryset from parent ViewSet

                    queryset = viewsets.ModelViewSet.filter_queryset(self, queryset)



                    # Filter by locale parameter

                    locale_code = self.request.query_params.get("locale")

                    if locale_code:

                        try:

                            locale = Locale.objects.get(

                                code=locale_code, is_active=True

                            )

                            queryset = queryset.filter(**{locale_field_name: locale})

                        except Locale.DoesNotExist:

                            pass  # Invalid locale, return empty queryset



                    return queryset



                return filter_queryset



            methods["filter_queryset"] = make_filter_queryset(config.locale_field)



        return methods



class RegistryViewSet(viewsets.ReadOnlyModelViewSet):



    ViewSet for browsing the content registry.



    serializer_class = RegistrySerializer

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]



    def get_queryset(self):

        """Return all registered configurations as a queryset-like object."""

        return content_registry.get_all_configs()



    def list(self, request):

        """List all registered content configurations."""

        configs = content_registry.get_all_configs()

        serializer = RegistrySerializer(

            [config.to_dict() for config in configs], many=True

        )

        return Response(serializer.data)



    def retrieve(self, request, pk=None):

        """Get a specific content configuration."""

        config = content_registry.get_config(pk)

        if not config:

            return Response(

                {"error": "Configuration not found"}, status=status.HTTP_404_NOT_FOUND

            )



        serializer = RegistrySerializer(config.to_dict())

        return Response(serializer.data)



    @extend_schema(

        summary="Get registry summary",

        description="Get a summary of all registered content types organized by kind.",

    )

    @action(detail=False, methods=["get"])

    def summary(self, request):

        """Get registry summary with statistics."""

        summary = content_registry.get_registry_summary()

        serializer = RegistrySummarySerializer(summary)

        return Response(serializer.data)



    @extend_schema(

        summary="Export registry configuration",

        description="Export all registry configurations as JSON.",

    )

    @action(detail=False, methods=["get"])

    def export(self, request):

        """Export registry configuration as JSON."""

        export_data = content_registry.export_configs()

        return Response(export_data, content_type="application/json")



def get_viewset_for_model(model_label: str) -> type[viewsets.ModelViewSet]:



    Get or create a ViewSet for a registered model.



    Args:

        model_label: Model label (e.g., 'cms.page')



    Returns:

        ModelViewSet class



    Raises:

        ValueError: If model is not registered



    config = content_registry.get_config(model_label)

    if not config:

        raise ValueError(f"Model {model_label} is not registered")



    return ContentViewSetFactory.create_viewset(config)



def get_viewset_for_config(config: ContentConfig) -> type[viewsets.ModelViewSet]:



    Get or create a ViewSet for a content configuration.



    Args:

        config: ContentConfig instance



    Returns:

        ModelViewSet class



    return ContentViewSetFactory.create_viewset(config)

