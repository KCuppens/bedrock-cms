from django.db import models


from apps.i18n.models import Locale


class SeoSettings(models.Model):
    """Global SEO settings per locale."""

    locale: models.OneToOneField = models.OneToOneField(
        Locale, on_delete=models.CASCADE, related_name="seo_settings"
    )

    # Basic SEO

    title_suffix: models.CharField = models.CharField(
        max_length=120,
        blank=True,
        help_text="Appended to page titles (e.g., ' - My Site')",
    )

    default_title: models.CharField = models.CharField(
        max_length=120, blank=True, help_text="Default page title when none is set"
    )

    default_description: models.TextField = models.TextField(
        blank=True, help_text="Default meta description for pages without one"
    )

    default_keywords: models.CharField = models.CharField(
        max_length=255, blank=True, help_text="Default meta keywords (comma-separated)"
    )

    # Open Graph

    default_og_asset: models.ForeignKey = models.ForeignKey(
        "files.FileUpload",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Default Open Graph image",
        related_name="seo_defaults",
    )

    default_og_title: models.CharField = models.CharField(
        max_length=120, blank=True, help_text="Default Open Graph title"
    )

    default_og_description: models.TextField = models.TextField(
        blank=True, help_text="Default Open Graph description"
    )

    default_og_type: models.CharField = models.CharField(
        max_length=50, default="website", help_text="Default Open Graph type"
    )

    default_og_site_name: models.CharField = models.CharField(
        max_length=120, blank=True, help_text="Site name for Open Graph"
    )

    # Twitter Card

    default_twitter_card: models.CharField = models.CharField(
        max_length=50,
        default="summary_large_image",
        choices=[
            ("summary", "Summary"),
            ("summary_large_image", "Summary with Large Image"),
            ("app", "App"),
            ("player", "Player"),
        ],
        help_text="Default Twitter card type",
    )

    default_twitter_site: models.CharField = models.CharField(
        max_length=50, blank=True, help_text="Twitter @username for the site"
    )

    default_twitter_creator: models.CharField = models.CharField(
        max_length=50, blank=True, help_text="Twitter @username for content creator"
    )

    default_twitter_asset: models.ForeignKey = models.ForeignKey(
        "files.FileUpload",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Default Twitter card image",
        related_name="twitter_seo_defaults",
    )

    # Technical SEO

    robots_default: models.CharField = models.CharField(
        max_length=64, default="index,follow", help_text="Default robots directive"
    )

    canonical_domain: models.CharField = models.CharField(
        max_length=255,
        blank=True,
        help_text="Canonical domain for URLs (e.g., https://example.com)",
    )

    google_site_verification: models.CharField = models.CharField(
        max_length=255, blank=True, help_text="Google Search Console verification code"
    )

    bing_site_verification: models.CharField = models.CharField(
        max_length=255, blank=True, help_text="Bing Webmaster Tools verification code"
    )

    # Schema.org / JSON-LD

    jsonld_default = models.JSONField(
        default=list, help_text="Default JSON-LD structured data blocks"
    )

    organization_jsonld = models.JSONField(
        default=dict, blank=True, help_text="Organization schema.org data"
    )

    # Additional Meta Tags

    meta_author: models.CharField = models.CharField(
        max_length=120, blank=True, help_text="Default author meta tag"
    )

    meta_generator: models.CharField = models.CharField(
        max_length=120, blank=True, help_text="Generator meta tag"
    )

    meta_viewport: models.CharField = models.CharField(
        max_length=255,
        default="width=device-width, initial-scale=1.0",
        help_text="Viewport meta tag",
    )

    # Social Media

    facebook_app_id: models.CharField = models.CharField(
        max_length=50, blank=True, help_text="Facebook App ID"
    )

    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:

        verbose_name = "SEO Settings"

        verbose_name_plural = "SEO Settings"

    def __str__(self):

        return f"SEO Settings for {self.locale.name}"


# Removed SeoDefaults model - section-based SEO defaults removed for simplicity

# All SEO configuration is now handled at the global (per-locale) level
