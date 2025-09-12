from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings

"""Custom Allauth adapter to send password reset emails to frontend."""
class CustomAccountAdapter(DefaultAccountAdapter):

    """Custom adapter to override Allauth URLs for our React frontend."""
    def get_password_reset_url(self, request, user, temp_key):

        """Return the password reset URL pointing to frontend."""
        The temp_key is in format: "uidb36-token"
        We need to return: http://localhost:8082/accounts/password/reset/key/{uidb36}-{token}/

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:8082")
        # The temp_key is already in the format we need: "uidb36-token"
        return f"{frontend_url}/accounts/password/reset/key/{temp_key}/"

    def send_mail(self, template_prefix, email, context):

        """Override to ensure password reset emails use frontend URLs."""
        # Replace any backend URLs with frontend URLs in the context
        if "password_reset_url" in context:
            backend_url = context["password_reset_url"]
            # Replace backend port with frontend port
            if "localhost:8000" in backend_url:
                frontend_url = backend_url.replace("localhost:8000", "localhost:8082")
                context["password_reset_url"] = frontend_url

        # Call the parent method to actually send the email
        return super().send_mail(template_prefix, email, context)
