import hashlib
import secrets
import uuid
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.text import slugify


def generate_uuid():
    """Generate a UUID4 string"""

    return str(uuid.uuid4())


def generate_short_uuid(length=8):
    """Generate a short UUID-like string"""

    return str(uuid.uuid4()).replace("-", "")[:length]


def generate_secure_token(length=32):
    """Generate a cryptographically secure random token"""

    return secrets.token_urlsafe(length)


def generate_hash(data: str, algorithm="sha256"):
    """Generate hash of data using specified algorithm"""

    hash_func = getattr(hashlib, algorithm)

    return hash_func(data.encode()).hexdigest()


def create_slug(text: str, max_length: int = 50) -> str:
    """Create a URL-friendly slug from text"""

    slug = slugify(text)

    if len(slug) > max_length:

        slug = slug[:max_length].rstrip("-")

    return slug


def safe_get_dict_value(
    dictionary: Dict[str, Any], key: str, default: Any = None
) -> Any:
    """Safely get value from dictionary with default"""

    try:

        return dictionary.get(key, default)

    except (KeyError, AttributeError):

        return default


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to specified length with suffix"""

    if len(text) <= max_length:

        return text

    return text[: max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human readable format"""

    if size_bytes == 0:

        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]

    i = 0

    size_float = float(size_bytes)

    while size_float >= 1024 and i < len(size_names) - 1:

        size_float /= 1024.0

        i += 1

    return f"{size_float:.1f} {size_names[i]}"


def get_client_ip(request) -> str:
    """Get client IP address from request"""

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if x_forwarded_for:

        ip = x_forwarded_for.split(",")[0]

    else:

        ip = request.META.get("REMOTE_ADDR")

    return ip


def get_user_agent(request) -> str:
    """Get user agent from request"""

    return request.META.get("HTTP_USER_AGENT", "")


def time_since_creation(created_at) -> str:
    """Get human-readable time since creation"""

    now = timezone.now()

    diff = now - created_at

    if diff.days > 0:

        return f"{diff.days} days ago"

    elif diff.seconds > 3600:

        hours = diff.seconds // 3600

        return f"{hours} hours ago"

    elif diff.seconds > 60:

        minutes = diff.seconds // 60

        return f"{minutes} minutes ago"

    else:

        return "Just now"


def send_notification_email(
    subject: str,
    message: str,
    recipient_list: List,
    from_email: Optional[str] = None,
    fail_silently: bool = False,
) -> bool:
    """Send notification email"""

    try:

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=fail_silently,
        )

        return True

    except Exception as e:

        if not fail_silently:

            raise e

        return False


def mask_email(email: str) -> str:
    """Mask email address for privacy"""

    if "@" not in email:

        return email

    local, domain = email.split("@", 1)

    if len(local) <= 2:

        masked_local = local[0] + "*" * (len(local) - 1)

    else:

        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]

    return f"{masked_local}@{domain}"


def validate_json_structure(
    data: Dict[str, Any], required_fields: List
) -> Dict[str, Any]:
    """Validate JSON data has required fields"""

    errors = {}

    for field in required_fields:

        if field not in data:

            errors[field] = f"Field '{field}' is required"

    return errors


def generate_unique_slug(
    model_class, title: str, slug_field: str = "slug", max_length: int = 50
) -> str:
    """Generate a unique slug for a model"""

    base_slug = create_slug(title, max_length)

    slug = base_slug
    counter = 1

    while model_class.objects.filter(**{slug_field: slug}).exists():
        # Calculate the suffix length to ensure we don't exceed max_length
        suffix = f"-{counter}"
        if len(base_slug) + len(suffix) > max_length:
            # Truncate base slug to make room for suffix
            truncated_length = max_length - len(suffix)
            slug = base_slug[:truncated_length] + suffix
        else:
            slug = f"{base_slug}{suffix}"
        counter += 1

    return slug


def get_object_or_none(model_class, **kwargs):
    """Get an object or return None if it doesn't exist"""

    try:
        return model_class.objects.get(**kwargs)
    except model_class.DoesNotExist:
        return None


def bulk_update_or_create(
    model_class, objects_data: List[Dict], unique_field: str = "id"
):
    """Bulk update or create objects"""

    if not objects_data:
        return [], []

    # Separate existing vs new objects
    existing_values = [
        obj.get(unique_field) for obj in objects_data if obj.get(unique_field)
    ]
    existing_objects = {
        getattr(obj, unique_field): obj
        for obj in model_class.objects.filter(
            **{f"{unique_field}__in": existing_values}
        )
    }

    objects_to_create = []
    objects_to_update = []

    for obj_data in objects_data:
        unique_value = obj_data.get(unique_field)
        if unique_value and unique_value in existing_objects:
            # Update existing object
            existing_obj = existing_objects[unique_value]
            for field, value in obj_data.items():
                setattr(existing_obj, field, value)
            objects_to_update.append(existing_obj)
        else:
            # Create new object
            objects_to_create.append(model_class(**obj_data))

    # Perform bulk operations
    created = []
    if objects_to_create:
        created = model_class.objects.bulk_create(objects_to_create)

    updated = []
    if objects_to_update:
        # Get all field names except the unique field
        update_fields = [
            field.name
            for field in model_class._meta.fields
            if field.name != unique_field and not field.primary_key
        ]
        model_class.objects.bulk_update(objects_to_update, update_fields)
        updated = objects_to_update

    return created, updated
