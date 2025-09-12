import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plus, BookOpen, Eye, Edit, Filter, Search, MoreHorizontal, Calendar, User, Tag as TagIcon, Folder, ExternalLink, Copy, Trash2, Download, RefreshCw } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import React, { useState, useEffect, useCallback, useMemo, memo } from "react";
// TODO: Add virtualization with react-window once import issues are resolved
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import BlogPostModal from "@/components/modals/BlogPostModal";
import DeleteConfirmModal from "@/components/modals/DeleteConfirmModal";
import { api } from "@/lib/api.ts";
import { useToast } from "@/components/ui/use-toast";

interface BlogPost {
  id: string;
  title: string;
  slug: string;
  locale: number; // The locale ID
  locale_code: string; // The locale code
  category_name: string;
  tag_names: string[];
  status: 'draft' | 'published' | 'scheduled';
  updated_at: string;
  author: string;
  author_name: string;
  published_at?: string;
  excerpt: string;
  presentation_page?: string | null; // ID of the presentation page
}

// Memoized Post Row Component with performance optimizations
const PostRow = memo<{
  post: BlogPost;
  selectedPosts: string[];
  toggleSelectPost: (id: string) => void;
  openDrawer: (post: BlogPost) => void;
  handleEditPost: (post: BlogPost) => void;
  handlePublishToggle: (post: BlogPost) => void;
  handleDuplicatePost: (post: BlogPost) => void;
  handleDeletePost: (post: BlogPost) => void;
  getStatusColor: (status: string) => string;
  formatDate: (dateString: string) => string;
  renderTags: (tags: string[] | undefined) => React.ReactNode;
}>(({
  post,
  selectedPosts,
  toggleSelectPost,
  openDrawer,
  handleEditPost,
  handlePublishToggle,
  handleDuplicatePost,
  handleDeletePost,
  getStatusColor,
  formatDate,
  renderTags
}) => {
  const handleRowClick = useCallback(() => openDrawer(post), [post, openDrawer]);
  const handleStopPropagation = useCallback((e: React.MouseEvent) => e.stopPropagation(), []);
  const handleToggleSelect = useCallback(() => toggleSelectPost(post.id), [post.id, toggleSelectPost]);
  const handleEdit = useCallback(() => handleEditPost(post), [post, handleEditPost]);
  const handlePublish = useCallback(() => handlePublishToggle(post), [post, handlePublishToggle]);
  const handleDuplicate = useCallback(() => handleDuplicatePost(post), [post, handleDuplicatePost]);
  const handleDelete = useCallback(() => handleDeletePost(post), [post, handleDeletePost]);
  const handlePreview = useCallback(() => {
    window.open(`/blog/${post.slug}`, '_blank');
  }, [post.slug]);

  return (
    <TableRow
      key={post.id}
      className="cursor-pointer hover:bg-muted/30"
      onClick={handleRowClick}
    >
      <TableCell onClick={handleStopPropagation}>
        <Checkbox
          checked={selectedPosts.includes(post.id)}
          onCheckedChange={handleToggleSelect}
        />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <div>
            <div className="font-medium">{post.title}</div>
            <div className="text-sm text-muted-foreground">/{post.slug}</div>
          </div>
          <Badge variant="secondary" className="text-xs">
            {post.locale_code}
          </Badge>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant="outline">{post.category_name || '-'}</Badge>
      </TableCell>
      <TableCell>{renderTags(post.tag_names)}</TableCell>
      <TableCell>
        <Badge className={getStatusColor(post.status)}>
          {post.status}
        </Badge>
      </TableCell>
      <TableCell onClick={handleStopPropagation}>
        <Badge variant="outline" className="text-xs">
          {post.presentation_page ? 'Custom' : 'Default'}
        </Badge>
      </TableCell>
      <TableCell>
        <div className="text-sm">
          <div>{formatDate(post.updated_at)}</div>
          <div className="text-muted-foreground text-xs">by {post.author_name}</div>
        </div>
      </TableCell>
      <TableCell>
        {post.published_at ? formatDate(post.published_at) : '-'}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <User className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm">{post.author_name}</span>
        </div>
      </TableCell>
      <TableCell onClick={handleStopPropagation}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              <MoreHorizontal className="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="bg-card border border-border shadow-lg z-50">
            <DropdownMenuItem onClick={handleEdit}>
              <Edit className="w-4 h-4 mr-2" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handlePreview}>
              <Eye className="w-4 h-4 mr-2" />
              Preview
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handlePublish}>
              <RefreshCw className="w-4 h-4 mr-2" />
              {post.status === 'published' ? 'Unpublish' : 'Publish'}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleDuplicate}>
              <Copy className="w-4 h-4 mr-2" />
              Duplicate
            </DropdownMenuItem>
            <DropdownMenuItem className="text-destructive" onClick={handleDelete}>
              <Trash2 className="w-4 h-4 mr-2" />
              Move to Trash
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
});

PostRow.displayName = 'PostRow';

const BlogPosts = memo(() => {
  // Initialize hooks first
  const { toast } = useToast();

  // State declarations
  const [selectedPosts, setSelectedPosts] = useState<string[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedPost, setSelectedPost] = useState<BlogPost | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [localeFilter, setLocaleFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState<Array<{id: number; name: string}>>([]);
  const [locales, setLocales] = useState<Array<{code: string; name: string}>>([]);

  // Modal states
  const [blogPostModalOpen, setBlogPostModalOpen] = useState(false);
  const [blogPostModalMode, setBlogPostModalMode] = useState<'add' | 'edit'>('add');
  const [editingPost, setEditingPost] = useState<BlogPost | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [postToDelete, setPostToDelete] = useState<BlogPost | null>(null);

  // Callback functions
  const loadPosts = useCallback(async () => {
    try {
      setLoading(true);
      const params: any = {};

      if (searchQuery) params.search = searchQuery;
      if (statusFilter !== 'all') params.status = statusFilter;
      if (localeFilter !== 'all') params.locale = localeFilter;
      if (categoryFilter !== 'all') params.category = categoryFilter;

      const response = await api.blog.posts.list(params);
      setPosts(response.results || response.data || []);
    } catch (error: any) {
      console.error('Failed to load blog posts:', error);
      toast({
        title: "Error",
        description: "Failed to load blog posts. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [searchQuery, statusFilter, localeFilter, categoryFilter, toast]);

  const loadFilters = useCallback(async () => {
    try {
      // Load categories and locales for filters
      const [categoriesResponse, localesResponse] = await Promise.all([
        api.blog.categories.list(),
        api.i18n.locales.list()
      ]);

      setCategories(categoriesResponse.results || categoriesResponse.data || []);
      setLocales(localesResponse.results || localesResponse.data || []);
    } catch (error: any) {
      console.error('Failed to load filter options:', error);
    }
  }, []);

  // Load filters on mount
  useEffect(() => {
    loadFilters();
  }, [loadFilters]);

  // Load posts when filters change
  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  const handleAddPost = useCallback(() => {
    setBlogPostModalMode('add');
    setEditingPost(null);
    setBlogPostModalOpen(true);
  }, []);

  const handleEditPost = useCallback((post: BlogPost) => {
    setBlogPostModalMode('edit');
    setEditingPost(post);
    setBlogPostModalOpen(true);
  }, []);

  const handleDeletePost = useCallback((post: BlogPost) => {
    setPostToDelete(post);
    setDeleteModalOpen(true);
  }, []);

  const handleSavePost = useCallback(async (postData: Partial<BlogPost>) => {
    try {
      if (blogPostModalMode === 'add') {
        const response = await api.blog.posts.create(postData);
        setPosts(prev => [response.data, ...prev]);
        toast({
          title: "Success",
          description: "Blog post created successfully.",
        });
      } else if (editingPost) {
        const response = await api.blog.posts.update(Number(editingPost.id), postData);
        setPosts(prev => prev.map(post =>
          post.id === editingPost.id ? response.data : post
        ));
        toast({
          title: "Success",
          description: "Blog post updated successfully.",
        });
      }
      setBlogPostModalOpen(false);
    } catch (error: any) {
      console.error('Failed to save blog post:', error);
      toast({
        title: "Error",
        description: error?.response?.data?.error || "Failed to save blog post.",
        variant: "destructive",
      });
    }
  }, [blogPostModalMode, editingPost, toast]);

  const handleConfirmDelete = useCallback(async () => {
    if (postToDelete) {
      try {
        await api.blog.posts.delete(Number(postToDelete.id));
        setPosts(prev => prev.filter(post => post.id !== postToDelete.id));
        toast({
          title: "Success",
          description: "Blog post deleted successfully.",
        });
      } catch (error: any) {
        console.error('Failed to delete blog post:', error);
        toast({
          title: "Error",
          description: "Failed to delete blog post.",
          variant: "destructive",
        });
      } finally {
        setPostToDelete(null);
        setDeleteModalOpen(false);
      }
    }
  }, [postToDelete, toast]);

  const getStatusColor = useCallback((status: string) => {
    switch (status) {
      case 'published': return 'bg-green-100 text-green-800';
      case 'draft': return 'bg-yellow-100 text-yellow-800';
      case 'scheduled': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  }, []);

  const formatDate = useCallback((dateString: string) => {
    if (!dateString) return '-';

    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Invalid date';

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }, []);

  const toggleSelectPost = useCallback((postId: string) => {
    setSelectedPosts(prev =>
      prev.includes(postId)
        ? prev.filter(id => id !== postId)
        : [...prev, postId]
    );
  }, []);

  const selectAllPosts = useCallback(() => {
    setSelectedPosts(selectedPosts.length === posts.length ? [] : posts.map(p => p.id));
  }, [selectedPosts.length, posts]);

  const openDrawer = useCallback((post: BlogPost) => {
    setSelectedPost(post);
    setDrawerOpen(true);
  }, []);

  const handlePublishToggle = useCallback(async (post: BlogPost) => {
    try {
      if (post.status === 'published') {
        const response = await api.blog.posts.unpublish(Number(post.id));
        setPosts(prev => prev.map(p => p.id === post.id ? response.data : p));
        toast({
          title: "Success",
          description: "Blog post unpublished successfully.",
        });
      } else {
        const response = await api.blog.posts.publish(Number(post.id));
        setPosts(prev => prev.map(p => p.id === post.id ? response.data : p));
        toast({
          title: "Success",
          description: "Blog post published successfully.",
        });
      }
    } catch (error: any) {
      console.error('Failed to toggle publish status:', error);
      toast({
        title: "Error",
        description: "Failed to update publish status.",
        variant: "destructive",
      });
    }
  }, [toast]);

  const handleDuplicatePost = useCallback(async (post: BlogPost) => {
    try {
      const response = await api.blog.posts.duplicate(Number(post.id), {
        title: `${post.title} (Copy)`,
        locale: post.locale, // Use the locale ID
        copy_tags: true,
        copy_category: true
      });

      // Add the duplicated post to the list
      if (response.data) {
        setPosts(prev => [response.data, ...prev]);
        toast({
          title: "Success",
          description: `Blog post "${post.title}" duplicated successfully.`,
        });
      }
    } catch (error: any) {
      console.error('Failed to duplicate blog post:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to duplicate blog post.",
        variant: "destructive",
      });
    }
  }, [toast]);

  const renderTags = useCallback((tags: string[] | undefined) => {
    if (!tags || tags.length === 0) {
      return <span className="text-muted-foreground text-xs">No tags</span>;
    }

    const visibleTags = tags.slice(0, 3);
    const remainingCount = tags.length - 3;

    return (
      <div className="flex items-center gap-1 flex-wrap">
        {visibleTags.map(tag => (
          <Badge key={tag} variant="outline" className="text-xs">
            {tag}
          </Badge>
        ))}
        {remainingCount > 0 && (
          <Badge variant="secondary" className="text-xs">
            +{remainingCount}
          </Badge>
        )}
      </div>
    );
  }, []);

  // Memoized values - must be called unconditionally
  const localeOptions = useMemo(() =>
    locales.map(locale => (
      <SelectItem key={locale.code} value={locale.code}>
        {locale.code.toUpperCase()}
      </SelectItem>
    )), [locales]
  );

  const categoryOptions = useMemo(() =>
    categories.map(category => (
      <SelectItem key={category.id} value={category.name}>
        {category.name}
      </SelectItem>
    )), [categories]
  );

  const postRows = useMemo(() =>
    posts.map((post) => (
      <PostRow
        key={post.id}
        post={post}
        selectedPosts={selectedPosts}
        toggleSelectPost={toggleSelectPost}
        openDrawer={openDrawer}
        handleEditPost={handleEditPost}
        handlePublishToggle={handlePublishToggle}
        handleDuplicatePost={handleDuplicatePost}
        handleDeletePost={handleDeletePost}
        getStatusColor={getStatusColor}
        formatDate={formatDate}
        renderTags={renderTags}
      />
    )), [posts, selectedPosts, toggleSelectPost, openDrawer, handleEditPost,
        handlePublishToggle, handleDuplicatePost, handleDeletePost,
        getStatusColor, formatDate, renderTags]
  );

  return (
    <div className="min-h-screen">
      <div className="flex">
        <Sidebar />
        <div className="flex-1 flex flex-col ml-72">
          <TopNavbar />
          <main className="flex-1 p-8">
            <div className="max-w-7xl mx-auto">
              {/* Header */}
              <div className="mb-8">
                <h1 className="text-3xl font-bold text-foreground">Blog Posts</h1>
                <p className="text-muted-foreground">Create and manage your blog content</p>
              </div>

              <div className="flex items-center justify-between mb-6">
                <div></div>
                <div className="flex items-center gap-2">
                  {selectedPosts.length > 0 && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline">
                          Bulk Actions ({selectedPosts.length})
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent>
                        <DropdownMenuItem>
                          <RefreshCw className="w-4 h-4 mr-2" />
                          Publish
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <RefreshCw className="w-4 h-4 mr-2" />
                          Unpublish
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem>
                          <Folder className="w-4 h-4 mr-2" />
                          Assign Category
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <TagIcon className="w-4 h-4 mr-2" />
                          Add/Remove Tags
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem>
                          <Download className="w-4 h-4 mr-2" />
                          Export CSV
                        </DropdownMenuItem>
                        <DropdownMenuItem className="text-destructive">
                          <Trash2 className="w-4 h-4 mr-2" />
                          Move to Trash
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                  <Button onClick={handleAddPost}>
                    <Plus className="w-4 h-4 mr-2" />
                    New Post
                  </Button>
                </div>
              </div>

              {/* Filters */}
              <div className="flex items-center gap-4 p-4 bg-muted/20 rounded-lg mb-6">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search title, slug..."
                className="pl-10"
                value={searchQuery}
                onChange={useCallback((e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value), [])}
              />
            </div>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="published">Published</SelectItem>
                <SelectItem value="scheduled">Scheduled</SelectItem>
              </SelectContent>
            </Select>

            <Select value={localeFilter} onValueChange={setLocaleFilter}>
              <SelectTrigger className="w-24">
                <SelectValue placeholder="Locale" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                {localeOptions}
              </SelectContent>
            </Select>

            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categoryOptions}
              </SelectContent>
            </Select>

            <Button variant="outline" size="sm">
              <Calendar className="w-4 h-4 mr-2" />
              Date Range
            </Button>
              </div>

              {/* Table */}
              <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={selectedPosts.length === posts.length && posts.length > 0}
                      onCheckedChange={selectAllPosts}
                    />
                  </TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Tags</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Template</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead>Published</TableHead>
                  <TableHead>Author</TableHead>
                  <TableHead className="w-12">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center py-8">
                      <div className="flex items-center justify-center space-x-2">
                        <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
                        <span>Loading blog posts...</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : posts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center py-8 text-muted-foreground">
                      No blog posts found. Create your first blog post to get started.
                    </TableCell>
                  </TableRow>
                ) : (
                  postRows
                )}
              </TableBody>
            </Table>
              </div>
            </div>
          </main>
        </div>
      </div>

      {/* Right Drawer */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
            <SheetContent className="w-96">
              <SheetHeader>
                <SheetTitle>{selectedPost?.title}</SheetTitle>
                <SheetDescription>Post details and analytics</SheetDescription>
              </SheetHeader>

              {selectedPost && (
                <div className="mt-6 space-y-6">
                  {/* SEO Snippet */}
                  <div>
                    <h4 className="font-medium mb-2">SEO Preview</h4>
                    <div className="p-3 border rounded-lg bg-muted/20">
                      <div className="text-blue-600 text-sm font-medium">{selectedPost.title}</div>
                      <div className="text-green-600 text-xs">yoursite.com/blog/{selectedPost.slug}</div>
                      <div className="text-sm text-muted-foreground mt-1">{selectedPost.excerpt}</div>
                    </div>
                  </div>

                  {/* Inbound Links */}
                  <div>
                    <h4 className="font-medium mb-2">Inbound Links</h4>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm">
                        <ExternalLink className="w-4 h-4 text-muted-foreground" />
                        <span>Homepage → Featured Posts</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <ExternalLink className="w-4 h-4 text-muted-foreground" />
                        <span>Related Articles Sidebar</span>
                      </div>
                    </div>
                  </div>

                  {/* Revisions */}
                  <div>
                    <h4 className="font-medium mb-2">Recent Revisions</h4>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <div>
                          <div>Updated content</div>
                          <div className="text-muted-foreground text-xs">by {selectedPost.author_name}</div>
                        </div>
                        <Badge variant="outline" className="text-xs">Current</Badge>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <div>
                          <div>Initial draft</div>
                          <div className="text-muted-foreground text-xs">by {selectedPost.author_name}</div>
                        </div>
                        <span className="text-xs text-muted-foreground">2 days ago</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </SheetContent>
      </Sheet>

      {/* Modals */}
      <BlogPostModal
        open={blogPostModalOpen}
        onOpenChange={setBlogPostModalOpen}
        mode={blogPostModalMode}
        post={editingPost}
        onSave={handleSavePost}
      />

      <DeleteConfirmModal
        open={deleteModalOpen}
        onOpenChange={setDeleteModalOpen}
        title="Delete Blog Post"
        description="This action cannot be undone. This will permanently delete the blog post."
        itemName={postToDelete?.title || ''}
        onConfirm={handleConfirmDelete}
        warningMessage="All associated comments and analytics data will also be removed."
      />
    </div>
  );
});

BlogPosts.displayName = 'BlogPosts';
export default BlogPosts;
