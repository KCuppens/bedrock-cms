"""
API views for translation management.
"""

import io
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import models

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from django.conf import settings

from .models import (
    Locale,
    TranslationGlossary,
    TranslationHistory,
    TranslationQueue,
    TranslationUnit,
    UiMessage,
    UiMessageTranslation,
)
from .serializers import (
    BulkAssignmentSerializer,
    BulkTranslationUpdateSerializer,
    BulkUiMessageUpdateSerializer,
    GlossarySearchSerializer,
    LocaleSerializer,
    MachineTranslationSuggestionSerializer,
    TranslationApprovalSerializer,
    TranslationAssignmentSerializer,
    TranslationGlossarySerializer,
    TranslationHistorySerializer,
    TranslationQueueSerializer,
    TranslationUnitSerializer,
    TranslationUnitUpdateSerializer,
    UiMessageSerializer,
    UiMessageTranslationSerializer,
)
from .tasks import bulk_auto_translate_ui_messages


class LocaleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing locales.

    Provides full CRUD operations for locale management.
    """

    queryset = Locale.objects.all()
    serializer_class = LocaleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["is_active", "is_default", "rtl"]
    ordering_fields = ["name", "code"]
    ordering = ["name"]

    def get_queryset(self):
        """Optionally filter by active status."""
        queryset = super().get_queryset()
        active_only = (
            self.request.query_params.get("active_only", "false").lower() == "true"
        )
        if active_only:
            queryset = queryset.filter(is_active=True)
        return queryset

    @extend_schema(
        summary="Toggle locale active status",
        description="Toggle the active status of a locale. Requires authentication.",
    )
    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def toggle_active(self, request, pk=None):
        """Toggle the active status of a locale."""
        locale = self.get_object()

        # Don't allow deactivating the default locale
        if locale.is_default and locale.is_active:
            return Response(
                {"error": "Cannot deactivate the default locale"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Toggle active status
        locale.is_active = not locale.is_active
        locale.save()

        serializer = self.get_serializer(locale)
        return Response(
            {
                "message": f'Locale {locale.code} {"activated" if locale.is_active else "deactivated"} successfully',
                "locale": serializer.data,
            }
        )

    @extend_schema(
        summary="Set locale as default",
        description="Set this locale as the default locale. Requires authentication.",
    )
    @action(
        detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def set_default(self, request, pk=None):
        """Set the locale as default."""
        locale = self.get_object()

        # If already default, no action needed
        if locale.is_default:
            return Response(
                {"message": f"Locale {locale.code} is already the default locale"},
                status=status.HTTP_200_OK,
            )

        # Auto-activate the locale if it's not active
        if not locale.is_active:
            locale.is_active = True

        # Remove default from all other locales and set this one as default
        Locale.objects.filter(is_default=True).update(is_default=False)
        locale.is_default = True
        locale.save()

        serializer = self.get_serializer(locale)
        return Response(
            {
                "message": f"Locale {locale.code} is now the default locale",
                "locale": serializer.data,
            }
        )

    @extend_schema(
        summary="Delete locale",
        description="Delete a locale. Cannot delete the default locale.",
    )
    def destroy(self, request, pk=None):
        """Delete a locale with validation."""
        locale = self.get_object()

        # Don't allow deleting the default locale
        if locale.is_default:
            return Response(
                {
                    "error": "Cannot delete the default locale. Set another locale as default first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if there are dependent objects (optional)
        # You might want to add checks for pages, translations, etc. that depend on this locale

        # Perform the deletion
        locale.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class TranslationUnitViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing translation units.

    Provides CRUD operations for translation units with filtering and bulk operations.
    """

    queryset = TranslationUnit.objects.select_related(
        "source_locale", "target_locale", "updated_by", "content_type"
    )
    serializer_class = TranslationUnitSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["target_locale", "source_locale", "status", "field"]
    search_fields = ["source_text", "target_text"]
    ordering_fields = ["updated_at", "created_at", "status"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action in ["update", "partial_update"]:
            return TranslationUnitUpdateSerializer
        return TranslationUnitSerializer

    def perform_update(self, serializer):
        """Set the updated_by field when updating."""
        serializer.save(updated_by=self.request.user)

    @extend_schema(
        summary="Get translations for a specific object",
        description="Retrieve all translation units for a specific object.",
        parameters=[
            OpenApiParameter(
                "model_label", str, description="Model label (e.g., cms.page)"
            ),
            OpenApiParameter("object_id", int, description="Object ID"),
            OpenApiParameter(
                "target_locale", str, description="Target locale code (optional)"
            ),
        ],
    )
    @action(detail=False, methods=["get"])
    def for_object(self, request):
        """Get translation units for a specific object."""
        model_label = request.query_params.get("model_label")
        object_id = request.query_params.get("object_id")
        target_locale_code = request.query_params.get("target_locale")

        if not model_label or not object_id:
            return Response(
                {"error": "model_label and object_id parameters are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            app_label, model_name = model_label.split(".")
            content_type = ContentType.objects.get(
                app_label=app_label, model=model_name
            )
        except (ValueError, ContentType.DoesNotExist):
            return Response(
                {"error": "Invalid model_label"}, status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset().filter(
            content_type=content_type, object_id=object_id
        )

        if target_locale_code:
            try:
                target_locale = Locale.objects.get(code=target_locale_code)
                queryset = queryset.filter(target_locale=target_locale)
            except Locale.DoesNotExist:
                return Response(
                    {"error": f"Locale {target_locale_code} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get translation status for an object",
        description="Get translation status for all locales for a specific object.",
        parameters=[
            OpenApiParameter(
                "model_label", str, description="Model label (e.g., cms.page)"
            ),
            OpenApiParameter("object_id", int, description="Object ID"),
        ],
    )
    @action(detail=False, methods=["get"])
    def status_for_object(self, request):
        """Get translation status for an object across all locales."""
        model_label = request.query_params.get("model_label")
        object_id = request.query_params.get("object_id")

        if not model_label or not object_id:
            return Response(
                {"error": "model_label and object_id parameters are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            app_label, model_name = model_label.split(".")
            content_type = ContentType.objects.get(
                app_label=app_label, model=model_name
            )
            model_class = content_type.model_class()
            model_class.objects.get(pk=object_id)
        except (ValueError, ContentType.DoesNotExist, model_class.DoesNotExist):
            return Response(
                {"error": "Invalid model_label or object not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get all active locales
        locales = Locale.objects.filter(is_active=True)
        status_data = []

        for locale in locales:
            # Get translation units for this locale
            units = TranslationUnit.objects.filter(
                content_type=content_type, object_id=object_id, target_locale=locale
            )

            # Calculate completion
            total_fields = units.count()
            completed_fields = units.filter(status="approved").count()

            status_data.append(
                {
                    "locale": LocaleSerializer(locale).data,
                    "total_fields": total_fields,
                    "completed_fields": completed_fields,
                    "completion_percentage": (
                        (completed_fields / total_fields * 100)
                        if total_fields > 0
                        else 0
                    ),
                    "missing_fields": total_fields - completed_fields,
                }
            )

        return Response(status_data)

    @extend_schema(
        summary="Bulk update translation units",
        description="Update multiple translation units in a single request.",
        request=BulkTranslationUpdateSerializer,
    )
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """Bulk update translation units."""
        serializer = BulkTranslationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        units_data = serializer.validated_data["units"]
        updated_units = []
        errors = []

        for unit_data in units_data:
            try:
                unit = TranslationUnit.objects.get(id=unit_data["id"])

                # Check permissions (optional)
                # if not self.check_object_permissions(request, unit):
                #     errors.append({'id': unit_data['id'], 'error': 'Permission denied'})
                #     continue

                # Update fields
                if "target_text" in unit_data:
                    unit.target_text = unit_data["target_text"]

                if "status" in unit_data:
                    unit.status = unit_data["status"]

                unit.updated_by = request.user
                unit.save()

                updated_units.append(unit.id)

            except TranslationUnit.DoesNotExist:
                errors.append(
                    {"id": unit_data["id"], "error": "Translation unit not found"}
                )
            except Exception as e:
                errors.append({"id": unit_data["id"], "error": str(e)})

        return Response(
            {
                "updated": updated_units,
                "errors": errors,
                "total_requested": len(units_data),
                "total_updated": len(updated_units),
            }
        )

    @extend_schema(
        summary="Approve translation",
        description="Approve a translation and mark it as completed.",
        request=TranslationApprovalSerializer,
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a translation."""
        translation_unit = self.get_object()
        serializer = TranslationApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = serializer.validated_data.get("comment", "")

        # Check if translation has content
        if not translation_unit.target_text.strip():
            return Response(
                {"error": "Cannot approve translation without target text"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Record history
        TranslationHistory.objects.create(
            translation_unit=translation_unit,
            action="approved",
            previous_status=translation_unit.status,
            new_status="approved",
            previous_target_text=translation_unit.target_text,
            new_target_text=translation_unit.target_text,
            comment=comment,
            performed_by=request.user,
        )

        # Update status
        translation_unit.status = "approved"
        translation_unit.updated_by = request.user
        translation_unit.save()

        # Update queue status if exists
        if hasattr(translation_unit, "queue_item"):
            translation_unit.queue_item.status = "completed"
            translation_unit.queue_item.save()

        serializer = self.get_serializer(translation_unit)
        return Response(serializer.data)

    @extend_schema(
        summary="Reject translation",
        description="Reject a translation and provide feedback.",
        request=TranslationApprovalSerializer,
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a translation."""
        translation_unit = self.get_object()
        serializer = TranslationApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = serializer.validated_data.get("comment", "")

        # Record history
        TranslationHistory.objects.create(
            translation_unit=translation_unit,
            action="rejected",
            previous_status=translation_unit.status,
            new_status="rejected",
            previous_target_text=translation_unit.target_text,
            new_target_text=translation_unit.target_text,
            comment=comment,
            performed_by=request.user,
        )

        # Update status
        translation_unit.status = "rejected"
        translation_unit.updated_by = request.user
        translation_unit.save()

        # Update queue status if exists
        if hasattr(translation_unit, "queue_item"):
            translation_unit.queue_item.status = "rejected"
            translation_unit.queue_item.save()

        serializer = self.get_serializer(translation_unit)
        return Response(serializer.data)

    @extend_schema(
        summary="Mark as draft",
        description="Mark a translation as draft status.",
        request=TranslationApprovalSerializer,
    )
    @action(detail=True, methods=["post"])
    def mark_as_draft(self, request, pk=None):
        """Mark a translation as draft."""
        translation_unit = self.get_object()
        serializer = TranslationApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = serializer.validated_data.get("comment", "")

        # Record history
        TranslationHistory.objects.create(
            translation_unit=translation_unit,
            action="status_changed",
            previous_status=translation_unit.status,
            new_status="draft",
            previous_target_text=translation_unit.target_text,
            new_target_text=translation_unit.target_text,
            comment=comment,
            performed_by=request.user,
        )

        # Update status
        translation_unit.status = "draft"
        translation_unit.updated_by = request.user
        translation_unit.save()

        # Update queue status if exists
        if hasattr(translation_unit, "queue_item"):
            translation_unit.queue_item.status = "in_progress"
            translation_unit.queue_item.save()

        serializer = self.get_serializer(translation_unit)
        return Response(serializer.data)

    @extend_schema(
        summary="Mark as needs review",
        description="Mark a translation as needs review status.",
        request=TranslationApprovalSerializer,
    )
    @action(detail=True, methods=["post"])
    def mark_needs_review(self, request, pk=None):
        """Mark a translation as needs review."""
        translation_unit = self.get_object()
        serializer = TranslationApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = serializer.validated_data.get("comment", "")

        # Check if translation has content
        if not translation_unit.target_text.strip():
            return Response(
                {"error": "Cannot mark as needs review without target text"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Record history
        TranslationHistory.objects.create(
            translation_unit=translation_unit,
            action="status_changed",
            previous_status=translation_unit.status,
            new_status="needs_review",
            previous_target_text=translation_unit.target_text,
            new_target_text=translation_unit.target_text,
            comment=comment,
            performed_by=request.user,
        )

        # Update status
        translation_unit.status = "needs_review"
        translation_unit.updated_by = request.user
        translation_unit.save()

        # Update queue status if exists
        if hasattr(translation_unit, "queue_item"):
            translation_unit.queue_item.status = "needs_review"
            translation_unit.queue_item.save()

        serializer = self.get_serializer(translation_unit)
        return Response(serializer.data)

    @extend_schema(
        summary="Get machine translation suggestion",
        description="Get machine translation suggestion for a translation unit.",
        request=MachineTranslationSuggestionSerializer,
    )
    @action(detail=True, methods=["post"])
    def mt_suggest(self, request, pk=None):
        """Get machine translation suggestion."""
        translation_unit = self.get_object()
        serializer = MachineTranslationSuggestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get data from request
        text = serializer.validated_data["text"]
        source_lang = serializer.validated_data["source_locale"]
        target_lang = serializer.validated_data["target_locale"]
        service = serializer.validated_data.get("service", "auto")

        # Use DeepL for machine translation suggestions
        try:
            from .services import DeepLTranslationService

            deepl = DeepLTranslationService()

            # Get translation from DeepL
            suggestion = deepl.translate(text, source_lang, target_lang)

            # If DeepL doesn't return a translation, return the original text
            if not suggestion:
                suggestion = text

        except Exception as e:
            # If DeepL service is not configured or fails, return the original text
            logger.warning(f"Translation service error: {e}")
            suggestion = text

        # Update queue item with suggestion if exists
        if hasattr(translation_unit, "queue_item"):
            translation_unit.queue_item.machine_translation_suggestion = suggestion
            translation_unit.queue_item.mt_service = service
            translation_unit.queue_item.save()

        return Response(
            {
                "suggestion": suggestion,
                "service": service,
                "source_text": translation_unit.source_text,
            }
        )

    @extend_schema(
        summary="Assign translation",
        description="Assign a translation to a user or unassign it.",
        request=TranslationAssignmentSerializer,
    )
    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Assign a translation to a user."""
        translation_unit = self.get_object()
        serializer = TranslationAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assigned_to = serializer.validated_data.get("assigned_to")
        comment = serializer.validated_data.get("comment", "")

        # Get or create queue item
        queue_item, created = TranslationQueue.objects.get_or_create(
            translation_unit=translation_unit,
            defaults={"created_by": request.user, "status": "pending"},
        )

        # Update assignment
        previous_assignee = queue_item.assigned_to
        queue_item.assigned_to = assigned_to
        queue_item.save()

        # Record history
        action = "assigned" if assigned_to else "unassigned"
        TranslationHistory.objects.create(
            translation_unit=translation_unit,
            action="assigned",
            previous_status=translation_unit.status,
            new_status=translation_unit.status,
            previous_target_text=translation_unit.target_text,
            new_target_text=translation_unit.target_text,
            comment=(
                f"{action.capitalize()}: {comment}" if comment else action.capitalize()
            ),
            performed_by=request.user,
        )

        # Update translation unit
        translation_unit.updated_by = request.user
        translation_unit.save()

        serializer = self.get_serializer(translation_unit)
        response_data = serializer.data
        response_data["assignment"] = {
            "assigned_to": assigned_to.id if assigned_to else None,
            "assigned_to_email": assigned_to.email if assigned_to else None,
            "previous_assignee": previous_assignee.id if previous_assignee else None,
            "previous_assignee_email": (
                previous_assignee.email if previous_assignee else None
            ),
        }

        return Response(response_data)

    @extend_schema(
        summary="Bulk assign translations",
        description="Assign multiple translations to a user or unassign them.",
        request=BulkAssignmentSerializer,
    )
    @action(detail=False, methods=["post"])
    def bulk_assign(self, request):
        """Bulk assign translations to a user."""
        serializer = BulkAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        translation_unit_ids = serializer.validated_data["translation_unit_ids"]
        assigned_to = serializer.validated_data.get("assigned_to")
        comment = serializer.validated_data.get("comment", "")

        # Get translation units
        translation_units = TranslationUnit.objects.filter(id__in=translation_unit_ids)

        assigned_units = []
        errors = []

        for translation_unit in translation_units:
            try:
                # Get or create queue item
                queue_item, created = TranslationQueue.objects.get_or_create(
                    translation_unit=translation_unit,
                    defaults={"created_by": request.user, "status": "pending"},
                )

                # Update assignment
                previous_assignee = queue_item.assigned_to
                queue_item.assigned_to = assigned_to
                queue_item.save()

                # Record history
                action = "assigned" if assigned_to else "unassigned"
                TranslationHistory.objects.create(
                    translation_unit=translation_unit,
                    action="assigned",
                    previous_status=translation_unit.status,
                    new_status=translation_unit.status,
                    previous_target_text=translation_unit.target_text,
                    new_target_text=translation_unit.target_text,
                    comment=(
                        f"Bulk {action}: {comment}" if comment else f"Bulk {action}"
                    ),
                    performed_by=request.user,
                )

                # Update translation unit
                translation_unit.updated_by = request.user
                translation_unit.save()

                assigned_units.append(
                    {
                        "id": translation_unit.id,
                        "assigned_to": assigned_to.id if assigned_to else None,
                        "assigned_to_email": assigned_to.email if assigned_to else None,
                        "previous_assignee": (
                            previous_assignee.id if previous_assignee else None
                        ),
                        "previous_assignee_email": (
                            previous_assignee.email if previous_assignee else None
                        ),
                    }
                )

            except Exception as e:
                errors.append({"id": translation_unit.id, "error": str(e)})

        return Response(
            {
                "assigned": assigned_units,
                "errors": errors,
                "total_requested": len(translation_unit_ids),
                "total_assigned": len(assigned_units),
                "assignee": (
                    {
                        "id": assigned_to.id if assigned_to else None,
                        "email": assigned_to.email if assigned_to else None,
                    }
                    if assigned_to
                    else None
                ),
            }
        )

    @extend_schema(
        summary="Mark translation as complete",
        description="Mark a translation as complete and move to approved status.",
        request=TranslationApprovalSerializer,
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark translation as complete."""
        translation_unit = self.get_object()
        serializer = TranslationApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = serializer.validated_data.get("comment", "")

        # Check if translation has content
        if not translation_unit.target_text.strip():
            return Response(
                {"error": "Cannot complete translation without target text"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Record history
        TranslationHistory.objects.create(
            translation_unit=translation_unit,
            action="status_changed",
            previous_status=translation_unit.status,
            new_status="approved",
            previous_target_text=translation_unit.target_text,
            new_target_text=translation_unit.target_text,
            comment=comment or "Marked as complete",
            performed_by=request.user,
        )

        # Update status
        translation_unit.status = "approved"
        translation_unit.updated_by = request.user
        translation_unit.save()

        # Update queue status if exists
        if hasattr(translation_unit, "queue_item"):
            translation_unit.queue_item.status = "completed"
            translation_unit.queue_item.save()

        serializer = self.get_serializer(translation_unit)
        return Response(serializer.data)

    @extend_schema(
        summary="Get translation history",
        description="Get history of changes for a translation unit.",
    )
    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """Get translation history."""
        translation_unit = self.get_object()
        history = TranslationHistory.objects.filter(
            translation_unit=translation_unit
        ).order_by("-created_at")

        serializer = TranslationHistorySerializer(history, many=True)
        return Response(serializer.data)


class UiMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing UI messages.
    """

    queryset = UiMessage.objects.all()
    serializer_class = UiMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["namespace"]
    search_fields = ["key", "description", "default_value"]
    ordering_fields = ["created_at", "updated_at", "namespace", "key"]
    ordering = ["namespace", "key"]

    @extend_schema(
        summary="Sync with .po files",
        description="Import from or export to .po files",
        parameters=[
            OpenApiParameter(
                "direction", str, description="Direction: import, export, or sync"
            ),
            OpenApiParameter(
                "locale", str, description="Specific locale code (optional)"
            ),
            OpenApiParameter(
                "namespace", str, description="Namespace (default: django)"
            ),
        ],
    )
    @action(
        detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def sync_po_files(self, request):
        """Sync with .po files."""
        direction = request.data.get("direction", "sync")
        locale_code = request.data.get("locale")
        namespace = request.data.get("namespace", "django")

        try:
            # Capture command output
            out = io.StringIO()

            # Build command arguments
            command_args = [
                "sync_po_files",
                f"--direction={direction}",
                f"--namespace={namespace}",
            ]
            if locale_code:
                command_args.append(f"--locale={locale_code}")

            # Run management command
            call_command(*command_args, stdout=out)

            output = out.getvalue()

            return Response(
                {
                    "status": "success",
                    "message": f"Successfully {direction}ed .po files",
                    "details": output,
                }
            )
        except CommandError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "status": "error",
                    "message": f"Failed to {direction} .po files: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Import Django built-in strings",
        description="Import Django's built-in translation strings into the database",
        parameters=[
            OpenApiParameter(
                "locale", str, description="Specific locale code (optional)"
            ),
            OpenApiParameter(
                "namespace", str, description="Namespace (default: django)"
            ),
        ],
    )
    @action(
        detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def import_django_strings(self, request):
        """Import Django built-in strings."""
        locale_code = request.data.get("locale")
        namespace = request.data.get("namespace", "django")

        try:
            # Capture command output
            out = io.StringIO()

            # Build command arguments
            command_args = ["import_django_translations", f"--namespace={namespace}"]
            if locale_code:
                command_args.append(f"--locale={locale_code}")

            # Run management command
            call_command(*command_args, stdout=out)

            output = out.getvalue()

            return Response(
                {
                    "status": "success",
                    "message": "Successfully imported Django strings",
                    "details": output,
                }
            )
        except CommandError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "status": "error",
                    "message": f"Failed to import Django strings: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Get message bundle for locale",
        description="Get all UI messages as a JSON bundle for a specific locale",
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="bundle/(?P<locale_code>[^/.]+)",
        permission_classes=[permissions.AllowAny],
    )
    def bundle(self, request, locale_code=None):
        """Get message bundle for a locale - publicly accessible for frontend."""
        try:
            locale = Locale.objects.get(code=locale_code)
        except Locale.DoesNotExist:
            return Response(
                {"error": f"Locale {locale_code} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get all messages with translations for this locale
        messages = {}
        for ui_message in UiMessage.objects.all():
            # Try to get translation for this locale
            try:
                translation = UiMessageTranslation.objects.get(
                    message=ui_message, locale=locale, status="approved"
                )
                messages[ui_message.key] = translation.value
            except UiMessageTranslation.DoesNotExist:
                # Fall back to default value
                messages[ui_message.key] = ui_message.default_value

        return Response(messages)

    @extend_schema(
        summary="Sync translation keys from frontend",
        description="Accept translation keys from frontend and create missing UiMessage entries",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "key": {"type": "string"},
                                "defaultValue": {"type": "string"},
                                "description": {"type": "string"},
                                "namespace": {"type": "string"},
                            },
                        },
                    },
                    "source": {
                        "type": "string",
                        "description": "Source of keys (build, runtime-discovery)",
                    },
                },
            }
        },
    )
    @action(detail=False, methods=["post"], url_path="sync-keys")
    def sync_keys(self, request):
        """
        Accept translation keys from frontend and create missing UiMessage entries.

        Keys from build process are auto-approved.
        Keys from runtime discovery need review.
        """
        from django.conf import settings

        keys_data = request.data.get("keys", [])
        source = request.data.get(
            "source", "unknown"
        )  # 'build', 'runtime-discovery', etc.

        # Determine if we should auto-approve
        auto_approve = source == "build" or getattr(
            settings, "AUTO_APPROVE_TRANSLATIONS", False
        )

        created = []
        updated = []
        errors = []

        for key_data in keys_data:
            key = key_data.get("key")
            if not key:
                continue

            try:
                # Extract namespace from key if not provided
                namespace = key_data.get("namespace")
                if not namespace:
                    namespace = key.split(".")[0] if "." in key else "general"

                # Determine description
                description = key_data.get("description", "")
                if not description:
                    description = f"Auto-discovered from {source}"

                ui_message, was_created = UiMessage.objects.update_or_create(
                    key=key,
                    defaults={
                        "namespace": namespace,
                        "default_value": key_data.get("defaultValue", key),
                        "description": description,
                    },
                )

                if was_created:
                    created.append(key)

                    # Auto-create approved translation for default locale if requested
                    if auto_approve:
                        default_locale = Locale.objects.filter(is_default=True).first()
                        if default_locale:
                            UiMessageTranslation.objects.create(
                                message=ui_message,
                                locale=default_locale,
                                value=ui_message.default_value,
                                status="approved",
                                updated_by=(
                                    request.user
                                    if request.user.is_authenticated
                                    else None
                                ),
                            )
                else:
                    # Only update if the default value is different and better
                    if (
                        key_data.get("defaultValue")
                        and key_data["defaultValue"] != key
                        and ui_message.default_value == key
                    ):
                        ui_message.default_value = key_data["defaultValue"]
                        ui_message.save()
                        updated.append(key)

            except Exception as e:
                errors.append({"key": key, "error": str(e)})

        # Log the sync activity
        if created or updated:
            from django.contrib.admin.models import ADDITION, LogEntry
            from django.contrib.contenttypes.models import ContentType

            LogEntry.objects.log_action(
                user_id=request.user.pk if request.user.is_authenticated else None,
                content_type_id=ContentType.objects.get_for_model(UiMessage).pk,
                object_id=None,
                object_repr=f"Synced {len(created)} new and {len(updated)} updated keys from {source}",
                action_flag=ADDITION,
                change_message=f"Source: {source}",
            )

        return Response(
            {
                "created": created,
                "updated": updated,
                "errors": errors,
                "total_processed": len(created) + len(updated),
                "source": source,
                "auto_approved": auto_approve,
            }
        )

    @extend_schema(
        summary="Report missing translation keys",
        description="Report missing translation keys detected at runtime for review",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "keys": {"type": "array", "items": {"type": "string"}},
                    "locale": {"type": "string"},
                    "url": {"type": "string"},
                    "component": {"type": "string"},
                },
            }
        },
    )
    @action(detail=False, methods=["post"], url_path="report-missing")
    def report_missing(self, request):
        """
        Report missing translation keys detected at runtime.
        These are logged for review but not auto-created.
        """
        from datetime import datetime

        from django.core.cache import cache

        keys = request.data.get("keys", [])
        locale = request.data.get("locale", "unknown")
        url = request.data.get("url", "")
        component = request.data.get("component", "")

        # Store in cache for admin review
        cache_key = f"missing_translations_{datetime.now().strftime('%Y%m%d')}"
        existing = cache.get(cache_key, [])

        for key in keys:
            entry = {
                "key": key,
                "locale": locale,
                "url": url,
                "component": component,
                "timestamp": datetime.now().isoformat(),
                "user": (
                    request.user.email if request.user.is_authenticated else "anonymous"
                ),
            }
            existing.append(entry)

        cache.set(cache_key, existing, 86400)  # Store for 24 hours

        return Response(
            {"reported": len(keys), "message": "Missing keys logged for review"}
        )

    @extend_schema(
        summary="Get translation discovery statistics",
        description="Get statistics about discovered translation keys",
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="discovery-stats",
        permission_classes=[permissions.AllowAny],
    )
    def discovery_stats(self, request):
        """Get statistics about discovered translation keys."""
        from datetime import datetime, timedelta

        from django.core.cache import cache
        from django.db.models import Count

        # Get counts
        total_messages = UiMessage.objects.count()

        # Messages created in last 24 hours
        recent_messages = UiMessage.objects.filter(
            created_at__gte=datetime.now() - timedelta(hours=24)
        ).count()

        # Messages by namespace
        by_namespace = (
            UiMessage.objects.values("namespace")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Untranslated messages per locale
        untranslated = {}
        for locale in Locale.objects.filter(is_active=True):
            translated = UiMessageTranslation.objects.filter(
                locale=locale, status="approved"
            ).values_list("message_id", flat=True)

            untranslated_count = UiMessage.objects.exclude(id__in=translated).count()

            untranslated[locale.code] = untranslated_count

        # Messages needing review (recently discovered)
        needs_review = UiMessage.objects.filter(
            description__icontains="discovered"
        ).count()

        # Get today's missing keys from cache
        cache_key = f"missing_translations_{datetime.now().strftime('%Y%m%d')}"
        missing_today = cache.get(cache_key, [])

        return Response(
            {
                "total_messages": total_messages,
                "recent_discoveries": recent_messages,
                "by_namespace": list(by_namespace),
                "untranslated_by_locale": untranslated,
                "needs_review": needs_review,
                "missing_keys_today": len(missing_today),
                "last_sync": request.session.get("last_translation_sync", "Never"),
            }
        )

    @extend_schema(
        summary="Import JSON translations",
        description="Import UI messages and translations from a JSON file",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "format": "binary",
                        "description": "JSON file containing translations",
                    },
                    "locale": {"type": "string", "description": "Target locale code"},
                    "namespace": {
                        "type": "string",
                        "description": "Namespace for messages (default: general)",
                    },
                    "flatten_keys": {
                        "type": "boolean",
                        "description": "Whether to flatten nested keys (default: true)",
                    },
                },
            }
        },
    )
    @action(
        detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def import_json(self, request):
        """Import translations from a JSON file."""
        import json
        from datetime import datetime

        # Get file from request
        if "file" not in request.FILES:
            return Response(
                {"status": "error", "message": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        json_file = request.FILES["file"]
        locale_code = request.data.get("locale")
        namespace = request.data.get("namespace", "general")
        flatten_keys = request.data.get("flatten_keys", "true").lower() == "true"

        if not locale_code:
            return Response(
                {"status": "error", "message": "Locale code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get locale
        try:
            locale = Locale.objects.get(code=locale_code)
        except Locale.DoesNotExist:
            return Response(
                {"status": "error", "message": f"Locale {locale_code} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Read and parse JSON file
            file_content = json_file.read().decode("utf-8")
            translations_data = json.loads(file_content)

            # Validate JSON structure
            if not isinstance(translations_data, dict):
                return Response(
                    {
                        "status": "error",
                        "message": "JSON must be an object with key-value pairs",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Flatten nested structure if requested
            def flatten_dict(d, parent_key=""):
                items = []
                for k, v in d.items():
                    new_key = f"{parent_key}.{k}" if parent_key else k
                    if isinstance(v, dict) and flatten_keys:
                        items.extend(flatten_dict(v, new_key).items())
                    else:
                        items.append((new_key, str(v)))
                return dict(items)

            translations = flatten_dict(translations_data)

            # Import translations
            created_messages = 0
            updated_messages = 0
            created_translations = 0
            updated_translations = 0
            errors = []

            for key, value in translations.items():
                try:
                    # Get or create UI message (key is unique, so only look up by key)
                    try:
                        message = UiMessage.objects.get(key=key)
                        message_created = False
                        # Update namespace and default value if different
                        if (
                            message.namespace != namespace
                            or message.default_value != value
                        ):
                            message.namespace = namespace
                            message.default_value = value
                            message.save()
                            updated_messages += 1
                    except UiMessage.DoesNotExist:
                        message = UiMessage.objects.create(
                            key=key,
                            namespace=namespace,
                            description=f'Imported from JSON on {datetime.now().strftime("%Y-%m-%d")}',
                            default_value=value,
                        )
                        message_created = True

                    if message_created:
                        created_messages += 1

                    # Get or create translation
                    translation, translation_created = (
                        UiMessageTranslation.objects.get_or_create(
                            message=message,
                            locale=locale,
                            defaults={
                                "value": value,
                                "status": "draft",
                                "updated_by": request.user,
                            },
                        )
                    )

                    if translation_created:
                        created_translations += 1
                    else:
                        # Update translation if changed
                        if translation.value != value:
                            translation.value = value
                            translation.status = "draft"
                            translation.updated_by = request.user
                            translation.save()
                            updated_translations += 1

                except Exception as e:
                    import traceback

                    error_msg = f"Error processing key '{key}': {str(e)}"
                    errors.append(error_msg)
                    # Log full traceback for debugging
                    print(f"DEBUG: {error_msg}")
                    print(f"DEBUG: Traceback: {traceback.format_exc()}")
                    continue

            # Check if any actual work was done
            total_changes = (
                created_messages
                + updated_messages
                + created_translations
                + updated_translations
            )

            # Prepare response
            if total_changes == 0 and errors:
                # All operations failed
                response_data = {
                    "status": "error",
                    "message": f"Import failed: {len(errors)} errors occurred, no data was imported",
                    "details": {
                        "total_keys": len(translations),
                        "messages_created": created_messages,
                        "messages_updated": updated_messages,
                        "translations_created": created_translations,
                        "translations_updated": updated_translations,
                        "errors": (
                            errors[:10] if len(errors) > 10 else errors
                        ),  # Show first 10 errors
                    },
                }
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
            elif errors:
                # Partial success
                response_data = {
                    "status": "warning",
                    "message": f"Partially imported {total_changes} changes with {len(errors)} errors",
                    "details": {
                        "total_keys": len(translations),
                        "messages_created": created_messages,
                        "messages_updated": updated_messages,
                        "translations_created": created_translations,
                        "translations_updated": updated_translations,
                        "errors": (
                            errors[:5] if len(errors) > 5 else errors
                        ),  # Show first 5 errors
                    },
                }
            else:
                # Full success
                response_data = {
                    "status": "success",
                    "message": f"Successfully imported {total_changes} changes from {len(translations)} keys",
                    "details": {
                        "total_keys": len(translations),
                        "messages_created": created_messages,
                        "messages_updated": updated_messages,
                        "translations_created": created_translations,
                        "translations_updated": updated_translations,
                        "errors": [],
                    },
                }

            return Response(response_data)

        except json.JSONDecodeError as e:
            return Response(
                {"status": "error", "message": f"Invalid JSON format: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": f"Import failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UiMessageTranslationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing UI message translations.
    """

    queryset = UiMessageTranslation.objects.select_related(
        "message", "locale", "updated_by"
    )
    serializer_class = UiMessageTranslationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["locale", "status", "message__namespace", "message"]
    search_fields = ["message__key", "value"]
    ordering_fields = ["updated_at", "created_at"]
    ordering = ["-updated_at"]

    def perform_create(self, serializer):
        """Set the updated_by field when creating."""
        serializer.save(updated_by=self.request.user)

    def perform_update(self, serializer):
        """Set the updated_by field when updating."""
        serializer.save(updated_by=self.request.user)

    @extend_schema(
        summary="Bulk update UI message translations",
        description="Update multiple UI message translations in a single request.",
        request=BulkUiMessageUpdateSerializer,
    )
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """Bulk update UI message translations."""
        serializer = BulkUiMessageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updates_data = serializer.validated_data["updates"]
        updated_translations = []
        errors = []

        for update_data in updates_data:
            try:
                message_id = update_data["message_id"]
                locale_id = update_data["locale_id"]
                value = update_data["value"]
                status_val = update_data.get("status", "draft")

                # Get or create translation
                translation, created = UiMessageTranslation.objects.get_or_create(
                    message_id=message_id,
                    locale_id=locale_id,
                    defaults={
                        "value": value,
                        "status": status_val,
                        "updated_by": request.user,
                    },
                )

                if not created:
                    translation.value = value
                    translation.status = status_val
                    translation.updated_by = request.user
                    translation.save()

                updated_translations.append(translation.id)

            except Exception as e:
                errors.append(
                    {
                        "message_id": update_data.get("message_id"),
                        "locale_id": update_data.get("locale_id"),
                        "error": str(e),
                    }
                )

        return Response(
            {
                "updated": updated_translations,
                "errors": errors,
                "total_requested": len(updates_data),
                "total_updated": len(updated_translations),
            }
        )

    @extend_schema(
        summary="Get UI namespaces",
        description="Get all UI message namespaces with translation progress.",
    )
    @action(detail=False, methods=["get"])
    def namespaces(self, request):
        """Get UI message namespaces with translation progress."""
        # Get all namespaces with message counts
        namespaces = (
            UiMessage.objects.values("namespace")
            .annotate(message_count=models.Count("id"))
            .order_by("namespace")
        )

        # Get active locales
        locales = Locale.objects.filter(is_active=True)

        # Calculate translation progress for each namespace
        result = []
        for ns in namespaces:
            namespace = ns["namespace"]
            message_count = ns["message_count"]

            # Get translation stats for this namespace
            locale_stats = []
            for locale in locales:
                translated_count = UiMessageTranslation.objects.filter(
                    message__namespace=namespace, locale=locale, status="approved"
                ).count()

                locale_stats.append(
                    {
                        "locale": LocaleSerializer(locale).data,
                        "translated": translated_count,
                        "total": message_count,
                        "percentage": (
                            (translated_count / message_count * 100)
                            if message_count > 0
                            else 0
                        ),
                    }
                )

            result.append(
                {
                    "namespace": namespace,
                    "message_count": message_count,
                    "locale_stats": locale_stats,
                }
            )

        return Response(result)

    @extend_schema(
        summary="Bulk auto-translate UI messages",
        description="Start background task to automatically translate missing UI messages using DeepL for the selected locale.",
        parameters=[
            OpenApiParameter(
                "locale",
                str,
                description="Target locale code (required)",
                required=True,
            ),
            OpenApiParameter(
                "source_locale",
                str,
                description="Source locale code (default: en)",
                required=False,
            ),
            OpenApiParameter(
                "namespace",
                str,
                description="Filter by namespace (optional)",
                required=False,
            ),
            OpenApiParameter(
                "max_translations",
                int,
                description="Maximum number of translations to create (optional)",
                required=False,
            ),
        ],
    )
    @action(detail=False, methods=["post"])
    def bulk_auto_translate(self, request):
        """Start bulk auto-translate UI messages task using DeepL."""
        locale_code = request.data.get("locale")
        source_locale_code = request.data.get("source_locale", "en")
        namespace = request.data.get("namespace")
        max_translations = request.data.get("max_translations")

        if not locale_code:
            return Response(
                {"status": "error", "message": "Target locale is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Validate locale exists
            target_locale = Locale.objects.get(code=locale_code, is_active=True)

            # Check how many messages need translation
            messages_query = UiMessage.objects.exclude(
                id__in=UiMessageTranslation.objects.filter(
                    locale=target_locale
                ).values_list("message_id", flat=True)
            )

            # Filter by namespace if provided
            if namespace:
                messages_query = messages_query.filter(namespace=namespace)

            total_messages = messages_query.count()

            if total_messages == 0:
                return Response(
                    {
                        "status": "success",
                        "message": "No messages need translation",
                        "task_id": None,
                        "details": {"total_messages": 0},
                    }
                )

            # Check if Celery is running in eager mode (local development)
            is_eager = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)

            if is_eager:
                # Run task synchronously for local development
                try:
                    result = bulk_auto_translate_ui_messages(
                        locale_code=locale_code,
                        source_locale_code=source_locale_code,
                        namespace=namespace,
                        max_translations=max_translations,
                    )

                    return Response(
                        {
                            "status": "success",
                            "message": result.get(
                                "message", "Auto-translation completed"
                            ),
                            "task_id": None,
                            "results": result.get("details", {}),
                            "eager_mode": True,
                        }
                    )
                except Exception as e:
                    logger.error(f"Eager auto-translation failed: {str(e)}")
                    return Response(
                        {
                            "status": "error",
                            "message": f"Auto-translation failed: {str(e)}",
                            "eager_mode": True,
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:
                # Start the background task for production
                task = bulk_auto_translate_ui_messages.delay(
                    locale_code=locale_code,
                    source_locale_code=source_locale_code,
                    namespace=namespace,
                    max_translations=max_translations,
                )

                return Response(
                    {
                        "status": "started",
                        "message": f"Auto-translation task started for {total_messages} messages",
                        "task_id": task.id,
                        "details": {
                            "total_messages": total_messages,
                            "locale": locale_code,
                            "namespace": namespace,
                            "max_translations": max_translations,
                        },
                        "eager_mode": False,
                    }
                )

        except Locale.DoesNotExist:
            return Response(
                {
                    "status": "error",
                    "message": f"Locale {locale_code} not found or not active",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Failed to start bulk auto-translate task: {str(e)}")
            return Response(
                {
                    "status": "error",
                    "message": f"Failed to start auto-translation: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        summary="Check auto-translate task status",
        description="Check the status of a bulk auto-translate task.",
        parameters=[
            OpenApiParameter(
                "task_id", str, description="Task ID to check", required=True
            ),
        ],
    )
    @action(detail=False, methods=["get"])
    def task_status(self, request):
        """Check the status of a bulk auto-translate task."""
        from celery.result import AsyncResult

        task_id = request.query_params.get("task_id")

        if not task_id:
            return Response(
                {"status": "error", "message": "Task ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Get task result
            task_result = AsyncResult(task_id)

            response_data = {
                "task_id": task_id,
                "status": task_result.status,
                "ready": task_result.ready(),
            }

            if task_result.status == "PENDING":
                response_data.update(
                    {
                        "message": "Task is waiting to start",
                        "progress": {"current": 0, "total": 0, "percentage": 0},
                    }
                )
            elif task_result.status == "PROGRESS":
                info = task_result.info or {}
                current = info.get("current", 0)
                total = info.get("total", 1)
                percentage = (current / total * 100) if total > 0 else 0

                response_data.update(
                    {
                        "message": info.get("status", "Task in progress"),
                        "progress": {
                            "current": current,
                            "total": total,
                            "percentage": round(percentage, 1),
                            "translated": info.get("translated", 0),
                            "errors": info.get("errors", 0),
                            "skipped": info.get("skipped", 0),
                        },
                    }
                )
            elif task_result.status == "SUCCESS":
                result = task_result.get()
                response_data.update(
                    {
                        "message": result.get("message", "Task completed successfully"),
                        "results": result.get("details", {}),
                        "progress": {
                            "current": result.get("details", {}).get(
                                "total_processed", 0
                            ),
                            "total": result.get("details", {}).get(
                                "total_processed", 0
                            ),
                            "percentage": 100,
                        },
                    }
                )
            elif task_result.status == "FAILURE":
                error_info = task_result.info or {}
                response_data.update(
                    {
                        "message": error_info.get("error", "Task failed"),
                        "error": (
                            str(task_result.result)
                            if task_result.result
                            else "Unknown error"
                        ),
                    }
                )
            else:
                response_data.update(
                    {
                        "message": f"Task status: {task_result.status}",
                        "info": task_result.info,
                    }
                )

            return Response(response_data)

        except Exception as e:
            logger.error(f"Failed to check task status: {str(e)}")
            return Response(
                {
                    "status": "error",
                    "message": f"Failed to check task status: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TranslationGlossaryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing translation glossary.
    """

    queryset = TranslationGlossary.objects.select_related(
        "source_locale", "target_locale", "created_by", "updated_by"
    )
    serializer_class = TranslationGlossarySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["source_locale", "target_locale", "category", "is_verified"]
    search_fields = ["term", "translation", "context"]
    ordering_fields = ["term", "created_at", "updated_at"]
    ordering = ["term"]

    def perform_create(self, serializer):
        """Set the created_by field when creating."""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Set the updated_by field when updating."""
        serializer.save(updated_by=self.request.user)

    @extend_schema(
        summary="Search glossary",
        description="Search for glossary terms by text.",
        request=GlossarySearchSerializer,
    )
    @action(detail=False, methods=["get"])
    def search(self, request):
        """Search glossary terms."""
        serializer = GlossarySearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        term = serializer.validated_data["term"]
        source_locale_id = serializer.validated_data.get("source_locale")
        target_locale_id = serializer.validated_data.get("target_locale")

        # Search in glossary
        queryset = self.get_queryset()

        # Filter by term (search in both term and translation)
        queryset = queryset.filter(
            models.Q(term__icontains=term) | models.Q(translation__icontains=term)
        )

        # Filter by locales if provided
        if source_locale_id:
            queryset = queryset.filter(source_locale_id=source_locale_id)
        if target_locale_id:
            queryset = queryset.filter(target_locale_id=target_locale_id)

        serializer = self.get_serializer(
            queryset[:20], many=True
        )  # Limit to 20 results
        return Response(serializer.data)


class TranslationQueueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing translation queue.
    """

    queryset = TranslationQueue.objects.select_related(
        "translation_unit",
        "assigned_to",
        "created_by",
        "translation_unit__source_locale",
        "translation_unit__target_locale",
    )
    serializer_class = TranslationQueueSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "priority", "assigned_to"]
    ordering_fields = ["priority", "deadline", "created_at"]
    ordering = ["-priority", "deadline"]

    def perform_create(self, serializer):
        """Set the created_by field when creating."""
        serializer.save(created_by=self.request.user)

    @extend_schema(
        summary="Assign translation to user",
        description="Assign a translation task to a specific user.",
    )
    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Assign translation to a user."""
        queue_item = self.get_object()
        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        queue_item.assigned_to = user
        queue_item.status = "assigned"
        queue_item.save()

        serializer = self.get_serializer(queue_item)
        return Response(serializer.data)

    @extend_schema(
        summary="Get overdue items", description="Get all overdue translation items."
    )
    @action(detail=False, methods=["get"])
    def overdue(self, request):
        """Get overdue translation items."""
        from django.utils import timezone

        overdue_items = self.get_queryset().filter(
            deadline__lt=timezone.now(),
            status__in=["pending", "assigned", "in_progress"],
        )

        serializer = self.get_serializer(overdue_items, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get translation queue summary",
        description="Get summary statistics for translation queue including status counts by locale.",
    )
    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get translation queue summary with locale breakdown."""
        from django.db.models import Count
        from django.utils import timezone

        # Get all active locales except the default source locale
        locales = Locale.objects.filter(is_active=True).exclude(is_default=True)

        locale_summaries = []

        for locale in locales:
            # Get queue items for this locale
            locale_queue = self.get_queryset().filter(
                translation_unit__target_locale=locale
            )

            # Count by status
            status_counts = (
                locale_queue.values("status")
                .annotate(count=Count("id"))
                .order_by("status")
            )

            status_dict = {item["status"]: item["count"] for item in status_counts}

            # Count by priority
            priority_counts = (
                locale_queue.values("priority")
                .annotate(count=Count("id"))
                .order_by("priority")
            )

            priority_dict = {
                item["priority"]: item["count"] for item in priority_counts
            }

            # Count overdue items
            overdue_count = locale_queue.filter(
                deadline__lt=timezone.now(),
                status__in=["pending", "assigned", "in_progress"],
            ).count()

            # Count total and pending
            total = locale_queue.count()
            pending = status_dict.get("pending", 0)
            in_progress = status_dict.get("in_progress", 0)
            completed = status_dict.get("completed", 0)

            # Calculate completion percentage
            completion_percentage = (completed / total * 100) if total > 0 else 100

            locale_summaries.append(
                {
                    "locale": {
                        "code": locale.code,
                        "name": locale.name,
                        "native_name": locale.native_name,
                    },
                    "total": total,
                    "pending": pending,
                    "in_progress": in_progress,
                    "completed": completed,
                    "rejected": status_dict.get("rejected", 0),
                    "assigned": status_dict.get("assigned", 0),
                    "overdue": overdue_count,
                    "completion_percentage": round(completion_percentage, 1),
                    "priority_breakdown": {
                        "urgent": priority_dict.get("urgent", 0),
                        "high": priority_dict.get("high", 0),
                        "medium": priority_dict.get("medium", 0),
                        "low": priority_dict.get("low", 0),
                    },
                }
            )

        # Sort by completion percentage (ascending) to show locales needing most work first
        locale_summaries.sort(key=lambda x: x["completion_percentage"])

        # Overall summary
        overall_queue = self.get_queryset()
        overall_total = overall_queue.count()
        overall_pending = overall_queue.filter(status="pending").count()
        overall_in_progress = overall_queue.filter(status="in_progress").count()
        overall_completed = overall_queue.filter(status="completed").count()
        overall_overdue = overall_queue.filter(
            deadline__lt=timezone.now(),
            status__in=["pending", "assigned", "in_progress"],
        ).count()

        return Response(
            {
                "overall": {
                    "total": overall_total,
                    "pending": overall_pending,
                    "in_progress": overall_in_progress,
                    "completed": overall_completed,
                    "overdue": overall_overdue,
                    "completion_percentage": round(
                        (
                            (overall_completed / overall_total * 100)
                            if overall_total > 0
                            else 100
                        ),
                        1,
                    ),
                },
                "locales": locale_summaries,
            }
        )


class TranslationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing translation history (read-only).
    """

    queryset = TranslationHistory.objects.select_related(
        "translation_unit", "performed_by"
    )
    serializer_class = TranslationHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["action", "translation_unit"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
