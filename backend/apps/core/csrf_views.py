from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET

CSRF token endpoint for frontend applications.

@require_GET
def get_csrf_token(request):  # noqa: C901

    Get CSRF token for frontend application.

    This endpoint allows the frontend to get a CSRF token
    that can be used for subsequent POST requests.

    token = get_token(request)
    response = JsonResponse({"csrfToken": token})

    # Set cookie as well for session-based auth
    response.set_cookie(
        "csrftoken",
        token,
        max_age=60 * 60 * 24 * 7,  # 1 week
        httponly=False,  # Allow JavaScript to read it
        samesite="Lax",
    )

    return response
