import React, { useMemo, useEffect } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { usePage, usePrefetchPage } from '@/hooks/usePage';
import { useLocaleSync } from '@/hooks/useLocaleSync';
import { useLocale } from '@/contexts/LocaleContext';
import { DynamicBlocksRenderer, usePrefetchBlocks } from '@/components/blocks/DynamicBlocksRenderer';
import PublicLayout from '@/components/PublicLayout';
import LoadingSpinner from '@/components/LoadingSpinner';
import NotFound from './NotFound';
import { Button } from '@/components/ui/button';
import { RefreshCw, Eye } from 'lucide-react';

/**
 * Performance-optimized dynamic page component that renders CMS pages.
 *
 * Features:
 * - SEO-optimized with resolved meta data
 * - Block-based content rendering
 * - Performance optimizations (prefetching, lazy loading, caching)
 * - Error boundaries and graceful degradation
 * - Preview mode support
 * - Accessibility features
 */
const DynamicPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { urlLocale, currentLocale } = useLocaleSync();
  const prefetchPage = usePrefetchPage();
  const prefetchBlocks = usePrefetchBlocks();

  // Extract path and preview token from URL, handling locale prefix
  const path = useMemo(() => {
    let actualPath = location.pathname;

    // If URL has locale prefix, remove it for API call
    if (urlLocale) {
      actualPath = location.pathname.replace(`/${urlLocale}`, '') || '/';
    }

    return actualPath;
  }, [location.pathname, urlLocale]);

  const searchParams = new URLSearchParams(location.search);
  const previewToken = searchParams.get('preview');
  const isPreviewMode = !!previewToken;

  // Fetch page data with optimizations
  const { page, loading, error, refetch, isStale } = usePage(path, {
    previewToken: previewToken || undefined,
    staleTime: isPreviewMode ? 0 : 5 * 60 * 1000, // No stale time for preview mode
    refetchOnWindowFocus: isPreviewMode, // Auto-refresh in preview mode
  });

  // Prefetch block components when page loads
  useEffect(() => {
    if (page?.blocks) {
      const blockTypes = page.blocks.map(block => block.type).filter(Boolean);
      if (blockTypes.length > 0) {
        prefetchBlocks(blockTypes);
      }
    }
  }, [page?.blocks, prefetchBlocks]);

  // Handle navigation prefetching (for performance)
  useEffect(() => {
    const handleMouseEnter = (e: Event) => {
      const link = (e.target as HTMLElement).closest('a[href]') as HTMLAnchorElement;
      if (link && link.href && link.href.startsWith(window.location.origin)) {
        const linkPath = new URL(link.href).pathname;
        if (linkPath !== path) {
          prefetchPage(linkPath);
        }
      }
    };

    // Add hover listeners to prefetch linked pages
    document.addEventListener('mouseenter', handleMouseEnter, { capture: true, passive: true });

    return () => {
      document.removeEventListener('mouseenter', handleMouseEnter, { capture: true });
    };
  }, [path, prefetchPage]);

  // Memoized SEO data extraction
  const seoData = useMemo(() => {
    if (!page?.resolved_seo) return null;

    const seo = page.resolved_seo;
    return {
      title: seo.title,
      description: seo.description,
      keywords: seo.keywords,
      canonicalUrl: seo.canonical_url || seo.page_url,
      ogImage: seo.og_image,
      ogType: seo.og_type || 'website',
      localeCode: seo.locale_code || currentLocale?.code || 'en',
      jsonLd: seo.jsonld || []
    };
  }, [page?.resolved_seo, currentLocale?.code]);

  // Handle loading states
  if (loading && !page) {
    return (
      <PublicLayout>
        <div className="flex items-center justify-center min-h-[50vh]">
          <LoadingSpinner />
        </div>
      </PublicLayout>
    );
  }

  // Handle error states
  if (error && !page) {
    // Check if it's a 404 error
    if (error.includes('not found') || error.includes('404')) {
      return <NotFound />;
    }

    // Other errors - show error page with retry
    return (
      <PublicLayout title="Error Loading Page">
        <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Unable to Load Page
            </h1>
            <p className="text-gray-600 mb-4">
              {error || 'An unexpected error occurred while loading this page.'}
            </p>
            <Button onClick={() => refetch()} className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4" />
              Retry
            </Button>
          </div>
        </div>
      </PublicLayout>
    );
  }

  // Handle 404 - page not found
  if (!page) {
    return <NotFound />;
  }

  // Check if page should be accessible
  if (page.status !== 'published' && !isPreviewMode) {
    return <NotFound />;
  }

  return (
    <>
      {/* SEO Head with resolved data */}
      {seoData && (
        <Helmet>
          <title>{seoData.title}</title>
          {seoData.description && <meta name="description" content={seoData.description} />}
          {seoData.keywords && <meta name="keywords" content={seoData.keywords} />}

          {/* Canonical URL */}
          {seoData.canonicalUrl && <link rel="canonical" href={seoData.canonicalUrl} />}

          {/* Open Graph */}
          <meta property="og:title" content={seoData.title} />
          {seoData.description && <meta property="og:description" content={seoData.description} />}
          <meta property="og:type" content={seoData.ogType} />
          <meta property="og:url" content={window.location.href} />
          {seoData.ogImage && <meta property="og:image" content={seoData.ogImage} />}

          {/* Language */}
          <html lang={seoData.localeCode} />

          {/* Hreflang alternates */}
          {page.seo_links?.alternates?.map((alternate, index) => (
            <link
              key={index}
              rel="alternate"
              hrefLang={alternate.hreflang}
              href={alternate.href}
            />
          ))}

          {/* JSON-LD structured data */}
          {seoData.jsonLd.map((jsonLdItem, index) => (
            <script key={index} type="application/ld+json">
              {JSON.stringify(jsonLdItem)}
            </script>
          ))}

          {/* Cache headers for performance */}
          {page.status === 'published' && !isPreviewMode && (
            <meta httpEquiv="Cache-Control" content="public, max-age=300" />
          )}
        </Helmet>
      )}

      {/* Preview mode banner */}
      {isPreviewMode && (
        <div className="bg-yellow-100 border-b border-yellow-200 px-4 py-2 text-center">
          <div className="flex items-center justify-center space-x-2 text-yellow-800">
            <Eye className="w-4 h-4" />
            <span className="font-medium">Preview Mode</span>
            <span className="text-sm">
              Viewing {page.status} content
            </span>
            {isStale && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => refetch()}
                className="ml-4"
              >
                Refresh
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Main page content with dynamic navigation and footer */}
      <PublicLayout
        title={seoData?.title || page.title}
        description={seoData?.description}
        keywords={seoData?.keywords}
        ogImage={seoData?.ogImage}
        ogType={seoData?.ogType}
        canonicalUrl={seoData?.canonicalUrl}
        localeCode={seoData?.localeCode}
        jsonLd={seoData?.jsonLd}
      >
        <main
          className="dynamic-page"
          data-page-id={page.id}
          data-page-status={page.status}
          data-locale={page.locale_code}
        >
          {/* Render blocks */}
          <DynamicBlocksRenderer
            blocks={page.blocks || []}
            className="page-blocks"
          />

          {/* Fallback content if no blocks */}
          {(!page.blocks || page.blocks.length === 0) && (
            <div className="container mx-auto px-4 py-12">
              <div className="max-w-3xl mx-auto">
                <h1 className="text-4xl font-bold mb-6">{page.title}</h1>
                <div className="prose prose-lg">
                  <p>This page is available but has no content blocks configured.</p>
                </div>
              </div>
            </div>
          )}
        </main>
      </PublicLayout>
    </>
  );
};

export default DynamicPage;
