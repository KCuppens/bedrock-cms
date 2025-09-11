"""
Custom Allauth adapter to send password reset emails to frontend.
"""

from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to override Allauth behavior for our React frontend.
    """

    def get_email_confirmation_url(self, request, emailconfirmation):
        """Return the email confirmation URL pointing to frontend."""
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:8082")
        return f"{frontend_url}/accounts/confirm-email/{emailconfirmation.key}/"

    def get_password_reset_url(self, request, user, temp_key):
        """
        Return the password reset URL pointing to frontend.

        Allauth passes the temp_key in format: "uidb36-token"
        We need to construct: /accounts/password/reset/key/{uidb36}-{token}/
        """
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:8082")
        # The temp_key is already in the format we need: "uidb36-token"
        return f"{frontend_url}/accounts/password/reset/key/{temp_key}/"

    def send_mail(self, template_prefix, email, context):
        """
        Override to ensure password reset emails use frontend URLs.
        """
        # Update the password reset URL in the context if present
        if "password_reset_url" in context:
            # Parse the backend URL and replace with frontend URL
            backend_url = context["password_reset_url"]
            if "/accounts/password/reset/key/" in backend_url:
                # Extract the key part (uidb36-token)
                key_part = backend_url.split("/accounts/password/reset/key/")[
                    -1
                ].rstrip("/")
                frontend_url = getattr(
                    settings, "FRONTEND_URL", "http://localhost:8082"
                )
                context["password_reset_url"] = (
                    f"{frontend_url}/accounts/password/reset/key/{key_part}/"
                )

        # Call the parent method to actually send the email
        return super().send_mail(template_prefix, email, context)
