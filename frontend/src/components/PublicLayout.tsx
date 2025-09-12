import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import SEOHead from '@/components/SEOHead';
import Navigation from '@/components/public/Navigation';
import Footer from '@/components/public/Footer';
import { useSiteSettings } from '@/hooks/useSiteSettings';

interface PublicLayoutProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
  keywords?: string;
  ogImage?: string;
  ogType?: string;
  canonicalUrl?: string;
  localeCode?: string;
  jsonLd?: any[];
}

const PublicLayout: React.FC<PublicLayoutProps> = ({
  children,
  title,
  description,
  keywords,
  ogImage,
  ogType,
  canonicalUrl,
  localeCode = 'en',
  jsonLd
}) => {
  const { siteSettings, loading, error } = useSiteSettings();

  // Debug logging
  console.log('🏗️ [PublicLayout] Render - loading:', loading, 'error:', error);
  console.log('🏗️ [PublicLayout] siteSettings:', siteSettings);
  console.log('🏗️ [PublicLayout] siteSettings type:', typeof siteSettings);
  console.log('🏗️ [PublicLayout] siteSettings keys:', siteSettings ? Object.keys(siteSettings) : 'null');
  console.log('🏗️ [PublicLayout] siteSettings?.navigation:', siteSettings?.navigation);
  console.log('🏗️ [PublicLayout] siteSettings?.footer:', siteSettings?.footer);

  // Show loading state while fetching site settings
  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <SEOHead
          title={title}
          description={description}
          keywords={keywords}
          ogImage={ogImage}
          ogType={ogType}
          canonicalUrl={canonicalUrl}
          localeCode={localeCode}
          jsonLd={jsonLd}
        />

        {/* Simple header while loading */}
        <header className="sticky top-0 z-50 w-full border-b bg-background/95">
          <div className="container mx-auto px-4">
            <div className="flex h-16 items-center justify-between">
              <Link to="/" className="flex items-center gap-2">
                <img
                  src="/bedrock-logo.png"
                  alt="Bedrock"
                  className="h-8 w-auto"
                />
              </Link>
              <div className="animate-pulse h-4 w-32 bg-gray-200 rounded"></div>
            </div>
          </div>
        </header>

        <main>{children}</main>

        {/* Simple footer while loading */}
        <footer className="border-t bg-muted/50">
          <div className="container mx-auto px-4 py-12">
            <div className="animate-pulse space-y-4">
              <div className="h-4 w-48 bg-gray-200 rounded"></div>
              <div className="h-3 w-32 bg-gray-200 rounded"></div>
            </div>
          </div>
        </footer>
      </div>
    );
  }

  // Default navigation and footer if site settings fail to load
  const defaultNavigation = [
    { id: 1, title: 'Home', slug: 'home', path: '/', position: 0 },
    { id: 2, title: 'Blog', slug: 'blog', path: '/blog', position: 1 },
  ];

  const defaultFooter = [
    { id: 1, title: 'About', slug: 'about', path: '/about', position: 0 },
    { id: 2, title: 'Contact', slug: 'contact', path: '/contact', position: 1 },
  ];

  const navigation = siteSettings?.navigation || defaultNavigation;
  const footerItems = siteSettings?.footer || defaultFooter;
  const siteName = 'Bedrock CMS';
  const homeUrl = siteSettings?.homepage?.path || '/';

  // Debug which navigation and footer is being used
  console.log('🧭 [PublicLayout] Using navigation:', navigation);
  console.log('🧭 [PublicLayout] Is using default navigation?', !siteSettings?.navigation);
  console.log('🧭 [PublicLayout] Navigation items count:', navigation.length);
  console.log('🦶 [PublicLayout] Using footer:', footerItems);
  console.log('🦶 [PublicLayout] Is using default footer?', !siteSettings?.footer);
  console.log('🦶 [PublicLayout] Footer items count:', footerItems.length);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <SEOHead
        title={title}
        description={description}
        keywords={keywords}
        ogImage={ogImage}
        ogType={ogType}
        canonicalUrl={canonicalUrl}
        localeCode={localeCode}
        jsonLd={jsonLd}
      />

      {/* Dynamic Navigation */}
      <Navigation
        menuItems={navigation}
        siteName={siteName}
        homeUrl={homeUrl}
      />

      {/* Main Content */}
      <main className="flex-1">{children}</main>

      {/* Dynamic Footer */}
      <Footer
        footerItems={footerItems}
        siteName={siteName}
        homeUrl={homeUrl}
      />
    </div>
  );
};

export default PublicLayout;
