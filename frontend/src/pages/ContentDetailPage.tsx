import React, { useMemo } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Helmet } from 'react-helmet-async';
import { api } from '@/lib/api';
import { DynamicBlocksRenderer } from '@/components/blocks/DynamicBlocksRenderer';
import NotFound from '@/pages/NotFound';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import PublicLayout from '@/components/PublicLayout';
import { useLocale } from '@/contexts/LocaleContext';

interface ContentData {
  id: string;
  title: string;
  content: string;
  excerpt?: string;
  [key: string]: any;
}

interface PresentationPage {
  id: string;
  title: string;
  blocks: Array<{
    type: string;
    props: Record<string, any>;
    id?: string;
    position?: number;
  }>;
}

interface ResolvedContent {
  content: ContentData;
  presentation_page: PresentationPage | null;
  resolution_source: 'individual' | 'category' | 'global_default' | 'fallback';
  seo: {
    title: string;
    description: string;
    og_image?: string;
    canonical_url: string;
  };
}

const ContentDetailPage: React.FC = () => {
  const location = useLocation();
  const { currentLocale } = useLocale();
  
  // Fetch resolved content and presentation
  const { data, isLoading, error } = useQuery<ResolvedContent>({
    queryKey: ['content-resolve', location.pathname, currentLocale],
    queryFn: async () => {
      const response = await api.get('/cms/pages/resolve_content/', {
        params: {
          path: location.pathname,
          locale: currentLocale
        }
      });
      return response.data;
    },
    retry: false,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
  
  // Inject content into presentation page blocks
  const enrichedBlocks = useMemo(() => {
    if (!data?.presentation_page?.blocks || !data?.content) {
      return [];
    }
    
    return data.presentation_page.blocks.map(block => {
      // Find detail blocks and inject content
      if (block.type.endsWith('_detail')) {
        return {
          ...block,
          props: {
            ...block.props,
            __injectedContent: data.content
          }
        };
      }
      return block;
    });
  }, [data]);
  
  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }
  
  // Error or not found
  if (error || !data?.content) {
    return <NotFound />;
  }
  
  // If no presentation page, use fallback layout
  if (!data.presentation_page) {
    return (
      <PublicLayout>
        <Helmet>
          <title>{data.seo.title}</title>
          <meta name="description" content={data.seo.description} />
          {data.seo.og_image && <meta property="og:image" content={data.seo.og_image} />}
          <link rel="canonical" href={data.seo.canonical_url} />
        </Helmet>
        
        <div className="container mx-auto px-4 py-8">
          <article className="prose prose-lg max-w-4xl mx-auto">
            <h1>{data.content.title}</h1>
            {data.content.excerpt && (
              <p className="lead text-xl text-gray-600">{data.content.excerpt}</p>
            )}
            <div dangerouslySetInnerHTML={{ __html: data.content.content }} />
          </article>
        </div>
      </PublicLayout>
    );
  }
  
  // Render with presentation page
  return (
    <PublicLayout>
      <Helmet>
        <title>{data.seo.title}</title>
        <meta name="description" content={data.seo.description} />
        {data.seo.og_image && <meta property="og:image" content={data.seo.og_image} />}
        <link rel="canonical" href={data.seo.canonical_url} />
      </Helmet>
      
      {/* Debug info in development */}
      {import.meta.env.DEV && (
        <div className="fixed bottom-4 right-4 z-50 bg-black/80 text-white text-xs p-2 rounded">
          <div>Template: {data.presentation_page.title}</div>
          <div>Source: {data.resolution_source}</div>
        </div>
      )}
      
      <DynamicBlocksRenderer blocks={enrichedBlocks} />
    </PublicLayout>
  );
};

export default ContentDetailPage;