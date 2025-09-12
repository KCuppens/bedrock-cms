import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { format } from "date-fns";
import { Calendar as CalendarIcon, X, Plus, Image as ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api.ts";
import RichTextEditor from "@/components/ui/rich-text-editor";
import { MediaPicker } from "@/components/ui/media-picker";

interface BlogPost {
  id: string;
  title: string;
  slug: string;
  locale: string;
  category: string;
  tags: string[];
  status: 'draft' | 'published' | 'scheduled';
  updatedAt: string;
  updatedBy: string;
  publishedAt?: string | Date;
  scheduledPublishAt?: string;
  scheduledUnpublishAt?: string;
  author?: string;
  excerpt: string;
  content?: string;
  social_image?: string | number; // Can be asset ID (number) or URL (string)
}

interface MediaAsset {
  id: string;
  filename: string;
  file: string;
  kind: 'image' | 'video' | 'file';
  width?: number;
  height?: number;
  size: number;
  created_at: string;
  description?: string;
  tags?: string;
}

interface BlogPostModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: 'add' | 'edit';
  post?: BlogPost;
  onSave: (post: Partial<BlogPost>) => void;
}

const BlogPostModal = ({ open, onOpenChange, mode, post, onSave }: BlogPostModalProps) => {
  const [formData, setFormData] = useState<Partial<BlogPost>>({
    title: '',
    slug: '',
    locale: 'EN',
    category: '',
    tags: [],
    status: 'draft',
    excerpt: '',
    content: '',
    publishedAt: undefined,
    scheduledPublishAt: '',
    scheduledUnpublishAt: ''
  });

  const [newTag, setNewTag] = useState('');
  const [publishDate, setPublishDate] = useState<Date>();
  const [categories, setCategories] = useState<Array<{id: number; name: string}>>([]);
  const [locales, setLocales] = useState<Array<{id: number; code: string; name: string; is_active: boolean}>>([]);
  const [availableTags, setAvailableTags] = useState<Array<{id: number; name: string}>>([]);
  const [loading, setLoading] = useState(false);
  const [showMediaPicker, setShowMediaPicker] = useState(false);
  const [selectedImage, setSelectedImage] = useState<MediaAsset | null>(null);

  // Load options when modal opens
  useEffect(() => {
    if (open) {
      loadOptions();
    }
  }, [open]);

  const loadOptions = async () => {
    try {
      setLoading(true);
      const [categoriesResponse, localesResponse, tagsResponse] = await Promise.all([
        api.blog.categories.list(),
        api.i18n.locales.list(),
        api.blog.tags.list()
      ]);

      setCategories(categoriesResponse.results || categoriesResponse.data || []);

      // Filter for only active locales
      const allLocales = localesResponse.results || localesResponse.data || [];
      const activeLocales = allLocales.filter((locale: any) => locale.is_active);
      setLocales(activeLocales);

      setAvailableTags(tagsResponse.results || tagsResponse.data || []);
    } catch (error: any) {
      console.error('Failed to load options:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (mode === 'edit' && post) {
      // When editing, convert locale ID back to locale code for the form
      let localeCode = 'en'; // default
      if (post.locale) {
        if (typeof post.locale === 'object' && post.locale.code) {
          // If locale is an object with code property
          localeCode = post.locale.code.toLowerCase();
        } else if (typeof post.locale === 'string') {
          // If locale is already a string (code)
          localeCode = post.locale.toLowerCase();
        } else if (typeof post.locale === 'number') {
          // If locale is an ID, find the matching locale from the loaded list
          const foundLocale = locales.find(locale => locale.id === post.locale);
          if (foundLocale) {
            localeCode = foundLocale.code.toLowerCase();
          }
        }
      }

      const { author, ...postWithoutAuthor } = post;

      // Convert ISO dates to datetime-local format for input fields
      const formatDateTimeForInput = (isoString: string | undefined) => {
        if (!isoString) return '';
        return new Date(isoString).toISOString().slice(0, 16);
      };

      setFormData({
        ...postWithoutAuthor,
        content: post.content || '', // Ensure content is always a string
        locale: localeCode,
        scheduledPublishAt: formatDateTimeForInput(post.scheduledPublishAt),
        scheduledUnpublishAt: formatDateTimeForInput(post.scheduledUnpublishAt)
      });

      // Load selected image if social_image exists
      if (post.social_image) {
        loadSelectedImage(post.social_image);
      }
      if (post.publishedAt) {
        setPublishDate(typeof post.publishedAt === 'string' ? new Date(post.publishedAt) : post.publishedAt);
      }
    } else {
      setFormData({
        title: '',
        slug: '',
        locale: 'en',
        category: '',
        tags: [],
        status: 'draft',
        excerpt: '',
        content: '',
        publishedAt: undefined,
        scheduledPublishAt: '',
        scheduledUnpublishAt: ''
      });
      setPublishDate(undefined);
      setSelectedImage(null);
    }
  }, [mode, post, open, locales]); // Add locales to dependency array

  const loadSelectedImage = async (imageId: string | number) => {
    try {
      const response = await api.files.get(String(imageId));
      if (response?.data) {
        setSelectedImage({
          id: response.data.id,
          filename: response.data.filename || 'Unknown',
          file: response.data.file,
          kind: response.data.kind || (response.data.is_image ? 'image' : 'file'),
          width: response.data.width,
          height: response.data.height,
          size: response.data.size,
          created_at: response.data.created_at,
          description: response.data.alt_text || ''
        });
      }
    } catch (error) {
      console.error('Failed to load selected image:', error);
    }
  };

  const handleImageSelect = (asset: MediaAsset) => {
    setSelectedImage(asset);
    setFormData(prev => ({ ...prev, social_image: asset.id }));
  };

  const handleImageRemove = () => {
    setSelectedImage(null);
    setFormData(prev => ({ ...prev, social_image: undefined }));
  };

  const getImageUrl = (asset: MediaAsset): string => {
    if (asset.file.startsWith('http')) {
      return asset.file;
    }
    return `http://localhost:8000${asset.file}`;
  };

  const handleInputChange = (field: keyof BlogPost, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));

    // Auto-generate slug from title
    if (field === 'title' && value) {
      const slug = value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
      setFormData(prev => ({ ...prev, slug }));
    }
  };

  const addTag = () => {
    if (newTag.trim() && !formData.tags?.includes(newTag.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...(prev.tags || []), newTag.trim()]
      }));
      setNewTag('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags?.filter(tag => tag !== tagToRemove) || []
    }));
  };

  const handleSave = () => {
    const postData = { ...formData };

    // Convert datetime-local to ISO string for API
    const formatDateTimeForAPI = (dateTimeLocal: string | undefined) => {
      if (!dateTimeLocal) return undefined;
      return new Date(dateTimeLocal).toISOString();
    };

    // Handle scheduling fields
    if (formData.scheduledPublishAt) {
      postData.scheduledPublishAt = formatDateTimeForAPI(formData.scheduledPublishAt);
    }
    if (formData.scheduledUnpublishAt) {
      postData.scheduledUnpublishAt = formatDateTimeForAPI(formData.scheduledUnpublishAt);
    }

    // Ensure content is included in the save data
    if (formData.content) {
      postData.content = formData.content;
    }

    // Remove author field - backend sets it automatically
    delete postData.author;

    // Include social_image if selected
    if (selectedImage) {
      postData.social_image = selectedImage.id;
    }

    // Convert locale code to locale ID for the API
    if (formData.locale) {
      const selectedLocale = locales.find(locale => locale.code.toLowerCase() === formData.locale);
      if (selectedLocale) {
        postData.locale = selectedLocale.id;
      }
    }

    // Convert category name to category ID for the API
    if (formData.category) {
      const selectedCategory = categories.find(category => category.name === formData.category);
      if (selectedCategory) {
        postData.category = selectedCategory.id;
      } else {
        // If category name not found, set to null
        postData.category = null;
      }
    } else {
      postData.category = null;
    }

    // Convert tag names to tag IDs for the API
    if (formData.tags && formData.tags.length > 0) {
      const tagIds = formData.tags.map(tagName => {
        const foundTag = availableTags.find(tag => tag.name === tagName);
        return foundTag ? foundTag.id : null;
      }).filter(id => id !== null);
      postData.tags = tagIds;
    } else {
      postData.tags = [];
    }

    onSave(postData);
    onOpenChange(false);
  };

  const isValid = formData.title?.trim() &&
    formData.slug?.trim() &&
    (formData.status !== 'scheduled' || formData.scheduledPublishAt);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>
            {mode === 'add' ? 'Create New Blog Post' : 'Edit Blog Post'}
          </DialogTitle>
          <DialogDescription>
            {mode === 'add'
              ? 'Add a new blog post to your collection.'
              : 'Make changes to your blog post here.'
            }
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto px-1">
          <div className="grid gap-4 py-4 pr-2">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="title">Title *</Label>
              <Input
                id="title"
                value={formData.title || ''}
                onChange={(e) => handleInputChange('title', e.target.value)}
                placeholder="Enter post title..."
              />
            </div>
            <div>
              <Label htmlFor="slug">Slug *</Label>
              <Input
                id="slug"
                value={formData.slug || ''}
                onChange={(e) => handleInputChange('slug', e.target.value)}
                placeholder="post-slug"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label>Locale</Label>
              <Select value={formData.locale} onValueChange={(value) => handleInputChange('locale', value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {locales.map(locale => (
                    <SelectItem key={locale.code} value={locale.code.toLowerCase()}>
                      {locale.name} ({locale.code.toUpperCase()})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Category</Label>
              <Select value={formData.category} onValueChange={(value) => handleInputChange('category', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select category..." />
                </SelectTrigger>
                <SelectContent>
                  {categories.map(category => (
                    <SelectItem key={category.id} value={category.name}>
                      {category.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Status</Label>
              <Select value={formData.status} onValueChange={(value) => handleInputChange('status', value as any)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="published">Published</SelectItem>
                  <SelectItem value="scheduled">Scheduled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>


          <div>
            <Label htmlFor="excerpt">Excerpt</Label>
            <Textarea
              id="excerpt"
              value={formData.excerpt || ''}
              onChange={(e) => handleInputChange('excerpt', e.target.value)}
              placeholder="Brief description..."
              rows={3}
            />
            <div className="text-sm text-muted-foreground mt-1">
              {(formData.excerpt?.length || 0)}/160 characters
            </div>
          </div>

          <div>
            <Label htmlFor="content">Content</Label>
            <div className="mt-2">
              <RichTextEditor
                value={formData.content || ''}
                onChange={(content) => handleInputChange('content', content)}
                placeholder="Write your blog post content here..."
                minHeight={300}
              />
            </div>
          </div>

          <div>
            <Label>Social Image</Label>
            <div className="mt-2 space-y-2">
              {selectedImage ? (
                <div className="relative group border rounded-lg p-4 bg-muted/30">
                  <div className="flex items-center space-x-4">
                    <div className="flex-shrink-0">
                      <img
                        src={getImageUrl(selectedImage)}
                        alt={selectedImage.description || selectedImage.filename}
                        className="w-16 h-16 object-cover rounded-md"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">
                        {selectedImage.filename}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {selectedImage.width}×{selectedImage.height}
                      </p>
                    </div>
                    <div className="flex-shrink-0 flex space-x-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setShowMediaPicker(true)}
                      >
                        Change
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleImageRemove}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-6 text-center">
                  <div className="space-y-2">
                    <div className="mx-auto w-12 h-12 bg-muted rounded-lg flex items-center justify-center">
                      <ImageIcon className="w-6 h-6 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">No image selected</p>
                      <p className="text-xs text-muted-foreground">
                        Choose an image for social media sharing
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setShowMediaPicker(true)}
                    >
                      Select Image
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div>
            <Label>Tags</Label>
            <div className="flex flex-wrap gap-2 mt-2 mb-2">
              {formData.tags?.map(tag => (
                <Badge key={tag} variant="secondary" className="flex items-center gap-1">
                  {tag}
                  <X
                    className="w-3 h-3 cursor-pointer"
                    onClick={() => removeTag(tag)}
                  />
                </Badge>
              ))}
            </div>
            <div className="flex gap-2">
              <Select value={newTag} onValueChange={setNewTag}>
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Select existing tag or type new one..." />
                </SelectTrigger>
                <SelectContent>
                  {availableTags.map(tag => (
                    <SelectItem key={tag.id} value={tag.name}>
                      {tag.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                placeholder="Or type new tag..."
                className="flex-1"
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
              />
              <Button type="button" variant="outline" size="sm" onClick={addTag}>
                <Plus className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Scheduling Fields - Show when status is scheduled */}
          {formData.status === 'scheduled' && (
            <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
              <Label className="text-base font-medium flex items-center gap-2">
                <CalendarIcon className="w-4 h-4" />
                Scheduling Options
              </Label>

              <div className="space-y-2">
                <Label htmlFor="scheduledPublishAt">Publish Date & Time *</Label>
                <Input
                  id="scheduledPublishAt"
                  type="datetime-local"
                  value={formData.scheduledPublishAt}
                  onChange={(e) => handleInputChange('scheduledPublishAt', e.target.value)}
                  min={new Date().toISOString().slice(0, 16)}
                />
                <p className="text-xs text-muted-foreground">
                  When the post should be automatically published
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="scheduledUnpublishAt">Unpublish Date & Time (Optional)</Label>
                <Input
                  id="scheduledUnpublishAt"
                  type="datetime-local"
                  value={formData.scheduledUnpublishAt}
                  onChange={(e) => handleInputChange('scheduledUnpublishAt', e.target.value)}
                  min={formData.scheduledPublishAt || new Date().toISOString().slice(0, 16)}
                />
                <p className="text-xs text-muted-foreground">
                  When the post should be automatically unpublished (leave empty to keep published)
                </p>
              </div>
            </div>
          )}

          {/* Scheduling Fields for Published Posts - Allow scheduling unpublish */}
          {formData.status === 'published' && (
            <div className="space-y-4 p-4 border rounded-lg bg-muted/30">
              <Label className="text-base font-medium flex items-center gap-2">
                <CalendarIcon className="w-4 h-4" />
                Auto-Unpublish (Optional)
              </Label>

              <div className="space-y-2">
                <Label htmlFor="scheduledUnpublishAt">Unpublish Date & Time</Label>
                <Input
                  id="scheduledUnpublishAt"
                  type="datetime-local"
                  value={formData.scheduledUnpublishAt}
                  onChange={(e) => handleInputChange('scheduledUnpublishAt', e.target.value)}
                  min={new Date().toISOString().slice(0, 16)}
                />
                <p className="text-xs text-muted-foreground">
                  Schedule when this post should be automatically unpublished
                </p>
              </div>
            </div>
          )}
          </div>
        </div>

        <DialogFooter className="flex-shrink-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!isValid}>
            {mode === 'add' ? 'Create Post' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>

      {/* Media Picker Modal */}
      <MediaPicker
        open={showMediaPicker}
        onOpenChange={setShowMediaPicker}
        onSelect={handleImageSelect}
        selectedAssetId={selectedImage?.id}
        title="Select Social Media Image"
        description="Choose an image that will be used when sharing this blog post on social media platforms."
        allowedTypes={['image']}
      />
    </Dialog>
  );
};

export default BlogPostModal;
