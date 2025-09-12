import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, User, Tag, Folder, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/utils';

interface BlogPost {
  id: number;
  title: string;
  slug: string;
  excerpt: string;
  author: {
    id: number;
    name: string;
    avatar?: string;
  };
  category?: {
    id: number;
    name: string;
    slug: string;
    color: string;
  };
  tags: Array<{
    id: number;
    name: string;
    slug: string;
  }>;
  published_at: string;
  featured_image?: string;
  read_time?: number;
}

interface BlogListBlockProps {
  title?: string;
  subtitle?: string;
  layout?: 'list' | 'grid' | 'cards' | 'minimal';
  columns?: number;
  limit?: number;
  category?: string;
  tags?: string[];
  featured_only?: boolean;
  order_by?: 'published_at' | 'created_at' | 'title' | 'random';
  show_excerpt?: boolean;
  show_author?: boolean;
  show_date?: boolean;
  show_category?: boolean;
  show_tags?: boolean;
  show_read_more?: boolean;
  read_more_text?: string;
  show_pagination?: boolean;
}

const BlogListBlock: React.FC<BlogListBlockProps> = ({
  title,
  subtitle,
  layout = 'grid',
  columns = 3,
  limit = 9,
  category,
  tags,
  featured_only = false,
  order_by = 'published_at',
  show_excerpt = true,
  show_author = true,
  show_date = true,
  show_category = true,
  show_tags = false,
  show_read_more = true,
  read_more_text = 'Read more',
  show_pagination = true
}) => {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    fetchPosts();
  }, [currentPage, category, tags, featured_only, order_by, limit]);

  const fetchPosts = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: any = {
        page: currentPage,
        limit,
        status: 'published',
        ordering: order_by === 'published_at' ? '-published_at' :
                  order_by === 'created_at' ? '-created_at' :
                  order_by === 'title' ? 'title' : undefined
      };

      if (category) params.category = category;
      if (tags && tags.length > 0) params.tags = tags.join(',');
      if (featured_only) params.featured = true;

      const response = await api.request({
        method: 'GET',
        url: '/api/v1/blog/posts/',
        params
      });

      setPosts(response.results || []);
      setTotalPages(Math.ceil((response.count || 0) / limit));
    } catch (err: any) {
      console.error('Failed to fetch blog posts:', err);
      setError('Failed to load blog posts');
    } finally {
      setLoading(false);
    }
  };

  const getGridColumns = () => {
    switch (columns) {
      case 1: return 'grid-cols-1';
      case 2: return 'grid-cols-1 md:grid-cols-2';
      case 3: return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
      case 4: return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4';
      default: return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
    }
  };

  const renderPost = (post: BlogPost) => {
    switch (layout) {
      case 'cards':
        return (
          <Card key={post.id} className="h-full hover:shadow-lg transition-shadow">
            {post.featured_image && (
              <div className="aspect-video bg-muted">
                <img
                  src={post.featured_image}
                  alt={post.title}
                  className="w-full h-full object-cover rounded-t-lg"
                />
              </div>
            )}
            <CardHeader>
              <div className="flex items-center gap-2 mb-2">
                {show_category && post.category && (
                  <Badge
                    variant="secondary"
                    style={{ backgroundColor: post.category.color + '20', color: post.category.color }}
                  >
                    {post.category.name}
                  </Badge>
                )}
                {show_date && (
                  <span className="text-sm text-muted-foreground">
                    {formatDate(post.published_at)}
                  </span>
                )}
              </div>
              <CardTitle className="line-clamp-2">
                <Link to={`/blog/${post.slug}`} className="hover:underline">
                  {post.title}
                </Link>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {show_excerpt && (
                <p className="text-muted-foreground line-clamp-3 mb-4">
                  {post.excerpt}
                </p>
              )}
              {show_author && (
                <div className="flex items-center gap-2 mb-4">
                  <User className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    {post.author.name}
                  </span>
                </div>
              )}
              {show_tags && post.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-4">
                  {post.tags.map(tag => (
                    <Badge key={tag.id} variant="outline" className="text-xs">
                      {tag.name}
                    </Badge>
                  ))}
                </div>
              )}
              {show_read_more && (
                <Link to={`/blog/${post.slug}`}>
                  <Button variant="link" className="p-0">
                    {read_more_text} <ArrowRight className="ml-1 w-4 h-4" />
                  </Button>
                </Link>
              )}
            </CardContent>
          </Card>
        );

      case 'minimal':
        return (
          <div key={post.id} className="border-b pb-4 last:border-0">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="font-semibold mb-1">
                  <Link to={`/blog/${post.slug}`} className="hover:underline">
                    {post.title}
                  </Link>
                </h3>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  {show_date && (
                    <span>{formatDate(post.published_at)}</span>
                  )}
                  {show_category && post.category && (
                    <span>{post.category.name}</span>
                  )}
                </div>
              </div>
              {show_read_more && (
                <Link to={`/blog/${post.slug}`}>
                  <ArrowRight className="w-5 h-5 text-muted-foreground hover:text-primary" />
                </Link>
              )}
            </div>
          </div>
        );

      case 'list':
        return (
          <div key={post.id} className="flex gap-4 pb-6 border-b last:border-0">
            {post.featured_image && (
              <div className="w-48 h-32 bg-muted rounded-lg flex-shrink-0">
                <img
                  src={post.featured_image}
                  alt={post.title}
                  className="w-full h-full object-cover rounded-lg"
                />
              </div>
            )}
            <div className="flex-1">
              <h3 className="text-xl font-semibold mb-2">
                <Link to={`/blog/${post.slug}`} className="hover:underline">
                  {post.title}
                </Link>
              </h3>
              {show_excerpt && (
                <p className="text-muted-foreground mb-3">
                  {post.excerpt}
                </p>
              )}
              <div className="flex items-center gap-4 text-sm">
                {show_author && (
                  <span className="text-muted-foreground">
                    By {post.author.name}
                  </span>
                )}
                {show_date && (
                  <span className="text-muted-foreground">
                    {formatDate(post.published_at)}
                  </span>
                )}
                {show_category && post.category && (
                  <Badge variant="secondary">
                    {post.category.name}
                  </Badge>
                )}
              </div>
            </div>
          </div>
        );

      default: // grid
        return renderPost({ ...post }); // Reuse cards layout for grid
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {title && <Skeleton className="h-8 w-48" />}
        <div className={`grid gap-6 ${getGridColumns()}`}>
          {[...Array(limit)].map((_, i) => (
            <Skeleton key={i} className="h-64" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (posts.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">No blog posts found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {(title || subtitle) && (
        <div className="text-center mb-8">
          {title && <h2 className="text-3xl font-bold mb-2">{title}</h2>}
          {subtitle && <p className="text-muted-foreground">{subtitle}</p>}
        </div>
      )}

      <div className={layout === 'list' || layout === 'minimal' ? 'space-y-6' : `grid gap-6 ${getGridColumns()}`}>
        {posts.map(post => renderPost(post))}
      </div>

      {show_pagination && totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          <Button
            variant="outline"
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </Button>
          <span className="flex items-center px-4">
            Page {currentPage} of {totalPages}
          </span>
          <Button
            variant="outline"
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
};

export default BlogListBlock;
