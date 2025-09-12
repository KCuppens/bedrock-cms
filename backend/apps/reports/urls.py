from django.urls import path

from . import views

"""
Reports URL configuration.
"""


app_name = "reports"

urlpatterns = [
    # Reports overview
    path("", views.reports_overview, name="overview"),
    # Broken links report
    path("broken-links/", views.broken_links_report, name="broken-links"),
    # Translation digest
    path("translation-digest/", views.translation_digest, name="translation-digest"),
    # Locale seeding
    path("seed-locale/", views.seed_locale, name="seed-locale"),
    # Task status checking
    path("task-status/<str:task_id>/", views.task_status, name="task-status"),
]
