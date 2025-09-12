import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Calendar, User, ArrowLeft, Share2, Bookmark } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import PublicLayout from '@/components/PublicLayout';

interface BlogPost {
  id: string;
  title: string;
  slug: string;
  content: string;
  excerpt: string;
  published_at: string;
  updated_at: string;
  author: {
    name: string;
    avatar?: string;
  };
  featured_image?: string;
  categories: Array<{
    id: string;
    name: string;
    slug: string;
  }>;
  tags: Array<{
    id: string;
    name: string;
    slug: string;
  }>;
  seo?: {
    title?: string;
    description?: string;
    og_image?: string;
  };
}

const BlogPost: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const { toast } = useToast();
  const [post, setPost] = useState<BlogPost | null>(null);
  const [relatedPosts, setRelatedPosts] = useState<BlogPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (slug) {
      loadPost(slug);
    }
  }, [slug]);

  useEffect(() => {
    // Update document title and meta description
    if (post) {
      document.title = post.seo?.title || `${post.title} | Blog`;

      // Update meta description
      const metaDescription = document.querySelector('meta[name="description"]');
      if (metaDescription) {
        metaDescription.setAttribute('content', post.seo?.description || post.excerpt);
      }

      // Update og:image
      const ogImage = document.querySelector('meta[property="og:image"]');
      if (ogImage && (post.seo?.og_image || post.featured_image)) {
        ogImage.setAttribute('content', post.seo?.og_image || post.featured_image || '');
      }
    }

    return () => {
      // Reset title when component unmounts
      document.title = 'Blog';
    };
  }, [post]);

  const loadPost = async (postSlug: string) => {
    try {
      setLoading(true);
      setNotFound(false);

      const response = await api.blog.posts.getBySlug(postSlug);
      const postData = response.data;

      if (!postData) {
        setNotFound(true);
        return;
      }

      setPost(postData);

      // Load related posts (same category, excluding current post)
      if (postData.categories.length > 0) {
        try {
          const relatedResponse = await api.blog.posts.list({
            category: postData.categories[0].slug,
            limit: 3,
            exclude: postData.id
          });
          setRelatedPosts(relatedResponse.data?.results || []);
        } catch (error) {
          console.error('Failed to load related posts:', error);
        }
      }

    } catch (error) {
      console.error('Failed to load blog post:', error);
      setNotFound(true);
    } finally {
      setLoading(false);
    }
  };

  const handleShare = async () => {
    const url = window.location.href;
    const title = post?.title || 'Blog Post';

    if (navigator.share) {
      try {
        await navigator.share({ title, url });
      } catch (error) {
        // User cancelled or error occurred
        copyToClipboard(url);
      }
    } else {
      copyToClipboard(url);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast({
        title: "Link copied!",
        description: "Post URL has been copied to clipboard.",
      });
    } catch (error) {
      toast({
        title: "Copy failed",
        description: "Unable to copy link to clipboard.",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (notFound || !post) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Post Not Found</h1>
          <p className="text-muted-foreground mb-6">
            The blog post you're looking for doesn't exist or has been moved.
          </p>
          <Button asChild>
            <Link to="/blog">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Blog
            </Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <PublicLayout
      title={post.title}
      description={post.excerpt}
      keywords={post.tags?.map(tag => tag.name).join(', ')}
      ogImage={post.featured_image}
      ogType="article"
      canonicalUrl={`${window.location.origin}/blog/${post.slug}`}
      jsonLd={[
        {
          "@context": "https://schema.org",
          "@type": "Article",
          "headline": post.title,
          "description": post.excerpt,
          "image": post.featured_image,
          "datePublished": post.published_at,
          "dateModified": post.updated_at || post.published_at,
          "author": {
            "@type": "Person",
            "name": post.author.name
          },
          "publisher": {
            "@type": "Organization",
            "name": "Bedrock CMS"
          }
        }
      ]}
    >
      <article className="py-8">
        <div className="container mx-auto px-4 max-w-4xl">
          {/* Back button */}
          <Button variant="ghost" asChild className="mb-6">
            <Link to="/blog">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Blog
            </Link>
          </Button>

          {/* Post header */}
          <header className="mb-8">
            {/* Categories */}
            <div className="flex flex-wrap gap-2 mb-4">
              {post.categories.map((category) => (
                <Badge key={category.id} variant="secondary">
                  <Link to={`/blog?category=${category.slug}`}>
                    {category.name}
                  </Link>
                </Badge>
              ))}
            </div>

            {/* Title */}
            <h1 className="text-4xl font-bold mb-4">{post.title}</h1>

            {/* Meta info */}
            <div className="flex flex-wrap items-center gap-6 text-muted-foreground mb-6">
              <div className="flex items-center gap-2">
                {post.author.avatar && (
                  <img
                    src={post.author.avatar}
                    alt={post.author.name}
                    className="w-8 h-8 rounded-full"
                  />
                )}
                <div className="flex items-center gap-1">
                  <User className="h-4 w-4" />
                  {post.author.name}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                {new Date(post.published_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </div>
              {post.updated_at !== post.published_at && (
                <div className="text-sm">
                  Updated: {new Date(post.updated_at).toLocaleDateString()}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleShare}>
                <Share2 className="h-4 w-4 mr-2" />
                Share
              </Button>
              <Button variant="outline" size="sm">
                <Bookmark className="h-4 w-4 mr-2" />
                Save
              </Button>
            </div>
          </header>

          {/* Featured image */}
          {post.featured_image && (
            <div className="mb-8">
              <img
                src={post.featured_image}
                alt={post.title}
                className="w-full rounded-lg shadow-lg"
              />
            </div>
          )}

          {/* Post content */}
          <div className="prose prose-lg max-w-none mb-12">
            <div dangerouslySetInnerHTML={{ __html: post.content }} />
          </div>

          {/* Tags */}
          {post.tags.length > 0 && (
            <div className="mb-8">
              <h3 className="font-semibold mb-3">Tags</h3>
              <div className="flex flex-wrap gap-2">
                {post.tags.map((tag) => (
                  <Badge key={tag.id} variant="outline">
                    <Link to={`/blog?tag=${tag.slug}`}>
                      #{tag.name}
                    </Link>
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </article>

      {/* Related posts */}
      {relatedPosts.length > 0 && (
        <section className="bg-muted/50 py-12">
          <div className="container mx-auto px-4 max-w-6xl">
            <h2 className="text-2xl font-bold mb-8">Related Posts</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {relatedPosts.map((relatedPost) => (
                <Card key={relatedPost.id} className="hover:shadow-lg transition-shadow">
                  {relatedPost.featured_image && (
                    <div className="aspect-video bg-muted overflow-hidden rounded-t-lg">
                      <img
                        src={relatedPost.featured_image}
                        alt={relatedPost.title}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}
                  <CardContent className="p-4">
                    <h3 className="font-semibold mb-2 line-clamp-2">
                      <Link
                        to={`/blog/${relatedPost.slug}`}
                        className="hover:text-primary transition-colors"
                      >
                        {relatedPost.title}
                      </Link>
                    </h3>
                    <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                      {relatedPost.excerpt}
                    </p>
                    <div className="text-xs text-muted-foreground">
                      {new Date(relatedPost.published_at).toLocaleDateString()}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>
      )}
    </PublicLayout>
  );
};

export default BlogPost;
