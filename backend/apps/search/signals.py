from django.db.models.signals import post_delete, post_save

from django.dispatch import receiver



from apps.registry.registry import content_registry



from .services import search_service



Signals for automatic search indexing.



Automatically indexes content when it's created, updated, or deleted.



@receiver(post_save)

def auto_index_content(sender, instance, created, **kwargs):



    Automatically index content when it's saved.



    Only indexes registered content types.



    # Check if this model is registered with the content registry

    if not content_registry.is_model_registered(sender):



    # Get the model configuration

    config = content_registry.get_config_by_model(sender)

    if not config:



    # Skip indexing if the content is not publishable or not published

    if config.can_publish:

        if hasattr(instance, "status"):

            if instance.status != "published":



        elif hasattr(instance, "is_published"):

            if not instance.is_published:



    try:

        # Index the object

        search_service.index_object(instance)

    except Exception:

        # Log error but don't break the save operation



@receiver(post_delete)

def auto_remove_from_index(sender, instance, **kwargs):



    Automatically remove content from index when deleted.



    Only affects registered content types.



    # Check if this model is registered with the content registry

    if not content_registry.is_model_registered(sender):



    try:

        # Remove from search index

        search_service.remove_from_index(instance)

    except Exception:

        # Log error but don't break the delete operation

