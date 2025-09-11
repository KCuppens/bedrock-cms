import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  ArrowLeft, 
  Eye, 
  Save, 
  MoreHorizontal, 
  Globe, 
  Image, 
  Calendar,
  User,
  Tag as TagIcon,
  Folder,
  AlertTriangle,
  ExternalLink,
  Clock,
  BookOpen,
  Palette,
  Search as SearchIcon,
  Link,
  FileText,
  History
} from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";

const BlogPostEditor = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isNew = id === 'new';

  const [post, setPost] = useState({
    title: isNew ? "" : "Getting Started with Content Management",
    slug: isNew ? "" : "getting-started-cms",
    status: "draft" as "draft" | "published" | "scheduled",
    locale: "EN",
    category: "",
    tags: [] as string[],
    author: "John Doe",
    excerpt: "",
    content: "",
    heroImage: null,
    publishedAt: null,
    seoTitle: "",
    seoDescription: "",
    showToc: true,
    showAuthor: true,
    showDates: true,
    showShare: true
  });

  const [lastSaved, setLastSaved] = useState("2 minutes ago");
  const [wordCount, setWordCount] = useState(1247);
  const [readingTime, setReadingTime] = useState(5);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [categories, setCategories] = useState<Array<{id: number; name: string}>>([]);
  const [tags, setTags] = useState<Array<{id: number; name: string}>>([]);
  const { toast } = useToast();

  // Load post data and options on mount
  useEffect(() => {
    if (!isNew) {
      loadPost();
    }
    loadOptions();
  }, [id, isNew]);

  // Auto-save functionality
  useEffect(() => {
    if (!isNew && post.title && post.content) {
      const autoSaveTimer = setTimeout(async () => {
        try {
          await api.blog.posts.autosave(Number(id), {
            title: post.title,
            content: post.content,
            excerpt: post.excerpt
          });
          setLastSaved("Just now");
        } catch (error) {
          console.error('Auto-save failed:', error);
          // Don't show toast for auto-save failures to avoid spam
          setLastSaved("Auto-save failed");
        }
      }, 30000); // Auto-save every 30 seconds

      return () => clearTimeout(autoSaveTimer);
    }
  }, [post.title, post.content, post.excerpt, isNew, id]);

  // Update word count when content changes
  useEffect(() => {
    const words = post.content.trim() ? post.content.trim().split(/\s+/).length : 0;
    setWordCount(words);
    setReadingTime(Math.max(1, Math.ceil(words / 250))); // 250 words per minute average
  }, [post.content]);

  const loadPost = async () => {
    try {
      setLoading(true);
      const response = await api.blog.posts.get(Number(id));
      const postData = response.data || response;
      setPost({
        title: postData.title || '',
        slug: postData.slug || '',
        status: postData.status || 'draft',
        locale: postData.locale?.code || postData.locale || 'EN',
        category: postData.category?.name || '',
        tags: postData.tags?.map((tag: any) => tag.name) || [],
        author: postData.author?.first_name + ' ' + postData.author?.last_name || postData.author || 'Current User',
        excerpt: postData.excerpt || '',
        content: postData.content || '',
        heroImage: postData.social_image?.url || null,
        publishedAt: postData.published_at || null,
        seoTitle: postData.seo?.title || '',
        seoDescription: postData.seo?.description || '',
        showToc: true,
        showAuthor: true,
        showDates: true,
        showShare: true
      });
      setWordCount(postData.content ? postData.content.split(/\s+/).length : 0);
    } catch (error: any) {
      console.error('Failed to load blog post:', error);
      toast({
        title: "Error",
        description: error?.response?.data?.message || "Failed to load blog post. The blog feature may not be available.",
        variant: "destructive",
      });
      // Navigate back to blog posts list on error
      setTimeout(() => navigate('/admin/blog/posts'), 2000);
    } finally {
      setLoading(false);
    }
  };

  const loadOptions = async () => {
    try {
      const [categoriesResponse, tagsResponse] = await Promise.all([
        api.blog.categories.list().catch(() => ({ results: [] })),
        api.blog.tags.list().catch(() => ({ results: [] }))
      ]);
      setCategories(categoriesResponse.results || categoriesResponse.data || []);
      setTags(tagsResponse.results || tagsResponse.data || []);
    } catch (error: any) {
      console.error('Failed to load options:', error);
      // Don't fail the entire component if categories/tags fail to load
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const postData = {
        title: post.title,
        slug: post.slug,
        excerpt: post.excerpt,
        content: post.content,
        category: post.category,
        tags: post.tags,
        seo: {
          title: post.seoTitle,
          description: post.seoDescription
        },
        status: post.status
      };

      if (isNew) {
        const response = await api.blog.posts.create(postData);
        // Navigate to edit mode with the new post ID
        navigate(`/blog-posts/edit/${response.data.id}`, { replace: true });
        toast({
          title: "Success",
          description: "Blog post created successfully.",
        });
      } else {
        await api.blog.posts.update(Number(id), postData);
        toast({
          title: "Success",
          description: "Blog post saved successfully.",
        });
      }
      setLastSaved("Just now");
    } catch (error: any) {
      console.error('Failed to save blog post:', error);
      toast({
        title: "Error",
        description: error?.response?.data?.error || "Failed to save blog post.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    try {
      setSaving(true);
      if (post.status === 'published') {
        // If already published, just save the changes
        await handleSave();
      } else {
        // First save the post, then publish it
        await handleSave();
        if (!isNew) {
          const response = await api.blog.posts.publish(Number(id));
          setPost(prev => ({ ...prev, status: 'published', publishedAt: response.data.published_at }));
          toast({
            title: "Success",
            description: "Blog post published successfully.",
          });
        }
      }
    } catch (error: any) {
      console.error('Failed to publish blog post:', error);
      toast({
        title: "Error",
        description: "Failed to publish blog post.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published': return 'bg-green-100 text-green-800';
      case 'draft': return 'bg-yellow-100 text-yellow-800';
      case 'scheduled': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="flex">
          <Sidebar />
          <div className="flex-1 flex flex-col ml-72">
            <TopNavbar />
            <main className="flex-1 p-8">
              <div className="max-w-7xl mx-auto">
                <div className="flex items-center justify-center h-96">
                  <div className="flex items-center space-x-2">
                    <div className="w-6 h-6 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
                    <span>Loading blog post...</span>
                  </div>
                </div>
              </div>
            </main>
          </div>
        </div>
      </div>
    );
  }

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
                <div className="flex items-center gap-4">
                  <Button variant="ghost" size="sm" onClick={() => navigate('/blog-posts')}>
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back
                  </Button>
                  <div>
                    <h1 className="text-3xl font-bold text-foreground">
                      {isNew ? 'New Blog Post' : post.title}
                    </h1>
                    <p className="text-muted-foreground">
                      Collections &gt; Blog Posts &gt; {isNew ? 'New Post' : post.title}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between mb-6">
                <div></div>
                <div className="flex items-center gap-4">
                  <Badge className={getStatusColor(post.status)}>
                    {post.status}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    Last saved {lastSaved}
                  </span>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm">
                      <Eye className="w-4 h-4 mr-2" />
                      Preview
                    </Button>
                    <Button onClick={handleSave} disabled={saving} variant="outline">
                      <Save className="w-4 h-4 mr-2" />
                      {saving ? 'Saving...' : 'Save Draft'}
                    </Button>
                    <Button onClick={handlePublish} disabled={saving}>
                      <Save className="w-4 h-4 mr-2" />
                      {saving ? 'Publishing...' : (post.status === 'published' ? 'Update' : 'Publish')}
                    </Button>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>Duplicate</DropdownMenuItem>
                        <DropdownMenuItem>Move to Trash</DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem>Export JSON</DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              </div>

              <div className="flex" style={{ height: 'calc(100vh - 200px)' }}>
                {/* Main Content */}
                <div className="flex-1 pr-6">
              <Tabs defaultValue="content" className="h-full">
                <TabsList className="mb-6">
                  <TabsTrigger value="content">Content</TabsTrigger>
                  <TabsTrigger value="design">Design</TabsTrigger>
                  <TabsTrigger value="seo">SEO</TabsTrigger>
                  <TabsTrigger value="relations">Relations</TabsTrigger>
                  <TabsTrigger value="publishing">Publishing</TabsTrigger>
                  <TabsTrigger value="revisions">Revisions</TabsTrigger>
                </TabsList>

                <TabsContent value="content" className="space-y-6">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="title">Title</Label>
                        <Input 
                          id="title"
                          value={post.title}
                          onChange={(e) => setPost(prev => ({ ...prev, title: e.target.value }))}
                          placeholder="Enter post title..."
                        />
                      </div>
                      <div>
                        <Label htmlFor="slug">Slug</Label>
                        <Input 
                          id="slug"
                          value={post.slug}
                          onChange={(e) => setPost(prev => ({ ...prev, slug: e.target.value }))}
                          placeholder="post-slug"
                        />
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="excerpt">Excerpt</Label>
                        <Textarea 
                          id="excerpt"
                          value={post.excerpt}
                          onChange={(e) => setPost(prev => ({ ...prev, excerpt: e.target.value }))}
                          placeholder="Brief description of the post..."
                          rows={3}
                        />
                        <div className="text-sm text-muted-foreground mt-1">
                          {post.excerpt.length}/160 characters
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <Label>Hero Image</Label>
                    <div className="mt-2 border-2 border-dashed border-border rounded-lg p-8 text-center">
                      <Image className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                      <div className="text-sm text-muted-foreground">
                        <Button variant="outline" size="sm">
                          Choose Image
                        </Button>
                        <p className="mt-2">or drag and drop</p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="content">Content</Label>
                    <div className="mt-2 border rounded-lg">
                      <div className="border-b p-2 flex items-center gap-2 bg-muted/20">
                        <Button variant="ghost" size="sm">Bold</Button>
                        <Button variant="ghost" size="sm">Italic</Button>
                        <Button variant="ghost" size="sm">Link</Button>
                        <Separator orientation="vertical" className="h-6" />
                        <Button variant="ghost" size="sm">H1</Button>
                        <Button variant="ghost" size="sm">H2</Button>
                        <Button variant="ghost" size="sm">H3</Button>
                        <Separator orientation="vertical" className="h-6" />
                        <Button variant="ghost" size="sm">Quote</Button>
                        <Button variant="ghost" size="sm">Code</Button>
                        <Button variant="ghost" size="sm">Image</Button>
                      </div>
                      <Textarea 
                        id="content"
                        value={post.content}
                        onChange={(e) => setPost(prev => ({ ...prev, content: e.target.value }))}
                        placeholder="Start writing your post content..."
                        className="border-0 min-h-96 resize-none focus-visible:ring-0"
                      />
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                      <span>{wordCount.toLocaleString()} words</span>
                      <span>{readingTime} min read</span>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="design" className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Palette className="w-5 h-5" />
                        Presentation Options
                      </CardTitle>
                      <CardDescription>
                        Customize how this post appears on your site
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="flex items-center justify-between">
                          <Label htmlFor="show-toc">Show Table of Contents</Label>
                          <Switch 
                            id="show-toc"
                            checked={post.showToc}
                            onCheckedChange={(checked) => setPost(prev => ({ ...prev, showToc: checked }))}
                          />
                        </div>
                        <div className="flex items-center justify-between">
                          <Label htmlFor="show-author">Show Author</Label>
                          <Switch 
                            id="show-author"
                            checked={post.showAuthor}
                            onCheckedChange={(checked) => setPost(prev => ({ ...prev, showAuthor: checked }))}
                          />
                        </div>
                        <div className="flex items-center justify-between">
                          <Label htmlFor="show-dates">Show Dates</Label>
                          <Switch 
                            id="show-dates"
                            checked={post.showDates}
                            onCheckedChange={(checked) => setPost(prev => ({ ...prev, showDates: checked }))}
                          />
                        </div>
                        <div className="flex items-center justify-between">
                          <Label htmlFor="show-share">Show Share Buttons</Label>
                          <Switch 
                            id="show-share"
                            checked={post.showShare}
                            onCheckedChange={(checked) => setPost(prev => ({ ...prev, showShare: checked }))}
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="seo" className="space-y-6">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="seo-title">SEO Title</Label>
                        <Input 
                          id="seo-title"
                          value={post.seoTitle}
                          onChange={(e) => setPost(prev => ({ ...prev, seoTitle: e.target.value }))}
                          placeholder="Custom SEO title..."
                        />
                        <div className="text-sm text-muted-foreground mt-1">
                          {post.seoTitle.length}/60 characters
                        </div>
                      </div>
                      <div>
                        <Label htmlFor="seo-description">Meta Description</Label>
                        <Textarea 
                          id="seo-description"
                          value={post.seoDescription}
                          onChange={(e) => setPost(prev => ({ ...prev, seoDescription: e.target.value }))}
                          placeholder="Brief description for search engines..."
                          rows={3}
                        />
                        <div className="text-sm text-muted-foreground mt-1">
                          {post.seoDescription.length}/160 characters
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <Label>Search Preview</Label>
                      <div className="mt-2 p-4 border rounded-lg bg-muted/20">
                        <div className="text-blue-600 text-lg font-medium">
                          {post.seoTitle || post.title}
                        </div>
                        <div className="text-green-600 text-sm">
                          yoursite.com/blog/{post.slug}
                        </div>
                        <div className="text-sm text-muted-foreground mt-1">
                          {post.seoDescription || post.excerpt}
                        </div>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="relations" className="space-y-6">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <div>
                        <Label>Category</Label>
                        <Select value={post.category} onValueChange={(value) => setPost(prev => ({ ...prev, category: value }))}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select category..." />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="technology">Technology</SelectItem>
                            <SelectItem value="business">Business</SelectItem>
                            <SelectItem value="marketing">Marketing</SelectItem>
                            <SelectItem value="design">Design</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div>
                        <Label>Tags</Label>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {post.tags.map(tag => (
                            <Badge key={tag} variant="secondary">
                              {tag}
                            </Badge>
                          ))}
                          <Button variant="outline" size="sm">
                            <TagIcon className="w-4 h-4 mr-2" />
                            Add Tag
                          </Button>
                        </div>
                      </div>

                      <div>
                        <Label>Author</Label>
                        <Select value={post.author} onValueChange={(value) => setPost(prev => ({ ...prev, author: value }))}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="John Doe">John Doe</SelectItem>
                            <SelectItem value="Jane Smith">Jane Smith</SelectItem>
                            <SelectItem value="Mike Johnson">Mike Johnson</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div>
                      <Label>Related Posts</Label>
                      <div className="mt-2 space-y-2">
                        <div className="text-sm text-muted-foreground">
                          Drag to reorder related posts
                        </div>
                        <Button variant="outline" size="sm" className="w-full">
                          <SearchIcon className="w-4 h-4 mr-2" />
                          Search Posts
                        </Button>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="publishing" className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Calendar className="w-5 h-5" />
                        Publishing Schedule
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <Label>Publish Date & Time</Label>
                        <Input 
                          type="datetime-local"
                          className="mt-2"
                        />
                      </div>
                      <div>
                        <Label>Unpublish Date (Optional)</Label>
                        <Input 
                          type="datetime-local"
                          className="mt-2"
                        />
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="revisions" className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 p-4 border rounded-lg">
                      <History className="w-5 h-5 text-muted-foreground" />
                      <div className="flex-1">
                        <div className="font-medium">Current Version</div>
                        <div className="text-sm text-muted-foreground">
                          Last updated {lastSaved} by {post.author}
                        </div>
                      </div>
                      <Badge variant="outline">Current</Badge>
                    </div>
                    
                    <div className="flex items-center gap-2 p-4 border rounded-lg">
                      <History className="w-5 h-5 text-muted-foreground" />
                      <div className="flex-1">
                        <div className="font-medium">Initial Draft</div>
                        <div className="text-sm text-muted-foreground">
                          Created 2 days ago by {post.author}
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        View Diff
                      </Button>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
                </div>

                {/* Right Sidebar */}
                <div className="w-80 border-l border-border/20 p-4 bg-muted/20">
              <div className="space-y-6">
                <div>
                  <Label>Locale</Label>
                  <Select value={post.locale} onValueChange={(value) => setPost(prev => ({ ...prev, locale: value }))}>
                    <SelectTrigger className="mt-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="EN">🇺🇸 English</SelectItem>
                      <SelectItem value="ES">🇪🇸 Spanish</SelectItem>
                      <SelectItem value="FR">🇫🇷 French</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>Validation</Label>
                  <div className="mt-2 space-y-2">
                    <div className="flex items-center gap-2 text-sm text-red-600">
                      <AlertTriangle className="w-4 h-4" />
                      <span>SEO title missing</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-yellow-600">
                      <AlertTriangle className="w-4 h-4" />
                      <span>No featured image</span>
                    </div>
                  </div>
                </div>

                <div>
                  <Label>Usage</Label>
                  <div className="mt-2 space-y-2">
                    <div className="flex items-center gap-2 text-sm">
                      <ExternalLink className="w-4 h-4 text-muted-foreground" />
                      <span>Featured on Homepage</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <Link className="w-4 h-4 text-muted-foreground" />
                      <span>2 internal links</span>
                    </div>
                  </div>
                </div>
              </div>
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export default BlogPostEditor;