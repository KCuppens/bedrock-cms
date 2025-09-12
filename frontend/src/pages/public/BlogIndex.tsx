import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Link, useSearchParams } from 'react-router-dom';
import { Calendar, User, Search, Filter } from 'lucide-react';
import PublicLayout from '@/components/PublicLayout';

interface BlogPost {
  id: string;
  title: string;
  slug: string;
  excerpt: string;
  published_at: string;
  author: {
    name: string;
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
}

interface Category {
  id: string;
  name: string;
  slug: string;
  post_count?: number;
}

const BlogIndex: React.FC = () => {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    // Initialize from URL params
    const search = searchParams.get('search') || '';
    const category = searchParams.get('category') || '';
    const page = parseInt(searchParams.get('page') || '1');

    setSearchQuery(search);
    setSelectedCategory(category);
    setCurrentPage(page);
  }, [searchParams]);

  useEffect(() => {
    loadContent();
  }, [currentPage, searchQuery, selectedCategory]);

  useEffect(() => {
    loadCategories();
  }, []);

  const loadContent = async () => {
    try {
      setLoading(true);

      const params: any = {
        page: currentPage,
        limit: 12,
        status: 'published'
      };

      if (searchQuery) params.search = searchQuery;
      if (selectedCategory) params.category = selectedCategory;

      const response = await api.blog.posts.list(params);

      setPosts(response.data?.results || []);
      setTotalPages(Math.ceil((response.data?.count || 0) / 12));

    } catch (error) {
      console.error('Failed to load blog posts:', error);
      setPosts([]);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await api.blog.categories.list();
      setCategories(response.data?.results || []);
    } catch (error) {
      console.error('Failed to load categories:', error);
    }
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setCurrentPage(1);
    updateURL({ search: query, page: '1' });
  };

  const handleCategoryFilter = (categorySlug: string) => {
    setSelectedCategory(categorySlug);
    setCurrentPage(1);
    updateURL({ category: categorySlug, page: '1' });
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    updateURL({ page: page.toString() });
  };

  const updateURL = (updates: Record<string, string>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) {
        newParams.set(key, value);
      } else {
        newParams.delete(key);
      }
    });
    setSearchParams(newParams);
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedCategory('');
    setCurrentPage(1);
    setSearchParams({});
  };

  if (loading && posts.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <PublicLayout
      title="Blog"
      description="Discover our latest blog posts, insights, and updates."
      keywords="blog, articles, posts, insights, updates"
      ogType="website"
      canonicalUrl={`${window.location.origin}/blog`}
    >
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-primary/10 via-primary/5 to-background py-16">
        <div className="container mx-auto px-4">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold mb-4">Our Blog</h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Insights, tutorials, and thoughts from our team. Stay up to date with the latest trends and developments.
            </p>
          </div>
        </div>
      </section>

      <section className="py-12">
        <div className="container mx-auto px-4">
          {/* Filters */}
          <div className="flex flex-col lg:flex-row gap-6 mb-8">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder="Search posts..."
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                variant={selectedCategory === '' ? "default" : "outline"}
                size="sm"
                onClick={() => handleCategoryFilter('')}
              >
                All Categories
              </Button>
              {categories.map((category) => (
                <Button
                  key={category.id}
                  variant={selectedCategory === category.slug ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleCategoryFilter(category.slug)}
                >
                  {category.name}
                  {category.post_count && (
                    <Badge variant="secondary" className="ml-2 text-xs">
                      {category.post_count}
                    </Badge>
                  )}
                </Button>
              ))}
            </div>

            {(searchQuery || selectedCategory) && (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                <Filter className="h-4 w-4 mr-2" />
                Clear Filters
              </Button>
            )}
          </div>

          {/* Posts Grid */}
          {posts.length > 0 ? (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
                {posts.map((post) => (
                  <Card key={post.id} className="hover:shadow-lg transition-shadow h-full flex flex-col">
                    {post.featured_image && (
                      <div className="aspect-video bg-muted overflow-hidden rounded-t-lg">
                        <img
                          src={post.featured_image}
                          alt={post.title}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    )}
                    <CardHeader className="flex-none">
                      <div className="flex flex-wrap gap-1 mb-2">
                        {post.categories.slice(0, 2).map((category) => (
                          <Badge key={category.id} variant="secondary" className="text-xs">
                            {category.name}
                          </Badge>
                        ))}
                      </div>
                      <CardTitle className="line-clamp-2">
                        <Link
                          to={`/blog/${post.slug}`}
                          className="hover:text-primary transition-colors"
                        >
                          {post.title}
                        </Link>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 flex flex-col">
                      <p className="text-muted-foreground mb-4 line-clamp-3 flex-1">
                        {post.excerpt}
                      </p>
                      <div className="flex items-center text-sm text-muted-foreground gap-4 mt-auto">
                        <div className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          {new Date(post.published_at).toLocaleDateString()}
                        </div>
                        <div className="flex items-center gap-1">
                          <User className="h-4 w-4" />
                          {post.author.name}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center gap-2">
                  <Button
                    variant="outline"
                    disabled={currentPage === 1}
                    onClick={() => handlePageChange(currentPage - 1)}
                  >
                    Previous
                  </Button>

                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const pageNum = i + Math.max(1, currentPage - 2);
                    if (pageNum > totalPages) return null;

                    return (
                      <Button
                        key={pageNum}
                        variant={pageNum === currentPage ? "default" : "outline"}
                        onClick={() => handlePageChange(pageNum)}
                      >
                        {pageNum}
                      </Button>
                    );
                  })}

                  <Button
                    variant="outline"
                    disabled={currentPage === totalPages}
                    onClick={() => handlePageChange(currentPage + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <h3 className="text-xl font-semibold mb-2">No posts found</h3>
              <p className="text-muted-foreground mb-4">
                {searchQuery || selectedCategory
                  ? "Try adjusting your search or filter criteria."
                  : "There are no published posts yet."
                }
              </p>
              {(searchQuery || selectedCategory) && (
                <Button onClick={clearFilters}>Clear Filters</Button>
              )}
            </div>
          )}
        </div>
      </section>
    </PublicLayout>
  );
};

export default BlogIndex;
