from django.contrib import admin

from .models import Redirect


@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):

    list_display = ["from_path", "to_path", "status", "locale", "created_at"]

    list_filter = ["status", "created_at"]

    search_fields = ["from_path", "to_path"]

    readonly_fields = ["created_at"]

    fieldsets = [
        (None, {"fields": ["from_path", "to_path", "status", "locale"]}),
        ("Timestamps", {"fields": ["created_at"], "classes": ["collapse"]}),
    ]
