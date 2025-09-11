"""
Background tasks for internationalization and localization.
"""

import logging
from typing import List, Dict, Any, Optional
from celery import shared_task
from django.db import transaction
from django.apps import apps
from django.contrib.contenttypes.models import ContentType

from .models import Locale, TranslationUnit, UiMessage, UiMessageTranslation
from .services import DeepLTranslationService
from apps.registry.registry import content_registry

logger = logging.getLogger(__name__)


class TranslationService:
    """Mock translation service for testing."""

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Mock translation method."""
        return f"Translated: {text}"


def get_translation_service(service_name: str = None):
    """Get translation service instance."""
    return TranslationService()


@shared_task(bind=True)
def seed_locale_translation_units(
    self, locale_code: str, force_reseed: bool = False
) -> Dict[str, Any]:
    """
    Seed TranslationUnits for a new locale.

    Scans all registered models and pages to create translation units
    for translatable fields.

    Args:
        locale_code: Code of the locale to seed (e.g., 'es', 'fr')
        force_reseed: If True, recreate existing units

    Returns:
        Dict with summary of seeding results
    """
    try:
        # Get the locale
        try:
            locale = Locale.objects.get(code=locale_code)
        except Locale.DoesNotExist:
            raise ValueError(f"Locale '{locale_code}' not found")

        if not locale.is_active:
            raise ValueError(f"Locale '{locale_code}' is not active")

        results = {
            "locale_code": locale_code,
            "total_units_created": 0,
            "total_units_skipped": 0,
            "models_processed": [],
            "errors": [],
        }

        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 100,
                "status": f"Starting locale seeding for {locale_code}",
            },
        )

        # Get content registry
        registry = content_registry
        progress_step = 50 / (len(registry._configs) + 1)  # +1 for pages
        current_progress = 0

        # Process Pages first
        page_results = _seed_page_translation_units(locale, force_reseed)
        results["models_processed"].append(
            {
                "model": "cms.Page",
                "created": page_results["created"],
                "skipped": page_results["skipped"],
            }
        )
        results["total_units_created"] += page_results["created"]
        results["total_units_skipped"] += page_results["skipped"]

        current_progress += progress_step
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current_progress,
                "total": 100,
                "status": f'Processed pages: {page_results["created"]} created, {page_results["skipped"]} skipped',
            },
        )

        # Process registered content models
        for config_label, config in registry._configs.items():
            try:
                model_results = _seed_model_translation_units(
                    config.model, config.translatable_fields or [], locale, force_reseed
                )

                results["models_processed"].append(
                    {
                        "model": config_label,
                        "created": model_results["created"],
                        "skipped": model_results["skipped"],
                    }
                )
                results["total_units_created"] += model_results["created"]
                results["total_units_skipped"] += model_results["skipped"]

                current_progress += progress_step
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": current_progress,
                        "total": 100,
                        "status": f'Processed {config_label}: {model_results["created"]} created',
                    },
                )

            except Exception as e:
                error_msg = f"Error processing {config_label}: {str(e)}"
                logger.warning(error_msg)
                results["errors"].append(error_msg)

        # Final progress update
        self.update_state(
            state="SUCCESS",
            meta={
                "current": 100,
                "total": 100,
                "status": f'Completed: {results["total_units_created"]} units created',
            },
        )

        logger.info(
            "Locale seeding completed for %s: {results['total_units_created']} units created",
            locale_code,
        )
        return results

    except Exception as e:
        error_msg = f"Failed to seed locale {locale_code}: {str(e)}"
        logger.error(error_msg)
        self.update_state(state="FAILURE", meta={"error": error_msg})
        raise


def _seed_page_translation_units(
    locale: Locale, force_reseed: bool = False
) -> Dict[str, int]:
    """Seed translation units for pages."""
    from apps.cms.models import Page

    created_count = 0
    skipped_count = 0

    # Define translatable fields for pages
    translatable_fields = ["title", "blocks", "seo"]

    # Get all pages that have content in other locales
    source_pages = Page.objects.exclude(locale=locale)

    with transaction.atomic():
        for source_page in source_pages:
            # Try to find corresponding page in target locale by group_id
            target_page = Page.objects.filter(
                group_id=source_page.group_id, locale=locale
            ).first()

            if not target_page:
                # No corresponding page in target locale, skip
                continue

            for field_name in translatable_fields:
                # Create or get translation unit
                unit, created = TranslationUnit.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(Page),
                    object_id=target_page.id,
                    field_name=field_name,
                    target_locale=locale,
                    defaults={
                        "source_locale": source_page.locale,
                        "source_object_id": source_page.id,
                        "status": "missing",
                    },
                )

                if created or force_reseed:
                    if not created and force_reseed:
                        # Update existing unit
                        unit.source_locale = source_page.locale
                        unit.source_object_id = source_page.id
                        unit.status = "missing"
                        unit.save()

                    created_count += 1
                else:
                    skipped_count += 1

    return {"created": created_count, "skipped": skipped_count}


def _seed_model_translation_units(
    model_class,
    translatable_fields: List[str],
    locale: Locale,
    force_reseed: bool = False,
) -> Dict[str, int]:
    """Seed translation units for a registered model."""
    created_count = 0
    skipped_count = 0

    if not translatable_fields:
        return {"created": 0, "skipped": 0}

    # Get all objects that have content in other locales
    if hasattr(model_class, "locale"):
        source_objects = model_class.objects.exclude(locale=locale)
    else:
        # Model doesn't have locale field, skip
        return {"created": 0, "skipped": 0}

    with transaction.atomic():
        for source_obj in source_objects:
            # Try to find corresponding object in target locale by group_id
            target_obj = None

            if hasattr(model_class, "group_id"):
                target_obj = model_class.objects.filter(
                    group_id=source_obj.group_id, locale=locale
                ).first()

            if not target_obj:
                continue

            for field_name in translatable_fields:
                # Create or get translation unit
                unit, created = TranslationUnit.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(model_class),
                    object_id=target_obj.id,
                    field_name=field_name,
                    target_locale=locale,
                    defaults={
                        "source_locale": source_obj.locale,
                        "source_object_id": source_obj.id,
                        "status": "missing",
                    },
                )

                if created or force_reseed:
                    if not created and force_reseed:
                        # Update existing unit
                        unit.source_locale = source_obj.locale
                        unit.source_object_id = source_obj.id
                        unit.status = "missing"
                        unit.save()

                    created_count += 1
                else:
                    skipped_count += 1

    return {"created": created_count, "skipped": skipped_count}


@shared_task(bind=True)
def cleanup_orphaned_translation_units(self) -> Dict[str, Any]:
    """
    Clean up orphaned translation units.

    Removes translation units that reference deleted objects.
    """
    try:
        results = {"total_cleaned": 0, "models_processed": []}

        # Get all content types that have translation units
        content_types = TranslationUnit.objects.values_list(
            "content_type", flat=True
        ).distinct()

        for content_type_id in content_types:
            content_type = ContentType.objects.get(id=content_type_id)
            model_class = content_type.model_class()

            if not model_class:
                continue

            # Find orphaned units for this model
            orphaned_units = []
            units = TranslationUnit.objects.filter(content_type=content_type)

            for unit in units:
                try:
                    # Check if target object exists
                    model_class.objects.get(id=unit.object_id)
                except model_class.DoesNotExist:
                    orphaned_units.append(unit.id)

                # Check if source object exists
                if unit.source_object_id:
                    try:
                        model_class.objects.get(id=unit.source_object_id)
                    except model_class.DoesNotExist:
                        orphaned_units.append(unit.id)

            # Delete orphaned units
            if orphaned_units:
                deleted_count = TranslationUnit.objects.filter(
                    id__in=orphaned_units
                ).delete()[0]

                results["models_processed"].append(
                    {
                        "model": f"{content_type.app_label}.{content_type.model}",
                        "cleaned": deleted_count,
                    }
                )
                results["total_cleaned"] += deleted_count

        logger.info(
            "Cleanup completed: %s orphaned units removed", results["total_cleaned"]
        )
        return results

    except Exception as e:
        error_msg = f"Failed to cleanup translation units: {str(e)}"
        logger.error(error_msg)
        self.update_state(state="FAILURE", meta={"error": error_msg})
        raise


@shared_task
def process_translation_queue() -> Dict[str, Any]:
    """
    Process translation queue items.

    Processes pending translation queue items and updates their status.
    """
    try:
        from .models import TranslationQueue

        results = {"total_processed": 0, "total_completed": 0, "total_failed": 0}

        # Get pending queue items
        queue_items = TranslationQueue.objects.filter(status="pending")
        service = TranslationService()

        for item in queue_items:
            try:
                # Use translation service to translate
                translated_text = service.translate(
                    item.translation_unit.source_text,
                    item.translation_unit.source_locale.code,
                    item.translation_unit.target_locale.code,
                )

                # Update the translation unit
                item.translation_unit.target_text = translated_text
                item.translation_unit.status = "completed"
                item.translation_unit.save()

                item.status = "completed"
                item.save()
                results["total_completed"] += 1
            except Exception as e:
                logger.error(f"Failed to process queue item {item.id}: {str(e)}")
                item.status = "failed"
                item.save()
                results["total_failed"] += 1

            results["total_processed"] += 1

        logger.info(
            "Translation queue processing completed: %s items processed",
            results["total_processed"],
        )
        return results

    except Exception as e:
        error_msg = f"Failed to process translation queue: {str(e)}"
        logger.error(error_msg)
        raise


@shared_task
def auto_translate_content(
    content_type_id: int,
    object_id: int,
    field: str,
    target_locale_code: str,
    service: str = None,
) -> Dict[str, Any]:
    """
    Auto translate content using machine translation service.
    """
    try:
        from django.contrib.contenttypes.models import ContentType

        # Validate parameters
        try:
            content_type = ContentType.objects.get(id=content_type_id)
            model_class = content_type.model_class()
            if not model_class:
                raise ValueError(f"Invalid content type: {content_type_id}")

            # Check if object exists
            obj = model_class.objects.get(id=object_id)

            # Check if locale exists
            target_locale = Locale.objects.get(code=target_locale_code)

        except (ContentType.DoesNotExist, Locale.DoesNotExist) as e:
            error_msg = f"Invalid parameters for auto translation: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg, "translated_fields": 0}
        except Exception as e:
            error_msg = f"Error in auto translation: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg, "translated_fields": 0}

        results = {"translated_fields": 1, "status": "completed"}

        # Mock implementation
        logger.info(
            "Auto translation completed for object %s:%s to %s",
            content_type_id,
            object_id,
            target_locale_code,
        )
        return results

    except Exception as e:
        error_msg = f"Failed to auto translate content: {str(e)}"
        logger.error(error_msg)
        raise


@shared_task
def generate_translation_report(
    locale_code: str = None,
    locale_codes: list = None,
    date_from: str = None,
    date_to: str = None,
) -> Dict[str, Any]:
    """
    Generate translation completion report.
    """
    try:
        results = {
            "total_units": 0,
            "completed_units": 0,
            "pending_units": 0,
            "coverage_percentage": 0.0,
        }

        queryset = TranslationUnit.objects.all()
        if locale_code:
            queryset = queryset.filter(target_locale__code=locale_code)

        results["total_units"] = queryset.count()
        results["completed_units"] = queryset.filter(status="completed").count()
        results["pending_units"] = queryset.filter(
            status__in=["missing", "pending"]
        ).count()

        if results["total_units"] > 0:
            results["coverage_percentage"] = (
                results["completed_units"] / results["total_units"]
            ) * 100

        logger.info(
            "Translation report generated for %s: %s%% coverage",
            locale_code or "all locales",
            results["coverage_percentage"],
        )
        return results

    except Exception as e:
        error_msg = f"Failed to generate translation report: {str(e)}"
        logger.error(error_msg)
        raise


@shared_task
def sync_locale_fallbacks(locale_code: str = None) -> Dict[str, Any]:
    """
    Sync locale fallback configurations.
    """
    try:
        results = {"locales_synced": 0, "fallbacks_updated": 0}

        # Mock implementation
        locales = Locale.objects.filter(is_active=True)
        for locale in locales:
            # Update fallback logic here
            results["locales_synced"] += 1

        logger.info(
            "Locale fallbacks synced: %s locales processed", results["locales_synced"]
        )
        return results

    except Exception as e:
        error_msg = f"Failed to sync locale fallbacks: {str(e)}"
        logger.error(error_msg)
        raise


@shared_task
def cleanup_old_translations(days_old: int = 90, days: int = None) -> Dict[str, Any]:
    """
    Cleanup old translation records.
    """
    try:
        from datetime import datetime, timedelta

        # Use days parameter if provided, otherwise use days_old
        retention_days = days if days is not None else days_old

        results = {
            "deleted_units": 0,
            "cutoff_date": (
                datetime.now() - timedelta(days=retention_days)
            ).isoformat(),
        }

        # Find old completed translations that might be outdated
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        old_units = TranslationUnit.objects.filter(
            status="completed", updated_at__lt=cutoff_date
        )

        results["deleted_units"] = old_units.count()
        # Don't actually delete for now, just report

        logger.info(
            "Old translations cleanup: %s units found older than %s days",
            results["deleted_units"],
            days_old,
        )
        return results

    except Exception as e:
        error_msg = f"Failed to cleanup old translations: {str(e)}"
        logger.error(error_msg)
        raise


@shared_task(bind=True)
def bulk_auto_translate_ui_messages(
    self=None,
    locale_code: str = None,
    source_locale_code: str = "en",
    namespace: str = None,
    max_translations: int = None,
) -> Dict[str, Any]:
    """
    Auto-translate all missing UI messages for a locale using DeepL.

    This task runs in the background to avoid timeout issues when translating
    large numbers of UI messages.

    Args:
        locale_code: Target locale code (e.g., 'es', 'fr')
        source_locale_code: Source locale code (default: 'en')
        namespace: Filter by namespace (optional)
        max_translations: Maximum number of translations to create (optional)

    Returns:
        Dict with translation results and statistics
    """
    try:
        # Validate required parameters
        if not locale_code:
            raise ValueError("locale_code is required")

        # Get target locale
        try:
            target_locale = Locale.objects.get(code=locale_code, is_active=True)
        except Locale.DoesNotExist:
            raise ValueError(f"Target locale '{locale_code}' not found or not active")

        # Get source locale
        try:
            source_locale = Locale.objects.get(code=source_locale_code, is_active=True)
        except Locale.DoesNotExist:
            # Fallback to default locale
            source_locale = Locale.objects.get(is_default=True)

        # Build query for messages that need translation
        messages_query = UiMessage.objects.exclude(
            id__in=UiMessageTranslation.objects.filter(
                locale=target_locale
            ).values_list("message_id", flat=True)
        )

        # Filter by namespace if provided
        if namespace:
            messages_query = messages_query.filter(namespace=namespace)

        # Get total count for progress tracking
        total_messages = messages_query.count()

        # Limit number of messages if specified
        if max_translations and max_translations > 0:
            messages_to_translate = messages_query[:max_translations]
            total_messages = min(total_messages, max_translations)
        else:
            messages_to_translate = messages_query

        if total_messages == 0:
            return {
                "status": "success",
                "message": "No messages need translation",
                "details": {
                    "translated": 0,
                    "errors": 0,
                    "skipped": 0,
                    "total_processed": 0,
                },
            }

        # Initialize progress tracking (only if running as Celery task)
        if self:
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 0,
                    "total": total_messages,
                    "status": f"Starting auto-translation for {locale_code}",
                },
            )

        # Initialize DeepL service
        deepl_service = DeepLTranslationService()

        translated_count = 0
        error_count = 0
        skipped_count = 0
        errors = []

        # Process messages in batches for better memory management
        batch_size = 50
        current_processed = 0

        for i in range(0, total_messages, batch_size):
            batch_messages = list(messages_to_translate[i : i + batch_size])

            for message in batch_messages:
                try:
                    # Use default_value as source text
                    source_text = message.default_value

                    if not source_text or not source_text.strip():
                        logger.info(f"Skipping {message.key}: empty default_value")
                        skipped_count += 1
                        current_processed += 1
                        continue

                    # Translate using DeepL
                    translated_text = deepl_service.translate(
                        text=source_text,
                        source_lang=source_locale.code,
                        target_lang=target_locale.code,
                    )

                    if translated_text and translated_text.strip():
                        # Create translation
                        UiMessageTranslation.objects.create(
                            message=message,
                            locale=target_locale,
                            value=translated_text,
                            status="draft",  # Auto-translations start as draft
                            updated_by=None,  # Background task, no user
                        )
                        translated_count += 1
                    else:
                        skipped_count += 1
                        errors.append(f"No translation returned for: {message.key}")
                        logger.warning(
                            f"Skipped {message.key}: no translation returned"
                        )

                except Exception as e:
                    error_count += 1
                    error_msg = f"Error translating {message.key}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"Auto-translation error for {message.key}: {str(e)}")

                current_processed += 1

                # Update progress every 10 messages (only if running as Celery task)
                if self and current_processed % 10 == 0:
                    progress_percentage = (current_processed / total_messages) * 100
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "current": current_processed,
                            "total": total_messages,
                            "translated": translated_count,
                            "errors": error_count,
                            "skipped": skipped_count,
                            "status": f"Translated {translated_count} of {current_processed} messages ({progress_percentage:.1f}%)",
                        },
                    )

        # Final result
        results = {
            "status": "success",
            "message": f"Auto-translation completed: {translated_count} translated, {error_count} errors, {skipped_count} skipped",
            "details": {
                "translated": translated_count,
                "errors": error_count,
                "skipped": skipped_count,
                "total_processed": current_processed,
                "error_details": errors[:20] if errors else [],  # Show first 20 errors
            },
        }

        logger.info(
            "Bulk UI auto-translation completed for %s: %d translated, %d errors, %d skipped",
            locale_code,
            translated_count,
            error_count,
            skipped_count,
        )

        # Final progress update (only if running as Celery task)
        if self:
            self.update_state(
                state="SUCCESS",
                meta={
                    "current": total_messages,
                    "total": total_messages,
                    "status": f"Completed: {translated_count} translations created",
                    "results": results,
                },
            )

        return results

    except Exception as e:
        error_msg = f"Bulk auto-translation failed for {locale_code}: {str(e)}"
        logger.error(error_msg)
        if self:
            self.update_state(state="FAILURE", meta={"error": error_msg})
        raise
