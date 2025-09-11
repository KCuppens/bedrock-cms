"""
URL patterns for search functionality.
"""

from django.urls import path
from . import views
from .global_search import global_search, search_suggestions

app_name = "search"

urlpatterns = [
    # Global search endpoints
    path("global/", global_search, name="global-search"),
    path("suggestions/", search_suggestions, name="search-suggestions"),
    # Public search endpoints
    path("", views.SearchAPIView.as_view(), name="search"),
    path("autocomplete/", views.autocomplete_view, name="autocomplete"),
    path("categories/", views.search_categories_view, name="categories"),
    # Admin endpoints
    path(
        "admin/suggestions/",
        views.SearchSuggestionListCreateView.as_view(),
        name="suggestion-list",
    ),
    path(
        "admin/suggestions/<uuid:pk>/",
        views.SearchSuggestionDetailView.as_view(),
        name="suggestion-detail",
    ),
    path("analytics/", views.search_analytics_view, name="analytics"),
    path("index/", views.SearchIndexListView.as_view(), name="index-list"),
    path("queries/", views.SearchQueryLogListView.as_view(), name="query-log"),
    path("bulk-index/", views.bulk_index_view, name="bulk-index"),
]
