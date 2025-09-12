import logging



from django.contrib.contenttypes.models import ContentType

from django.db.models.signals import post_delete, post_save, pre_save

from django.dispatch import receiver



from apps.cms.models import Page



from .models import Locale

from .settings_sync import DjangoSettingsSync

from .translation import TranslationManager



"""Signal handlers for automatic translation unit creation and locale synchronization."""



logger = logging.getLogger(__name__)



@receiver(post_save, sender=Page)

def create_page_translation_units(sender, instance, created, **kwargs):

    """Create translation units when a page is saved."""

    try:

        # Skip if this is being restored from a revision
        if getattr(instance, "_skip_translation_units", False):
            return

        # Get the page's locale (source locale)

        source_locale = instance.locale

        user = getattr(instance, "_current_user", None)



        # Create or update translation units

        TranslationManager.create_translation_units(

            obj=instance, source_locale=source_locale, user=user

        )



    except Exception:
        # Don't let translation unit creation break page saving
        # This would be logged in production
        pass



@receiver(pre_save, sender=Page)

def store_old_page_data(sender, instance, **kwargs):

    """Store old page data to detect changes in translatable fields."""

    if instance.pk:

        try:

            old_instance = Page.objects.get(pk=instance.pk)

            instance._old_title = old_instance.title

            instance._old_blocks = old_instance.blocks

        except Page.DoesNotExist:

            instance._old_title = None

            instance._old_blocks = None



# Generic signal handler for any model that gets registered for translation

def create_translation_units_handler(sender, instance, created, **kwargs):



    """Generic signal handler for creating translation units.

    This can be connected to any model that supports translation.
    """



    try:

        # Get the source locale - this would need to be customized per model

        # For now, assume models have a 'locale' field

        if hasattr(instance, "locale"):

            source_locale = instance.locale

        else:

            # Fall back to default locale

            source_locale = Locale.objects.get(is_default=True, is_active=True)



        user = getattr(instance, "_current_user", None)



        # Create or update translation units

        TranslationManager.create_translation_units(

            obj=instance, source_locale=source_locale, user=user

        )



    except Exception:
        # Don't let translation unit creation break saving
        pass



def register_model_for_translation(model_class, fields=None):



    """Register a model to automatically create translation units.

    Args:
        model_class: Model class to register
        fields: List of translatable field names (optional)
    """



    if fields:

        content_type = ContentType.objects.get_for_model(model_class)

        model_label = f"{content_type.app_label}.{content_type.model}"

        TranslationManager.register_translatable_fields(model_label, fields)



    # Connect the signal

    post_save.connect(create_translation_units_handler, sender=model_class, weak=False)



# Locale synchronization signals



@receiver(post_save, sender=Locale)

def sync_django_settings_on_locale_save(sender, instance, created, **kwargs):



    """Sync Django settings when a locale is saved.

    This clears the settings cache to ensure fresh data is loaded
    when Django settings are next accessed.
    """



    try:



        # Clear the cache to force refresh of dynamic settings

        DjangoSettingsSync.clear_cache()



        action = "Created" if created else "Updated"

        logger.info(

            f"{action} locale '{instance.code}' - Django settings cache cleared"

        )



        # Log if default locale changed

        if instance.is_default:

            logger.info(

                f"Default locale set to '{instance.code}' - LANGUAGE_CODE will update dynamically"

            )



    except Exception as e:

        logger.error(f"Failed to sync Django settings after locale save: {e}")



@receiver(post_delete, sender=Locale)

def sync_django_settings_on_locale_delete(sender, instance, **kwargs):



    """Sync Django settings when a locale is deleted.

    This clears the settings cache and ensures another locale
    becomes the default if the default locale was deleted.
    """



    try:



        # Clear the cache to force refresh of dynamic settings

        DjangoSettingsSync.clear_cache()



        logger.info(f"Deleted locale '{instance.code}' - Django settings cache cleared")



        # If the default locale was deleted, ensure we have a new default

        if instance.is_default:

            try:

                # Try to set the first active locale as default

                new_default = Locale.objects.filter(is_active=True).first()

                if new_default:

                    new_default.is_default = True

                    new_default.save()

                    logger.info(f"Set '{new_default.code}' as new default locale")

                else:

                    logger.warning(

                        "No active locales found after deleting default locale"

                    )

            except Exception as e:

                logger.error(f"Failed to set new default locale: {e}")



    except Exception as e:

        logger.error(f"Failed to sync Django settings after locale deletion: {e}")



@receiver(pre_save, sender=Locale)

def validate_locale_changes(sender, instance, **kwargs):



    """Validate locale changes before saving.

    Ensures there's always at least one default locale and handles
    default locale transitions properly.
    """



    try:

        # If this is a new locale being set as default, unset other defaults

        if instance.is_default:

            Locale.objects.filter(is_default=True).exclude(pk=instance.pk).update(

                is_default=False

            )



        # If this was the default locale and is being set to not default,

        # ensure another locale becomes default

        if instance.pk:  # Only for existing locales

            old_instance = Locale.objects.get(pk=instance.pk)

            if old_instance.is_default and not instance.is_default:

                # Find another active locale to be default

                other_locale = (

                    Locale.objects.filter(is_active=True)

                    .exclude(pk=instance.pk)

                    .first()

                )



                if other_locale:

                    other_locale.is_default = True

                    other_locale.save()

                    logger.info(

                        f"Transferred default locale from '{instance.code}' to '{other_locale.code}'"

                    )

                else:

                    # Force this locale to remain default if no others available

                    instance.is_default = True

                    logger.warning(

                        f"Cannot remove default status from '{instance.code}' - no other active locales"

                    )



    except Exception as e:

        logger.error(f"Failed to validate locale changes: {e}")

