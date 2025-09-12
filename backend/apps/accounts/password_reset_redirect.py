from django.conf import settings
from django.shortcuts import redirect
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.http import require_GET
from django.contrib.auth import get_user_model

"""
Handle password reset URL redirects from Allauth to frontend.
"""



@require_GET
def password_reset_redirect(request, uidb36, key):
    """
    Redirect Allauth password reset URLs to frontend.

    Allauth sends URLs like:
    /accounts/password/reset/key/4-cvteep-7d4243083d5d48b785e9d73cff267a72/

    We need to redirect to:
    /password-reset/{uid}/{token}
    """

    User = get_user_model()

    # The uidb36 is the user ID in base36 format
    # The key is the token

    # Get frontend URL from settings or default to localhost
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:8082")

    # Convert base36 user ID to base64 for consistency with Django's default
    try:
        # Convert base36 to int
        user_id = int(uidb36, 36)
        # Get the user to verify they exist
        user = User.objects.get(pk=user_id)
        # Convert to base64
        uid = urlsafe_base64_encode(force_bytes(user.pk))
    except (ValueError, User.DoesNotExist):
        # Invalid user ID, redirect to password reset request page
        return redirect(f"{frontend_url}/forgot-password")

    # Redirect to frontend with the UID and token
    return redirect(f"{frontend_url}/password-reset/{uid}/{key}")


@require_GET
def email_verification_redirect(request, key):
    """
    Redirect email verification URLs to frontend.

    Allauth sends URLs like:
    /accounts/confirm-email/{key}/

    We can handle this by redirecting to a frontend page.
    """
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:8082")

    # For now, just redirect to sign-in with a message
    # You can create a dedicated email verification page if needed
    return redirect(f"{frontend_url}/sign-in?verify={key}")
