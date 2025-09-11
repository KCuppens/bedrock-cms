import React, { Suspense } from 'react';
import { usePage } from '@/hooks/usePage';
import { useLocaleSync } from '@/hooks/useLocaleSync';
import PublicLayout from '@/components/PublicLayout';
import { DynamicBlocksRenderer } from '@/components/blocks/DynamicBlocksRenderer';
import { Helmet } from 'react-helmet-async';

// Lazy load the static homepage as fallback
const StaticHomePage = React.lazy(() => import('./StaticHomePage'));

/**
 * HomePage component that checks for a CMS page at "/" first,
 * and falls back to static homepage if none exists.
 */
const HomePage: React.FC = () => {
  // Sync URL locale with locale context
  useLocaleSync();
  
  const { page, loading, error } = usePage('/');

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    );
  }

  // If we found a CMS page at "/", render it dynamically
  if (page && !error) {
    const seoData = page.resolved_seo;
    
    return (
      <>
        {/* SEO Head with resolved data */}
        {seoData && (
          <Helmet>
            <title>{seoData.title}</title>
            {seoData.description && <meta name="description" content={seoData.description} />}
            {seoData.keywords && <meta name="keywords" content={seoData.keywords} />}
            {seoData.canonical_url && <link rel="canonical" href={seoData.canonical_url} />}
            
            {/* Open Graph */}
            <meta property="og:title" content={seoData.title} />
            {seoData.description && <meta property="og:description" content={seoData.description} />}
            <meta property="og:type" content={seoData.og_type || 'website'} />
            <meta property="og:url" content={window.location.href} />
            {seoData.og_image && <meta property="og:image" content={seoData.og_image} />}
            
            {/* Language */}
            <html lang={seoData.locale_code || 'en'} />
          </Helmet>
        )}

        {/* Render CMS page content with navigation and footer */}
        <PublicLayout
          title={seoData?.title || page.title}
          description={seoData?.description}
          keywords={seoData?.keywords}
          ogImage={seoData?.og_image}
          ogType={seoData?.og_type}
          canonicalUrl={seoData?.canonical_url}
          localeCode={seoData?.locale_code || 'en'}
          jsonLd={seoData?.json_ld}
        >
          <main 
            className="dynamic-homepage"
            data-page-id={page.id}
            data-page-status={page.status}
          >
            <DynamicBlocksRenderer 
              blocks={page.blocks || []} 
              className="homepage-blocks"
            />
            
            {/* Fallback if no blocks */}
            {(!page.blocks || page.blocks.length === 0) && (
              <div className="container mx-auto px-4 py-12">
                <h1 className="text-4xl font-bold mb-6">{page.title}</h1>
                <p>Welcome to our website!</p>
              </div>
            )}
          </main>
        </PublicLayout>
      </>
    );
  }

  // No CMS page found or error occurred - fall back to static homepage
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    }>
      <StaticHomePage />
    </Suspense>
  );
};

export default HomePage;