import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from apps.i18n.models import Locale

from .rbac import ScopedLocale
from .serializers import UserSerializer

User = get_user_model()


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role/Group model"""

    permissions = serializers.SerializerMethodField()

    user_count = serializers.IntegerField(read_only=True)

    locale_scopes = serializers.SerializerMethodField()

    locale_scope_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    class Meta:

        model = Group

        fields = [
            "id",
            "name",
            "permissions",
            "user_count",
            "locale_scopes",
            "locale_scope_ids",
        ]

    def get_permissions(self, obj):  # noqa: C901
        """Get permissions for the role"""

        return [
            {
                "id": perm.id,
                "name": perm.name,
                "codename": perm.codename,
                "content_type": perm.content_type.model,
            }
            for perm in obj.permissions.all()
        ]

    def get_locale_scopes(self, obj):  # noqa: C901
        """Get locale scopes for the role"""

        return [
            {
                "id": scope.locale.id,
                "code": scope.locale.code,
                "name": scope.locale.name,
            }
            for scope in obj.locale_scopes.select_related("locale").all()
        ]


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission model"""

    content_type_display = serializers.CharField(
        source="content_type.model", read_only=True
    )

    class Meta:

        model = Permission

        fields = ["id", "name", "codename", "content_type", "content_type_display"]


class UserInviteSerializer(serializers.Serializer):
    """Serializer for user invitation"""

    email = serializers.EmailField()

    role = serializers.CharField(
        required=False
    )  # Single role name for backward compatibility

    roles = serializers.ListField(  # Multiple role IDs
        child=serializers.IntegerField(), required=False, allow_empty=True
    )

    message = serializers.CharField(required=False)

    resend = serializers.BooleanField(default=False)  # Flag for resending invites

    def validate(self, data):  # noqa: C901
        """Custom validation for invite/resend logic"""

        email = data["email"]

        resend = data.get("resend", False)

        user_exists = User.objects.filter(email=email).exists()

        if resend:

            # For resend, user must exist

            if not user_exists:

                raise serializers.ValidationError(
                    {
                        "email": "Cannot resend invite - user with this email does not exist"
                    }
                )

        else:

            # For new invite, user must not exist

            if user_exists:

                raise serializers.ValidationError(
                    {
                        "email": "User with this email already exists. Use resend=true to resend invite."
                    }
                )

        return data


@extend_schema_view(
    list=extend_schema(summary="List all users", tags=["User Management"]),
    retrieve=extend_schema(summary="Get user details", tags=["User Management"]),
    update=extend_schema(summary="Update user", tags=["User Management"]),
    partial_update=extend_schema(
        summary="Partially update user", tags=["User Management"]
    ),
    destroy=extend_schema(summary="Delete user", tags=["User Management"]),
)
class UserManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for user management (admin only)"""

    queryset = User.objects.all()

    serializer_class = UserSerializer

    permission_classes = [IsAdminUser]

    def get_queryset(self):  # noqa: C901
        """Filter users based on query parameters"""

        queryset = self.queryset

        # Filter by active status

        is_active = self.request.query_params.get("is_active")

        if is_active is not None:

            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Filter by role/group

        role = self.request.query_params.get("role")

        if role:

            queryset = queryset.filter(groups__name=role)

        # Search

        search = self.request.query_params.get("search")

        if search:

            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        return queryset.select_related().prefetch_related("groups", "user_permissions")

    @extend_schema(
        summary="Invite new user or resend invitation", tags=["User Management"]
    )
    @action(detail=False, methods=["post"])
    def invite(self, request):  # noqa: C901
        """Send invitation to new user or resend invitation to existing user"""

        serializer = UserInviteSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        role = serializer.validated_data.get(
            "role"
        )  # Single role name (backward compatibility)

        role_ids = serializer.validated_data.get("roles", [])  # Multiple role IDs

        message = serializer.validated_data.get("message", "")

        is_resend = serializer.validated_data.get("resend", False)

        if is_resend:

            # Resend invite to existing user

            try:

                user = User.objects.get(email=email)

                # Generate new password reset token for the invite

                # Create reset token for password setup

                token = default_token_generator.make_token(user)

                urlsafe_base64_encode(force_bytes(user.pk))

                # Send resend invitation email

                send_mail(
                    subject=f"Invitation Reminder - {settings.SITE_NAME}",
                    message=f"""

                    This is a reminder about your invitation to {settings.SITE_NAME}.



                    {message}



                    Please use the following link to set up your password:

                    {settings.FRONTEND_URL}/accounts/password/reset/key/{user.pk}-{token}/



                    If you already have an account, you can sign in at:

                    {settings.FRONTEND_URL}/sign-in
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )

                return Response(
                    {"message": f"Invitation resent to {email}", "user_id": user.id},
                    status=status.HTTP_200_OK,
                )

            except User.DoesNotExist:

                return Response(
                    {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
                )

        else:

            # Create new user invitation

            temp_password = secrets.token_urlsafe(16)

            user = User.objects.create_user(
                email=email,
                password=temp_password,
                is_active=False,  # Will be activated on first login
            )

            # Assign roles if specified

            # First check for multiple role IDs (preferred)

            if role_ids:

                for role_id in role_ids:

                    try:

                        group = Group.objects.get(pk=role_id)

                        user.groups.add(group)

                    except Group.DoesNotExist:
                        pass

            # Fallback to single role name for backward compatibility

            elif role:

                try:

                    group = Group.objects.get(name=role)

                    user.groups.add(group)

                except Group.DoesNotExist:
                    pass

            # Generate password reset token for new user

            # Create reset token for password setup

            token = default_token_generator.make_token(user)

            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Send invitation email

            send_mail(
                subject=f"Invitation to {settings.SITE_NAME}",
                message=(
                    f"You have been invited to {settings.SITE_NAME}.\n\n"
                    f"{message}\n\n"
                    f"Please use the following link to set up your password:\n"
                    f"{settings.FRONTEND_URL}/accounts/password/reset/key/{user.pk}-{token}/"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            return Response(
                {"message": f"Invitation sent to {email}", "user_id": user.id},
                status=status.HTTP_201_CREATED,
            )

    @extend_schema(summary="Update user roles", tags=["User Management"])
    @action(detail=True, methods=["put"])
    def roles(self, request, pk=None):  # noqa: C901
        """Update user's roles"""

        user = self.get_object()

        role_ids = request.data.get("role_ids", [])

        # Clear existing groups

        user.groups.clear()

        # Add new groups

        for role_id in role_ids:

            try:

                group = Group.objects.get(pk=role_id)

                user.groups.add(group)

            except Group.DoesNotExist:
                pass

        return Response(
            {
                "message": "Roles updated successfully",
                "roles": [g.name for g in user.groups.all()],
            }
        )

    @extend_schema(summary="Deactivate user", tags=["User Management"])
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):  # noqa: C901
        """Deactivate a user account"""

        user = self.get_object()

        user.is_active = False

        user.save()

        return Response({"message": f"User {user.email} has been deactivated"})

    @extend_schema(summary="Reactivate user", tags=["User Management"])
    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):  # noqa: C901
        """Reactivate a user account"""

        user = self.get_object()

        user.is_active = True

        user.save()

        return Response({"message": f"User {user.email} has been reactivated"})

    @extend_schema(summary="Delete user", tags=["User Management"])
    def destroy(self, request, pk=None):  # noqa: C901
        """Delete a user with validation"""

        user = self.get_object()

        # Prevent deleting the current user

        if user.id == request.user.id:

            return Response(
                {"error": "You cannot delete your own account"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent deleting superusers (optional - remove if not needed)

        if user.is_superuser:

            return Response(
                {"error": "Cannot delete superuser accounts"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Store email for response message

        user_email = user.email

        # Perform the deletion

        user.delete()

        return Response({"message": f"User {user_email} has been deleted successfully"})


@extend_schema_view(
    list=extend_schema(summary="List all roles", tags=["Role Management"]),
    create=extend_schema(summary="Create new role", tags=["Role Management"]),
    retrieve=extend_schema(summary="Get role details", tags=["Role Management"]),
    update=extend_schema(summary="Update role", tags=["Role Management"]),
    partial_update=extend_schema(
        summary="Partially update role", tags=["Role Management"]
    ),
    destroy=extend_schema(summary="Delete role", tags=["Role Management"]),
)
class RoleViewSet(viewsets.ModelViewSet):
    """ViewSet for role/group management"""

    queryset = Group.objects.all()

    serializer_class = RoleSerializer

    permission_classes = [IsAdminUser]

    def get_queryset(self):  # noqa: C901
        """Get roles with user count"""

        return self.queryset.annotate(user_count=Count("user"))

    def create(self, request, *args, **kwargs):  # noqa: C901
        """Create a new role/group"""

        data = getattr(request, "data", request.POST)

        name = data.get("name")

        locale_scope_ids = data.get("locale_scope_ids", [])

        if not name:

            return Response(
                {"error": "Role name is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create the group/role

        try:

            group = Group.objects.create(name=name)

            # Create locale scopes if provided

            if locale_scope_ids:

                for locale_id in locale_scope_ids:

                    try:

                        locale = Locale.objects.get(pk=locale_id)

                        ScopedLocale.objects.create(group=group, locale=locale)

                    except Locale.DoesNotExist:

                        # Skip invalid locale IDs
                        pass

            serializer = self.get_serializer(group)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:

            return Response(
                {"error": f"Failed to create role: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):  # noqa: C901
        """Update an existing role/group"""

        kwargs.pop("partial", False)

        instance = self.get_object()

        data = getattr(request, "data", request.POST)

        name = data.get("name")

        locale_scope_ids = data.get("locale_scope_ids", [])

        # Update name if provided

        if name:

            instance.name = name

            instance.save()

        # Update locale scopes if provided

        if "locale_scope_ids" in data:

            # Clear existing locale scopes

            ScopedLocale.objects.filter(group=instance).delete()

            # Create new locale scopes

            for locale_id in locale_scope_ids:

                try:

                    locale = Locale.objects.get(pk=locale_id)

                    ScopedLocale.objects.create(group=instance, locale=locale)

                except Locale.DoesNotExist:

                    # Skip invalid locale IDs
                    pass

        serializer = self.get_serializer(instance)

        return Response(serializer.data)

    @extend_schema(summary="Manage role permissions", tags=["Role Management"])
    @action(detail=True, methods=["get", "post", "put"])
    def permissions(self, request, pk=None):  # noqa: C901
        """Get or update permissions for a role"""

        role = self.get_object()

        if request.method == "GET":

            # Return current permissions

            permissions = [
                {
                    "id": perm.id,
                    "name": perm.name,
                    "codename": perm.codename,
                    "content_type": perm.content_type.model,
                }
                for perm in role.permissions.all()
            ]

            return Response(
                {"role_id": role.id, "role_name": role.name, "permissions": permissions}
            )

        elif request.method in ["POST", "PUT"]:

            # Update permissions

            permission_ids = request.data.get("permission_ids", [])

            # Clear existing permissions

            role.permissions.clear()

            # Add new permissions

            for perm_id in permission_ids:

                try:

                    permission = Permission.objects.get(pk=perm_id)

                    role.permissions.add(permission)

                except Permission.DoesNotExist:
                    pass

            return Response(
                {
                    "message": "Permissions updated successfully",
                    "permissions": [p.codename for p in role.permissions.all()],
                }
            )


@extend_schema_view(
    list=extend_schema(summary="List all permissions", tags=["Permission Management"]),
    retrieve=extend_schema(
        summary="Get permission details", tags=["Permission Management"]
    ),
)
class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing available permissions"""

    queryset = Permission.objects.all()

    serializer_class = PermissionSerializer

    permission_classes = [IsAdminUser]

    def get_queryset(self):  # noqa: C901
        """Filter permissions"""

        queryset = self.queryset

        # Filter by content type

        content_type = self.request.query_params.get("content_type")

        if content_type:

            queryset = queryset.filter(content_type__model=content_type)

        # Search

        search = self.request.query_params.get("search")

        if search:

            queryset = queryset.filter(
                Q(name__icontains=search) | Q(codename__icontains=search)
            )

        return queryset.select_related("content_type")


@extend_schema(summary="Get available scopes", tags=["Permission Management"])
@api_view(["GET"])
@permission_classes([IsAdminUser])
def get_scopes(request):  # noqa: C901
    """Get available permission scopes"""

    # These would be defined in your RBAC system

    scopes = [
        {"id": "global", "name": "Global", "description": "System-wide scope"},
        {"id": "locale", "name": "Locale", "description": "Locale-specific scope"},
        {"id": "section", "name": "Section", "description": "Section-specific scope"},
        {
            "id": "category",
            "name": "Category",
            "description": "Category-specific scope",
        },
    ]

    return Response(scopes)
