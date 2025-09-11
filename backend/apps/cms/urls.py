from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.pages import PagesViewSet
from .views import sitemap_view
from .versioning_views import PageRevisionViewSet, AuditEntryViewSet
from .views.category import CategoryViewSet, TagViewSet, CollectionViewSet
from .views.redirect import RedirectViewSet
from .views.seo import SeoSettingsViewSet
from .views.blocks import BlockTypesView, BlockSchemaView
from .views.block_types import BlockTypeViewSet
from .views.navigation import NavigationView, FooterView, SiteSettingsView
from .views.mock_revisions import MockRevisionsView

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
        "pages/<int:page_id>/revisions/",
        MockRevisionsView.as_view(),
        name="page-revisions",
    ),
    path("sitemap-<str:locale_code>.xml", sitemap_view, name="sitemap"),
]
