from django.utils import timezone



from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import OpenApiParameter, extend_schema

from rest_framework import filters, status, viewsets

from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response



from .versioning import AuditEntry, PageRevision, RevisionDiffer

from .versioning_serializers import (  # functionality

    API,

    AuditEntrySerializer,

    AutosaveSerializer,

    PageRevisionDetailSerializer,

    PageRevisionSerializer,

    PublishPageSerializer,

    RevertRevisionSerializer,

    RevisionDiffSerializer,

    UnpublishPageSerializer,

    audit,

    versioning,

    views,

)





class PageRevisionViewSet(viewsets.ReadOnlyModelViewSet):



    ViewSet for managing page revisions.



    """Provides read-only access to page revisions with diff and revert functionality."""



    queryset = PageRevision.objects.select_related("created_by", "page")

    serializer_class = PageRevisionSerializer

    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]

    filterset_fields = ["page", "is_published_snapshot", "is_autosave", "created_by"]

    ordering_fields = ["created_at"]

    ordering = ["-created_at"]



    def get_serializer_class(self):  # noqa: C901

        """Use detailed serializer for retrieve action."""

        if self.action == "retrieve":

            return PageRevisionDetailSerializer

        return PageRevisionSerializer



    def get_queryset(self):  # noqa: C901

        """Filter queryset based on user permissions."""

        queryset = super().get_queryset()



        # Users can only see revisions for pages they have access to

        if not self.request.user.is_superuser:

            # This would integrate with RBAC to filter based on user's locale/section access

            # For now, just ensure user is authenticated



        return queryset



    @extend_schema(

        summary="Get diff between two revisions",

        description="Compare two revisions and return detailed differences.",

        parameters=[

            OpenApiParameter(

                "against", str, description="ID of revision to compare against"

            )

        ],

        responses={200: RevisionDiffSerializer},

    )

    @action(detail=True, methods=["get"])

    def diff(self, request, pk=None):  # noqa: C901

        """Get diff between this revision and another."""

        revision = self.get_object()

        against_id = request.query_params.get("against")



        if not against_id:

            return Response(

                {"error": "against parameter is required"},

                status=status.HTTP_400_BAD_REQUEST,

            )



        try:

            against_revision = PageRevision.objects.get(

                id=against_id, page=revision.page

            )

        except PageRevision.DoesNotExist:

            return Response(

                {"error": "Revision not found"}, status=status.HTTP_404_NOT_FOUND

            )



        # Ensure we're comparing in the right order (older -> newer)

        if against_revision.created_at > revision.created_at:

            diff_data = RevisionDiffer.diff_revisions(revision, against_revision)

        else:

            diff_data = RevisionDiffer.diff_revisions(against_revision, revision)



        serializer = RevisionDiffSerializer(diff_data)

        return Response(serializer.data)



    @extend_schema(

        summary="Diff revision against current page state",

        description="Compare this revision with the current page state.",

        responses={200: RevisionDiffSerializer},

    )

    @action(detail=True, methods=["get"])

    def diff_current(self, request, pk=None):  # noqa: C901

        """Get diff between this revision and current page state."""

        revision = self.get_object()

        page = revision.page



        diff_data = RevisionDiffer.diff_current_page(page, revision)

        serializer = RevisionDiffSerializer(diff_data)

        return Response(serializer.data)



    @extend_schema(

        summary="Revert page to this revision",

        description="Restore the page content to this revision state.",

        request=RevertRevisionSerializer,

        responses={

            200: {"type": "object", "properties": {"message": {"type": "string"}}}

        },

    )

    @action(detail=True, methods=["post"])

    def revert(self, request, pk=None):  # noqa: C901

        """Revert page to this revision."""

        revision = self.get_object()

        serializer = RevertRevisionSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)



        # Check permissions

        page = revision.page

        if not request.user.has_perm("cms.change_page"):

            return Response(

                {"error": "You do not have permission to edit pages"},

                status=status.HTTP_403_FORBIDDEN,

            )



        # Set context for signals

        page._current_user = request.user

        page._current_request = request

        page._revision_comment = f"Reverted to revision from {revision.created_at.strftime('%Y-%m-%d %H:%M')}. {serializer.validated_data.get('comment', '')}"



        # Restore the revision

        updated_page = revision.restore_to_page()



        # Create audit entry for revert action

        AuditEntry.log(

            actor=request.user,

            action="revert",

            obj=updated_page,

            meta={

                "reverted_to_revision_id": str(revision.id),

                "reverted_from_status": updated_page.status,

                "comment": serializer.validated_data.get("comment", ""),

            },

            request=request,

        )



        return Response(

            {"message": f"Page reverted to revision from {revision.created_at}"}

        )



class AuditEntryViewSet(viewsets.ReadOnlyModelViewSet):



    ViewSet for audit entries.



    Provides read-only access to audit log entries with filtering.



    queryset = AuditEntry.objects.select_related("actor").prefetch_related(

        "content_object"

    )

    serializer_class = AuditEntrySerializer

    permission_classes = [IsAuthenticated]

    filter_backends = [

        DjangoFilterBackend,

        filters.SearchFilter,

        filters.OrderingFilter,

    ]

    filterset_fields = ["actor", "action", "model_label", "object_id"]

    search_fields = ["actor__email", "model_label", "meta"]

    ordering_fields = ["created_at"]

    ordering = ["-created_at"]



    def get_queryset(self):  # noqa: C901

        """Filter queryset based on user permissions."""

        queryset = super().get_queryset()



        # Non-superusers can only see audit entries for objects they have access to

        if not self.request.user.is_superuser:

            # This would integrate with RBAC for more granular filtering

            # For now, just show entries for pages the user can view

            if self.request.user.has_perm("cms.view_page"):

                # Filter to CMS-related entries

                queryset = queryset.filter(model_label__startswith="cms.")



        return queryset



# Mixin to add versioning endpoints to PageViewSet

class VersioningMixin:



    """Mixin to add versioning functionality to the PageViewSet."""



    @extend_schema(

        summary="Get page revisions",

        description="List all revisions for this page.",

        responses={200: PageRevisionSerializer(many=True)},

    )

    @action(detail=True, methods=["get"])

    def revisions(self, request, pk=None):  # noqa: C901

        """Get all revisions for this page."""

        page = self.get_object()

        revisions = page.revisions.all()



        # Apply pagination

        page_obj = self.paginate_queryset(revisions)

        if page_obj is not None:

            serializer = PageRevisionSerializer(page_obj, many=True)

            return self.get_paginated_response(serializer.data)



        serializer = PageRevisionSerializer(revisions, many=True)

        return Response(serializer.data)



    @extend_schema(

        summary="Create manual autosave",

        description="Manually create an autosave revision.",

        request=AutosaveSerializer,

        responses={

            201: {"type": "object", "properties": {"revision_id": {"type": "string"}}}

        },

    )

    @action(detail=True, methods=["post"])

    def autosave(self, request, pk=None):  # noqa: C901

        """Create a manual autosave revision."""

        page = self.get_object()

        serializer = AutosaveSerializer(

            data=request.data, context={"page": page, "user": request.user}

        )

        serializer.is_valid(raise_exception=True)



        # Check permissions

        if not request.user.has_perm("cms.change_page"):

            return Response(

                {"error": "You do not have permission to edit pages"},

                status=status.HTTP_403_FORBIDDEN,

            )



        # Create autosave revision

        revision = PageRevision.create_snapshot(

            page=page,

            user=request.user,

            is_published=False,

            is_autosave=True,

            comment=serializer.validated_data.get("comment", "Manual autosave"),

        )



        return Response(

            {"revision_id": str(revision.id)}, status=status.HTTP_201_CREATED

        )



    @extend_schema(

        summary="Publish page",

        description="Publish a page and create a published revision snapshot.",

        request=PublishPageSerializer,

        responses={

            200: {"type": "object", "properties": {"message": {"type": "string"}}}

        },

    )

    @action(detail=True, methods=["post"])

    def publish(self, request, pk=None):  # noqa: C901

        """Publish a page."""

        page = self.get_object()

        serializer = PublishPageSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)



        # Check permissions

        if not request.user.has_perm("cms.publish_page", page):

            return Response(

                {"error": "You do not have permission to publish this page"},

                status=status.HTTP_403_FORBIDDEN,

            )



        # Set publish data

        page.status = "published"

        page.published_at = serializer.validated_data.get(

            "published_at", timezone.now()

        )



        # Set context for signals

        page._current_user = request.user

        page._current_request = request

        page._revision_comment = serializer.validated_data.get(

            "comment", "Page published"

        )

        page._was_published_now = True



        page.save()



        return Response({"message": "Page published successfully"})



    @extend_schema(

        summary="Unpublish page",

        description="Unpublish a page and create an audit entry.",

        request=UnpublishPageSerializer,

        responses={

            200: {"type": "object", "properties": {"message": {"type": "string"}}}

        },

    )

    @action(detail=True, methods=["post"])

    def unpublish(self, request, pk=None):  # noqa: C901

        """Unpublish a page."""

        page = self.get_object()

        serializer = UnpublishPageSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)



        # Check permissions

        if not request.user.has_perm("cms.publish_page", page):

            return Response(

                {"error": "You do not have permission to unpublish this page"},

                status=status.HTTP_403_FORBIDDEN,

            )



        # Unpublish

        page.status = "draft"

        page.published_at = None



        # Set context for signals

        page._current_user = request.user

        page._current_request = request

        page._revision_comment = serializer.validated_data.get(

            "comment", "Page unpublished"

        )

        page._was_unpublished_now = True



        page.save()



        return Response({"message": "Page unpublished successfully"})



    @extend_schema(

        summary="Get page audit trail",

        description="Get audit entries for this page.",

        responses={200: AuditEntrySerializer(many=True)},

    )

    @action(detail=True, methods=["get"])

    def audit(self, request, pk=None):  # noqa: C901

        """Get audit trail for this page."""

        page = self.get_object()



        # Get audit entries for this page

        audit_entries = AuditEntry.objects.filter(

            model_label="cms.page", object_id=page.id

        ).select_related("actor")



        # Apply pagination

        page_obj = self.paginate_queryset(audit_entries)

        if page_obj is not None:

            serializer = AuditEntrySerializer(page_obj, many=True)

            return self.get_paginated_response(serializer.data)



        serializer = AuditEntrySerializer(audit_entries, many=True)

        return Response(serializer.data)

