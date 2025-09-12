import json



from django.core.exceptions import ValidationError

from django.utils.translation import gettext_lazy as _



"""Custom validators for the core app."""



def validate_json_size(value, max_size_mb=1):
    """
    Validate that JSON field size doesn't exceed the limit.

    Args:
        value: The JSON value to validate
        max_size_mb: Maximum size in megabytes (default 1MB)
    """
    if value is None:



    # Convert to JSON string to measure size

    try:

        json_str = json.dumps(value)

        size_bytes = len(json_str.encode("utf-8"))

        max_bytes = max_size_mb * 1024 * 1024



        if size_bytes > max_bytes:

            raise ValidationError(

                _(

                    "JSON data size (%(size).2f MB) exceeds maximum allowed size (%(max_size)d MB)."

                ),

                params={"size": size_bytes / (1024 * 1024), "max_size": max_size_mb},

                code="json_too_large",

            )

    except (TypeError, ValueError) as e:

        raise ValidationError(

            _("Invalid JSON data: %(error)s"),

            params={"error": str(e)},

            code="invalid_json",

        )



def validate_json_structure(value, max_depth=10):
    """
    Validate JSON structure to prevent deeply nested objects.



    Args:

        value: The JSON value to validate

        max_depth: Maximum nesting depth allowed
    """

    def check_depth(obj, current_depth=0):

        if current_depth > max_depth:

            raise ValidationError(

                _("JSON nesting depth exceeds maximum allowed depth of %(max_depth)d"),

                params={"max_depth": max_depth},

                code="json_too_deep",

            )



        if isinstance(obj, dict):

            for v in obj.values():

                check_depth(v, current_depth + 1)

        elif isinstance(obj, list):

            for item in obj:

                check_depth(item, current_depth + 1)



    if value is not None:

        check_depth(value)



class JSONSizeValidator:



    Validator class for JSON field size limits.



    def __init__(self, max_size_mb=1):

        self.max_size_mb = max_size_mb



    def __call__(self, value):

        validate_json_size(value, self.max_size_mb)



    def deconstruct(self):

# Imports that were malformed - commented out
#         """return ("apps.core.validators.JSONSizeValidator", [self.max_size_mb], {})"""

