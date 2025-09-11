from django.contrib import admin
from django.utils.html import format_html
from django.db import transaction
from .models import (
    Locale,
    TranslationUnit,
    UiMessage,
    UiMessageTranslation,
    TranslationGlossary,
    TranslationQueue,
    TranslationHistory,
)


@admin.register(Locale)
class LocaleAdmin(admin.ModelAdmin):
    """Admin interface for Locale model."""

    list_display = [
        "code",
        "name",
        "native_name",
        "is_default_display",
        "is_active",
        "rtl_display",
        "fallback",
        "sort_order",
    ]
    list_filter = ["is_active", "is_default", "rtl"]
    search_fields = ["code", "name", "native_name"]
    ordering = ["sort_order", "name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        ("Basic Information", {"fields": ["code", "name", "native_name"]}),
        ("Configuration", {"fields": ["fallback", "rtl", "sort_order"]}),
        ("Status", {"fields": ["is_active", "is_default"]}),
        (
            "Timestamps",
            {"fields": ["created_at", "updated_at"], "classes": ["collapse"]},
        ),
    ]

    actions = ["make_default", "activate_locales", "deactivate_locales"]

    def is_default_display(self, obj):
        """Display default status with styling."""
        if obj.is_default:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Default</span>'
            )
        return "–"

    is_default_display.short_description = "Default"
    is_default_display.admin_order_field = "is_default"

    def rtl_display(self, obj):
        """Display RTL status."""
        if obj.rtl:
            return format_html('<span style="color: blue;">RTL</span>')
        return "–"

    rtl_display.short_description = "RTL"
    rtl_display.admin_order_field = "rtl"

    def make_default(self, request, queryset):
        """Action to set a locale as default."""
        if queryset.count() != 1:
            self.message_user(
                request,
                "Please select exactly one locale to make default.",
                level="error",
            )
            return

        locale = queryset.first()

        with transaction.atomic():
            # Remove default from all other locales
            Locale.objects.exclude(id=locale.id).update(is_default=False)
            # Set this locale as default and active
            locale.is_default = True
            locale.is_active = True
            locale.save()

        self.message_user(request, f'"{locale.name}" is now the default locale.')

    make_default.short_description = "Set as default locale"

    def activate_locales(self, request, queryset):
        """Action to activate selected locales."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} locale(s).")

    activate_locales.short_description = "Activate selected locales"

    def deactivate_locales(self, request, queryset):
        """Action to deactivate selected locales."""
        # Prevent deactivating the default locale
        default_in_selection = queryset.filter(is_default=True).exists()
        if default_in_selection:
            self.message_user(
                request,
                "Cannot deactivate the default locale. Please set another locale as default first.",
                level="error",
            )
            return

        count = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {count} locale(s).")

    deactivate_locales.short_description = "Deactivate selected locales"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("fallback")

    def save_model(self, request, obj, form, change):
        """Custom save to handle validation."""
        try:
            obj.save()
        except Exception as e:
            self.message_user(request, f"Error saving locale: {e}", level="error")
            return

        if change:
            self.message_user(request, f'Locale "{obj.name}" updated successfully.')
        else:
            self.message_user(request, f'Locale "{obj.name}" created successfully.')


@admin.register(TranslationGlossary)
class TranslationGlossaryAdmin(admin.ModelAdmin):
    """Admin interface for TranslationGlossary model."""

    list_display = [
        "term",
        "translation",
        "source_locale",
        "target_locale",
        "category",
        "is_verified",
        "created_at",
    ]
    list_filter = ["source_locale", "target_locale", "category", "is_verified"]
    search_fields = ["term", "translation", "context"]
    ordering = ["term"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        ("Translation", {"fields": ["term", "translation", "context"]}),
        ("Locales", {"fields": ["source_locale", "target_locale"]}),
        ("Classification", {"fields": ["category", "is_verified"]}),
        (
            "Metadata",
            {
                "fields": ["created_by", "updated_by", "created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def save_model(self, request, obj, form, change):
        """Set created_by and updated_by fields."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TranslationQueue)
class TranslationQueueAdmin(admin.ModelAdmin):
    """Admin interface for TranslationQueue model."""

    list_display = [
        "translation_unit",
        "status",
        "priority",
        "assigned_to",
        "deadline",
        "word_count",
        "is_overdue",
        "created_at",
    ]
    list_filter = ["status", "priority", "assigned_to", "deadline"]
    search_fields = [
        "translation_unit__source_text",
        "translation_unit__target_text",
        "notes",
    ]
    ordering = ["-priority", "deadline"]
    readonly_fields = ["created_at", "updated_at", "word_count", "is_overdue"]

    fieldsets = [
        ("Translation", {"fields": ["translation_unit", "status", "priority"]}),
        ("Assignment", {"fields": ["assigned_to", "deadline", "estimated_hours"]}),
        (
            "Machine Translation",
            {
                "fields": ["machine_translation_suggestion", "mt_service"],
                "classes": ["collapse"],
            },
        ),
        ("Notes", {"fields": ["notes"]}),
        (
            "Metadata",
            {
                "fields": [
                    "word_count",
                    "is_overdue",
                    "created_by",
                    "created_at",
                    "updated_at",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    def save_model(self, request, obj, form, change):
        """Set created_by field."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TranslationHistory)
class TranslationHistoryAdmin(admin.ModelAdmin):
    """Admin interface for TranslationHistory model."""

    list_display = ["translation_unit", "action", "performed_by", "created_at"]
    list_filter = ["action", "performed_by", "created_at"]
    search_fields = ["translation_unit__source_text", "comment"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at"]

    def has_add_permission(self, request):
        """Disable adding history entries manually."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing history entries."""
        return False


# Register existing models if not already registered
@admin.register(TranslationUnit)
class TranslationUnitAdmin(admin.ModelAdmin):
    """Admin interface for TranslationUnit model."""

    list_display = [
        "content_type",
        "content_object",
        "field",
        "source_locale",
        "target_locale",
        "status",
        "updated_by",
        "updated_at",
    ]
    list_filter = ["source_locale", "target_locale", "status", "content_type"]
    search_fields = ["source_text", "target_text"]
    ordering = ["-updated_at"]
    readonly_fields = ["created_at", "updated_at", "model_label"]


@admin.register(UiMessage)
class UiMessageAdmin(admin.ModelAdmin):
    """Admin interface for UiMessage model."""

    list_display = ["key", "namespace", "default_value", "created_at"]
    list_filter = ["namespace"]
    search_fields = ["key", "namespace", "description", "default_value"]
    ordering = ["namespace", "key"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(UiMessageTranslation)
class UiMessageTranslationAdmin(admin.ModelAdmin):
    """Admin interface for UiMessageTranslation model."""

    list_display = ["message", "locale", "status", "updated_by", "updated_at"]
    list_filter = ["locale", "status", "message__namespace"]
    search_fields = ["message__key", "value"]
    ordering = ["-updated_at"]
    readonly_fields = ["created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        """Set updated_by field."""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
