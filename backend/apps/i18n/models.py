from typing import TYPE_CHECKING, cast



from django.contrib.auth import get_user_model

from django.contrib.contenttypes.fields import GenericForeignKey

from django.contrib.contenttypes.models import ContentType

from django.core.exceptions import ValidationError

from django.db import models

from django.db.models import (

    BooleanField,

    CharField,

    DateTimeField,

    DecimalField,

    ForeignKey,

    OneToOneField,

    PositiveIntegerField,

    QuerySet,

    TextField,

)

from django.utils import timezone



if TYPE_CHECKING:

    from django.contrib.auth.models import AbstractUser as User



class Locale(models.Model):

    """Locale model for multi-language support."""



    code: CharField = models.CharField(

        max_length=10, unique=True, help_text="Language code (e.g., 'en', 'es', 'fr')"

    )

    name: CharField = models.CharField(

        max_length=100,

        help_text="Human-readable name in English (e.g., 'English', 'Spanish')",

    )

    native_name: CharField = models.CharField(

        max_length=100,

        default="",

        help_text="Native name in the language itself (e.g., 'English', 'Español', 'Français')",

    )

    fallback: ForeignKey = models.ForeignKey(

        "self",

        null=True,

        blank=True,

        on_delete=models.SET_NULL,

        help_text="Fallback locale if content is not available in this locale",

    )

    rtl: BooleanField = models.BooleanField(

        default=False,

        help_text="True if this is a right-to-left language (e.g., Arabic, Hebrew)",

    )

    sort_order: PositiveIntegerField = models.PositiveIntegerField(

        default=0, help_text="Sort order for locale lists (lower numbers first)"

    )

    is_active: BooleanField = models.BooleanField(

        default=True, help_text="Whether this locale is active and available for use"

    )

    is_default: BooleanField = models.BooleanField(

        default=False, help_text="Whether this is the default locale for the site"

    )

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: DateTimeField = models.DateTimeField(

        auto_now=True, null=True, blank=True

    )



    class Meta:

        ordering = ["sort_order", "name"]

        indexes = [

            models.Index(fields=["is_active", "sort_order"]),

            models.Index(fields=["is_default"]),

        ]



    def __str__(self):  # noqa: C901

        return f"{self.name} ({self.code})"



    def clean(self):  # noqa: C901

        """Validate locale data."""

        super().clean()



        # Check for fallback cycles

        if self.fallback:

            self._check_fallback_cycle()



    def _check_fallback_cycle(self):  # noqa: C901

        """Check for cycles in fallback chain."""

        visited = set()

        current = self.fallback



        while current and current.id not in visited:

            if current.id == self.id:

                raise ValidationError(

                    {

                        "fallback": "Fallback creates a cycle. A locale cannot fall back to itself or create a circular chain."

                    }

                )

            visited.add(current.id)

            current = current.fallback



    def get_fallback_chain(self):  # noqa: C901

        """Get the complete fallback chain for this locale."""

        chain = [self]

        current = self.fallback

        visited = {self.id}



        while current and current.id not in visited:

            chain.append(current)

            visited.add(current.id)

            current = current.fallback



        return chain



    def save(self, *args, **kwargs):  # noqa: C901

        # Ensure only one default locale

        if self.is_default:

            Locale.objects.exclude(id=self.id).update(is_default=False)



        # Ensure we have a default locale if this is the only active one

        if not self.is_default and self.is_active:

            if (

                not Locale.objects.exclude(id=self.id)

                .filter(is_default=True, is_active=True)

                .exists()

            ):

                self.is_default = True



        # Run validation

        self.full_clean()



        super().save(*args, **kwargs)



# Define User type properly for mypy

if TYPE_CHECKING:

    pass  # User is imported in the TYPE_CHECKING block above

else:

    User = get_user_model()



class TranslationUnit(models.Model):



    Track translatable content for any model field.



    Supports content translation workflow with status tracking and fallback resolution.



    STATUS_CHOICES = [

        ("missing", "Missing"),

        ("draft", "Draft"),

        ("needs_review", "Needs Review"),

        ("approved", "Approved"),

        ("rejected", "Rejected"),

    ]



    # Generic foreign key to any translatable object

    content_type: ForeignKey = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    object_id: PositiveIntegerField = models.PositiveIntegerField()

    content_object = GenericForeignKey("content_type", "object_id")



    # Field being translated

    field: CharField = models.CharField(

        max_length=100,

        help_text="Name of the field being translated (e.g., 'title', 'blocks')",

    )



    # Translation details

    source_locale: ForeignKey = models.ForeignKey(

        Locale,

        on_delete=models.CASCADE,

        related_name="source_translations",

        help_text="Locale of the source content",

    )

    target_locale: ForeignKey = models.ForeignKey(

        Locale,

        on_delete=models.CASCADE,

        related_name="target_translations",

        help_text="Locale being translated to",

    )



    # Content

    source_text: TextField = models.TextField(

        help_text="Original text in source locale"

    )

    target_text: TextField = models.TextField(

        blank=True, help_text="Translated text in target locale"

    )



    # Status and metadata

    status: CharField = models.CharField(

        max_length=20,

        choices=STATUS_CHOICES,

        default="missing",

        help_text="Translation status",

    )

    updated_by: ForeignKey = models.ForeignKey(

        User,

        on_delete=models.SET_NULL,

        null=True,

        blank=True,

        help_text="User who last updated this translation",

    )

    updated_at: DateTimeField = models.DateTimeField(auto_now=True)

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)



    class Meta:

        unique_together = [

            ("content_type", "object_id", "field", "source_locale", "target_locale")

        ]

        indexes = [

            models.Index(fields=["content_type", "object_id", "field"]),

            models.Index(fields=["target_locale", "status"]),

            models.Index(fields=["source_locale", "target_locale"]),

        ]

        ordering = ["-updated_at"]



    def __str__(self):  # noqa: C901

        target_text = f" -> {self.target_text}" if self.target_text else ""

        return f"{self.content_type.model}.{self.field} ({self.source_locale.code} → {self.target_locale.code}){target_text}"



    @property

    def model_label(self) -> str:  # noqa: C901

        """Get the model label for this translation unit."""

        # Type cast to help mypy understand the content_type attributes

        content_type = cast(ContentType, self.content_type)

        return f"{content_type.app_label}.{content_type.model}"



    @property

    def is_complete(self) -> bool:  # noqa: C901

        """Check if translation is complete (has target text and approved status)."""

        return bool(self.target_text) and self.status == "approved"



    @classmethod

    def upsert_unit(

        cls,

        obj,

        field: str,

        source_locale: Locale,

        target_locale: Locale,

        source_text: str,

        user: User | None = None,

    ) -> "TranslationUnit":



        Create or update a translation unit.



        Args:

            obj: The object being translated

            field: Field name being translated

            source_locale: Source locale

            target_locale: Target locale

            source_text: Current source text

            user: User making the update



        Returns:

            TranslationUnit instance



        content_type = ContentType.objects.get_for_model(obj)



        unit, created = cls.objects.get_or_create(

            content_type=content_type,

            object_id=obj.pk,

            field=field,

            source_locale=source_locale,

            target_locale=target_locale,

            defaults={

                "source_text": source_text,

                "updated_by": user,

                "status": "missing",

            },

        )



        # Update source text if changed

        if not created and unit.source_text != source_text:

            unit.source_text = source_text

            unit.updated_by = user

            # If source changed, mark translation as needing update

            if unit.status == "approved":

                unit.status = "needs_review"

            unit.save()



        return unit



    @classmethod

    def get_units_for_object(

        cls, obj, target_locale: Locale | None = None

    ) -> "QuerySet[TranslationUnit]":

        """Get all translation units for an object."""

        content_type = ContentType.objects.get_for_model(obj)

        qs = cls.objects.filter(content_type=content_type, object_id=obj.pk)



        if target_locale:

            qs = qs.filter(target_locale=target_locale)



        return qs



class UiMessage(models.Model):



    UI messages that need to be translated for the frontend.



    key: CharField = models.CharField(

        max_length=200,

        unique=True,

        help_text="Unique key for this message (e.g., 'auth.login.title')",

    )

    namespace: CharField = models.CharField(

        max_length=100,

        default="general",

        help_text="Namespace for organizing messages (e.g., 'auth', 'cms', 'general')",

    )

    description: TextField = models.TextField(

        blank=True, help_text="Description of when/where this message is used"

    )

    default_value: TextField = models.TextField(

        help_text="Default text in the default locale"

    )

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: DateTimeField = models.DateTimeField(auto_now=True)



    class Meta:

        ordering = ["namespace", "key"]

        indexes = [

            models.Index(fields=["namespace"]),

            models.Index(fields=["key"]),

        ]



    def __str__(self):  # noqa: C901

        return f"{self.namespace}.{self.key}"



class UiMessageTranslation(models.Model):



    Translations for UI messages.



    STATUS_CHOICES = [

        ("missing", "Missing"),

        ("draft", "Draft"),

        ("needs_review", "Needs Review"),

        ("approved", "Approved"),

    ]



    message: ForeignKey = models.ForeignKey(

        UiMessage, on_delete=models.CASCADE, related_name="translations"

    )

    locale: ForeignKey = models.ForeignKey(

        Locale, on_delete=models.CASCADE, related_name="ui_translations"

    )

    value: TextField = models.TextField(help_text="Translated message text")

    status: CharField = models.CharField(

        max_length=20,

        choices=STATUS_CHOICES,

        default="draft",

        help_text="Translation status",

    )

    updated_by: ForeignKey = models.ForeignKey(

        User,

        on_delete=models.SET_NULL,

        null=True,

        blank=True,

        help_text="User who last updated this translation",

    )

    updated_at: DateTimeField = models.DateTimeField(auto_now=True)

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)



    class Meta:

        unique_together = [("message", "locale")]

        indexes = [

            models.Index(fields=["locale", "status"]),

        ]

        ordering = ["message__namespace", "message__key"]



    def __str__(self):  # noqa: C901

        return f"{self.message.key} ({self.locale.code}): {self.value}"



class TranslationGlossary(models.Model):



    Translation glossary for consistent terminology across translations.



    term: CharField = models.CharField(

        max_length=200, help_text="Original term or phrase"

    )

    source_locale: ForeignKey = models.ForeignKey(

        Locale,

        on_delete=models.CASCADE,

        related_name="glossary_source_terms",

        help_text="Source locale of the term",

    )

    target_locale: ForeignKey = models.ForeignKey(

        Locale,

        on_delete=models.CASCADE,

        related_name="glossary_target_terms",

        help_text="Target locale for translation",

    )

    translation: CharField = models.CharField(

        max_length=200, help_text="Translated term or phrase"

    )

    context: TextField = models.TextField(

        blank=True, help_text="Context or usage notes for this translation"

    )

    category: CharField = models.CharField(

        max_length=100,

        default="general",

        help_text="Category for organizing terms (e.g., 'ui', 'technical', 'brand')",

    )

    is_verified: BooleanField = models.BooleanField(

        default=False,

        help_text="Whether this translation has been verified by a linguist",

    )

    created_by: ForeignKey = models.ForeignKey(

        User,

        on_delete=models.SET_NULL,

        null=True,

        related_name="glossary_created",

        help_text="User who created this glossary entry",

    )

    updated_by: ForeignKey = models.ForeignKey(

        User,

        on_delete=models.SET_NULL,

        null=True,

        related_name="glossary_updated",

        help_text="User who last updated this glossary entry",

    )

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: DateTimeField = models.DateTimeField(auto_now=True)



    class Meta:

        unique_together = [("term", "source_locale", "target_locale")]

        indexes = [

            models.Index(fields=["term"]),

            models.Index(fields=["source_locale", "target_locale"]),

            models.Index(fields=["category"]),

            models.Index(fields=["is_verified"]),

        ]

        ordering = ["term"]

        verbose_name_plural = "Translation glossaries"



    def __str__(self):  # noqa: C901

        return f"{self.term} ({self.source_locale.code} → {self.target_locale.code})"



class TranslationQueue(models.Model):



    Queue system for managing translation workflow and assignments.



    STATUS_CHOICES = [

        ("pending", "Pending"),

        ("assigned", "Assigned"),

        ("in_progress", "In Progress"),

        ("completed", "Completed"),

        ("rejected", "Rejected"),

    ]



    PRIORITY_CHOICES = [

        ("low", "Low"),

        ("medium", "Medium"),

        ("high", "High"),

        ("urgent", "Urgent"),

    ]



    translation_unit: OneToOneField = models.OneToOneField(

        TranslationUnit,

        on_delete=models.CASCADE,

        related_name="queue_item",

        help_text="Translation unit to be processed",

    )

    status: CharField = models.CharField(

        max_length=20,

        choices=STATUS_CHOICES,

        default="pending",

        help_text="Current status in the translation workflow",

    )

    priority: CharField = models.CharField(

        max_length=10,

        choices=PRIORITY_CHOICES,

        default="medium",

        help_text="Priority level for this translation task",

    )

    assigned_to: ForeignKey = models.ForeignKey(

        User,

        on_delete=models.SET_NULL,

        null=True,

        blank=True,

        related_name="assigned_translations",

        help_text="User assigned to translate this content",

    )

    deadline: DateTimeField = models.DateTimeField(

        null=True, blank=True, help_text="Deadline for completing this translation"

    )

    notes: TextField = models.TextField(

        blank=True, help_text="Internal notes about this translation task"

    )

    machine_translation_suggestion: TextField = models.TextField(

        blank=True, help_text="Machine translation suggestion for reference"

    )

    mt_service: CharField = models.CharField(

        max_length=50,

        blank=True,

        help_text="Machine translation service used (e.g., 'google', 'deepl', 'azure')",

    )

    word_count: PositiveIntegerField = models.PositiveIntegerField(

        default=0, help_text="Word count of source text for effort estimation"

    )

    estimated_hours: DecimalField = models.DecimalField(

        max_digits=5,

        decimal_places=2,

        null=True,

        blank=True,

        help_text="Estimated hours to complete this translation",

    )

    created_by: ForeignKey = models.ForeignKey(

        User,

        on_delete=models.SET_NULL,

        null=True,

        related_name="queued_translations",

        help_text="User who added this item to the queue",

    )

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: DateTimeField = models.DateTimeField(auto_now=True)



    class Meta:

        indexes = [

            models.Index(fields=["status", "priority", "-created_at"]),

            models.Index(fields=["assigned_to", "status"]),

            models.Index(fields=["deadline"]),

        ]

        ordering = ["-priority", "-created_at"]



    def __str__(self):  # noqa: C901

        return f"Queue: {self.translation_unit} ({self.status})"



    @property

    def is_overdue(self):  # noqa: C901

        """Check if the translation is overdue."""

        if not self.deadline:

            return False



        return timezone.now() > self.deadline



    def calculate_word_count(self):  # noqa: C901

        """Calculate approximate word count from source text."""

        if not self.translation_unit.source_text:

            return 0



        # Simple word count - could be enhanced with better text processing

        words = len(self.translation_unit.source_text.split())

        self.word_count = words

        return words



    def save(self, *args, **kwargs):  # noqa: C901

        """Override save to calculate word count if needed."""

        if not self.word_count:

            self.calculate_word_count()

        super().save(*args, **kwargs)



class TranslationHistory(models.Model):



    History tracking for translation changes and status updates.



    ACTION_CHOICES = [

        ("created", "Created"),

        ("updated", "Updated"),

        ("approved", "Approved"),

        ("rejected", "Rejected"),

        ("status_changed", "Status Changed"),

        ("assigned", "Assigned"),

    ]



    translation_unit: ForeignKey = models.ForeignKey(

        TranslationUnit,

        on_delete=models.CASCADE,

        related_name="history",

        help_text="Translation unit this history entry belongs to",

    )

    action: CharField = models.CharField(

        max_length=20, choices=ACTION_CHOICES, help_text="Type of action performed"

    )

    previous_status: CharField = models.CharField(

        max_length=20, blank=True, help_text="Previous status before the change"

    )

    new_status: CharField = models.CharField(

        max_length=20, blank=True, help_text="New status after the change"

    )

    previous_target_text: TextField = models.TextField(

        blank=True, help_text="Previous target text before the change"

    )

    new_target_text: TextField = models.TextField(

        blank=True, help_text="New target text after the change"

    )

    comment: TextField = models.TextField(

        blank=True, help_text="Optional comment explaining the change"

    )

    performed_by: ForeignKey = models.ForeignKey(

        User,

        on_delete=models.SET_NULL,

        null=True,

        help_text="User who performed this action",

    )

    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)



    class Meta:

        indexes = [

            models.Index(fields=["translation_unit", "-created_at"]),

            models.Index(fields=["action", "-created_at"]),

        ]

        ordering = ["-created_at"]

        verbose_name_plural = "Translation histories"



    def __str__(self):  # noqa: C901

        return f"{self.translation_unit} - {self.action} by {self.performed_by}"

