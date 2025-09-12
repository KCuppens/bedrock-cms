from typing import Any



from django.conf import settings



from apps.i18n.models import Locale



from .models import Page

from .seo import SeoSettings





def deep_merge_dicts(

    base: dict[str, Any], *overrides: dict[str, Any]

) -> dict[str, Any]:

    """Deep merge multiple dictionaries with later ones taking precedence."""

    result = base.copy()



    for override in overrides:

        if not override:



        for key, value in override.items():

            if (

                key in result

                and isinstance(result[key], dict)

                and isinstance(value, dict)

            ):

                result[key] = deep_merge_dicts(result[key], value)

            else:

                result[key] = value



    return result



def get_best_matching_seo_default(path: str, locale: Locale) -> dict | None:

    """Find the best matching SEO default for a path. Now returns None since section-based defaults were removed."""

    # Section-based SEO defaults were removed for simplicity

    # All SEO configuration is now handled at the global (per-locale) level

    return None



def resolve_seo(page: Page) -> dict[str, Any]:



    Resolve final SEO for a page by merging: Global → Section → Page

    Drafts get forced noindex.



    locale = page.locale



    # 1. Start with global SEO settings

    global_seo = {}

    try:

        seo_settings = SeoSettings.objects.get(locale=locale)

        global_seo = {

            "title_suffix": seo_settings.title_suffix,

            "description": seo_settings.default_description,

            "robots": seo_settings.robots_default,

            "jsonld": (

                seo_settings.jsonld_default.copy()

                if seo_settings.jsonld_default

                else []

            ),

        }



        # Add OG asset if available (will be implemented in Phase 3)

        # if hasattr(seo_settings, 'default_og_asset') and seo_settings.default_og_asset:

        #     global_seo['og'] = {

        #         'image': str(seo_settings.default_og_asset.file.url) if hasattr(seo_settings.default_og_asset, 'file') else None

        #     }



    except SeoSettings.DoesNotExist:

        # Default fallback

        global_seo = {"robots": "index,follow", "jsonld": []}



    # 2. Use page-level SEO (section-based defaults were removed)

    page_seo = page.seo.copy() if page.seo else {}



    # 3. Merge everything: Global → Page

    resolved_seo = deep_merge_dicts(global_seo, page_seo)



    # 5. Force noindex for drafts

    if page.status == "draft":

        resolved_seo["robots"] = "noindex,nofollow"



    # 6. Build final title with suffix

    if "title" not in resolved_seo:

        resolved_seo["title"] = page.title



    if resolved_seo.get("title_suffix"):

        resolved_seo["title"] = f"{resolved_seo['title']}{resolved_seo['title_suffix']}"



    # Clean up internal fields

    resolved_seo.pop("title_suffix", None)



    return resolved_seo



def generate_canonical_url(page: Page, base_url: str | None = None) -> str:

    """Generate canonical URL for a page."""

    if not base_url:

        base_url = getattr(settings, "CMS_SITEMAP_BASE_URL", "http://localhost:8000")



    return f"{base_url.rstrip('/')}{page.path}"



def generate_hreflang_alternates(

    page: Page, base_url: str | None = None

) -> list[dict[str, str]]:

    """Generate hreflang alternates for all locales of this page."""

    if not base_url:

        base_url = getattr(settings, "CMS_SITEMAP_BASE_URL", "http://localhost:8000")



    # Find all pages in the same group (same content, different locales)

    alternates = []



    # Get all pages with same group_id and active locales

    related_pages = Page.objects.filter(

        group_id=page.group_id, locale__is_active=True

    ).select_related("locale")



    for related_page in related_pages:

        # Safety check for locale

        if related_page.locale:

            alternates.append(

                {

                    "hreflang": related_page.locale.code,  # type: ignore[attr-defined]

                    "href": f"{base_url.rstrip('/')}{related_page.path}",

                }

            )



    return alternates



def generate_seo_links(page: Page, base_url: str | None = None) -> dict[str, Any]:

    """Generate canonical and hreflang data for a page."""

    return {

        "canonical": generate_canonical_url(page, base_url),

        "alternates": generate_hreflang_alternates(page, base_url),

    }

