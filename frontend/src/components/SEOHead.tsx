import React from 'react';
import { Helmet } from 'react-helmet-async';
import { useSEOMetaTags } from '@/hooks/use-seo';

interface SEOHeadProps {
  title?: string;
  description?: string;
  keywords?: string;
  ogImage?: string;
  ogType?: string;
  canonicalUrl?: string;
  localeCode?: string;
  jsonLd?: any[];
}

const SEOHead: React.FC<SEOHeadProps> = ({
  title,
  description,
  keywords,
  ogImage,
  ogType,
  canonicalUrl,
  localeCode = 'en',
  jsonLd
}) => {
  const metaTags = useSEOMetaTags(
    title,
    description,
    keywords,
    ogImage,
    ogType,
    canonicalUrl,
    localeCode
  );

  if (!metaTags) {
    // While loading, render minimal meta tags
    return (
      <Helmet>
        <title>{title || 'Bedrock CMS'}</title>
        {description && <meta name="description" content={description} />}
      </Helmet>
    );
  }

  return (
    <Helmet>
      {/* Basic Meta Tags */}
      <title>{metaTags.title}</title>
      {metaTags.description && <meta name="description" content={metaTags.description} />}
      {metaTags.keywords && <meta name="keywords" content={metaTags.keywords} />}
      {metaTags.author && <meta name="author" content={metaTags.author} />}
      {metaTags.robots && <meta name="robots" content={metaTags.robots} />}

      {/* Canonical URL */}
      {metaTags.canonical && <link rel="canonical" href={metaTags.canonical} />}

      {/* Open Graph Tags */}
      <meta property="og:title" content={metaTags.ogTitle} />
      {metaTags.ogDescription && <meta property="og:description" content={metaTags.ogDescription} />}
      <meta property="og:type" content={metaTags.ogType} />
      {metaTags.ogSiteName && <meta property="og:site_name" content={metaTags.ogSiteName} />}
      {metaTags.ogImage && <meta property="og:image" content={metaTags.ogImage} />}
      <meta property="og:url" content={window.location.href} />
      {metaTags.facebookAppId && <meta property="fb:app_id" content={metaTags.facebookAppId} />}

      {/* Twitter Card Tags */}
      <meta name="twitter:card" content={metaTags.twitterCard} />
      <meta name="twitter:title" content={metaTags.ogTitle} />
      {metaTags.ogDescription && <meta name="twitter:description" content={metaTags.ogDescription} />}
      {metaTags.twitterImage && <meta name="twitter:image" content={metaTags.twitterImage} />}
      {metaTags.twitterSite && <meta name="twitter:site" content={metaTags.twitterSite} />}
      {metaTags.twitterCreator && <meta name="twitter:creator" content={metaTags.twitterCreator} />}

      {/* Verification Tags */}
      {metaTags.googleVerification && <meta name="google-site-verification" content={metaTags.googleVerification} />}
      {metaTags.bingVerification && <meta name="msvalidate.01" content={metaTags.bingVerification} />}

      {/* JSON-LD Structured Data */}
      {metaTags.jsonLd && metaTags.jsonLd.map((jsonLdItem, index) => (
        <script key={index} type="application/ld+json">
          {JSON.stringify(jsonLdItem)}
        </script>
      ))}

      {/* Custom JSON-LD if provided */}
      {jsonLd && jsonLd.map((jsonLdItem, index) => (
        <script key={`custom-${index}`} type="application/ld+json">
          {JSON.stringify(jsonLdItem)}
        </script>
      ))}
    </Helmet>
  );
};

export default SEOHead;
