from django.contrib.auth import authenticate, get_user_model, login, logout

from django.contrib.auth.password_validation import validate_password

from django.contrib.auth.tokens import default_token_generator as django_token_generator

from django.core.exceptions import ValidationError

from django.core.validators import validate_email

from django.utils.encoding import force_str

from django.utils.http import urlsafe_base64_decode


from allauth.account.forms import ResetPasswordForm, default_token_generator

from drf_spectacular.utils import extend_schema

from rest_framework import status

from rest_framework.decorators import api_view, permission_classes, throttle_classes

from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework.response import Response

from rest_framework.throttling import AnonRateThrottle

from rest_framework.views import APIView


from .serializers import UserSerializer


User = get_user_model()


class LoginThrottle(AnonRateThrottle):
    """Rate limiting for login attempts"""

    scope = "login"

    rate = "5/min"


class PasswordResetThrottle(AnonRateThrottle):
    """Rate limiting for password reset requests"""

    scope = "password_reset"

    rate = "3/hour"


@extend_schema(
    summary="User login",
    description="Authenticate user and create session",
    request={
        "type": "object",
        "properties": {
            "email": {"type": "string", "format": "email"},
            "password": {"type": "string"},
        },
        "required": ["email", "password"],
    },
    responses={
        200: UserSerializer,
        400: {"description": "Invalid credentials"},
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def login_view(request):  # noqa: C901
    """REST API endpoint for user login"""

    email = request.data.get("email", "").lower().strip()

    password = request.data.get("password", "")

    if not email or not password:

        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Authenticate user

    user = authenticate(request, username=email, password=password)

    if user is None:

        return Response(
            {"error": "Invalid email or password"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not user.is_active:

        return Response(
            {"error": "Account is disabled"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Email verification is disabled - users can login immediately

    # No verification check needed since ACCOUNT_EMAIL_VERIFICATION = "none"

    # Login user (creates session)

    login(request, user)

    # Return user data

    serializer = UserSerializer(user, context={"request": request})

    return Response(
        {
            "user": serializer.data,
            "message": "Login successful",
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    summary="User logout",
    description="Logout current user and destroy session",
    responses={
        200: {"description": "Logout successful"},
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):  # noqa: C901
    """REST API endpoint for user logout"""

    logout(request)

    return Response(
        {"message": "Logout successful"},
        status=status.HTTP_200_OK,
    )


@extend_schema(
    summary="Get current user",
    description="Get current authenticated user information",
    responses={
        200: UserSerializer,
        401: {"description": "Not authenticated"},
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user_view(request):  # noqa: C901
    """REST API endpoint to get current user"""

    serializer = UserSerializer(request.user, context={"request": request})

    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    summary="Request password reset",
    description="Send password reset email to user",
    request={
        "type": "object",
        "properties": {
            "email": {"type": "string", "format": "email"},
        },
        "required": ["email"],
    },
    responses={
        200: {"description": "Password reset email sent"},
        400: {"description": "Invalid email"},
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetThrottle])
def password_reset_view(request):  # noqa: C901
    """REST API endpoint for password reset request"""

    email = request.data.get("email", "").lower().strip()

    if not email:

        return Response(
            {"error": "Email is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate email format

    try:

        validate_email(email)

    except ValidationError:

        return Response(
            {"error": "Invalid email format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Use Allauth's password reset form

    form = ResetPasswordForm(data={"email": email})

    if form.is_valid():

        # This will send the password reset email

        form.save(request)

        # Always return success to prevent email enumeration

        return Response(
            {
                "message": "If an account exists with this email, a password reset link has been sent."
            },
            status=status.HTTP_200_OK,
        )

    # Even if form is invalid, return success to prevent enumeration

    return Response(
        {
            "message": "If an account exists with this email, a password reset link has been sent."
        },
        status=status.HTTP_200_OK,
    )


def _parse_token_from_formats(uid_param, token_param):  # noqa: C901
    """Parse UID and token from different formats:

    1. Standard Django format: separate uid and token

    2. Allauth format: combined token like "4-cvtit9-cc6628ec2531c2cc114f2d6d8f06d72d"

    """

    if uid_param and token_param:

        # Standard format: /password-reset/uid/token

        try:

            user_id = force_str(urlsafe_base64_decode(uid_param))

            return user_id, token_param

        except (TypeError, ValueError):
            pass

    # Try allauth format: "4-cvtit9-cc6628ec2531c2cc114f2d6d8f06d72d"

    full_token = uid_param or token_param

    if full_token and "-" in full_token:

        parts = full_token.split("-")

        if len(parts) >= 2:

            # First part is base36 user ID, rest is token

            try:

                user_id_base36 = parts[0]

                user_id = str(int(user_id_base36, 36))  # Convert base36 to decimal

                token = "-".join(parts[1:])  # Join remaining parts as token

                return user_id, token

            except ValueError:
                pass

    raise ValueError("Invalid token format")


@extend_schema(
    summary="Verify password reset token",
    description="Verify if password reset token is valid",
    request={
        "type": "object",
        "properties": {
            "uid": {"type": "string"},
            "token": {"type": "string"},
            "full_token": {"type": "string"},
        },
    },
    responses={
        200: {"description": "Token is valid"},
        400: {"description": "Invalid or expired token"},
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_verify_token(request):  # noqa: C901
    """REST API endpoint for verifying password reset token"""

    uid = request.data.get("uid")

    token = request.data.get("token")

    full_token = request.data.get("full_token")

    try:

        user_id, parsed_token = _parse_token_from_formats(uid or full_token, token)

        user = User.objects.get(pk=user_id)

    except (ValueError, User.DoesNotExist):

        return Response(
            {"error": "Invalid reset link", "valid": False},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if token is valid using allauth's token generator

    # Try allauth token generator first

    if default_token_generator.check_token(user, parsed_token):

        return Response(
            {"message": "Token is valid", "valid": True, "user_id": user_id},
            status=status.HTTP_200_OK,
        )

    # Fallback to Django's token generator

    if django_token_generator.check_token(user, parsed_token):

        return Response(
            {"message": "Token is valid", "valid": True, "user_id": user_id},
            status=status.HTTP_200_OK,
        )

    return Response(
        {"error": "Invalid or expired reset link", "valid": False},
        status=status.HTTP_400_BAD_REQUEST,
    )


@extend_schema(
    summary="Confirm password reset",
    description="Reset password with token from email",
    request={
        "type": "object",
        "properties": {
            "uid": {"type": "string"},
            "token": {"type": "string"},
            "full_token": {"type": "string"},
            "new_password1": {"type": "string"},
            "new_password2": {"type": "string"},
        },
        "required": ["new_password1", "new_password2"],
    },
    responses={
        200: {"description": "Password reset successful"},
        400: {"description": "Invalid token or passwords don't match"},
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm_view(request):  # noqa: C901
    """REST API endpoint for password reset confirmation"""

    uid = request.data.get("uid")

    token = request.data.get("token")

    full_token = request.data.get("full_token")

    new_password1 = request.data.get("new_password1")

    new_password2 = request.data.get("new_password2")

    if not new_password1 or not new_password2:

        return Response(
            {"error": "Both password fields are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if new_password1 != new_password2:

        return Response(
            {"error": "Passwords do not match"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:

        user_id, parsed_token = _parse_token_from_formats(uid or full_token, token)

        user = User.objects.get(pk=user_id)

    except (ValueError, User.DoesNotExist):

        return Response(
            {"error": "Invalid reset link"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if token is valid using allauth's token generator

    token_valid = False

    # Try allauth token generator first

    if default_token_generator.check_token(user, parsed_token):

        token_valid = True

    else:

        # Fallback to Django's token generator

        if django_token_generator.check_token(user, parsed_token):

            token_valid = True

    if not token_valid:

        return Response(
            {"error": "Invalid or expired reset link"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate password strength

    try:

        validate_password(new_password1, user)

    except ValidationError as e:

        return Response(
            {"error": "; ".join(e.messages)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Set the new password

    user.set_password(new_password1)

    # Activate user if they were inactive (e.g., from invitation)

    if not user.is_active:

        user.is_active = True

    user.save()

    return Response(
        {"message": "Password has been reset successfully"},
        status=status.HTTP_200_OK,
    )


class SessionCheckView(APIView):
    """Check if user has valid session"""

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Check session",
        description="Check if current session is valid",
        responses={
            200: UserSerializer,
            401: {"description": "Not authenticated"},
        },
    )
    def get(self, request):  # noqa: C901

        if request.user.is_authenticated:

            serializer = UserSerializer(request.user, context={"request": request})

            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {"error": "Not authenticated"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
