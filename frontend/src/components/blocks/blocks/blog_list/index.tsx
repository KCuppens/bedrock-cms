import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Calendar, User, Tag, ArrowRight } from 'lucide-react';
import type { BlockComponentProps } from '../../types';

interface BlogPost {
  id: number;
  title: string;
  slug: string;
  excerpt?: string;
  content?: string;
  featured_image?: string;
  author?: string;
  created_at: string;
  updated_at: string;
  status: string;
  categories?: Array<{ name: string; slug: string }>;
  tags?: Array<{ name: string; slug: string }>;
}

interface BlogListContent {
  title?: string;
  description?: string;
  posts?: BlogPost[];
  limit?: number;
  category?: string;
  tag?: string;
  ordering?: string;
  show_excerpt?: boolean;
  show_author?: boolean;
  show_date?: boolean;
  show_categories?: boolean;
  show_tags?: boolean;
  columns?: 1 | 2 | 3 | 4;
  cta_text?: string;
  cta_link?: string;
}

const BlogListBlock: React.FC<BlockComponentProps<BlogListContent>> = ({ 
  content = {},
  isEditing = false 
}) => {
  const {
    title = 'Latest Blog Posts',
    description,
    posts = [],
    show_excerpt = true,
    show_author = true,
    show_date = true,
    show_categories = true,
    show_tags = false,
    columns = 3,
    cta_text = 'Read More',
  } = content;

  const getGridCols = () => {
    switch (columns) {
      case 1: return 'grid-cols-1';
      case 2: return 'grid-cols-1 md:grid-cols-2';
      case 4: return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4';
      default: return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (isEditing && (!posts || posts.length === 0)) {
    return (
      <div className="p-8 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900">Blog List Block</h3>
          <p className="mt-2 text-sm text-gray-600">
            This block will display a list of blog posts
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Configure the block settings to select which posts to display
          </p>
        </div>
      </div>
    );
  }

  // Sample data for preview in editor
  const displayPosts = posts.length > 0 ? posts : (isEditing ? [
    {
      id: 1,
      title: 'Sample Blog Post 1',
      slug: 'sample-post-1',
      excerpt: 'This is a sample excerpt for the first blog post.',
      featured_image: 'https://via.placeholder.com/400x250',
      author: 'John Doe',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      status: 'published',
      categories: [{ name: 'Technology', slug: 'technology' }],
      tags: [{ name: 'React', slug: 'react' }]
    },
    {
      id: 2,
      title: 'Sample Blog Post 2',
      slug: 'sample-post-2',
      excerpt: 'This is a sample excerpt for the second blog post.',
      featured_image: 'https://via.placeholder.com/400x250',
      author: 'Jane Smith',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      status: 'published',
      categories: [{ name: 'Design', slug: 'design' }],
      tags: [{ name: 'UI/UX', slug: 'ui-ux' }]
    },
    {
      id: 3,
      title: 'Sample Blog Post 3',
      slug: 'sample-post-3',
      excerpt: 'This is a sample excerpt for the third blog post.',
      featured_image: 'https://via.placeholder.com/400x250',
      author: 'Bob Johnson',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      status: 'published',
      categories: [{ name: 'Business', slug: 'business' }],
      tags: [{ name: 'Strategy', slug: 'strategy' }]
    }
  ] : []);

  return (
    <div className="py-8">
      {(title || description) && (
        <div className="text-center mb-8">
          {title && <h2 className="text-3xl font-bold text-gray-900">{title}</h2>}
          {description && <p className="mt-2 text-lg text-gray-600">{description}</p>}
        </div>
      )}

      <div className={`grid ${getGridCols()} gap-6`}>
        {displayPosts.map((post) => (
          <Card key={post.id} className="overflow-hidden hover:shadow-lg transition-shadow">
            {post.featured_image && (
              <div className="aspect-video overflow-hidden bg-gray-100">
                <img 
                  src={post.featured_image} 
                  alt={post.title}
                  className="w-full h-full object-cover"
                />
              </div>
            )}
            <CardContent className="p-6">
              {show_categories && post.categories && post.categories.length > 0 && (
                <div className="flex gap-2 mb-2">
                  {post.categories.map((cat) => (
                    <Badge key={cat.slug} variant="secondary" className="text-xs">
                      {cat.name}
                    </Badge>
                  ))}
                </div>
              )}
              
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                {post.title}
              </h3>
              
              {show_excerpt && post.excerpt && (
                <p className="text-gray-600 mb-4 line-clamp-3">{post.excerpt}</p>
              )}
              
              <div className="flex items-center gap-4 text-sm text-gray-500">
                {show_author && post.author && (
                  <div className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    <span>{post.author}</span>
                  </div>
                )}
                {show_date && (
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    <span>{formatDate(post.created_at)}</span>
                  </div>
                )}
              </div>
              
              {show_tags && post.tags && post.tags.length > 0 && (
                <div className="flex gap-2 mt-3">
                  {post.tags.map((tag) => (
                    <Badge key={tag.slug} variant="outline" className="text-xs">
                      <Tag className="h-3 w-3 mr-1" />
                      {tag.name}
                    </Badge>
                  ))}
                </div>
              )}
              
              {cta_text && (
                <a 
                  href={`/blog/${post.slug}`}
                  className="inline-flex items-center gap-1 mt-4 text-primary hover:text-primary/80 font-medium"
                >
                  {cta_text}
                  <ArrowRight className="h-4 w-4" />
                </a>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {displayPosts.length === 0 && !isEditing && (
        <div className="text-center py-12">
          <p className="text-gray-500">No blog posts found</p>
        </div>
      )}
    </div>
  );
};

export default BlogListBlock;