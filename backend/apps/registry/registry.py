"""
Global content registry for CMS content types.
"""

# mypy: ignore-errors

import json
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from .config import ContentConfig


class ContentRegistryError(Exception):
    """Exception raised for content registry errors."""

    pass


class ContentRegistry:
    """
    Global registry for CMS content types.

    Manages registration, validation, and access to content configurations.
    """

    def __init__(self):
        self._configs: dict[str, ContentConfig] = {}
        self._by_model: dict[type[models.Model], ContentConfig] = {}
        self._validated = False

    def register(self, config: ContentConfig):
        """
        Register a content configuration.

        Args:
            config: ContentConfig instance to register

        Raises:
            ContentRegistryError: If config is invalid or already registered
        """
        model_label = config.model_label

        if model_label in self._configs:
            raise ContentRegistryError(f"Model {model_label} is already registered")

        # Store config
        self._configs[model_label] = config
        self._by_model[config.model] = config

        # Reset validation flag
        self._validated = False

    def unregister(self, model_label: str):
        """
        Unregister a content configuration.

        Args:
            model_label: Model label to unregister
        """
        if model_label in self._configs:
            config = self._configs[model_label]
            del self._configs[model_label]
            del self._by_model[config.model]
            self._validated = False

    def get_config(self, model_label: str) -> ContentConfig | None:
        """
        Get a content configuration by model label.

        Args:
            model_label: Model label (e.g., 'cms.page')

        Returns:
            ContentConfig instance or None if not found
        """
        return self._configs.get(model_label)

    def get_config_by_model(self, model: type[models.Model]) -> ContentConfig | None:
        """
        Get a content configuration by model class.

        Args:
            model: Django model class

        Returns:
            ContentConfig instance or None if not found
        """
        return self._by_model.get(model)

    def get_all_configs(self) -> list[ContentConfig]:
        """Get all registered configurations."""
        return list(self._configs.values())

    def get_configs_by_kind(self, kind: str) -> list[ContentConfig]:
        """
        Get all configurations of a specific kind.

        Args:
            kind: Content kind ('collection', 'singleton', 'snippet')

        Returns:
            List of ContentConfig instances
        """
        return [config for config in self._configs.values() if config.kind == kind]

    def get_model_labels(self) -> list[str]:
        """Get all registered model labels."""
        return list(self._configs.keys())

    def is_registered(self, model_label: str) -> bool:
        """Check if a model label is registered."""
        return model_label in self._configs

    def is_model_registered(self, model: type[models.Model]) -> bool:
        """Check if a model class is registered."""
        return model in self._by_model

    def validate_all(self):
        """
        Validate all registered configurations.

        Raises:
            ContentRegistryError: If any configuration is invalid
        """
        if self._validated:
            return

        errors = []

        for model_label, config in self._configs.items():
            try:
                config._validate_config()
            except ValidationError as e:
                errors.append(f"{model_label}: {e}")

        if errors:
            raise ContentRegistryError(
                "Content registry validation failed:\n" + "\n".join(errors)
            )

        self._validated = True

    def get_registry_summary(self) -> dict[str, Any]:
        """
        Get a summary of all registered content types.

        Returns:
            Dictionary with registry statistics and configurations
        """
        configs_by_kind = {}
        for kind in ["collection", "singleton", "snippet"]:
            configs_by_kind[kind] = [
                config.to_dict() for config in self.get_configs_by_kind(kind)
            ]

        return {
            "total_registered": len(self._configs),
            "by_kind": {
                kind: len(configs) for kind, configs in configs_by_kind.items()
            },
            "configs": configs_by_kind,
        }

    def export_configs(self) -> str:
        """
        Export all configurations as JSON.

        Returns:
            JSON string of all configurations
        """
        export_data = {
            "registry_version": "1.0",
            "configs": {
                model_label: config.to_dict()
                for model_label, config in self._configs.items()
            },
        }
        return json.dumps(export_data, indent=2, default=str)

    def clear(self):
        """Clear all registered configurations."""
        self._configs.clear()
        self._by_model.clear()
        self._validated = False


# Global registry instance
content_registry = ContentRegistry()


def register(config: ContentConfig):
    """
    Register a content configuration with the global registry.

    Args:
        config: ContentConfig instance to register
    """
    content_registry.register(config)


def register_model(
    model: type[models.Model], kind: str, name: str = None, **kwargs
) -> ContentConfig:
    """
    Convenience function to register a model with the content registry.

    Args:
        model: Django model class
        kind: Content kind ('collection', 'singleton', 'snippet')
        name: Human-readable name (defaults to model verbose_name)
        **kwargs: Additional ContentConfig parameters

    Returns:
        The created ContentConfig instance
    """
    if name is None:
        name = model._meta.verbose_name

    config = ContentConfig(model=model, kind=kind, name=name, **kwargs)

    register(config)
    return config


def get_config(model_label: str) -> ContentConfig | None:
    """Get a content configuration by model label."""
    return content_registry.get_config(model_label)


def get_config_by_model(model: type[models.Model]) -> ContentConfig | None:
    """Get a content configuration by model class."""
    return content_registry.get_config_by_model(model)


def get_all_configs() -> list[ContentConfig]:
    """Get all registered configurations."""
    return content_registry.get_all_configs()


def is_registered(model_label: str) -> bool:
    """Check if a model label is registered."""
    return content_registry.is_registered(model_label)


def validate_registry():
    """Validate all registered configurations."""
    content_registry.validate_all()


# Auto-register some core CMS models
def register_core_models():
    """Register core CMS models with sensible defaults."""
    try:
        from apps.cms.models import Page

        register_model(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=["title", "blocks", "seo"],
            searchable_fields=["title", "blocks"],
            seo_fields=["title", "seo"],
            route_pattern="/{slug}",
            can_publish=True,
            allowed_block_types=None,  # Allow all block types
            ordering=["-updated_at", "position"],
        )

    except ImportError:
        # CMS models not available yet
        pass

    # Register blog models
    try:
        from apps.blog.models import BlogPost, Category, Tag

        # Register BlogPost as a collection
        register_model(
            model=BlogPost,
            kind="collection",
            name="Blog Posts",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=["title", "excerpt", "content", "blocks", "seo"],
            searchable_fields=["title", "excerpt", "content", "blocks"],
            seo_fields=["title", "excerpt", "seo"],
            route_pattern="/blog/{slug}",
            can_publish=True,
            allowed_block_types=None,  # Allow all block types
            ordering=["-published_at", "-created_at"],
        )

        # Register Category as a collection
        register_model(
            model=Category,
            kind="collection",
            name="Blog Categories",
            slug_field="slug",
            locale_field=None,  # Categories are global
            translatable_fields=["name", "description"],
            searchable_fields=["name", "description"],
            seo_fields=["name", "description"],  # Use available fields for SEO
            route_pattern="/blog/category/{slug}",
            can_publish=False,  # Categories don't have publish status
            ordering=["name"],
        )

        # Register Tag as a collection
        register_model(
            model=Tag,
            kind="collection",
            name="Blog Tags",
            slug_field="slug",
            locale_field=None,  # Tags are global
            translatable_fields=["name", "description"],
            searchable_fields=["name", "description"],
            seo_fields=["name", "description"],  # Use available fields for SEO
            route_pattern="/blog/tag/{slug}",
            can_publish=False,  # Tags don't have publish status
            ordering=["name"],
        )

    except ImportError:
        # Blog models not available yet
        pass
