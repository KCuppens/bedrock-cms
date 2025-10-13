"""
Validators for Schema.org structured data.

Provides validation utilities to ensure JSON-LD schemas comply
with Schema.org specifications.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

# Common Schema.org types with their required properties
SCHEMA_TYPES = {
    "Article": {
        "required": ["headline"],
        "recommended": ["author", "datePublished", "image", "publisher"],
    },
    "BlogPosting": {
        "required": ["headline"],
        "recommended": ["author", "datePublished", "image", "publisher"],
    },
    "WebPage": {"required": ["name"], "recommended": ["description", "url"]},
    "Organization": {"required": ["name"], "recommended": ["url", "logo"]},
    "BreadcrumbList": {"required": ["itemListElement"], "recommended": []},
    "Person": {"required": ["name"], "recommended": []},
    "Product": {
        "required": ["name"],
        "recommended": ["image", "description", "offers"],
    },
    "Event": {
        "required": ["name", "startDate"],
        "recommended": ["location", "description"],
    },
    "FAQPage": {"required": ["mainEntity"], "recommended": []},
    "HowTo": {"required": ["name", "step"], "recommended": ["description", "image"]},
    "LocalBusiness": {
        "required": ["name", "address"],
        "recommended": ["telephone", "openingHoursSpecification"],
    },
}


class SchemaValidationError(Exception):
    """Exception raised for schema validation errors."""

    pass


class SchemaValidator:
    """Validator for Schema.org JSON-LD structured data."""

    @staticmethod
    def validate(
        schema: Any, strict: bool = False
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a schema object.

        Args:
            schema: Schema dict, list, or JSON string to validate
            strict: If True, treat warnings as errors

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        try:
            # Parse if string
            if isinstance(schema, str):
                try:
                    schema = json.loads(schema)
                except json.JSONDecodeError as e:
                    errors.append(f"Invalid JSON: {str(e)}")
                    return False, errors, warnings

            # Handle list of schemas
            if isinstance(schema, list):
                for i, item in enumerate(schema):
                    is_valid, item_errors, item_warnings = SchemaValidator.validate(
                        item, strict
                    )
                    errors.extend([f"Schema {i}: {e}" for e in item_errors])
                    warnings.extend([f"Schema {i}: {w}" for w in item_warnings])

                return len(errors) == 0, errors, warnings

            # Validate single schema
            schema_errors, schema_warnings = SchemaValidator._validate_single_schema(
                schema
            )
            errors.extend(schema_errors)
            warnings.extend(schema_warnings)

        except Exception as e:
            errors.append(f"Unexpected validation error: {str(e)}")

        is_valid = (
            len(errors) == 0
            if not strict
            else (len(errors) == 0 and len(warnings) == 0)
        )
        return is_valid, errors, warnings

    @staticmethod
    def _validate_single_schema(schema: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Validate a single schema object.

        Args:
            schema: Schema dictionary

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        # Must be a dict
        if not isinstance(schema, dict):
            errors.append("Schema must be a JSON object")
            return errors, warnings

        # Check for @type
        if "@type" not in schema:
            errors.append("Schema must have @type property")
            return errors, warnings

        schema_type = schema["@type"]

        # Check if @context is present
        if "@context" not in schema:
            warnings.append(
                "Schema should have @context property (e.g., 'https://schema.org')"
            )

        # Validate known schema types
        if schema_type in SCHEMA_TYPES:
            type_spec = SCHEMA_TYPES[schema_type]

            # Check required properties
            for prop in type_spec["required"]:
                if prop not in schema:
                    errors.append(
                        f"Required property '{prop}' is missing for {schema_type}"
                    )

            # Check recommended properties
            for prop in type_spec["recommended"]:
                if prop not in schema:
                    warnings.append(
                        f"Recommended property '{prop}' is missing for {schema_type}"
                    )

            # Type-specific validation
            type_errors, type_warnings = SchemaValidator._validate_type_specific(
                schema, schema_type
            )
            errors.extend(type_errors)
            warnings.extend(type_warnings)
        else:
            warnings.append(f"Unknown schema type: {schema_type}")

        return errors, warnings

    @staticmethod
    def _validate_type_specific(
        schema: Dict[str, Any], schema_type: str
    ) -> Tuple[List[str], List[str]]:
        """
        Perform type-specific validation.

        Args:
            schema: Schema dictionary
            schema_type: The @type value

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        if schema_type in ["Article", "BlogPosting"]:
            # Validate author
            if "author" in schema:
                if not isinstance(schema["author"], dict):
                    errors.append("author should be an object (Person or Organization)")
                elif "@type" not in schema["author"]:
                    warnings.append("author should have @type property")

            # Validate publisher
            if "publisher" in schema:
                if not isinstance(schema["publisher"], dict):
                    errors.append("publisher should be an object (Organization)")
                elif schema["publisher"].get("@type") != "Organization":
                    warnings.append("publisher should be of type Organization")
                elif "name" not in schema["publisher"]:
                    errors.append("publisher must have a name property")

            # Validate image
            if "image" in schema:
                image = schema["image"]
                if not isinstance(image, (str, list, dict)):
                    errors.append("image must be a URL string, array, or ImageObject")

        elif schema_type == "BreadcrumbList":
            # Validate itemListElement
            if "itemListElement" in schema:
                items = schema["itemListElement"]
                if not isinstance(items, list):
                    errors.append("itemListElement must be an array")
                else:
                    for i, item in enumerate(items):
                        if not isinstance(item, dict):
                            errors.append(f"itemListElement[{i}] must be an object")
                            continue

                        if "@type" not in item or item["@type"] != "ListItem":
                            errors.append(
                                f"itemListElement[{i}] must have @type: ListItem"
                            )

                        if "position" not in item:
                            errors.append(
                                f"itemListElement[{i}] must have position property"
                            )

                        if "name" not in item:
                            warnings.append(
                                f"itemListElement[{i}] should have name property"
                            )

        elif schema_type == "FAQPage":
            # Validate mainEntity
            if "mainEntity" in schema:
                entities = schema["mainEntity"]
                if not isinstance(entities, list):
                    errors.append("mainEntity must be an array")
                else:
                    for i, entity in enumerate(entities):
                        if not isinstance(entity, dict):
                            errors.append(f"mainEntity[{i}] must be an object")
                            continue

                        if entity.get("@type") != "Question":
                            errors.append(f"mainEntity[{i}] must be of type Question")

                        if "acceptedAnswer" not in entity:
                            errors.append(
                                f"mainEntity[{i}] must have acceptedAnswer property"
                            )
                        elif not isinstance(entity["acceptedAnswer"], dict):
                            errors.append(
                                f"mainEntity[{i}].acceptedAnswer must be an object"
                            )
                        elif entity["acceptedAnswer"].get("@type") != "Answer":
                            warnings.append(
                                f"mainEntity[{i}].acceptedAnswer should be of type Answer"
                            )

        elif schema_type == "HowTo":
            # Validate step
            if "step" in schema:
                steps = schema["step"]
                if not isinstance(steps, list):
                    errors.append("step must be an array")
                else:
                    for i, step in enumerate(steps):
                        if not isinstance(step, dict):
                            errors.append(f"step[{i}] must be an object")
                            continue

                        if step.get("@type") != "HowToStep":
                            warnings.append(f"step[{i}] should be of type HowToStep")

                        if "text" not in step and "itemListElement" not in step:
                            errors.append(
                                f"step[{i}] must have text or itemListElement property"
                            )

        elif schema_type == "Organization":
            # Validate logo
            if "logo" in schema:
                logo = schema["logo"]
                if not isinstance(logo, (str, dict)):
                    errors.append("logo must be a URL string or ImageObject")
                elif isinstance(logo, dict) and logo.get("@type") != "ImageObject":
                    warnings.append("logo object should be of type ImageObject")

        return errors, warnings

    @staticmethod
    def get_schema_types() -> List[Dict[str, Any]]:
        """
        Get list of supported schema types with their specifications.

        Returns:
            List of schema type definitions
        """
        types = []
        for type_name, spec in SCHEMA_TYPES.items():
            types.append(
                {
                    "type": type_name,
                    "required_properties": spec["required"],
                    "recommended_properties": spec["recommended"],
                }
            )
        return types


def validate_page_schema(page) -> Tuple[bool, List[str], List[str]]:
    """
    Validate schema stored in a page's SEO field.

    Args:
        page: Page or BlogPost model instance

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    if not hasattr(page, "seo") or not page.seo:
        return True, [], ["No schema data found"]

    seo = page.seo if isinstance(page.seo, dict) else {}

    # Check for schemas array (new format)
    if "schemas" in seo and isinstance(seo["schemas"], list):
        all_errors = []
        all_warnings = []

        for i, schema_obj in enumerate(seo["schemas"]):
            if "data" in schema_obj:
                is_valid, errors, warnings = SchemaValidator.validate(
                    schema_obj["data"]
                )
                all_errors.extend([f"Schema {i}: {e}" for e in errors])
                all_warnings.extend([f"Schema {i}: {w}" for w in warnings])

        return len(all_errors) == 0, all_errors, all_warnings

    # Check for jsonLd string (old format)
    elif "jsonLd" in seo or "json_ld" in seo:
        json_ld = seo.get("jsonLd") or seo.get("json_ld")
        if json_ld:
            return SchemaValidator.validate(json_ld)

    return True, [], ["No schema data to validate"]
