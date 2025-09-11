import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

User = get_user_model()


class PageView(models.Model):
    """Track page views and visitor analytics"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(
        "cms.Page",
        on_delete=models.CASCADE,
        related_name="page_views",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="page_views",
    )

    # Visitor tracking
    session_id = models.CharField(max_length=40, db_index=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()

    # Page details
    url = models.URLField(max_length=1024)
    referrer = models.URLField(max_length=1024, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True)

    # Timing metrics
    load_time = models.PositiveIntegerField(null=True, blank=True)  # in milliseconds
    time_on_page = models.PositiveIntegerField(null=True, blank=True)  # in seconds

    # Geographic data (optional)
    country = models.CharField(max_length=2, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)

    # Device info
    device_type = models.CharField(
        max_length=20,
        choices=[
            ("desktop", "Desktop"),
            ("mobile", "Mobile"),
            ("tablet", "Tablet"),
            ("other", "Other"),
        ],
        default="other",
    )
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)

    # Timestamps
    viewed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["viewed_at"]),
            models.Index(fields=["page", "viewed_at"]),
            models.Index(fields=["session_id", "viewed_at"]),
            models.Index(fields=["user", "viewed_at"]),
            models.Index(fields=["ip_address", "viewed_at"]),
        ]
        ordering = ["-viewed_at"]

    def __str__(self):
        return f"View of {self.url} at {self.viewed_at}"


class UserActivity(models.Model):
    """Track user actions and interactions"""

    ACTION_TYPES = [
        ("login", "User Login"),
        ("logout", "User Logout"),
        ("page_create", "Page Created"),
        ("page_update", "Page Updated"),
        ("page_delete", "Page Deleted"),
        ("page_publish", "Page Published"),
        ("file_upload", "File Uploaded"),
        ("file_delete", "File Deleted"),
        ("search", "Search Query"),
        ("form_submit", "Form Submitted"),
        ("download", "File Downloaded"),
        ("click", "Link/Button Clicked"),
        ("error", "Error Occurred"),
        ("other", "Other Action"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")

    # Action details
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.CharField(max_length=255, blank=True)

    # Related object (generic foreign key)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    # Context data
    metadata = models.JSONField(default=dict, blank=True)

    # Request details
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=40, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["session_id", "created_at"]),
            models.Index(fields=["content_type", "object_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.get_action_display()} at {self.created_at}"


class ContentMetrics(models.Model):
    """Aggregate content performance metrics"""

    CONTENT_TYPES = [
        ("page", "Page"),
        ("blog_post", "Blog Post"),
        ("file", "File"),
        ("other", "Other"),
    ]

    # Content reference
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    # Metrics period
    date = models.DateField(db_index=True)
    content_category = models.CharField(
        max_length=20, choices=CONTENT_TYPES, default="other"
    )

    # Performance metrics
    views = models.PositiveIntegerField(default=0)
    unique_views = models.PositiveIntegerField(default=0)
    avg_time_on_content = models.PositiveIntegerField(default=0)  # in seconds
    bounce_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0,
    )

    # Engagement metrics
    shares = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    downloads = models.PositiveIntegerField(default=0)

    # SEO metrics
    search_impressions = models.PositiveIntegerField(default=0)
    search_clicks = models.PositiveIntegerField(default=0)
    avg_position = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["content_type", "object_id", "date"]
        indexes = [
            models.Index(fields=["date", "content_category"]),
            models.Index(fields=["content_type", "object_id", "date"]),
            models.Index(fields=["views", "date"]),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"Metrics for {self.content_object} on {self.date}"


class Assessment(models.Model):
    """Security and compliance assessments"""

    ASSESSMENT_TYPES = [
        ("security", "Security Assessment"),
        ("compliance", "Compliance Audit"),
        ("performance", "Performance Review"),
        ("accessibility", "Accessibility Check"),
        ("seo", "SEO Audit"),
    ]

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="scheduled"
    )

    # Assessment details
    target_url = models.URLField(blank=True, null=True)
    scope = models.JSONField(default=dict, blank=True)  # Define what's being assessed

    # Results
    score = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="low")
    findings = models.JSONField(default=list, blank=True)
    recommendations = models.TextField(blank=True)

    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_assessments",
    )
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_assessments"
    )

    # Timestamps
    scheduled_for = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["assessment_type", "status"]),
            models.Index(fields=["severity", "created_at"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["scheduled_for"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_assessment_type_display()})"


class Risk(models.Model):
    """Risk management and tracking"""

    RISK_CATEGORIES = [
        ("security", "Security Risk"),
        ("operational", "Operational Risk"),
        ("compliance", "Compliance Risk"),
        ("technical", "Technical Risk"),
        ("business", "Business Risk"),
    ]

    SEVERITY_LEVELS = [
        ("very_low", "Very Low"),
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("very_high", "Very High"),
    ]

    STATUS_CHOICES = [
        ("identified", "Identified"),
        ("assessed", "Assessed"),
        ("mitigated", "Mitigated"),
        ("accepted", "Accepted"),
        ("closed", "Closed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=RISK_CATEGORIES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="identified"
    )

    # Risk assessment
    probability = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Probability of occurrence (1-5)",
    )
    impact = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Impact severity (1-5)",
    )
    risk_score = models.PositiveIntegerField(default=1)  # probability * impact
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)

    # Mitigation
    mitigation_plan = models.TextField(blank=True)
    mitigation_deadline = models.DateField(null=True, blank=True)
    mitigation_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Assignment
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_risks",
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_risks",
    )

    # Related assessment
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risks",
    )

    # Timestamps
    identified_at = models.DateTimeField(auto_now_add=True)
    last_reviewed = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["category", "status"]),
            models.Index(fields=["severity", "identified_at"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["risk_score", "identified_at"]),
        ]
        ordering = ["-risk_score", "-identified_at"]

    def save(self, *args, **kwargs):
        # Calculate risk score
        self.risk_score = self.probability * self.impact

        # Determine severity based on risk score
        if self.risk_score <= 4:
            self.severity = "very_low"
        elif self.risk_score <= 8:
            self.severity = "low"
        elif self.risk_score <= 12:
            self.severity = "medium"
        elif self.risk_score <= 16:
            self.severity = "high"
        else:
            self.severity = "very_high"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} (Risk Score: {self.risk_score})"


class Threat(models.Model):
    """Security threat tracking and monitoring"""

    THREAT_TYPES = [
        ("malware", "Malware"),
        ("phishing", "Phishing"),
        ("ddos", "DDoS Attack"),
        ("brute_force", "Brute Force"),
        ("sql_injection", "SQL Injection"),
        ("xss", "Cross-Site Scripting"),
        ("csrf", "Cross-Site Request Forgery"),
        ("data_breach", "Data Breach"),
        ("insider", "Insider Threat"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("detected", "Detected"),
        ("investigating", "Investigating"),
        ("contained", "Contained"),
        ("resolved", "Resolved"),
        ("false_positive", "False Positive"),
    ]

    SEVERITY_LEVELS = [
        ("info", "Informational"),
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    threat_type = models.CharField(max_length=20, choices=THREAT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="detected")
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default="low")

    # Threat details
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    target_url = models.URLField(blank=True, null=True)
    attack_vector = models.CharField(max_length=255, blank=True)
    indicators = models.JSONField(default=list, blank=True)  # IOCs

    # Impact assessment
    affected_systems = models.JSONField(default=list, blank=True)
    data_compromised = models.BooleanField(default=False)
    service_disrupted = models.BooleanField(default=False)
    estimated_damage = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Response
    response_actions = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)

    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_threats",
    )
    reported_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reported_threats"
    )

    # Timestamps
    detected_at = models.DateTimeField(default=timezone.now, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["threat_type", "status"]),
            models.Index(fields=["severity", "detected_at"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["detected_at"]),
            models.Index(fields=["source_ip", "detected_at"]),
        ]
        ordering = ["-detected_at"]

    def __str__(self):
        return f"{self.title} ({self.get_severity_display()})"


class AnalyticsSummary(models.Model):
    """Daily/weekly/monthly analytics summaries for dashboard"""

    PERIOD_TYPES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    date = models.DateField(db_index=True)
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES)

    # Traffic metrics
    total_views = models.PositiveIntegerField(default=0)
    unique_visitors = models.PositiveIntegerField(default=0)
    returning_visitors = models.PositiveIntegerField(default=0)
    avg_session_duration = models.PositiveIntegerField(default=0)  # in seconds
    bounce_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # User activity
    new_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    user_actions = models.PositiveIntegerField(default=0)

    # Content metrics
    pages_published = models.PositiveIntegerField(default=0)
    files_uploaded = models.PositiveIntegerField(default=0)
    content_updates = models.PositiveIntegerField(default=0)

    # Security metrics
    threats_detected = models.PositiveIntegerField(default=0)
    risks_identified = models.PositiveIntegerField(default=0)
    assessments_completed = models.PositiveIntegerField(default=0)

    # Performance metrics
    avg_load_time = models.PositiveIntegerField(default=0)  # in milliseconds
    uptime_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["date", "period_type"]
        indexes = [
            models.Index(fields=["date", "period_type"]),
            models.Index(fields=["period_type", "date"]),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_period_type_display()} summary for {self.date}"
