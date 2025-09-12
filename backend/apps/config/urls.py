from django.conf import settings

from django.conf.urls.static import static

from django.contrib import admin

from django.urls import include, path


from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


from apps.cms.views import default_sitemap_view, sitemap_view


urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema.yaml", SpectacularAPIView.as_view(), name="schema-yaml"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Legacy schema URLs (for backward compatibility)
    path("schema/", SpectacularAPIView.as_view(), name="schema-legacy"),
    path(
        "schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui-legacy",
    ),
    path(
        "schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc-legacy",
    ),
    # Sitemaps (at root level for SEO)
    path("sitemap.xml", default_sitemap_view, name="default-sitemap"),
    path("sitemap-<str:locale_code>.xml", sitemap_view, name="sitemap"),
    # API endpoints
    path("api/v1/", include("apps.api.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/blog/", include("apps.blog.urls")),
    path("api/v1/cms/", include("apps.cms.urls")),
    path(
        "api/v1/redirects/", include("apps.cms.redirect_urls")
    ),  # Direct redirects endpoint
    path("api/v1/i18n/", include("apps.i18n.urls")),
    path("api/v1/", include("apps.registry.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    # Authentication
    path("auth/", include("apps.accounts.urls")),
    # Note: Allauth password reset URLs are handled by the frontend React app
    # The frontend serves /accounts/password/reset/key/:uidb36-:token
    path("accounts/", include("allauth.urls")),
    # Operations
    path("", include("apps.ops.urls")),
]


# Serve media files in development

if settings.DEBUG:

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Add development-only email preview URLs

    urlpatterns += [
        path("dev/", include("apps.emails.urls")),
    ]
