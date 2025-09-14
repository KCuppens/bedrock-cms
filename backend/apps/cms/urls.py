from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .versioning_views import AuditEntryViewSet, PageRevisionViewSet
from .views import sitemap_view
from .views.block_types import BlockTypeViewSet
from .views.blocks import BlockSchemaView, BlockTypesView
from .views.category import CategoryViewSet, CollectionViewSet, TagViewSet
from .views.navigation import FooterView, NavigationView, SiteSettingsView
from .views.pages import PagesViewSet
from .views.redirect import RedirectViewSet
from .views.seo import PublicSeoSettingsView, SeoSettingsViewSet

router = DefaultRouter()

router.register(r"pages", PagesViewSet, basename="pages")

router.register(r"revisions", PageRevisionViewSet, basename="revisions")

router.register(r"audit", AuditEntryViewSet, basename="audit")

router.register(r"categories", CategoryViewSet, basename="categories")

router.register(r"tags", TagViewSet, basename="tags")

router.register(r"collections", CollectionViewSet, basename="collections")

router.register(r"redirects", RedirectViewSet, basename="redirects")

router.register(r"seo-settings", SeoSettingsViewSet, basename="seo-settings")

router.register(r"block-types", BlockTypeViewSet, basename="block-types")


urlpatterns = [
    path("", include(router.urls)),
    path("blocks/", BlockTypesView.as_view(), name="block-types"),
    path(
        "blocks/<str:block_type>/schema/",
        BlockSchemaView.as_view(),
        name="block-schema",
    ),
    path("navigation/", NavigationView.as_view(), name="navigation"),
    path("footer/", FooterView.as_view(), name="footer"),
    path("site-settings/", SiteSettingsView.as_view(), name="site-settings"),
    path(
        "public/seo-settings/<str:locale_code>/",
        PublicSeoSettingsView.as_view(),
        name="public-seo-settings",
    ),
    path("sitemap-<str:locale_code>.xml", sitemap_view, name="sitemap"),
]
