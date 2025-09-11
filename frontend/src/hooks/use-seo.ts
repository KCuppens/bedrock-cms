import { useState, useEffect } from 'react';
import { api } from '@/lib/api.ts';

interface SEOSettings {
  id?: number;
  locale: number;
  locale_code: string;
  locale_name: string;
  title_suffix: string;
  default_title: string;
  default_description: string;
  default_keywords: string;
  default_og_title: string;
  default_og_description: string;
  default_og_type: string;
  default_og_site_name: string;
  default_og_asset?: string; // UUID of the file
  default_og_image_url?: string;
  default_twitter_card: string;
  default_twitter_site: string;
  default_twitter_creator: string;
  default_twitter_asset?: string; // UUID of the file
  default_twitter_image_url?: string;
  robots_default: string;
  canonical_domain: string;
  google_site_verification: string;
  bing_site_verification: string;
  meta_author: string;
  meta_generator: string;
  meta_viewport: string;
  facebook_app_id: string;
  jsonld_default: any[];
  organization_jsonld: any;
}

interface SEOMetaTags {
  title: string;
  description: string;
  keywords?: string;
  author?: string;
  robots?: string;
  canonical?: string;
  ogTitle: string;
  ogDescription: string;
  ogType: string;
  ogSiteName?: string;
  ogImage?: string;
  twitterCard: string;
  twitterSite?: string;
  twitterCreator?: string;
  twitterImage?: string;
  googleVerification?: string;
  bingVerification?: string;
  facebookAppId?: string;
  jsonLd?: any[];
}

export const useSEOSettings = (localeCode: string = 'en') => {
  const [settings, setSettings] = useState<SEOSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSEOSettings = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Try to get SEO settings for the locale
        const response = await api.seoSettings.getByLocale(localeCode);
        setSettings(response.data || response);
      } catch (err) {
        // If no settings found, use defaults
        console.warn(`No SEO settings found for locale ${localeCode}, using defaults`);
        setSettings({
          locale: 0,
          locale_code: localeCode,
          locale_name: localeCode.toUpperCase(),
          title_suffix: ' | Bedrock CMS',
          default_title: 'Bedrock CMS',
          default_description: 'Powerful content management system with multi-language support, media management, and SEO optimization.',
          default_keywords: 'cms, content management, website builder',
          default_og_title: 'Bedrock CMS',
          default_og_description: 'Powerful content management system with multi-language support, media management, and SEO optimization.',
          default_og_type: 'website',
          default_og_site_name: 'Bedrock CMS',
          default_twitter_card: 'summary_large_image',
          default_twitter_site: '',
          default_twitter_creator: '',
          robots_default: 'index,follow',
          canonical_domain: '',
          google_site_verification: '',
          bing_site_verification: '',
          meta_author: 'Bedrock CMS',
          meta_generator: 'Bedrock CMS',
          meta_viewport: 'width=device-width, initial-scale=1.0',
          facebook_app_id: '',
          jsonld_default: [],
          organization_jsonld: {}
        });
        setError(null);
      } finally {
        setLoading(false);
      }
    };

    fetchSEOSettings();
  }, [localeCode]);

  return { settings, loading, error };
};

export const useSEOMetaTags = (
  pageTitle?: string,
  pageDescription?: string,
  pageKeywords?: string,
  ogImage?: string,
  ogType?: string,
  canonicalUrl?: string,
  localeCode: string = 'en'
): SEOMetaTags | null => {
  const { settings, loading, error } = useSEOSettings(localeCode);

  if (loading || !settings) {
    return null;
  }

  // Build final meta title
  const finalTitle = pageTitle 
    ? `${pageTitle}${settings.title_suffix}` 
    : settings.default_title || 'Bedrock CMS';

  // Build final description
  const finalDescription = pageDescription || settings.default_description || '';

  // Build final keywords
  const finalKeywords = pageKeywords || settings.default_keywords || '';

  // Build OG title
  const finalOgTitle = pageTitle || settings.default_og_title || finalTitle;

  // Build OG description
  const finalOgDescription = pageDescription || settings.default_og_description || finalDescription;

  // Build canonical URL
  const finalCanonical = canonicalUrl || (settings.canonical_domain ? `${settings.canonical_domain}${window.location.pathname}` : undefined);

  // Build OG image URL
  const finalOgImage = ogImage || settings.default_og_image_url || '';

  // Build Twitter image URL
  const finalTwitterImage = ogImage || settings.default_og_image_url || '';

  return {
    title: finalTitle,
    description: finalDescription,
    keywords: finalKeywords,
    author: settings.meta_author,
    robots: settings.robots_default,
    canonical: finalCanonical,
    ogTitle: finalOgTitle,
    ogDescription: finalOgDescription,
    ogType: ogType || settings.default_og_type || 'website',
    ogSiteName: settings.default_og_site_name,
    ogImage: finalOgImage,
    twitterCard: settings.default_twitter_card || 'summary_large_image',
    twitterSite: settings.default_twitter_site,
    twitterCreator: settings.default_twitter_creator,
    twitterImage: finalTwitterImage,
    googleVerification: settings.google_site_verification,
    bingVerification: settings.bing_site_verification,
    facebookAppId: settings.facebook_app_id,
    jsonLd: settings.jsonld_default && settings.jsonld_default.length > 0 ? settings.jsonld_default : undefined
  };
};