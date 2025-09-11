import { useState, useCallback, useEffect, useMemo } from "react";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { useAutosave } from "@/hooks/useAutosave";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/api.ts";
import { useToast } from "@/hooks/use-toast";
import { DynamicBlockRenderer } from "@/components/blocks/DynamicBlockRenderer";
import { Page, Block as ApiBlock } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  Plus,
  Eye,
  Globe,
  Copy,
  Download,
  Settings,
  GripVertical,
  Edit,
  Trash2,
  Save,
  Loader2,
  Undo,
  Redo,
  Layout,
  Type,
  Image,
  Star,
  Grid,
  Columns,
  Megaphone,
  HelpCircle,
  X,
  Search,
  History,
  Filter,
  Calendar,
  User,
  Tag,
  Archive,
  ListFilter,
  LayoutGrid,
  List,
  MoreHorizontal,
  Clock,
  Share2,
  AlertTriangle,
  Bookmark
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

export interface Block {
  id: string;
  type: 'hero' | 'richtext' | 'image' | 'gallery' | 'columns' | 'cta' | 'faq' | 'collection_list' | 'content_detail';
  content: any;
  props?: any; // For content_detail block
  position: number;
}

export interface PageData {
  id: string;
  title: string;
  slug: string;
  status: 'draft' | 'published' | 'scheduled';
  locale: string;
  parent?: string;
  blocks: Block[];
  isPresentationPage?: boolean;
  contentType?: 'blog.blogpost' | 'page.page';
  inMainMenu: boolean;
  inFooter: boolean;
  isHomepage: boolean;
  seo: {
    title?: string;
    description?: string;
    ogImage?: string;
    canonical?: string;
    noindex: boolean;
    nofollow: boolean;
    jsonLd?: string;
  };
  schedule?: {
    publishAt?: string;
    unpublishAt?: string;
  };
}

const mockPage: PageData = {
  id: "1",
  title: "Blog Post Detail Template",
  slug: "blog-post-detail",
  status: "draft",
  locale: "en",
  isPresentationPage: true,
  contentType: "blog.blogpost",
  inMainMenu: false,
  inFooter: false,
  isHomepage: false,
  blocks: [
    {
      id: "block-1",
      type: "hero",
      content: {
        title: "Blog Article",
        subtitle: "Insights and stories from our team"
      },
      position: 0
    },
    {
      id: "block-2", 
      type: "content_detail",
      content: {
        label: "blog.blogpost",
        source: "route",
        options: {
          show_toc: true,
          show_author: true,
          show_dates: true,
          show_share: true,
          show_reading_time: true
        }
      },
      position: 1
    }
  ],
  seo: {
    title: "{{post.title}} - Blog",
    description: "{{post.excerpt}}",
    noindex: false,
    nofollow: false
  }
};

const PageEditor = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [page, setPage] = useState<PageData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [editMode, setEditMode] = useState(true);
  const [selectedBlock, setSelectedBlock] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [detailsDrawerOpen, setDetailsDrawerOpen] = useState(false);
  const [presentationDrawerOpen, setPresentationDrawerOpen] = useState(false);
  const [selectedSamplePost, setSelectedSamplePost] = useState<string>('sample-1');
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [addBlockModalOpen, setAddBlockModalOpen] = useState(false);
  const [addBlockPosition, setAddBlockPosition] = useState<number>(0);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [tempBlockSettings, setTempBlockSettings] = useState<Block | null>(null);
  const [isSavingBlockSettings, setIsSavingBlockSettings] = useState(false);

  // Create autosave function
  const autosaveFunction = useCallback(async (data: PageData) => {
    if (!data || !id) return;
    
    const pageId = parseInt(id);
    // Map frontend blocks back to API format
    const apiBlocks = data.blocks.map(block => ({
      id: parseInt(block.id) || null,
      type: block.type,
      content: block.content,
      position: block.position,
      props: block.props || null
    }));
    
    await api.cms.pages.update(pageId, {
      title: data.title,
      slug: data.slug,
      locale: data.locale || 'en', // Ensure locale is provided
      blocks: apiBlocks,
      seo: data.seo,
      status: data.status,
      in_main_menu: data.inMainMenu,
      in_footer: data.inFooter,
      is_homepage: data.isHomepage
    });
  }, [id]);

  // Manual save function for save buttons
  const handleSave = useCallback(async () => {
    if (!page || !id || isSaving) return;
    
    setIsSaving(true);
    try {
      const pageId = parseInt(id);
      
      // Map frontend blocks back to API format
      const apiBlocks = page.blocks.map(block => ({
        id: parseInt(block.id) || null,
        type: block.type,
        content: block.content,
        position: block.position,
        props: block.props || null
      }));
      
      // Make API call with all required fields including locale
      await api.cms.pages.update(pageId, {
        title: page.title,
        slug: page.slug,
        locale: page.locale || 'en', // Ensure locale is provided
        blocks: apiBlocks,
        seo: page.seo,
        status: page.status,
        in_main_menu: page.inMainMenu,
        in_footer: page.inFooter,
        is_homepage: page.isHomepage,
        schedule: page.schedule
      });
      
      // Success feedback
      setHasUnsavedChanges(false);
      setLastSaved(new Date());
      toast({
        title: "Page saved",
        description: "Your changes have been saved successfully.",
      });
      
    } catch (error: any) {
      console.error('Save failed:', error);
      
      // Handle validation errors
      if (error?.response?.data && typeof error.response.data === 'object') {
        const validationErrors = error.response.data;
        const errorMessages = Object.entries(validationErrors)
          .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : messages}`)
          .join('; ');
          
        toast({
          title: "Validation Error",
          description: errorMessages,
          variant: "destructive",
        });
      } else {
        toast({
          title: "Save Failed",
          description: error?.message || "Failed to save page. Please try again.",
          variant: "destructive",
        });
      }
    } finally {
      setIsSaving(false);
    }
  }, [page, id, isSaving, toast]);

  // Initialize autosave hook - DISABLED for manual save
  const autosaveState = useAutosave(page || {} as PageData, autosaveFunction, {
    interval: 30000, // 30 seconds
    debounceDelay: 2000, // 2 seconds
    enabled: false, // DISABLED - using manual save buttons instead
    maxRetries: 3,
    storageKey: `page-editor-${id}`
  });

  // Data mapping functions
  const mapApiPageToPageData = useCallback((apiPage: Page): PageData => {
    if (!apiPage) {
      throw new Error('API page data is null or undefined');
    }
    
    if (!apiPage.id) {
      throw new Error('API page missing required id field');
    }

    return {
      id: apiPage.id.toString(),
      title: apiPage.title || '',
      slug: apiPage.slug || '',
      status: apiPage.status || 'draft',
      locale: typeof apiPage.locale === 'object' ? apiPage.locale.code : (apiPage.locale || 'en'),
      isPresentationPage: detectPageType(apiPage) === 'presentation',
      contentType: detectContentType(apiPage),
      inMainMenu: (apiPage as any).in_main_menu || (apiPage as any).inMainMenu || false,
      inFooter: (apiPage as any).in_footer || (apiPage as any).inFooter || false,
      isHomepage: (apiPage as any).is_homepage || (apiPage as any).isHomepage || apiPage.slug === '' || apiPage.path === '/',
      blocks: mapApiBlocksToBlocks(apiPage.blocks || []),
      seo: {
        title: apiPage.seo?.title || '',
        description: apiPage.seo?.description || '',
        ogImage: apiPage.seo?.ogImage || '',
        canonical: apiPage.seo?.canonical || '',
        noindex: apiPage.seo?.noindex || false,
        nofollow: apiPage.seo?.nofollow || false,
        jsonLd: apiPage.seo?.jsonLd || ''
      }
    };
  }, []);

  const detectPageType = (apiPage: Page): 'normal' | 'presentation' => {
    // Check if page has content_detail blocks
    const hasContentDetail = apiPage.blocks?.some((block: any) => block.type === 'content_detail');
    
    // Additional logic: check for specific presentation patterns
    const hasTemplateVariables = apiPage.title?.includes('{{') || 
                                apiPage.seo?.title?.includes('{{') ||
                                apiPage.seo?.description?.includes('{{');
    
    // Check if slug suggests it's a template (contains parameters or is generic)
    const isTemplateSlug = apiPage.slug?.includes('[') || 
                          apiPage.slug === 'blog-detail' || 
                          apiPage.slug === 'post-detail';
    
    return (hasContentDetail || hasTemplateVariables || isTemplateSlug) ? 'presentation' : 'normal';
  };

  const detectContentType = (apiPage: Page): 'blog.blogpost' | 'page.page' | undefined => {
    // Check content_detail blocks for label
    const contentDetailBlock = apiPage.blocks?.find((block: any) => block.type === 'content_detail');
    if (contentDetailBlock?.content?.label) {
      return contentDetailBlock.content.label as 'blog.blogpost' | 'page.page';
    }
    
    // Fallback to slug-based detection
    if (apiPage.slug?.includes('blog') || apiPage.slug?.includes('post')) {
      return 'blog.blogpost';
    }
    
    // Default to page if it's a presentation page, otherwise undefined for normal pages
    return detectPageType(apiPage) === 'presentation' ? 'page.page' : undefined;
  };

  const mapApiBlocksToBlocks = (apiBlocks: ApiBlock[]): Block[] => {
    return apiBlocks.map((apiBlock, index) => ({
      id: apiBlock.id?.toString() || `block-${Date.now()}-${index}`,
      type: apiBlock.type as Block['type'],
      content: apiBlock.content || {},
      position: apiBlock.position || index
    }));
  };

  // Load page data from API
  const loadPageData = useCallback(async (pageId: number) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await api.cms.pages.get(pageId);
      console.log('API Response:', response); // Debug log
      
      if (!response) {
        throw new Error('API response is empty or malformed');
      }
      
      // The API returns the page data directly, not wrapped in a 'data' property
      const pageData = mapApiPageToPageData(response);
      setPage(pageData);
      setLastSaved(new Date(response.updated_at || Date.now()));
    } catch (error: any) {
      console.error('Failed to load page data:', error);
      console.error('Error details:', {
        pageId,
        error: error.message,
        response: error?.response?.data,
        status: error?.response?.status
      });
      
      const errorMessage = error?.response?.data?.detail || 
                         error?.response?.data?.message || 
                         error?.message ||
                         'Failed to load page data';
      setError(errorMessage);
      toast({
        title: "Error loading page",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [mapApiPageToPageData, toast]);

  // Load page data on mount
  useEffect(() => {
    if (id) {
      const pageId = parseInt(id);
      if (isNaN(pageId)) {
        setError('Invalid page ID');
        setIsLoading(false);
        return;
      }
      loadPageData(pageId);
    } else {
      setError('No page ID provided');
      setIsLoading(false);
    }
  }, [id, loadPageData]);
  const [blockToDelete, setBlockToDelete] = useState<string | null>(null);

  // Sample blog posts for presentation preview
  const samplePosts = [
    {
      id: 'sample-1',
      title: 'Getting Started with Content Management',
      excerpt: 'Learn the basics of organizing and structuring your content effectively...',
      content: '<p>This is the full content of the blog post about content management...</p>',
      author: 'John Doe',
      publishedAt: '2024-01-15'
    },
    {
      id: 'sample-2', 
      title: 'Advanced SEO Techniques',
      excerpt: 'Discover powerful SEO strategies to boost your content visibility...',
      content: '<p>Here we explore advanced SEO techniques and best practices...</p>',
      author: 'Jane Smith',
      publishedAt: '2024-01-14'
    }
  ];

  const isPresentationMode = page?.isPresentationPage && page?.contentType === 'blog.blogpost';
  const postsUsingThisTemplate = 24; // Mock count
  const hasContentDetailBlock = page?.blocks.some(block => 
    block.type === 'content_detail'
  ) || false;
  const contentDetailBlockCount = page?.blocks.filter(block => 
    block.type === 'content_detail'
  ).length || 0;

  // Auto-save functionality with debouncing
  const savePageData = useCallback(async () => {
    if (!page || !id) return;
    
    setIsSaving(true);
    try {
      const pageId = parseInt(id);
      // Map frontend blocks back to API format
      const apiBlocks = page.blocks.map(block => ({
        id: parseInt(block.id) || null,
        type: block.type,
        content: block.content,
        position: block.position,
        props: block.props || null
      }));
      
      await api.cms.pages.update(pageId, {
        title: page.title,
        slug: page.slug,
        blocks: apiBlocks,
        seo: page.seo,
        status: page.status,
        in_main_menu: page.inMainMenu,
        in_footer: page.inFooter,
        is_homepage: page.isHomepage
      });
      setLastSaved(new Date());
      setHasUnsavedChanges(false);
    } catch (error: any) {
      console.error('Failed to save page:', error);
      toast({
        title: "Save failed",
        description: error?.response?.data?.detail || "Failed to save page changes",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  }, [page, id, api, toast]);

  // Helper function to generate slug from title
  const generateSlug = (title: string): string => {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9 -]/g, '') // Remove special characters
      .replace(/\s+/g, '-') // Replace spaces with hyphens
      .replace(/-+/g, '-') // Replace multiple hyphens with single hyphen
      .trim()
      .replace(/^-|-$/g, ''); // Remove leading/trailing hyphens
  };

  // Individual block operations
  const createBlockOnServer = useCallback(async (block: Block) => {
    if (!id) return null;
    
    try {
      const pageId = parseInt(id);
      const apiBlock = {
        type: block.type,
        props: block.content || {},  // Backend expects props, not content
        position: block.position,
        id: block.id
      };
      
      // Use the page's insertBlock endpoint
      const response = await api.cms.pages.insertBlock(pageId, apiBlock, block.position);
      
      // Return the full updated page data with transformed blocks
      if (response.data) {
        return transformPageData(response.data);
      }
      return null;
    } catch (error: any) {
      console.error('Failed to create block:', error);
      toast({
        title: "Block creation failed",
        description: error?.response?.data?.detail || "Failed to create block",
        variant: "destructive",
      });
      return null;
    }
  }, [id, api, toast]);

  const updateBlockOnServer = useCallback(async (block: Block) => {
    if (!id || !page) return null;
    
    try {
      // Skip if it's a temporary ID
      if (block.id.startsWith('temp-')) return null;
      
      // Find the block index in the page's blocks array
      const blockIndex = page.blocks.findIndex(b => b.id === block.id);
      if (blockIndex === -1) return null;
      
      // Use the specific update block endpoint
      const pageId = parseInt(id);
      const response = await api.cms.pages.updateBlock(pageId, {
        block_index: blockIndex,
        props: block.content || {}
      });
      
      // Return the full updated page data with transformed blocks
      if (response.data) {
        return transformPageData(response.data);
      }
      return null;
    } catch (error: any) {
      console.error('Failed to update block:', error);
      toast({
        title: "Block update failed",
        description: error?.response?.data?.detail || "Failed to update block",
        variant: "destructive",
      });
      return null;
    }
  }, [id, page, api, toast]);

  const deleteBlockOnServer = useCallback(async (blockId: string) => {
    if (!id || !page) return;
    
    try {
      // Skip if it's a temporary ID
      if (blockId.startsWith('temp-')) return;
      
      // Find the block index in the page's blocks array
      const blockIndex = page.blocks.findIndex(b => b.id === blockId);
      if (blockIndex === -1) return;
      
      // Use the page's deleteBlock endpoint with the block index
      await api.cms.pages.deleteBlock(parseInt(id), blockIndex);
    } catch (error: any) {
      console.error('Failed to delete block:', error);
      toast({
        title: "Block deletion failed",
        description: error?.response?.data?.detail || "Failed to delete block",
        variant: "destructive",
      });
    }
  }, [id, page, api, toast]);

  // Debounced auto-save
  const debouncedSave = useMemo(() => {
    let timeoutId: NodeJS.Timeout;
    return () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        if (hasUnsavedChanges) {
          savePageData();
        }
      }, 2000); // Save after 2 seconds of inactivity
    };
  }, [savePageData, hasUnsavedChanges]);

  // Trigger auto-save when page data changes
  useEffect(() => {
    if (hasUnsavedChanges) {
      debouncedSave();
    }
  }, [hasUnsavedChanges, debouncedSave]);

  // Initialize tempBlockSettings when selectedBlock changes
  useEffect(() => {
    if (selectedBlock && page) {
      const block = page.blocks.find(b => b.id === selectedBlock);
      if (block) {
        setTempBlockSettings(block);
      }
    } else {
      setTempBlockSettings(null);
    }
  }, [selectedBlock, page]);

  // Keyboard shortcuts for PageEditor
  useKeyboardShortcuts({
    onSave: () => {
      savePageData();
    },
    onToggleEdit: () => setEditMode(!editMode),
    onUndo: () => {
      console.log('Undo action');
    },
    onRedo: () => {
      console.log('Redo action');
    },
    onAddBlockFocus: () => {
      if (page) {
        setAddBlockModalOpen(true);
        setAddBlockPosition(page.blocks.length);
      }
    },
    onMoveBlockUp: () => {
      if (selectedBlock && page) {
        const blockIndex = page.blocks.findIndex(b => b.id === selectedBlock);
        if (blockIndex > 0) {
          const blocks = [...page.blocks];
          [blocks[blockIndex], blocks[blockIndex - 1]] = [blocks[blockIndex - 1], blocks[blockIndex]];
          setPage(prev => prev ? { ...prev, blocks } : null);
          setHasUnsavedChanges(true);
        }
      }
    },
    onMoveBlockDown: () => {
      if (selectedBlock && page) {
        const blockIndex = page.blocks.findIndex(b => b.id === selectedBlock);
        if (blockIndex < page.blocks.length - 1) {
          const blocks = [...page.blocks];
          [blocks[blockIndex], blocks[blockIndex + 1]] = [blocks[blockIndex + 1], blocks[blockIndex]];
          setPage(prev => prev ? { ...prev, blocks } : null);
          setHasUnsavedChanges(true);
        }
      }
    },
    enableBlockShortcuts: true
  });


  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleBlockUpdate = useCallback(async (blockId: string, updates: Partial<Block>) => {
    if (!page) return;
    
    // Optimistically update UI
    const updatedBlocks = page.blocks.map(block =>
      block.id === blockId ? { ...block, ...updates } : block
    );
    
    setPage(prev => prev ? ({
      ...prev,
      blocks: updatedBlocks
    }) : null);
    
    // Find the updated block and save it to server immediately
    const updatedBlock = updatedBlocks.find(block => block.id === blockId);
    if (updatedBlock) {
      const updatedPageData = await updateBlockOnServer(updatedBlock);
      if (updatedPageData) {
        // Update with server response to ensure consistency
        setPage(updatedPageData);
        setHasUnsavedChanges(false); // Block is now synced, only page-level changes would remain
      } else {
        // If server update failed, mark as unsaved for full page save fallback
        setHasUnsavedChanges(true);
      }
    }
  }, [page, updateBlockOnServer]);

  const handleAddBlock = async (type: Block['type'], position: number) => {
    if (!page) return;
    
    // Validate content_detail blocks for presentation pages
    if (type === 'content_detail' && isPresentationMode) {
      const existingContentDetailBlocks = page.blocks.filter(b => b.type === 'content_detail').length;
      if (existingContentDetailBlocks >= 1) {
        alert('Presentation pages can only have one content_detail block');
        return;
      }
    }
    
    const newBlock: Block = {
      id: `temp-${Date.now()}`, // Temporary ID until server responds
      type,
      content: getDefaultContent(type),
      position
    };
    
    // Update positions of existing blocks
    const updatedBlocks = page.blocks.map(block => 
      block.position >= position 
        ? { ...block, position: block.position + 1 }
        : block
    );
    
    // Optimistically update UI
    setPage(prev => prev ? ({
      ...prev,
      blocks: [...updatedBlocks, newBlock].sort((a, b) => a.position - b.position)
    }) : null);
    
    setAddBlockModalOpen(false);
    
    // Create block on server and update with full page data
    const updatedPageData = await createBlockOnServer(newBlock);
    if (updatedPageData) {
      // Use the full server response to update the page state
      setPage(updatedPageData);
      setHasUnsavedChanges(false); // Server is now in sync
    } else {
      // Revert on failure
      setPage(prev => prev ? ({
        ...prev,
        blocks: prev.blocks.filter(block => block.id !== newBlock.id)
      }) : null);
    }
  };

  const handleDeleteBlock = (blockId: string) => {
    if (!page) return;
    
    setPage(prev => prev ? ({
      ...prev,
      blocks: prev.blocks.filter(block => block.id !== blockId)
    }) : null);
    
    setHasUnsavedChanges(true);
    setSelectedBlock(null);
  };

  const confirmDeleteBlock = (blockId: string) => {
    setBlockToDelete(blockId);
    setDeleteConfirmOpen(true);
  };

  const handleDuplicateBlock = async (blockId: string) => {
    if (!page || !id) return;
    
    const blockIndex = page.blocks.findIndex(b => b.id === blockId);
    if (blockIndex === -1) return;
    
    try {
      const pageId = parseInt(id);
      const response = await api.cms.pages.duplicateBlock(pageId, { block_index: blockIndex });
      
      // Update the page with the transformed server response
      if (response.data) {
        const updatedPageData = transformPageData(response.data);
        setPage(updatedPageData);
        setHasUnsavedChanges(false); // Server is now in sync
        
        toast({
          title: "Block duplicated",
          description: "The block has been successfully duplicated.",
        });
      }
    } catch (error: any) {
      console.error('Failed to duplicate block:', error);
      toast({
        title: "Duplication failed",
        description: error?.response?.data?.detail || "Failed to duplicate block",
        variant: "destructive",
      });
    }
  };

  const executeDeleteBlock = async () => {
    if (blockToDelete && page && id) {
      // Optimistically update UI
      const blockToRemove = page.blocks.find(b => b.id === blockToDelete);
      setPage(prev => prev ? ({
        ...prev,
        blocks: prev.blocks.filter(block => block.id !== blockToDelete)
      }) : null);
      
      setSelectedBlock(null);
      setBlockToDelete(null);
      setDeleteConfirmOpen(false);
      
      try {
        // Delete on server
        await deleteBlockOnServer(blockToDelete);
        
        // Reload page data to get the updated state from server
        const pageId = parseInt(id);
        await loadPageData(pageId);
        setHasUnsavedChanges(false); // Server is now in sync
      } catch (error) {
        // Revert optimistic update on failure
        setPage(prev => prev && blockToRemove ? ({
          ...prev,
          blocks: [...prev.blocks, blockToRemove].sort((a, b) => a.position - b.position)
        }) : prev);
      }
    }
  };

  // Handle publishing a page
  const handlePublishPage = async () => {
    if (!page || !id) return;
    
    try {
      const pageId = parseInt(id);
      await api.cms.pages.publish(pageId);
      
      // Update page status locally
      setPage(prev => prev ? { ...prev, status: 'published' } : null);
      
      toast({
        title: "Page published",
        description: `"${page.title}" has been published successfully.`,
      });
    } catch (error: any) {
      console.error('Failed to publish page:', error);
      toast({
        title: "Publish failed",
        description: error?.response?.data?.detail || "Failed to publish page",
        variant: "destructive",
      });
    }
  };

  // Handle unpublishing a page (set to draft)
  const handleUnpublishPage = async () => {
    if (!page || !id) return;
    
    try {
      const pageId = parseInt(id);
      await api.cms.pages.unpublish(pageId);
      
      // Update page status locally
      setPage(prev => prev ? { ...prev, status: 'draft' } : null);
      
      toast({
        title: "Page unpublished",
        description: `"${page.title}" has been set to draft.`,
      });
    } catch (error: any) {
      console.error('Failed to unpublish page:', error);
      toast({
        title: "Unpublish failed",
        description: error?.response?.data?.detail || "Failed to unpublish page",
        variant: "destructive",
      });
    }
  };

  // Handle exporting page as JSON
  const handleExportJSON = () => {
    if (!page) return;
    
    const exportData = {
      ...page,
      exportedAt: new Date().toISOString(),
    };
    
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `page-${page.slug}-${Date.now()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    toast({
      title: "Page exported",
      description: `Downloaded as ${exportFileDefaultName}`,
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (active.id !== over?.id && page) {
      setPage(prev => {
        if (!prev) return null;
        
        const blocks = [...prev.blocks];
        const oldIndex = blocks.findIndex(block => block.id === active.id);
        const newIndex = blocks.findIndex(block => block.id === over?.id);

        const reorderedBlocks = arrayMove(blocks, oldIndex, newIndex).map((block, index) => ({
          ...block,
          position: index
        }));

        return {
          ...prev,
          blocks: reorderedBlocks
        };
      });

      setHasUnsavedChanges(true);
    }
  };

  const getDefaultContent = (type: Block['type']) => {
    switch (type) {
      case 'hero':
        return { title: "Hero Title", subtitle: "Hero subtitle" };
      case 'richtext':
        return { content: "<p>Start writing your content...</p>" };  // Backend expects 'content' not 'html'
      case 'image':
        return { src: "", alt: "", caption: "" };
      case 'gallery':
        return { images: [] };
      case 'columns':
        return { columns: [], gap: "md" };  // Backend expects gap field
      case 'cta':
        return { 
          title: "Ready to get started?",
          description: "",
          primaryButtonText: "",
          primaryButtonUrl: "#",
          secondaryButtonText: "",
          secondaryButtonUrl: "#"
        };
      case 'faq':
        return { items: [{ question: "Question?", answer: "Answer here." }] };
      case 'collection_list':
        return { 
          source: "blog.blogpost",
          mode: "query",
          filters: { tags: [], category: null, author: null, dateRange: null },
          order: "newest",
          limit: 10,
          pagination: "load-more",
          layout: "grid",
          showImage: true,
          showExcerpt: true,
          showAuthor: true,
          showDate: true,
          showReadingTime: false,
          emptyStateText: "No blog posts found.",
          emitItemListJsonLd: false
        };
      case 'content_detail':
        return {
          label: "blog.blogpost", // Content type to display
          source: "route", // "route" or {"id": number} for specific content
          options: {
            show_toc: true,
            show_author: true,
            show_dates: true,
            show_share: true,
            show_reading_time: true
          }
        };
      default:
        return {};
    }
  };

  const formatLastSaved = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const statusColors = {
    draft: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400",
    published: "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400",
    scheduled: "bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400"
  };


  // Visual Block Palette Modal Component
  const VisualBlockPalette = () => {
    const [blockTypes, setBlockTypes] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Load block types from API
    useEffect(() => {
      const loadBlockTypes = async () => {
        if (!addBlockModalOpen) {
          return; // Don't load if modal is not open
        }
        
        try {
          setLoading(true);
          console.log('Fetching block types from API...');
          
          const response = await api.blocks.list();
          console.log('Block types API response:', response);
          
          if (response && response.block_types) {
            setBlockTypes(response.block_types);
            setError(null);
          } else {
            throw new Error('No block types in response');
          }
        } catch (err: any) {
          console.error('Failed to load block types:', err);
          setError('Failed to load block types');
          
          // Fallback to hardcoded blocks if API fails
          setBlockTypes([
            { type: "hero", label: "Hero Section", icon: "star", description: "Large banner with title and subtitle", category: "layout" },
            { type: "richtext", label: "Rich Text", icon: "type", description: "Formatted text content", category: "content" },
            { type: "image", label: "Image", icon: "image", description: "Single image with caption", category: "media" },
            { type: "columns", label: "Columns", icon: "columns", description: "Multi-column layout", category: "layout" },
            { type: "cta", label: "Call to Action", icon: "megaphone", description: "Call-to-action section", category: "conversion" },
            { type: "faq", label: "FAQ", icon: "help-circle", description: "Frequently asked questions", category: "content" },
            { type: "collection_list", label: "Blog List", icon: "grid", description: "Display list of blog posts", category: "blog" },
            { type: "content_detail", label: "Content Detail", icon: "layout", description: "Display detailed blog post content", category: "blog" }
          ]);
        } finally {
          setLoading(false);
        }
      };

      loadBlockTypes();
    }, [addBlockModalOpen]); // Reload when modal opens

    // Icon mapping for the block types
    const iconMap: Record<string, any> = {
      star: Star,
      type: Type,
      image: Image,
      grid: Grid,
      columns: Columns,
      megaphone: Megaphone,
      "help-circle": HelpCircle,
      "list-filter": ListFilter,
      "layout-grid": LayoutGrid,
      layout: Layout,
    };

    const articleBlocks = [
      {
        type: 'richtext' as const,
        label: 'Article Content',
        icon: Type,
        description: 'Main article body content',
        category: 'article',
        recommended: true
      },
      {
        type: 'cta' as const,
        label: 'Newsletter Signup',
        icon: Megaphone,
        description: 'Newsletter subscription form',
        category: 'article'
      },
      {
        type: 'columns' as const,
        label: 'Related Posts',
        icon: Columns,
        description: 'Show related blog posts',
        category: 'article'
      },
      {
        type: 'richtext' as const,
        label: 'Author Bio',
        icon: Type,
        description: 'Author information card',
        category: 'article'
      },
      {
        type: 'richtext' as const,
        label: 'Share Bar',
        icon: Type,
        description: 'Social media share buttons',
        category: 'article'
      }
    ];

    const getBlockPreview = (type: string, label: string) => {
      switch (type) {
        case 'hero':
          return (
            <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4 rounded text-center">
              <h3 className="font-bold text-sm mb-1">{isPresentationMode ? '{{post.title}}' : 'Hero Title'}</h3>
              <p className="text-xs opacity-80">{isPresentationMode ? '{{post.excerpt}}' : 'Hero subtitle'}</p>
            </div>
          );
        case 'richtext':
          if (label === 'Article Content') {
            return (
              <div className="p-4 border rounded bg-blue-50">
                <div className="space-y-2">
                  <div className="h-2 bg-blue-300 rounded w-full"></div>
                  <div className="h-2 bg-blue-300 rounded w-4/5"></div>
                  <div className="text-xs text-blue-600 font-medium">{'{{post.content}}'}</div>
                </div>
              </div>
            );
          }
          return (
            <div className="p-4 border rounded">
              <div className="space-y-2">
                <div className="h-2 bg-gray-300 rounded w-full"></div>
                <div className="h-2 bg-gray-300 rounded w-4/5"></div>
                <div className="h-2 bg-gray-300 rounded w-3/4"></div>
              </div>
            </div>
          );
        default:
          return (
            <div className="p-4 border rounded bg-gray-50 text-center">
              <div className="w-8 h-8 mx-auto mb-2 bg-gray-300 rounded"></div>
              <p className="text-xs text-gray-500">{label}</p>
            </div>
          );
      }
    };

    const blocksToShow = isPresentationMode ? [...articleBlocks, ...blockTypes] : blockTypes;

    return (
      <Dialog open={addBlockModalOpen} onOpenChange={setAddBlockModalOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5" />
              Add Block
              {isPresentationMode && (
                <Badge variant="secondary" className="ml-2">
                  Article Layout
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>
          
          {isPresentationMode && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h4 className="font-medium text-blue-900 mb-2">Recommended for Blog Posts</h4>
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
                {articleBlocks.map((block) => (
                  <Button
                    key={`${block.type}-${block.label}`}
                    variant="outline"
                    className="h-auto p-3 flex flex-col items-center gap-2 hover:border-blue-500 border-blue-200"
                    onClick={() => handleAddBlock(block.type, addBlockPosition)}
                  >
                    <div className="w-full">
                      {getBlockPreview(block.type, block.label)}
                    </div>
                    <div className="text-center">
                      <div className="font-medium text-sm">{block.label}</div>
                      {block.recommended && (
                        <Badge variant="secondary" className="text-xs mt-1">Recommended</Badge>
                      )}
                    </div>
                  </Button>
                ))}
              </div>
              <div className="mt-4 text-sm text-blue-700">
                <strong>Typical Pattern:</strong> Header → Article Content → Author Bio → Related Posts → Footer
              </div>
            </div>
          )}
          
          {loading ? (
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Card key={i} className="p-4">
                  <div className="flex flex-col items-center gap-3">
                    <Skeleton className="h-20 w-full rounded" />
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-3 w-full" />
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <div className="space-y-6">
              {/* Group blocks by category */}
              {Object.entries(
                blockTypes.reduce((acc: Record<string, any[]>, block) => {
                  const category = block.category || 'Other';
                  if (!acc[category]) acc[category] = [];
                  acc[category].push(block);
                  return acc;
                }, {})
              ).map(([category, categoryBlocks]) => (
                <div key={category}>
                  <h4 className="font-medium text-sm text-muted-foreground mb-3 uppercase tracking-wide">
                    {category}
                  </h4>
                  <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
                    {categoryBlocks.map((block) => {
                      const Icon = iconMap[block.icon] || Layout; // Fallback to Layout icon
                      
                      return (
                        <Button
                          key={block.type}
                          variant="outline"
                          className="h-auto p-4 flex flex-col items-center gap-3 hover:border-primary"
                          onClick={() => handleAddBlock(block.type as Block['type'], addBlockPosition)}
                        >
                          <div className="w-full">
                            {getBlockPreview(block.type, block.label)}
                          </div>
                          <div className="text-center">
                            <div className="font-medium text-sm">{block.label}</div>
                            <div className="text-xs text-muted-foreground mt-1">
                              {block.description}
                            </div>
                          </div>
                        </Button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    );
  };

  // Sortable Block Component
  const SortableBlock = ({ block, index }: { block: Block; index: number }) => {
    const {
      attributes,
      listeners,
      setNodeRef,
      transform,
      transition,
      isDragging,
    } = useSortable({ id: block.id });

    const style = {
      transform: CSS.Transform.toString(transform),
      transition,
    };

    const isSelected = selectedBlock === block.id;
    
    const blockClasses = editMode 
      ? `relative group border-2 transition-colors ${
          isSelected ? 'border-primary' : 'border-transparent hover:border-primary/30'
        } ${isDragging ? 'opacity-50 z-50' : ''}` 
      : '';

    // Block content is now rendered using DynamicBlockRenderer
    const renderBlockContent_REMOVED = () => {
      switch (block.type) {
        case 'hero':
          // Check if backgroundImage is a valid URL (not a CSS gradient)
          const hasValidBackgroundImage = block.content.backgroundImage && 
            !block.content.backgroundImage.startsWith('linear-gradient') &&
            !block.content.backgroundImage.startsWith('radial-gradient') &&
            (block.content.backgroundImage.startsWith('http') || 
             block.content.backgroundImage.startsWith('/') ||
             block.content.backgroundImage.startsWith('data:'));
          
          return (
            <div 
              className="text-primary-foreground py-16 px-8 text-center rounded-lg"
              style={{
                backgroundImage: hasValidBackgroundImage 
                  ? `url(${block.content.backgroundImage})`
                  : undefined,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                background: hasValidBackgroundImage 
                  ? undefined 
                  : 'linear-gradient(135deg, rgb(59, 130, 246) 0%, rgba(59, 130, 246, 0.8) 100%)'
              }}
            >
              <h1 className="text-3xl font-bold mb-4">{block.content.title}</h1>
              <p className="text-lg opacity-90">{block.content.subtitle}</p>
            </div>
          );
          
        case 'richtext':
          return (
            <div className="prose prose-lg max-w-none py-6 px-4">
              <div dangerouslySetInnerHTML={{ __html: block.content.html }} />
            </div>
          );
          
        case 'image':
          return (
            <div className="py-6 text-center">
              <div className="bg-muted/50 rounded-lg p-8 border-2 border-dashed border-muted-foreground/20">
                <Image className="w-12 h-12 mx-auto mb-3 text-muted-foreground" />
                <p className="text-muted-foreground">Click to add image</p>
              </div>
            </div>
          );
          
        case 'gallery':
          return (
            <div className="py-6 px-4">
              <div className="grid grid-cols-3 gap-4">
                {block.content.images && block.content.images.length > 0 ? (
                  block.content.images.map((img: any, idx: number) => (
                    <div key={idx} className="bg-muted/50 rounded-lg p-4 border-2 border-dashed border-muted-foreground/20">
                      <Image className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                      <p className="text-xs text-center text-muted-foreground">Image {idx + 1}</p>
                    </div>
                  ))
                ) : (
                  <>
                    {[1, 2, 3].map(i => (
                      <div key={i} className="bg-muted/50 rounded-lg p-4 border-2 border-dashed border-muted-foreground/20">
                        <Image className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                        <p className="text-xs text-center text-muted-foreground">Empty slot</p>
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>
          );
          
        case 'columns':
          return (
            <div className="grid grid-cols-2 gap-6 py-6 px-4">
              {block.content.columns && block.content.columns.length > 0 ? (
                block.content.columns.map((col: any, idx: number) => (
                  <div key={idx} className="space-y-3">
                    <h3 className="font-semibold">Column {idx + 1}</h3>
                    <p className="text-muted-foreground">{col.content || "Empty column"}</p>
                  </div>
                ))
              ) : (
                <>
                  <div className="border-2 border-dashed border-muted-foreground/20 rounded-lg p-6 text-center">
                    <p className="text-muted-foreground">Column 1</p>
                  </div>
                  <div className="border-2 border-dashed border-muted-foreground/20 rounded-lg p-6 text-center">
                    <p className="text-muted-foreground">Column 2</p>
                  </div>
                </>
              )}
            </div>
          );
          
        case 'cta':
          return (
            <div className="bg-accent text-accent-foreground py-10 px-8 text-center rounded-lg">
              <h2 className="text-xl font-bold mb-4">{block.content.title}</h2>
              <Button size="lg" variant="secondary">
                {block.content.button?.text}
              </Button>
            </div>
          );
          
        case 'collection_list':
          return (
            <div className="py-6 px-4">
              <div className="border-2 border-dashed border-muted-foreground/20 rounded-lg p-6 bg-muted/20">
                <div className="flex items-center gap-3 mb-4">
                  <Grid className="w-6 h-6 text-primary" />
                  <h3 className="font-semibold text-lg">Collection List Block</h3>
                </div>
                <div className="text-sm text-muted-foreground space-y-2">
                  <p>Source: <span className="font-medium text-foreground">{block.content.source}</span></p>
                  <p>Layout: <span className="font-medium text-foreground">{block.content.layout}</span></p>
                  <p>Limit: <span className="font-medium text-foreground">{block.content.limit} items</span></p>
                  {block.content.emptyStateText && (
                    <p className="italic">Empty state: "{block.content.emptyStateText}"</p>
                  )}
                </div>
                <div className="mt-4 grid grid-cols-3 gap-3">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="bg-card p-3 rounded border">
                      <div className="h-2 bg-muted rounded mb-2" />
                      <div className="h-2 bg-muted rounded w-3/4" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
          
        case 'content_detail':
          return (
            <div className="py-6 px-4">
              <div className="border-2 border-primary/30 border-dashed rounded-lg p-6 bg-primary/5">
                <div className="flex items-center gap-3 mb-4">
                  <Layout className="w-6 h-6 text-primary" />
                  <h3 className="font-semibold text-lg">Content Detail Block</h3>
                  {page.isPresentationPage && (
                    <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-300">
                      Dynamic Content Slot
                    </Badge>
                  )}
                </div>
                <div className="text-sm text-muted-foreground space-y-2 mb-4">
                  <p>Content Type: <span className="font-medium text-foreground">{block.content.label}</span></p>
                  <p>Source: <span className="font-medium text-foreground">
                    {block.content.source === 'route' ? 'From URL Route' : `Specific ID: ${block.content.source.id}`}
                  </span></p>
                </div>
                <div className="grid grid-cols-5 gap-2 text-xs">
                  {block.content.options?.show_toc && (
                    <Badge variant="secondary">TOC</Badge>
                  )}
                  {block.content.options?.show_author && (
                    <Badge variant="secondary">Author</Badge>
                  )}
                  {block.content.options?.show_dates && (
                    <Badge variant="secondary">Dates</Badge>
                  )}
                  {block.content.options?.show_share && (
                    <Badge variant="secondary">Share</Badge>
                  )}
                  {block.content.options?.show_reading_time && (
                    <Badge variant="secondary">Reading Time</Badge>
                  )}
                </div>
                {isPresentationMode && selectedSamplePost && (
                  <div className="mt-4 p-4 bg-card rounded-lg border">
                    <p className="text-xs text-muted-foreground mb-2">Preview with sample data:</p>
                    <h4 className="font-semibold">
                      {samplePosts.find(p => p.id === selectedSamplePost)?.title}
                    </h4>
                    <p className="text-sm text-muted-foreground mt-1">
                      {samplePosts.find(p => p.id === selectedSamplePost)?.excerpt}
                    </p>
                  </div>
                )}
              </div>
            </div>
          );
          
        case 'faq':
          return (
            <div className="py-6 px-4">
              <div className="space-y-3">
                <h3 className="font-semibold text-lg">FAQ</h3>
                {block.content.items && block.content.items.length > 0 ? (
                  <div className="space-y-3">
                    {block.content.items.map((item: any, idx: number) => (
                      <div key={idx} className="border rounded-lg p-4 bg-card">
                        <div className="font-medium mb-2">Q: {item.question || "Question"}</div>
                        <div className="text-sm text-muted-foreground">A: {item.answer || "Answer"}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="border-2 border-dashed border-muted-foreground/20 rounded-lg p-6 text-center">
                    <p className="text-muted-foreground">No FAQ items yet. Click to add questions.</p>
                  </div>
                )}
              </div>
            </div>
          );
          
        default:
          return (
            <div className="py-6 px-4 text-center">
              <p className="text-muted-foreground">Unknown block type: {block.type}</p>
            </div>
          );
      }
    };

    return (
      <div ref={setNodeRef} style={style} className={`relative group ${blockClasses}`}>
        {/* Add Block Above Button */}
        {editMode && (
          <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity z-20">
            <Button
              size="sm"
              variant="outline"
              className="h-6 px-2 bg-card border shadow-md hover:bg-primary hover:text-primary-foreground"
              onClick={() => {
                setAddBlockPosition(block.position);
                setAddBlockModalOpen(true);
              }}
            >
              <Plus className="w-3 h-3 mr-1" />
              <span className="text-xs">Add</span>
            </Button>
          </div>
        )}

        <Card className="mb-4">
          <CardContent className="p-0 relative">
            {editMode && (
              <>
                {/* Drag handle */}
                <div 
                  className="absolute left-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity z-10 cursor-grab active:cursor-grabbing bg-card border rounded p-1 shadow-sm"
                  {...attributes}
                  {...listeners}
                >
                  <GripVertical className="w-4 h-4 text-muted-foreground" />
                </div>
                
                {/* Control buttons */}
                <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 w-8 p-0 bg-card"
                    onClick={() => setSelectedBlock(block.id)}
                    title="Edit block"
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 w-8 p-0 bg-card hover:bg-primary hover:text-primary-foreground"
                    onClick={() => handleDuplicateBlock(block.id)}
                    title="Duplicate block"
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 w-8 p-0 bg-card hover:bg-destructive hover:text-destructive-foreground"
                    onClick={() => confirmDeleteBlock(block.id)}
                    title="Delete block"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </>
            )}
            
            <div className={editMode ? "cursor-pointer" : ""}>
              <DynamicBlockRenderer
                block={{
                  id: block.id,
                  type: block.type,
                  props: block.content,
                  position: block.position
                }}
                isEditing={editMode && selectedBlock === block.id}
                isSelected={selectedBlock === block.id}
                onChange={(updatedBlock) => {
                  handleUpdateBlock(block.id, { content: updatedBlock.props });
                }}
                onSelect={() => editMode && setSelectedBlock(block.id)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Add Block Below Button */}
        {editMode && (
          <div className="absolute -bottom-3 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity z-20">
            <Button
              size="sm"
              variant="outline"
              className="h-6 px-2 bg-card border shadow-md hover:bg-primary hover:text-primary-foreground"
              onClick={() => {
                setAddBlockPosition(block.position + 1);
                setAddBlockModalOpen(true);
              }}
            >
              <Plus className="w-3 h-3 mr-1" />
              <span className="text-xs">Add</span>
            </Button>
          </div>
        )}
      </div>
    );
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-unified flex items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent mx-auto mb-4" />
          <p className="text-muted-foreground">Loading page data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !page) {
    return (
      <div className="min-h-screen bg-gradient-unified flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Page Not Found</h1>
          <p className="text-muted-foreground mb-4">{error || 'The requested page could not be loaded.'}</p>
          <Button 
            onClick={() => navigate('/dashboard/pages')}
            variant="outline"
          >
            Back to Pages
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-unified">
      <div className="flex flex-col">
        <main className="flex-1 p-8">
          <div className="max-w-7xl mx-auto">
            
            {/* Header */}
            <div className="mb-8">
              <Breadcrumb className="mb-4">
                <BreadcrumbList>
                  <BreadcrumbItem>
                    <BreadcrumbLink href="/dashboard">Dashboard</BreadcrumbLink>
                  </BreadcrumbItem>
                  <BreadcrumbSeparator />
                  <BreadcrumbItem>
                    <BreadcrumbLink href="/dashboard/pages">Pages</BreadcrumbLink>
                  </BreadcrumbItem>
                  <BreadcrumbSeparator />
                  <BreadcrumbItem>
                    <BreadcrumbPage>{page?.title || 'Page'}</BreadcrumbPage>
                  </BreadcrumbItem>
                </BreadcrumbList>
              </Breadcrumb>

              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                <div className="flex items-center gap-4">
                  <h1 className="text-3xl font-bold text-foreground">{page?.title || 'Untitled Page'}</h1>
                  {page?.status && (
                    <Badge className={statusColors[page.status]}>
                      {page.status.charAt(0).toUpperCase() + page.status.slice(1)}
                    </Badge>
                  )}
                  {isPresentationMode && (
                    <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-300">
                      Presentation: Blog Detail
                    </Badge>
                  )}
                </div>
                
                <div className="flex items-center gap-3">
                  <span className="text-sm text-muted-foreground">
                    {isSaving ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Saving...
                      </span>
                    ) : lastSaved ? (
                      <span className="flex items-center gap-2">
                        <Save className="w-4 h-4" />
                        Saved at {formatLastSaved(lastSaved)}
                      </span>
                    ) : hasUnsavedChanges ? (
                      <span className="flex items-center gap-2 text-amber-600">
                        <AlertTriangle className="w-4 h-4" />
                        Unsaved changes
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <Save className="w-4 h-4" />
                        Up to date
                      </span>
                    )}
                  </span>
                  
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => {
                      if (page) {
                        const frontendUrl = import.meta.env.VITE_FRONTEND_URL || 'http://localhost:8080';
                        // Handle root/homepage - check for empty string or '/'
                        // The backend sends empty string for homepage
                        const isRoot = !page.slug || page.slug === '/' || page.slug === '';
                        const url = isRoot ? frontendUrl : `${frontendUrl}/${page.slug}`;
                        window.open(url, '_blank');
                      }
                    }}
                  >
                    <Eye className="w-4 h-4 mr-2" />
                    Preview
                  </Button>
                  
                  {page?.status === 'published' ? (
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={handleUnpublishPage}
                      className="text-orange-600 border-orange-200 hover:bg-orange-50"
                    >
                      <Archive className="w-4 h-4 mr-2" />
                      Set as Draft
                    </Button>
                  ) : (
                    <Button size="sm" onClick={() => {
                      if (isPresentationMode) {
                        // Purge cache for all posts using this template
                        setSaving(true);
                        setTimeout(() => {
                          setSaving(false);
                          setLastSaved(new Date());
                        }, 1000);
                      } else {
                        handlePublishPage();
                      }
                    }}>
                      <Globe className="w-4 h-4 mr-2" />
                      {isPresentationMode ? 'Publish & Purge Cache' : 'Publish'}
                    </Button>
                  )}
                  
                  <Button variant="outline" size="sm" onClick={handleExportJSON}>
                    <Download className="w-4 h-4 mr-2" />
                    Export JSON
                  </Button>
                  
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => setDetailsDrawerOpen(true)}
                  >
                    <Settings className="w-4 h-4 mr-2" />
                    Details
                  </Button>
                  
                  {isPresentationMode && (
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => setPresentationDrawerOpen(true)}
                    >
                      <Layout className="w-4 h-4 mr-2" />
                      Context
                    </Button>
                  )}
              </div>
            </div>
            </div>

            {/* Edit Mode Toggle */}
            <div className="mb-6">
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <Button 
                        variant={editMode ? "default" : "outline"}
                        onClick={() => setEditMode(!editMode)}
                      >
                        {editMode ? <Eye className="w-4 h-4 mr-2" /> : <Edit className="w-4 h-4 mr-2" />}
                        {editMode ? "Preview Mode" : "Edit Mode"}
                      </Button>
                      
                      {editMode && (
                        <div className="flex items-center gap-2">
                          <Button variant="ghost" size="sm" disabled>
                            <Undo className="w-4 h-4 mr-2" />
                            Undo
                          </Button>
                          <Button variant="ghost" size="sm" disabled>
                            <Redo className="w-4 h-4 mr-2" />
                            Redo
                          </Button>
                        </div>
                      )}
                    </div>
                    
                    {editMode && (
                      <div className="text-sm text-muted-foreground">
                        Drag blocks to reorder • Click to edit • Trash to delete
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Main Content - Full Width Canvas */}
            <div>
              <div className="w-full">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Layout className="w-5 h-5" />
                      Page Content
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <DndContext
                      sensors={sensors}
                      collisionDetection={closestCenter}
                      onDragEnd={handleDragEnd}
                    >
                      <SortableContext 
                        items={page?.blocks.map(block => block.id) || []} 
                        strategy={verticalListSortingStrategy}
                      >
                        <div className="space-y-0">
                          {page?.blocks
                            ?.sort((a, b) => a.position - b.position)
                            .map((block, index) => (
                              <SortableBlock key={block.id} block={block} index={index} />
                            )) || []}
                        </div>
                        
                        {(!page?.blocks || page.blocks.length === 0) && (
                          <div className="py-20 text-center">
                            <Layout className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
                            <h3 className="text-lg font-medium mb-2">Empty page</h3>
                            <p className="text-muted-foreground mb-6">Start building by adding blocks</p>
                            <Button
                              onClick={() => {
                                if (page) {
                                  setAddBlockPosition(0);
                                  setAddBlockModalOpen(true);
                                }
                              }}
                              className="mt-4"
                            >
                              <Plus className="w-4 h-4 mr-2" />
                              Add Your First Block
                            </Button>
                          </div>
                        )}
                      </SortableContext>
                    </DndContext>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Block Settings Drawer */}
      <Sheet 
        open={!!selectedBlock} 
        onOpenChange={(open) => {
          if (!open) {
            setSelectedBlock(null);
            setTempBlockSettings(null);
          }
        }}
      >
        <SheetContent className="w-96 overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Block Settings
            </SheetTitle>
          </SheetHeader>
          <div className="mt-6 flex flex-col h-full">
            {(() => {
              const block = tempBlockSettings || page?.blocks.find(b => b.id === selectedBlock);
              if (!block || !page) return null;
              
              const originalBlock = page.blocks.find(b => b.id === selectedBlock);
              const hasBlockChanges = tempBlockSettings && originalBlock && 
                JSON.stringify(tempBlockSettings.content) !== JSON.stringify(originalBlock.content);
              
              const handleBlockSettingsUpdate = (updates: Partial<Block>) => {
                setTempBlockSettings(prev => prev ? ({ ...prev, ...updates }) : null);
              };
              
              const handleSaveBlockSettings = async () => {
                if (!hasBlockChanges || !tempBlockSettings) return;
                
                setIsSavingBlockSettings(true);
                await handleBlockUpdate(tempBlockSettings.id, tempBlockSettings);
                setIsSavingBlockSettings(false);
                setSelectedBlock(null);
                setTempBlockSettings(null);
              };
              
              return (
                <div className="flex flex-col h-full">
                  <div className="flex-1 space-y-4 overflow-y-auto pr-2">
                    <div className="flex items-center gap-2 mb-4">
                      <Badge variant="secondary">{block.type}</Badge>
                      <Badge variant="outline" className="text-xs">
                        ID: {block.id.slice(-6)}
                      </Badge>
                    </div>
                    
                    {block.type === 'hero' && (
                    <>
                      <div>
                        <Label>Title</Label>
                        <Input
                          value={block.content.title || ""}
                          onChange={(e) => handleBlockSettingsUpdate({
                            content: { ...block.content, title: e.target.value }
                          })}
                        />
                      </div>
                      <div>
                        <Label>Subtitle</Label>
                        <Textarea
                          value={block.content.subtitle || ""}
                          onChange={(e) => handleBlockSettingsUpdate({
                            content: { ...block.content, subtitle: e.target.value }
                          })}
                        />
                      </div>
                    </>
                  )}
                  
                  {block.type === 'richtext' && (
                    <div>
                      <Label>Content</Label>
                      <Textarea
                        value={block.content.html?.replace(/<[^>]*>/g, '') || ""}
                        onChange={(e) => handleBlockSettingsUpdate({
                          content: { html: `<p>${e.target.value}</p>` }
                        })}
                        rows={8}
                      />
                    </div>
                  )}
                  
                  {block.type === 'image' && (
                    <>
                      <div>
                        <Label>Image URL</Label>
                        <Input
                          value={block.content.src || ""}
                          onChange={(e) => handleBlockSettingsUpdate({
                            content: { ...block.content, src: e.target.value }
                          })}
                          placeholder="https://example.com/image.jpg"
                        />
                      </div>
                      <div>
                        <Label>Alt Text</Label>
                        <Input
                          value={block.content.alt || ""}
                          onChange={(e) => handleBlockSettingsUpdate({
                            content: { ...block.content, alt: e.target.value }
                          })}
                          placeholder="Describe the image"
                        />
                      </div>
                    </>
                  )}
                  
                  {block.type === 'cta' && (
                    <>
                      <div>
                        <Label>Title</Label>
                        <Input
                          value={block.content.title || ""}
                          onChange={(e) => handleBlockSettingsUpdate({
                            content: { ...block.content, title: e.target.value }
                          })}
                          placeholder="Ready to get started?"
                        />
                      </div>
                      <div>
                        <Label>Description</Label>
                        <Textarea
                          value={block.content.description || ""}
                          onChange={(e) => handleBlockSettingsUpdate({
                            content: { ...block.content, description: e.target.value }
                          })}
                          placeholder="Add a description to provide more context (optional)"
                          rows={3}
                        />
                      </div>
                      <Separator className="my-4" />
                      <div className="space-y-4">
                        <h4 className="text-sm font-medium">Primary Button</h4>
                        <div>
                          <Label>Primary Button Text</Label>
                          <Input
                            value={block.content.primaryButtonText || ""}
                            onChange={(e) => handleBlockSettingsUpdate({
                              content: { ...block.content, primaryButtonText: e.target.value }
                            })}
                            placeholder="Get Started (leave empty to hide)"
                          />
                        </div>
                        <div>
                          <Label>Primary Button URL</Label>
                          <Input
                            value={block.content.primaryButtonUrl || ""}
                            onChange={(e) => handleBlockSettingsUpdate({
                              content: { ...block.content, primaryButtonUrl: e.target.value }
                            })}
                            placeholder="https://example.com or #"
                          />
                        </div>
                      </div>
                      <Separator className="my-4" />
                      <div className="space-y-4">
                        <h4 className="text-sm font-medium">Secondary Button (Optional)</h4>
                        <div>
                          <Label>Secondary Button Text</Label>
                          <Input
                            value={block.content.secondaryButtonText || ""}
                            onChange={(e) => handleBlockSettingsUpdate({
                              content: { ...block.content, secondaryButtonText: e.target.value }
                            })}
                            placeholder="Learn More (optional)"
                          />
                        </div>
                        <div>
                          <Label>Secondary Button URL</Label>
                          <Input
                            value={block.content.secondaryButtonUrl || ""}
                            onChange={(e) => handleBlockSettingsUpdate({
                              content: { ...block.content, secondaryButtonUrl: e.target.value }
                            })}
                            placeholder="https://example.com or #"
                          />
                        </div>
                      </div>
                    </>
                  )}
                  
                  {block.type === 'collection_list' && (
                    <>
                      <Card className="mb-4">
                        <CardHeader>
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Grid className="w-4 h-4" />
                            Data Source
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div>
                            <Label>Content Type</Label>
                            <Select
                              value={block.content.contentType || "blog.blogpost"}
                              onValueChange={(value) => handleBlockSettingsUpdate({
                                content: { ...block.content, contentType: value }
                              })}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="blog.blogpost">Blog Posts</SelectItem>
                                <SelectItem value="cms.page">Pages</SelectItem>
                                <SelectItem value="media.mediafile">Media Files</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button 
                              variant={block.content.mode === 'query' ? 'default' : 'outline'} 
                              size="sm"
                              onClick={() => handleBlockSettingsUpdate({
                                content: { ...block.content, mode: 'query' }
                              })}
                            >
                              Query
                            </Button>
                            <Button 
                              variant={block.content.mode === 'curated' ? 'default' : 'outline'} 
                              size="sm"
                              onClick={() => handleBlockSettingsUpdate({
                                content: { ...block.content, mode: 'curated' }
                              })}
                            >
                              Curated
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                      
                      <Card className="mb-4">
                        <CardHeader>
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Filter className="w-4 h-4" />
                            Query Filters
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div>
                            <Label className="flex items-center gap-2">
                              <Tag className="w-4 h-4" />
                              Tags
                            </Label>
                            <Input placeholder="Enter tags..." />
                          </div>
                          <div>
                            <Label className="flex items-center gap-2">
                              <Bookmark className="w-4 h-4" />
                              Category
                            </Label>
                            <Input placeholder="Select category..." />
                          </div>
                          <div>
                            <Label className="flex items-center gap-2">
                              <User className="w-4 h-4" />
                              Author
                            </Label>
                            <Input placeholder="Select author..." />
                          </div>
                          <div>
                            <Label className="flex items-center gap-2">
                              <Calendar className="w-4 h-4" />
                              Date Range
                            </Label>
                            <Input placeholder="Select date range..." />
                          </div>
                        </CardContent>
                      </Card>
                      
                      <Card className="mb-4">
                        <CardHeader>
                          <CardTitle className="text-sm flex items-center gap-2">
                            <ListFilter className="w-4 h-4" />
                            Display Settings
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div>
                            <Label>Layout</Label>
                            <div className="flex gap-2 mt-2">
                              <Button 
                                variant={block.content.layout === 'grid' ? 'default' : 'outline'} 
                                size="sm"
                                onClick={() => handleBlockSettingsUpdate({
                                  content: { ...block.content, layout: 'grid' }
                                })}
                              >
                                <LayoutGrid className="w-4 h-4 mr-1" />
                                Grid
                              </Button>
                              <Button 
                                variant={block.content.layout === 'list' ? 'default' : 'outline'} 
                                size="sm"
                                onClick={() => handleBlockSettingsUpdate({
                                  content: { ...block.content, layout: 'list' }
                                })}
                              >
                                <List className="w-4 h-4 mr-1" />
                                List
                              </Button>
                            </div>
                          </div>
                          <div>
                            <Label>Limit (per page)</Label>
                            <Input 
                              type="number" 
                              value={block.content.limit || 10}
                              onChange={(e) => handleBlockSettingsUpdate({
                                content: { ...block.content, limit: parseInt(e.target.value) }
                              })}
                            />
                          </div>
                          <Separator />
                          <div className="space-y-3">
                            <Label className="text-sm font-medium">Card Options</Label>
                            {[
                              { key: 'showImage', label: 'Show Image', icon: Image },
                              { key: 'showExcerpt', label: 'Show Excerpt', icon: Type },
                              { key: 'showAuthor', label: 'Show Author', icon: User },
                              { key: 'showDate', label: 'Show Date', icon: Calendar },
                              { key: 'showReadingTime', label: 'Show Reading Time', icon: Clock }
                            ].map(option => (
                              <div key={option.key} className="flex items-center justify-between">
                                <Label className="flex items-center gap-2 text-sm">
                                  <option.icon className="w-4 h-4" />
                                  {option.label}
                                </Label>
                                <Button
                                  variant={block.content[option.key] ? 'default' : 'outline'}
                                  size="sm"
                                  onClick={() => handleBlockSettingsUpdate({
                                    content: { ...block.content, [option.key]: !block.content[option.key] }
                                  })}
                                >
                                  {block.content[option.key] ? 'On' : 'Off'}
                                </Button>
                              </div>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    </>
                  )}
                  
                  {block.type === 'content_detail' && (
                    <>
                      <Card className="mb-4">
                        <CardHeader>
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Layout className="w-4 h-4" />
                            Content Binding
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div>
                            <Label>Content Type</Label>
                            <Select
                              value={block.content.contentType || "blog.blogpost"}
                              onValueChange={(value) => handleBlockSettingsUpdate({
                                content: { ...block.content, contentType: value }
                              })}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="blog.blogpost">Blog Posts</SelectItem>
                                <SelectItem value="cms.page">Pages</SelectItem>
                                <SelectItem value="media.mediafile">Media Files</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <Label>Source</Label>
                            <div className="flex gap-2 mt-2">
                              <Button 
                                variant={block.content.source === 'route' ? 'default' : 'outline'} 
                                size="sm"
                                onClick={() => handleBlockSettingsUpdate({
                                  content: { ...block.content, source: 'route' }
                                })}
                              >
                                Route (Default)
                              </Button>
                              <Button 
                                variant={block.content.source === 'specific' ? 'default' : 'outline'} 
                                size="sm"
                                onClick={() => handleBlockSettingsUpdate({
                                  content: { ...block.content, source: 'specific' }
                                })}
                              >
                                Specific ID
                              </Button>
                            </div>
                          </div>
                          {block.content.source === 'specific' && (
                            <div>
                              <Label>Post ID</Label>
                              <Input 
                                placeholder="Enter specific post ID..."
                                value={block.content.specificId || ""}
                                onChange={(e) => handleBlockSettingsUpdate({
                                  content: { ...block.content, specificId: e.target.value }
                                })}
                              />
                            </div>
                          )}
                        </CardContent>
                      </Card>
                      
                      <Card className="mb-4">
                        <CardHeader>
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Settings className="w-4 h-4" />
                            Display Options
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          {[
                            { key: 'showToc', label: 'Show Table of Contents', icon: List },
                            { key: 'showAuthor', label: 'Show Author', icon: User },
                            { key: 'showDates', label: 'Show Dates', icon: Calendar },
                            { key: 'showShareBar', label: 'Show Share Bar', icon: Share2 },
                            { key: 'showReadingTime', label: 'Show Reading Time', icon: Clock }
                          ].map(option => (
                            <div key={option.key} className="flex items-center justify-between">
                              <Label className="flex items-center gap-2 text-sm">
                                <option.icon className="w-4 h-4" />
                                {option.label}
                              </Label>
                              <Button
                                variant={block.content[option.key] ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => handleBlockSettingsUpdate({
                                  content: { ...block.content, [option.key]: !block.content[option.key] }
                                })}
                              >
                                {block.content[option.key] ? 'On' : 'Off'}
                              </Button>
                            </div>
                          ))}
                        </CardContent>
                      </Card>
                      
                      {isPresentationMode && (
                        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                          <div className="flex items-start gap-2">
                            <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
                            <div>
                              <p className="text-sm font-medium text-amber-800">Presentation Page Notice</p>
                              <p className="text-sm text-amber-700 mt-1">
                                This page can be used as a presentation template for blog posts.
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                  
                  </div>
                  
                  {/* Save Button */}
                  <div className="pt-4 border-t sticky bottom-0 bg-background">
                    <div className="flex justify-between items-center gap-2">
                      <div className="flex items-center gap-2">
                        {hasBlockChanges && (
                          <Badge variant="secondary">
                            <span className="w-2 h-2 bg-orange-500 rounded-full mr-2"></span>
                            Unsaved changes
                          </Badge>
                        )}
                      </div>
                      <Button 
                        onClick={handleSaveBlockSettings} 
                        disabled={isSavingBlockSettings || !hasBlockChanges}
                        variant={hasBlockChanges ? "default" : "outline"}
                      >
                        {isSavingBlockSettings ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Save className="h-4 w-4 mr-2" />
                            Save Changes
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>
        </SheetContent>
      </Sheet>

      {/* Details Drawer */}
      <Sheet open={detailsDrawerOpen} onOpenChange={setDetailsDrawerOpen}>
        <SheetContent className="w-96 overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center justify-between">
              <span>Page Details</span>
              <div className="flex items-center gap-2">
                {hasUnsavedChanges && (
                  <Badge variant="secondary">
                    Unsaved changes
                  </Badge>
                )}
                <Button 
                  size="sm" 
                  onClick={handleSave} 
                  disabled={isSaving || !hasUnsavedChanges}
                  variant={hasUnsavedChanges ? "default" : "outline"}
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-1" />
                      Save
                    </>
                  )}
                </Button>
              </div>
            </SheetTitle>
          </SheetHeader>
          <div className="mt-6 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Page Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>Title</Label>
                  <Input 
                    value={page?.title || ''} 
                    onChange={(e) => {
                      if (page) {
                        const newTitle = e.target.value;
                        const newSlug = page.slug === '' || page.slug === generateSlug(page.title) 
                          ? generateSlug(newTitle) 
                          : page.slug;
                        
                        setPage(prev => prev ? ({
                          ...prev,
                          title: newTitle,
                          slug: newSlug
                        }) : null);
                        setHasUnsavedChanges(true);
                      }
                    }}
                    placeholder="Enter page title..."
                  />
                </div>
                <div>
                  <Label>Slug</Label>
                  <div className="flex gap-2">
                    <Input 
                      value={page?.isHomepage ? '/' : (page?.slug || '')}
                      onChange={(e) => {
                        if (page && !page.isHomepage) {
                          setPage(prev => prev ? ({
                            ...prev,
                            slug: e.target.value
                          }) : null);
                          setHasUnsavedChanges(true);
                        }
                      }}
                      placeholder={page?.isHomepage ? '/' : 'page-url-slug'}
                      disabled={page?.isHomepage}
                    />
                    {!page?.isHomepage && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          if (page) {
                            const generatedSlug = generateSlug(page.title);
                            setPage(prev => prev ? ({
                              ...prev,
                              slug: generatedSlug
                            }) : null);
                            setHasUnsavedChanges(true);
                          }
                        }}
                      >
                        Generate
                      </Button>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    URL: {page?.isHomepage ? '/' : `/${page?.slug || 'page-slug'}`}
                  </div>
                </div>
                <div>
                  <Label>Status</Label>
                  <select 
                    value={page?.status || 'draft'}
                    onChange={(e) => {
                      if (page) {
                        setPage(prev => prev ? ({
                          ...prev,
                          status: e.target.value as PageData['status']
                        }) : null);
                        setHasUnsavedChanges(true);
                      }
                    }}
                    className="w-full p-2 border rounded-md"
                  >
                    <option value="draft">Draft</option>
                    <option value="published">Published</option>
                    <option value="scheduled">Scheduled</option>
                  </select>
                </div>
                {page?.status === 'scheduled' && (
                  <div>
                    <Label>Publish At</Label>
                    <Input 
                      type="datetime-local"
                      value={page.schedule?.publishAt || ''}
                      onChange={(e) => {
                        if (page) {
                          setPage(prev => prev ? ({
                            ...prev,
                            schedule: { ...prev.schedule, publishAt: e.target.value }
                          }) : null);
                          setHasUnsavedChanges(true);
                        }
                      }}
                    />
                  </div>
                )}
                
                {/* Separator for page options */}
                <div className="border-t pt-4">
                  <Label className="text-base font-medium">Page Options</Label>
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        checked={page?.isHomepage || false}
                        onChange={(e) => {
                          if (page) {
                            const isHomepage = e.target.checked;
                            setPage(prev => prev ? ({
                              ...prev,
                              isHomepage,
                              slug: isHomepage ? '' : (prev.slug === '' ? generateSlug(prev.title) : prev.slug)
                            }) : null);
                            setHasUnsavedChanges(true);
                          }
                        }}
                        className="rounded"
                      />
                      Set as Homepage
                    </Label>
                    {page?.isHomepage && (
                      <Badge variant="secondary" className="text-xs">
                        Root URL (/)
                      </Badge>
                    )}
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        checked={page?.inMainMenu || false}
                        onChange={(e) => {
                          if (page) {
                            setPage(prev => prev ? ({
                              ...prev,
                              inMainMenu: e.target.checked
                            }) : null);
                            setHasUnsavedChanges(true);
                          }
                        }}
                        className="rounded"
                      />
                      Include in Main Menu
                    </Label>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        checked={page?.inFooter || false}
                        onChange={(e) => {
                          if (page) {
                            setPage(prev => prev ? ({
                              ...prev,
                              inFooter: e.target.checked
                            }) : null);
                            setHasUnsavedChanges(true);
                          }
                        }}
                        className="rounded"
                      />
                      Include in Footer
                    </Label>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Search className="w-4 h-4" />
                  SEO
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>SEO Title</Label>
                  <Input 
                    value={page?.seo?.title || ''} 
                    onChange={(e) => {
                      if (page) {
                        setPage(prev => prev ? ({
                          ...prev,
                          seo: { ...prev.seo, title: e.target.value }
                        }) : null);
                        setHasUnsavedChanges(true);
                      }
                    }}
                    placeholder="Enter SEO title..."
                    maxLength={60}
                  />
                  <div className="text-xs text-muted-foreground mt-1">
                    {page?.seo?.title?.length || 0}/60 characters
                  </div>
                </div>
                <div>
                  <Label>Meta Description</Label>
                  <Textarea 
                    value={page?.seo?.description || ''} 
                    onChange={(e) => {
                      if (page) {
                        setPage(prev => prev ? ({
                          ...prev,
                          seo: { ...prev.seo, description: e.target.value }
                        }) : null);
                        setHasUnsavedChanges(true);
                      }
                    }}
                    placeholder="Enter meta description..."
                    maxLength={160}
                    rows={3}
                  />
                  <div className="text-xs text-muted-foreground mt-1">
                    {page?.seo?.description?.length || 0}/160 characters
                  </div>
                </div>
                <div>
                  <Label>Canonical URL</Label>
                  <Input 
                    value={page?.seo?.canonical || ''} 
                    onChange={(e) => {
                      if (page) {
                        setPage(prev => prev ? ({
                          ...prev,
                          seo: { ...prev.seo, canonical: e.target.value }
                        }) : null);
                        setHasUnsavedChanges(true);
                      }
                    }}
                    placeholder="https://example.com/canonical-url"
                  />
                </div>
                <div>
                  <Label>Open Graph Image</Label>
                  <Input 
                    value={page?.seo?.ogImage || ''} 
                    onChange={(e) => {
                      if (page) {
                        setPage(prev => prev ? ({
                          ...prev,
                          seo: { ...prev.seo, ogImage: e.target.value }
                        }) : null);
                        setHasUnsavedChanges(true);
                      }
                    }}
                    placeholder="https://example.com/og-image.jpg"
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        checked={page?.seo?.noindex || false}
                        onChange={(e) => {
                          if (page) {
                            setPage(prev => prev ? ({
                              ...prev,
                              seo: { ...prev.seo, noindex: e.target.checked }
                            }) : null);
                            setHasUnsavedChanges(true);
                          }
                        }}
                        className="rounded"
                      />
                      No Index
                    </Label>
                  </div>
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-2">
                      <input 
                        type="checkbox" 
                        checked={page?.seo?.nofollow || false}
                        onChange={(e) => {
                          if (page) {
                            setPage(prev => prev ? ({
                              ...prev,
                              seo: { ...prev.seo, nofollow: e.target.checked }
                            }) : null);
                            setHasUnsavedChanges(true);
                          }
                        }}
                        className="rounded"
                      />
                      No Follow
                    </Label>
                  </div>
                </div>
                <div>
                  <Label>JSON-LD Schema</Label>
                  <Textarea 
                    value={page?.seo?.jsonLd || ''} 
                    onChange={(e) => {
                      if (page) {
                        setPage(prev => prev ? ({
                          ...prev,
                          seo: { ...prev.seo, jsonLd: e.target.value }
                        }) : null);
                        setHasUnsavedChanges(true);
                      }
                    }}
                    placeholder='{"@context": "https://schema.org", ...}'
                    rows={4}
                  />
                  <div className="text-xs text-muted-foreground mt-1">
                    Enter valid JSON-LD structured data
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* Bottom Save Button */}
            <div className="flex justify-between items-center gap-2 pt-4 border-t sticky bottom-0 bg-background">
              <div className="flex items-center gap-2">
                {hasUnsavedChanges && (
                  <Badge variant="secondary">
                    <span className="w-2 h-2 bg-orange-500 rounded-full mr-2"></span>
                    Unsaved changes
                  </Badge>
                )}
              </div>
              <Button 
                onClick={handleSave} 
                disabled={isSaving || !hasUnsavedChanges}
                variant={hasUnsavedChanges ? "default" : "outline"}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>

      {/* Presentation Context Drawer */}
      {isPresentationMode && (
        <Sheet open={presentationDrawerOpen} onOpenChange={setPresentationDrawerOpen}>
          <SheetContent className="w-96 overflow-y-auto">
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2">
                <Layout className="w-5 h-5" />
                Presentation Context
              </SheetTitle>
            </SheetHeader>
            <div className="mt-6 space-y-6">
              {/* Content Type */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Content Type</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">blog.blogpost</Badge>
                    <span className="text-sm text-muted-foreground">(readonly)</span>
                  </div>
                </CardContent>
              </Card>

              {/* Sample Object Picker */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Preview with Sample Post</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Label>Sample Object</Label>
                  <select 
                    className="w-full p-2 border rounded-md"
                    value={selectedSamplePost}
                    onChange={(e) => setSelectedSamplePost(e.target.value)}
                  >
                    {samplePosts.map(post => (
                      <option key={post.id} value={post.id}>
                        {post.title}
                      </option>
                    ))}
                  </select>
                  <div className="text-sm text-muted-foreground">
                    <div><strong>Author:</strong> {samplePosts.find(p => p.id === selectedSamplePost)?.author}</div>
                    <div><strong>Published:</strong> {samplePosts.find(p => p.id === selectedSamplePost)?.publishedAt}</div>
                  </div>
                </CardContent>
              </Card>

              {/* Required Blocks Check */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Required Blocks</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      {contentDetailBlockCount === 1 ? (
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      ) : (
                        <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                      )}
                      <span className="text-sm">content_detail block (exactly once)</span>
                    </div>
                    {contentDetailBlockCount === 0 && (
                      <p className="text-xs text-red-600 mt-2">
                        Missing required content_detail block for blog post content
                      </p>
                    )}
                    {contentDetailBlockCount > 1 && (
                      <p className="text-xs text-red-600 mt-2">
                        Too many content_detail blocks: found {contentDetailBlockCount}, only 1 allowed
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Slots Guidance */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Recommended Layout</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-1 bg-blue-500 rounded"></div>
                      <span>Header (navigation, breadcrumbs)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-1 bg-green-500 rounded"></div>
                      <span>Body (article content)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-1 bg-purple-500 rounded"></div>
                      <span>Sidebar (author, related posts)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-1 bg-orange-500 rounded"></div>
                      <span>Footer (newsletter, links)</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Impact */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Template Usage</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-sm">
                    <div className="font-medium text-lg">{postsUsingThisTemplate}</div>
                    <div className="text-muted-foreground">blog posts currently use this template</div>
                    <div className="mt-2 text-xs text-yellow-600">
                      ⚠️ Changes affect all posts using this presentation page
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </SheetContent>
        </Sheet>
      )}

      {/* Visual Block Palette Modal */}
      <VisualBlockPalette />

      {/* Delete Confirmation Modal */}
      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Block</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this block? This action cannot be undone and all content within this block will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              setDeleteConfirmOpen(false);
              setBlockToDelete(null);
            }}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={executeDeleteBlock}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete Block
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default PageEditor;