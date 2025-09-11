"""
Content configuration and registry for CMS content types.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Type, Union
from django.db import models
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.contrib.contenttypes.models import ContentType


@dataclass
class ContentConfig:
    """
    Configuration for registering a Django model as CMS content.
    
    This defines how a model should be exposed through the CMS API,
    including routing, SEO, search, and translation settings.
    """
    
    # Required fields
    model: Type[models.Model]
    kind: str  # 'collection', 'singleton', 'snippet'
    name: str
    
    # Optional fields with defaults
    slug_field: Optional[str] = None
    locale_field: Optional[str] = 'locale'
    translatable_fields: List[str] = field(default_factory=list)
    searchable_fields: List[str] = field(default_factory=list)
    seo_fields: List[str] = field(default_factory=lambda: ['title', 'seo'])
    route_pattern: Optional[str] = None
    can_publish: bool = True
    allowed_block_types: Optional[List[str]] = None
    form_fields: Optional[List[str]] = None
    ordering: List[str] = field(default_factory=lambda: ['-created_at'])
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()
    
    @property
    def model_label(self) -> str:
        """Get the model label (app.model) for this config."""
        content_type = ContentType.objects.get_for_model(self.model)
        return f"{content_type.app_label}.{content_type.model}"
    
    @property
    def app_label(self) -> str:
        """Get the app label for this config."""
        content_type = ContentType.objects.get_for_model(self.model)
        return content_type.app_label
    
    @property
    def model_name(self) -> str:
        """Get the model name for this config."""
        content_type = ContentType.objects.get_for_model(self.model)
        return content_type.model
    
    @property
    def verbose_name(self) -> str:
        """Get the verbose name of the model."""
        return str(self.model._meta.verbose_name)
    
    @property
    def verbose_name_plural(self) -> str:
        """Get the verbose name plural of the model."""
        return str(self.model._meta.verbose_name_plural)
    
    def _validate_config(self):
        """Validate the configuration against the model."""
        errors = []
        
        # Validate kind
        valid_kinds = ['collection', 'singleton', 'snippet']
        if self.kind not in valid_kinds:
            errors.append(f"Invalid kind '{self.kind}'. Must be one of: {valid_kinds}")
        
        # Validate field existence
        model_fields = {f.name for f in self.model._meta.get_fields()}
        
        # Check slug_field
        if self.slug_field and self.slug_field not in model_fields:
            errors.append(f"slug_field '{self.slug_field}' does not exist on model {self.model}")
        
        # Check locale_field
        if self.locale_field and self.locale_field not in model_fields:
            errors.append(f"locale_field '{self.locale_field}' does not exist on model {self.model}")
        
        # Check translatable_fields
        for field_name in self.translatable_fields:
            if field_name not in model_fields:
                errors.append(f"translatable_field '{field_name}' does not exist on model {self.model}")
        
        # Check searchable_fields
        for field_name in self.searchable_fields:
            # Handle nested fields (e.g., 'seo.title')
            root_field = field_name.split('.')[0]
            if root_field not in model_fields:
                errors.append(f"searchable_field '{field_name}' root field '{root_field}' does not exist on model {self.model}")
        
        # Check seo_fields
        for field_name in self.seo_fields:
            root_field = field_name.split('.')[0]
            if root_field not in model_fields:
                errors.append(f"seo_field '{field_name}' root field '{root_field}' does not exist on model {self.model}")
        
        # Check form_fields if specified
        if self.form_fields:
            for field_name in self.form_fields:
                if field_name not in model_fields:
                    errors.append(f"form_field '{field_name}' does not exist on model {self.model}")
        
        # Check ordering fields
        for field_name in self.ordering:
            # Remove ordering prefix (- or +)
            clean_field = field_name.lstrip('-+')
            if clean_field not in model_fields:
                errors.append(f"ordering field '{field_name}' ('{clean_field}') does not exist on model {self.model}")
        
        # Validate specific combinations
        if self.kind == 'singleton' and self.slug_field:
            errors.append("Singleton content types should not have a slug_field")
        
        if self.kind in ['collection', 'snippet'] and not self.slug_field:
            errors.append(f"{self.kind.title()} content types should have a slug_field")
        
        # Validate route_pattern for collections
        if self.kind == 'collection' and self.route_pattern and '{slug}' not in self.route_pattern:
            errors.append("Collection route_pattern should contain '{slug}' placeholder")
        
        if errors:
            raise ValidationError(
                f"Invalid ContentConfig for {self.model}: " + "; ".join(errors)
            )
    
    def get_effective_form_fields(self) -> List[str]:
        """
        Get the effective form fields to use for serialization.
        
        Returns form_fields if specified, otherwise all model fields.
        """
        if self.form_fields:
            return self.form_fields
        
        # Return all model field names
        return [f.name for f in self.model._meta.get_fields() 
                if not f.many_to_many and not f.one_to_many]
    
    def supports_publishing(self) -> bool:
        """Check if this content type supports publishing."""
        return self.can_publish and hasattr(self.model, 'status')
    
    def supports_localization(self) -> bool:
        """Check if this content type supports localization."""
        return self.locale_field is not None
    
    def get_route_pattern(self) -> Optional[str]:
        """Get the route pattern for this content type."""
        if self.route_pattern:
            return self.route_pattern
        
        # Generate default route patterns
        if self.kind == 'collection' and self.slug_field:
            return f"/{self.model_name}/{{slug}}"
        elif self.kind == 'singleton':
            return f"/{self.model_name}"
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            'model_label': self.model_label,
            'kind': self.kind,
            'name': self.name,
            'slug_field': self.slug_field,
            'locale_field': self.locale_field,
            'translatable_fields': self.translatable_fields,
            'searchable_fields': self.searchable_fields,
            'seo_fields': self.seo_fields,
            'route_pattern': self.get_route_pattern(),
            'can_publish': self.can_publish,
            'allowed_block_types': self.allowed_block_types,
            'form_fields': self.form_fields,
            'ordering': self.ordering,
            'verbose_name': self.verbose_name,
            'verbose_name_plural': self.verbose_name_plural,
            'supports_publishing': self.supports_publishing(),
            'supports_localization': self.supports_localization(),
        }