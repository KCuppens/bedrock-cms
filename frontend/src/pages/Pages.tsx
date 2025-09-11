import { useState, useMemo, useCallback, memo, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import { PagesEmptyState } from "@/components/EmptyStates";
import { api } from "@/lib/api";
import { Page as ApiPage, PageCreateRequest, Locale, PageRevision } from "@/types/api";
import { toast } from "sonner";
import { useTranslation } from "@/contexts/TranslationContext";
import { useLocale } from "@/contexts/LocaleContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { SimpleDialog, SimpleDialogHeader, SimpleDialogTitle } from "@/components/ui/simple-dialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Plus,
  Search,
  Filter,
  Copy,
  Edit,
  Eye,
  MoreHorizontal,
  GripVertical,
  Trash2,
  Download,
  Users,
  FileText,
  Globe,
  Calendar,
  ExternalLink,
  Link,
  History,
  ChevronDown,
  ChevronRight,
  Send,
  Archive,
} from "lucide-react";
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
} from '@dnd-kit/sortable';
import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// Using ApiPage from types, extending with display fields
interface Page extends ApiPage {
  updatedBy?: string;
  internalLinks?: number;
  incomingLinks?: number;
  level?: number;
  inMainMenu?: boolean;
  inFooter?: boolean;
  isHomepage?: boolean;
  recent_revisions?: PageRevision[];
}

interface SortableRowProps {
  page: Page;
  isSelected: boolean;
  onSelect: () => void;
  onOpenDrawer: () => void;
  copyToClipboard: (text: string) => void;
  formatDate: (date: string) => string;
  statusColors: Record<string, string>;
  onNavigate: (pageId: string) => void;
  onEdit: (page: Page) => void;
  onDuplicate: (page: Page) => void;
  onDelete: (page: Page) => void;
  onPublish: (page: Page) => void;
  onUnpublish: (page: Page) => void;
  hasChildren?: boolean;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

const SortableRow = memo<SortableRowProps>(({ page, isSelected, onSelect, onOpenDrawer, copyToClipboard, formatDate, statusColors, onNavigate, onEdit, onDuplicate, onDelete, onPublish, onUnpublish, hasChildren, isExpanded, onToggleExpand }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: page.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const handleStopPropagation = useCallback((e: React.MouseEvent) => e.stopPropagation(), []);
  const handleCopyToClipboard = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    copyToClipboard(page.path);
  }, [page.path, copyToClipboard]);
  const handleEdit = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit(page);
  }, [page, onEdit]);
  const handleNavigate = useCallback(() => onNavigate(page.id), [page.id, onNavigate]);

  return (
    <TableRow
      ref={setNodeRef}
      style={style}
      key={page.id}
      className={`border-border hover:bg-muted/30 cursor-pointer ${isDragging ? 'opacity-50' : ''}`}
      onClick={onOpenDrawer}
    >
      <TableCell>
        <Checkbox
          checked={isSelected}
          onCheckedChange={onSelect}
          onClick={handleStopPropagation}
        />
      </TableCell>
      <TableCell>
        <div
          className="cursor-grab active:cursor-grabbing"
          {...attributes}
          {...listeners}
          onClick={handleStopPropagation}
        >
          <GripVertical className="w-4 h-4 text-muted-foreground" />
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          {/* Indentation for hierarchy */}
          <div style={{ paddingLeft: `${(page.level || 0) * 20}px` }} className="flex items-center gap-2">
            {/* Expand/collapse button */}
            {hasChildren && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 hover:bg-muted"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleExpand?.();
                }}
              >
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
              </Button>
            )}
            
            {/* If no children, add spacing */}
            {!hasChildren && <div className="w-6" />}
            
            <span className="font-medium">{page.title}</span>
            {/* Memoized template badge computation */}
            <TemplateBadge blocks={page.blocks} />
            {page.isHomepage && (
              <Badge variant="default" className="text-xs bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20">
                Homepage
              </Badge>
            )}
            {page.inMainMenu && (
              <Badge variant="outline" className="text-xs">
                Main Menu
              </Badge>
            )}
            {page.inFooter && (
              <Badge variant="outline" className="text-xs">
                Footer
              </Badge>
            )}
            <Badge variant="secondary" className="text-xs">
              {page.locale}
            </Badge>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <code className="text-sm text-muted-foreground bg-muted/50 px-2 py-1 rounded">
            {page.path}
          </code>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={handleCopyToClipboard}
          >
            <Copy className="w-3 h-3" />
          </Button>
        </div>
      </TableCell>
      <TableCell>
        <Badge className={statusColors[page.status] || STATUS_COLORS.draft}>
          {page.status.charAt(0).toUpperCase() + page.status.slice(1)}
        </Badge>
      </TableCell>
      <TableCell>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              onClick={handleStopPropagation}
            >
              <MoreHorizontal className="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={handleEdit}>
              <Edit className="w-4 h-4 mr-2" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem onClick={(e) => {
              e.stopPropagation();
              handlePreviewPage(page);
            }}>
              <Eye className="w-4 h-4 mr-2" />
              Preview
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleNavigate}>
              <ExternalLink className="w-4 h-4 mr-2" />
              Inline Edit
            </DropdownMenuItem>
            <DropdownMenuItem onClick={(e) => {
              e.stopPropagation();
              onDuplicate(page);
            }}>
              <Copy className="w-4 h-4 mr-2" />
              Duplicate
            </DropdownMenuItem>
            {page.status === 'draft' ? (
              <DropdownMenuItem 
                className="text-green-600"
                onClick={(e) => {
                  e.stopPropagation();
                  onPublish(page);
                }}
              >
                <Send className="w-4 h-4 mr-2" />
                Publish
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem 
                className="text-orange-600"
                onClick={(e) => {
                  e.stopPropagation();
                  onUnpublish(page);
                }}
              >
                <Archive className="w-4 h-4 mr-2" />
                Unpublish
              </DropdownMenuItem>
            )}
            <DropdownMenuItem 
              className="text-destructive"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(page);
              }}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
});

SortableRow.displayName = 'SortableRow';

const mockPages: Page[] = [
  {
    id: "1",
    title: "Homepage",
    path: "/",
    status: "published",
    locale: "EN",
    updatedAt: "2024-01-15T10:30:00Z",
    updatedBy: "Mark Bennet",
    internalLinks: 12,
    incomingLinks: 45,
    level: 0,
    inMainMenu: true,
    inFooter: false,
    isHomepage: true
  },
  {
    id: "2",
    title: "About",
    path: "/about",
    status: "published",
    locale: "EN",
    updatedAt: "2024-01-14T14:22:00Z",
    updatedBy: "Sarah Johnson",
    internalLinks: 8,
    incomingLinks: 23,
    level: 0,
    inMainMenu: true,
    inFooter: true,
    isHomepage: false
  },
  {
    id: "3",
    title: "Our Team",
    path: "/about/team",
    status: "published",
    locale: "EN",
    updatedAt: "2024-01-14T11:00:00Z",
    updatedBy: "Sarah Johnson",
    internalLinks: 3,
    incomingLinks: 8,
    parentId: "2",
    level: 1,
    inMainMenu: false,
    inFooter: false,
    isHomepage: false
  },
  {
    id: "4",
    title: "Our History",
    path: "/about/history",
    status: "draft",
    locale: "EN",
    updatedAt: "2024-01-13T16:30:00Z",
    updatedBy: "Sarah Johnson", 
    internalLinks: 2,
    incomingLinks: 1,
    parentId: "2",
    level: 1,
    inMainMenu: false,
    inFooter: false,
    isHomepage: false
  },
  {
    id: "5",
    title: "Products",
    path: "/products",
    status: "published",
    locale: "EN",
    updatedAt: "2024-01-13T09:15:00Z",
    updatedBy: "Mark Bennet",
    internalLinks: 15,
    incomingLinks: 32,
    level: 0,
    inMainMenu: true,
    inFooter: false,
    isHomepage: false
  },
  {
    id: "6",
    title: "Product Launch 2024",
    path: "/products/launch-2024",
    status: "scheduled",
    locale: "EN",
    updatedAt: "2024-01-13T09:15:00Z",
    updatedBy: "Mark Bennet",
    internalLinks: 5,
    incomingLinks: 2,
    parentId: "5",
    level: 1,
    inMainMenu: false,
    inFooter: false,
    isHomepage: false
  },
  {
    id: "7",
    title: "Features",
    path: "/products/features",
    status: "published",
    locale: "EN",
    updatedAt: "2024-01-12T14:20:00Z",
    updatedBy: "Mark Bennet",
    internalLinks: 8,
    incomingLinks: 12,
    parentId: "5",
    level: 1,
    inMainMenu: false,
    inFooter: false,
    isHomepage: false
  },
  {
    id: "8",
    title: "Blog",
    path: "/blog",
    status: "published",
    locale: "EN",
    updatedAt: "2024-01-12T16:45:00Z",
    updatedBy: "Alex Thompson",
    internalLinks: 20,
    incomingLinks: 45,
    level: 0,
    inMainMenu: true,
    inFooter: false,
    isHomepage: false
  },
  {
    id: "9",
    title: "Upcoming Features",
    path: "/blog/upcoming-features",
    status: "draft",
    locale: "EN",
    updatedAt: "2024-01-12T16:45:00Z",
    updatedBy: "Alex Thompson",
    internalLinks: 3,
    incomingLinks: 0,
    parentId: "8",
    level: 1,
    inMainMenu: false,
    inFooter: false,
    isHomepage: false
  },
  {
    id: "10",
    title: "Página de Inicio",
    path: "/es/",
    status: "published",
    locale: "ES",
    updatedAt: "2024-01-11T11:20:00Z",
    updatedBy: "Maria Garcia",
    internalLinks: 10,
    incomingLinks: 34,
    level: 0,
    inMainMenu: true,
    inFooter: false,
    isHomepage: false
  }
];

// Move static objects outside component to prevent recreation
const STATUS_COLORS = {
  draft: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400",
  published: "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400",
  scheduled: "bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400"
} as const;

// Memoized component for template badge to optimize expensive computation
const TemplateBadge = memo<{ blocks?: any[] }>(({ blocks }) => {
  const templateInfo = useMemo(() => {
    const detailBlock = blocks?.find((block: any) => 
      typeof block === 'object' && block?.type?.endsWith('_detail')
    );
    if (!detailBlock) return null;
    
    const contentType = detailBlock.type.replace('_detail', '');
    return { contentType };
  }, [blocks]);

  if (!templateInfo) return null;

  return (
    <Badge variant="outline" className="text-xs bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20">
      <FileText className="w-3 h-3 mr-1" />
      {templateInfo.contentType} template
    </Badge>
  );
});

const Pages = memo(() => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { currentLocale } = useLocale();
  const [pages, setPages] = useState<Page[]>([]);
  const [locales, setLocales] = useState<Locale[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Component-level memory management
  const abortControllerRef = useRef<AbortController>(new AbortController());
  const isMountedRef = useRef(true);
  const timersRef = useRef<Set<NodeJS.Timeout>>(new Set());
  
  // Safe state setter to prevent updates on unmounted components
  const safeSetState = useCallback((setState: Function) => {
    return (...args: any[]) => {
      if (isMountedRef.current && !abortControllerRef.current.signal.aborted) {
        setState(...args);
      }
    };
  }, []);
  
  const [selectedPages, setSelectedPages] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [localeFilter, setLocaleFilter] = useState<string>(currentLocale?.code || "all");
  const [selectedPage, setSelectedPage] = useState<Page | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expandedPages, setExpandedPages] = useState<string[]>([]);
  const [newPageModalOpen, setNewPageModalOpen] = useState(false);
  const [editPageModalOpen, setEditPageModalOpen] = useState(false);
  const [editingPage, setEditingPage] = useState<Page | null>(null);
  const [isCreatingPage, setIsCreatingPage] = useState(false);
  const [isUpdatingPage, setIsUpdatingPage] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [pageToDelete, setPageToDelete] = useState<Page | null>(null);
  const [isDeletingPage, setIsDeletingPage] = useState(false);
  const [newPageForm, setNewPageForm] = useState<{
    title: string;
    slug: string;
    parentId: string;
    locale: string;
    status: 'draft' | 'published' | 'scheduled';
    scheduledPublishAt: string;
    scheduledUnpublishAt: string;
    inMainMenu: boolean;
    inFooter: boolean;
    isHomepage: boolean;
  }>({
    title: "",
    slug: "",
    parentId: "none",
    locale: "",
    status: "draft",
    scheduledPublishAt: "",
    scheduledUnpublishAt: "",
    inMainMenu: false,
    inFooter: false,
    isHomepage: false
  });

  // Helper function to format relative time
  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
    
    if (diffInHours < 1) {
      const diffInMinutes = Math.floor(diffInHours * 60);
      return diffInMinutes === 1 
        ? t('pages.time.minute_ago', '1 minute ago')
        : t('pages.time.minutes_ago', `${diffInMinutes} minutes ago`);
    } else if (diffInHours < 24) {
      const hours = Math.floor(diffInHours);
      return hours === 1
        ? t('pages.time.hour_ago', '1 hour ago')
        : t('pages.time.hours_ago', `${hours} hours ago`);
    } else {
      const days = Math.floor(diffInHours / 24);
      return days === 1
        ? t('pages.time.day_ago', '1 day ago')
        : t('pages.time.days_ago', `${days} days ago`);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      abortControllerRef.current.abort();
      // Clear any pending timers
      timersRef.current.forEach(timer => clearTimeout(timer));
      timersRef.current.clear();
    };
  }, []);

  // Helper to add timer with cleanup tracking
  const addTimer = useCallback((timeout: NodeJS.Timeout) => {
    timersRef.current.add(timeout);
    return timeout;
  }, []);

  // Define loadLocales function before using it
  const loadLocales = useCallback(async () => {
    if (!isMountedRef.current) return;
    
    try {
      const response = await api.request({
        method: 'GET',
        url: '/api/v1/i18n/locales/',
        signal: abortControllerRef.current.signal
      });
      
      if (!isMountedRef.current) return;
      safeSetState(setLocales)(response.results || response || []);
    } catch (error: any) {
      if (error.name === 'AbortError' || !isMountedRef.current) return;
      console.error('Failed to load locales:', error);
    }
  }, [safeSetState]);

  // Load locales on component mount
  useEffect(() => {
    loadLocales();
  }, [loadLocales]);

  // Load pages when filters change or on mount
  useEffect(() => {
    const abortController = new AbortController();
    
    const fetchPages = async () => {
      if (!isMountedRef.current) return;
      
      try {
        safeSetState(setLoading)(true);
        const filters: any = {};
        
        if (searchQuery) {
          filters.q = searchQuery;
        }
        if (statusFilter !== 'all') {
          filters.status = statusFilter;
        }
        if (localeFilter !== 'all') {
          filters.locale = localeFilter;
        }
        
        const response = await api.request({
          method: 'GET',
          url: '/api/v1/cms/pages/',
          params: filters,
          signal: abortController.signal
        });
        
        if (!isMountedRef.current || abortController.signal.aborted) return;
        
        const pagesData = response.results || [];
        
        // Transform API pages to include display fields
        const transformedPages: Page[] = pagesData.map((page: ApiPage) => ({
          ...page,
          id: page.id.toString(), // Convert to string for consistency
          parentId: page.parent ? page.parent.toString() : undefined, // Map backend 'parent' to frontend 'parentId'
          locale: typeof page.locale === 'object' ? page.locale.code : page.locale,
          updatedBy: (page as any).updated_by_name || (page as any).updated_by || '',
          internalLinks: 0, // TODO: Get from API
          incomingLinks: 0, // TODO: Get from API
          level: 0, // Will be calculated in hierarchy
          inMainMenu: (page as any).in_main_menu || (page as any).inMainMenu || false,
          inFooter: (page as any).in_footer || (page as any).inFooter || false,
          isHomepage: (page as any).is_homepage || page.path === '/' || page.slug === ''
        }));
        
        safeSetState(setPages)(transformedPages);
      } catch (error: any) {
        if (error.name === 'AbortError' || !isMountedRef.current) return;
        toast.error(t('pages.errors.load_failed', 'Failed to load pages'));
        console.error(error);
      } finally {
        if (!abortController.signal.aborted && isMountedRef.current) {
          safeSetState(setLoading)(false);
        }
      }
    };

    fetchPages();
    
    return () => {
      abortController.abort();
    };
  }, [searchQuery, statusFilter, localeFilter, safeSetState, t]);

  // Update locale filter when current locale changes
  useEffect(() => {
    if (currentLocale?.code && localeFilter !== currentLocale.code) {
      setLocaleFilter(currentLocale.code);
    }
  }, [currentLocale?.code, localeFilter]);

  // Update form default locale when locales are loaded
  useEffect(() => {
    if (locales.length > 0 && !newPageForm.locale) {
      const defaultLocale = locales.find(l => l.is_default)?.code || locales[0]?.code || "";
      setNewPageForm(prev => ({ ...prev, locale: defaultLocale }));
    }
  }, [locales]); // Removed newPageForm.locale to prevent infinite loop

  // Define loadPages function for manual refresh
  const loadPages = useCallback(async () => {
    try {
      setLoading(true);
      const filters: any = {};
      
      if (searchQuery) {
        filters.q = searchQuery;
      }
      if (statusFilter !== 'all') {
        filters.status = statusFilter;
      }
      if (localeFilter !== 'all') {
        filters.locale = localeFilter;
      }
      
      const response = await api.cms.pages.list(filters);
      const pagesData = response.results || [];
      
      // Transform API pages to include display fields
      const transformedPages: Page[] = pagesData.map((page: ApiPage) => ({
        ...page,
        id: page.id.toString(), // Convert to string for consistency
        parentId: page.parent ? page.parent.toString() : undefined, // Map backend 'parent' to frontend 'parentId'
        locale: typeof page.locale === 'object' ? page.locale.code : page.locale,
        updatedBy: (page as any).updated_by_name || (page as any).updated_by || '',
        internalLinks: 0, // TODO: Get from API
        incomingLinks: 0, // TODO: Get from API
        level: 0, // Will be calculated in hierarchy
        inMainMenu: (page as any).in_main_menu || (page as any).inMainMenu || false,
        inFooter: (page as any).in_footer || (page as any).inFooter || false,
        isHomepage: (page as any).is_homepage || page.path === '/' || page.slug === ''
      }));
      
      // Group pages by parent and sort each group by position
      const pagesByParent = new Map<string | undefined, Page[]>();
      
      // Group pages by parent
      transformedPages.forEach(page => {
        const parentKey = page.parentId || 'ROOT';
        if (!pagesByParent.has(parentKey)) {
          pagesByParent.set(parentKey, []);
        }
        pagesByParent.get(parentKey)!.push(page);
      });
      
      // Sort each group by position
      pagesByParent.forEach((pages, parentKey) => {
        pages.sort((a, b) => (a.position || 0) - (b.position || 0));
      });
      
      // Build final sorted array: ROOT pages first, then child pages
      const sortedPages: Page[] = [];
      
      // Add root pages first (sorted by position)
      const rootPages = pagesByParent.get('ROOT') || [];
      sortedPages.push(...rootPages);
      
      // Add child pages (sorted by position within each parent)
      pagesByParent.forEach((pages, parentKey) => {
        if (parentKey !== 'ROOT') {
          sortedPages.push(...pages);
        }
      });
      
      setPages(sortedPages);
    } catch (error) {
      toast.error('Failed to load pages');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, statusFilter, localeFilter])

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Helper function to get children of a parent page
  const getChildPages = useCallback((parentId: string) => {
    return pages.filter(page => page.parentId === parentId);
  }, [pages]);

  // Helper function to check if a page has children
  const hasChildren = useCallback((pageId: string) => {
    return pages.some(page => page.parentId === pageId);
  }, [pages]);

  // Toggle expand/collapse for a page
  const toggleExpandPage = useCallback((pageId: string) => {
    setExpandedPages(prev => 
      prev.includes(pageId) 
        ? prev.filter(id => id !== pageId)
        : [...prev, pageId]
    );
  }, []);

  // Filter pages based on search query, status, and locale
  const filteredPages = useMemo(() => {
    return pages.filter(page => {
      const matchesSearch = page.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           page.path.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === "all" || page.status === statusFilter;
      const matchesLocale = localeFilter === "all" || page.locale === localeFilter;
      
      return matchesSearch && matchesStatus && matchesLocale;
    });
  }, [pages, searchQuery, statusFilter, localeFilter]);

  // Memoize hierarchical pages computation for performance
  const hierarchicalPages = useMemo(() => {
    const hierarchicalPages: Page[] = [];
    
    // First add all root pages (no parent)
    const rootPages = filteredPages.filter(page => !page.parentId);
    
    const addPagesRecursively = (parentPages: Page[], level = 0) => {
      parentPages.forEach(page => {
        const pageWithLevel = { ...page, level };
        hierarchicalPages.push(pageWithLevel);
        
        // If page is expanded, add children
        if (expandedPages.includes(page.id)) {
          const children = getChildPages(page.id).filter(child => 
            filteredPages.some(p => p.id === child.id)
          );
          if (children.length > 0) {
            addPagesRecursively(children, level + 1);
          }
        }
      });
    };
    
    addPagesRecursively(rootPages);
    return hierarchicalPages;
  }, [filteredPages, expandedPages, getChildPages]);
  
  // Legacy function for backward compatibility
  const getHierarchicalPages = useCallback((filterSearch = true) => {
    return filterSearch ? hierarchicalPages : pages;
  }, [hierarchicalPages, pages]);

  // Handle creating a new page
  const handleCreatePage = useCallback(async () => {
    try {
      setIsCreatingPage(true);
      
      // Validate scheduling fields
      if (newPageForm.status === 'scheduled' && !newPageForm.scheduledPublishAt) {
        toast({
          title: "Validation Error",
          description: "Please select a publish date and time for scheduled pages",
          variant: "destructive"
        });
        setIsCreatingPage(false);
        return;
      }
      
      // Convert datetime-local to ISO string for API
      const formatDateTimeForAPI = (dateTimeLocal: string) => {
        if (!dateTimeLocal) return undefined;
        return new Date(dateTimeLocal).toISOString();
      };
      
      const createRequest: PageCreateRequest = {
        title: newPageForm.title,
        slug: newPageForm.isHomepage ? "" : newPageForm.slug,
        locale: newPageForm.locale,
        parent: newPageForm.parentId !== "none" ? parseInt(newPageForm.parentId) : undefined,
        status: newPageForm.status,
        scheduled_publish_at: formatDateTimeForAPI(newPageForm.scheduledPublishAt),
        scheduled_unpublish_at: formatDateTimeForAPI(newPageForm.scheduledUnpublishAt),
        in_main_menu: newPageForm.inMainMenu,
        in_footer: newPageForm.inFooter,
        is_homepage: newPageForm.isHomepage
      };

      await api.cms.pages.create(createRequest);
      toast.success(t('pages.success.created', 'Page created successfully'));
      
      // Defer state updates to next tick to avoid React batching issues
      setTimeout(() => {
        setNewPageModalOpen(false);
        setNewPageForm({
          title: "",
          slug: "",
          parentId: "none",
          locale: locales.find(l => l.is_default)?.code || "",
          status: "draft",
          inMainMenu: false,
          inFooter: false,
          isHomepage: false
        });
        setIsCreatingPage(false);
      }, 0);
      
      // Load pages after a slight delay to ensure dialog closes smoothly
      setTimeout(() => {
        loadPages();
      }, 100);
    } catch (error) {
      toast.error(t('pages.errors.create_failed', 'Failed to create page'));
      console.error(error);
      setIsCreatingPage(false);
    }
  }, [newPageForm, locales]);

  const handleDuplicatePage = useCallback(async (page: Page) => {
    try {
      const duplicatedPage = await api.cms.pages.duplicate(page.id);
      
      // The API returns the page object directly
      if (duplicatedPage && duplicatedPage.title) {
        toast.success(t('pages.success.duplicated_as', `Page duplicated as "${duplicatedPage.title}"`));
      } else {
        toast.success(t('pages.success.duplicated', 'Page duplicated successfully'));
      }
      
      // Reload pages to show the new duplicate
      loadPages();
    } catch (error) {
      toast.error(t('pages.errors.duplicate_failed', 'Failed to duplicate page'));
      console.error(error);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Memoized preview handler to prevent function recreation
  const handlePreviewPage = useCallback((page: Page) => {
    const frontendUrl = import.meta.env.VITE_FRONTEND_URL || 'http://localhost:8080';
    const isRoot = !page.slug || page.slug === '/' || page.slug === '';
    const url = isRoot ? frontendUrl : `${frontendUrl}/${page.slug}`;
    window.open(url, '_blank');
  }, []);

  // Handle publishing a page
  const handlePublishPage = useCallback(async (page: Page) => {
    try {
      await api.cms.pages.publish(parseInt(page.id));
      toast.success(t('pages.success.published', `Page "${page.title}" published successfully`));
      loadPages(); // Reload to show updated status
    } catch (error) {
      toast.error(t('pages.errors.publish_failed', 'Failed to publish page'));
      console.error(error);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle unpublishing a page
  const handleUnpublishPage = useCallback(async (page: Page) => {
    try {
      await api.cms.pages.unpublish(parseInt(page.id));
      toast.success(t('pages.success.unpublished', `Page "${page.title}" unpublished successfully`));
      loadPages(); // Reload to show updated status
    } catch (error) {
      toast.error(t('pages.errors.unpublish_failed', 'Failed to unpublish page'));
      console.error(error);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle deleting a page
  const handleDeletePage = useCallback(async () => {
    if (!pageToDelete) return;
    
    try {
      setIsDeletingPage(true);
      
      // Check if page has children and pass cascade parameter
      const hasChildPages = hasChildren(pageToDelete.id);
      if (hasChildPages) {
        // For pages with children, we need to pass cascade=true
        // The API client's delete method needs to be updated to support this
        // Use fetch directly for cascade parameter support
        const response = await fetch(`/api/v1/cms/pages/${pageToDelete.id}/?cascade=true`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            ...api.getAuthHeaders()
          }
        });
        if (!response.ok) throw new Error('Delete failed');
      } else {
        await api.cms.pages.delete(parseInt(pageToDelete.id));
      }
      
      toast.success(t('pages.success.deleted', `Page "${pageToDelete.title}" has been deleted`));
      
      // Close modal and reset state
      setDeleteModalOpen(false);
      setPageToDelete(null);
      
      // Reload pages
      loadPages();
    } catch (error) {
      toast.error(t('pages.errors.delete_failed', 'Failed to delete page'));
      console.error(error);
    } finally {
      setIsDeletingPage(false);
    }
  }, [pageToDelete]); // eslint-disable-line react-hooks/exhaustive-deps

  // Open delete confirmation modal
  const openDeleteModal = useCallback((page: Page) => {
    setPageToDelete(page);
    setDeleteModalOpen(true);
  }, []);

  // Handle bulk delete
  const handleBulkDelete = useCallback(async () => {
    try {
      const deletePromises = selectedPages.map(pageId =>
        api.cms.pages.delete(parseInt(pageId))
      );
      
      await Promise.all(deletePromises);
      toast.success(t('pages.success.bulk_deleted', `Successfully deleted ${selectedPages.length} page(s)`));
      
      // Clear selection and reload
      setSelectedPages([]);
      loadPages();
    } catch (error) {
      toast.error(t('pages.errors.bulk_delete_failed', 'Failed to delete some pages'));
      console.error(error);
    }
  }, [selectedPages]); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle editing an existing page
  const handleEditPage = useCallback(async () => {
    if (!editingPage) return;
    
    try {
      setIsUpdatingPage(true);
      
      // Validate scheduling fields
      if (newPageForm.status === 'scheduled' && !newPageForm.scheduledPublishAt) {
        toast({
          title: "Validation Error",
          description: "Please select a publish date and time for scheduled pages",
          variant: "destructive"
        });
        setIsUpdatingPage(false);
        return;
      }
      
      // Handle slug for homepage - convert '/' to empty string for backend
      const apiSlug = newPageForm.isHomepage ? '' : newPageForm.slug.replace(/^\/+/, '');
      
      // Convert datetime-local to ISO string for API
      const formatDateTimeForAPI = (dateTimeLocal: string) => {
        if (!dateTimeLocal) return undefined;
        return new Date(dateTimeLocal).toISOString();
      };
      
      const updateRequest = {
        title: newPageForm.title,
        slug: apiSlug,
        locale: newPageForm.locale,
        parent: newPageForm.parentId !== "none" ? parseInt(newPageForm.parentId) : undefined,
        status: newPageForm.status,
        scheduled_publish_at: formatDateTimeForAPI(newPageForm.scheduledPublishAt),
        scheduled_unpublish_at: formatDateTimeForAPI(newPageForm.scheduledUnpublishAt),
        in_main_menu: newPageForm.inMainMenu,
        in_footer: newPageForm.inFooter,
        is_homepage: newPageForm.isHomepage
      };

      await api.cms.pages.update(parseInt(editingPage.id), updateRequest);
      toast.success(t('pages.success.updated', 'Page updated successfully'));
      
      // Defer state updates to next tick to avoid React batching issues
      setTimeout(() => {
        setEditPageModalOpen(false);
        setEditingPage(null);
        setNewPageForm({
          title: "",
          slug: "",
          parentId: "none",
          locale: locales.find(l => l.is_default)?.code || "",
          status: "draft",
          scheduledPublishAt: "",
          scheduledUnpublishAt: "",
          inMainMenu: false,
          inFooter: false,
          isHomepage: false
        });
        setIsUpdatingPage(false);
      }, 0);
      
      // Load pages after a slight delay to ensure dialog closes smoothly
      setTimeout(() => {
        loadPages();
      }, 100);
    } catch (error) {
      toast.error(t('pages.errors.update_failed', 'Failed to update page'));
      console.error(error);
      setIsUpdatingPage(false);
    }
  }, [editingPage, newPageForm, locales]); // eslint-disable-line react-hooks/exhaustive-deps

  // Open edit modal with pre-filled data
  const openEditModal = useCallback((page: Page) => {
    setEditingPage(page);
    
    // Handle slug for homepage vs regular pages
    let displaySlug = page.slug || '';
    if (page.isHomepage || page.path === '/' || page.slug === '') {
      displaySlug = '/';
    }
    
    // Convert ISO dates to datetime-local format for input fields
    const formatDateTimeForInput = (isoString: string | undefined) => {
      if (!isoString) return '';
      return new Date(isoString).toISOString().slice(0, 16);
    };
    
    setNewPageForm({
      title: page.title,
      slug: displaySlug,
      parentId: page.parentId || "none",
      locale: page.locale,
      status: page.status,
      scheduledPublishAt: formatDateTimeForInput(page.scheduled_publish_at),
      scheduledUnpublishAt: formatDateTimeForInput(page.scheduled_unpublish_at),
      inMainMenu: page.inMainMenu || false,
      inFooter: page.inFooter || false,
      isHomepage: page.isHomepage || false
    });
    setEditPageModalOpen(true);
  }, []);

  // Generate slug from title
  const generateSlug = useCallback((title: string) => {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, '-')
      .replace(/^-+|-+$/g, '');
  }, []);

  // Update slug when title changes
  const handleTitleChange = useCallback((title: string) => {
    setNewPageForm(prev => {
      // If it's homepage, keep the slug as '/'
      if (prev.isHomepage) {
        return { ...prev, title };
      }
      
      // For new pages (empty slug) or if slug matches generated version of old title
      const shouldAutoGenerate = prev.slug === '' || prev.slug === generateSlug(prev.title);
      
      return {
        ...prev,
        title,
        slug: shouldAutoGenerate ? generateSlug(title) : prev.slug
      };
    });
  }, [generateSlug]);

  // Handle homepage checkbox change
  const handleHomepageChange = useCallback((isHomepage: boolean) => {
    setNewPageForm(prev => ({
      ...prev,
      isHomepage,
      slug: isHomepage ? '/' : (prev.slug === '/' ? generateSlug(prev.title) : prev.slug)
    }));
  }, [generateSlug]);

  const handlePageSelect = useCallback((pageId: string) => {
    setSelectedPages(prev => 
      prev.includes(pageId) 
        ? prev.filter(id => id !== pageId)
        : [...prev, pageId]
    );
  }, []);

  const handleSelectAll = useCallback(() => {
    if (selectedPages.length === filteredPages.length && filteredPages.length > 0) {
      setSelectedPages([]);
    } else {
      setSelectedPages(filteredPages.map(page => page.id));
    }
  }, [selectedPages.length, filteredPages]);

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    const { active, over } = event;

    if (active.id !== over?.id) {
      const oldIndex = pages.findIndex((page) => page.id === active.id);
      const newIndex = pages.findIndex((page) => page.id === over?.id);

      if (oldIndex === -1 || newIndex === -1) return;

      const draggedPage = pages[oldIndex];

      // Optimistic update
      const newPages = arrayMove(pages, oldIndex, newIndex);
      setPages(newPages);

      try {
        // Get the parent group for the dragged page
        const parentId = draggedPage.parentId || null;
        
        // Get the ordered list of page IDs for this parent group
        const pageIds = newPages
          .filter(p => {
            // Filter pages by same parent
            if (parentId === null) {
              return !p.parentId;
            }
            return p.parentId === parentId;
          })
          .map(p => parseInt(p.id));
        
        // Use the unified reorder endpoint
        await api.pages.reorder(
          parentId ? parseInt(parentId) : null,
          pageIds
        );
        
        // Refresh data to ensure consistency
        await loadPages();
      } catch (error) {
        console.error('Failed to reorder pages:', error);
        // Revert optimistic update
        setPages(pages);
        toast.error(t('pages.errors.reorder_failed', 'Failed to reorder pages'));
      }
    }
  }, [pages, loadPages]);

  const copyToClipboard = useCallback((text: string) => {
    navigator.clipboard.writeText(text);
  }, []);

  // Modal handlers
  const handleOpenNewPageModal = useCallback(() => setNewPageModalOpen(true), []);
  const handleCloseNewPageModal = useCallback(() => setNewPageModalOpen(false), []);
  const handleCloseEditPageModal = useCallback(() => setEditPageModalOpen(false), []);

  const formatDate = useCallback((dateString: string) => {
    // Handle null, undefined, empty string, or invalid date strings
    if (!dateString) {
      return '';
    }
    
    const date = new Date(dateString);
    
    // Check if date is invalid
    if (isNaN(date.getTime())) {
      return '';
    }
    
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
    
    // If less than 24 hours ago, show relative time
    if (diffInHours < 24 && diffInHours >= 0) {
      if (diffInHours < 1) {
        const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
        return diffInMinutes <= 1 ? 'Just now' : `${diffInMinutes}m ago`;
      }
      return `${Math.floor(diffInHours)}h ago`;
    }
    
    // If within the current year, don't show year
    if (date.getFullYear() === now.getFullYear()) {
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    }
    
    // For older dates, include year
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }, []);

  const openPageDrawer = useCallback((page: Page) => {
    setSelectedPage(page);
    setDrawerOpen(true);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="flex">
          <Sidebar />
          <div className="flex-1 flex flex-col ml-72">
            <TopNavbar />
            <main className="flex-1 p-8">
              <div className="max-w-7xl mx-auto">
                <div className="mb-8">
                  <h1 className="text-3xl font-bold text-foreground mb-2">{t('pages.title', 'Pages')}</h1>
                  <p className="text-muted-foreground">Loading pages...</p>
                </div>
              </div>
            </main>
          </div>
        </div>
      </div>
    );
  }

  if (filteredPages.length === 0 && searchQuery === "" && statusFilter === "all") {
    // Empty state - no pages at all
    return (
      <>
        <div className="min-h-screen">
          <div className="flex">
            <Sidebar />
            <div className="flex-1 flex flex-col ml-72">
              <TopNavbar />
              <main className="flex-1 p-8">
                <div className="max-w-7xl mx-auto">
                  <div className="mb-8">
                    <h1 className="text-3xl font-bold text-foreground mb-2">{t('pages.title', 'Pages')}</h1>
                    <p className="text-muted-foreground">Manage your website content and structure</p>
                  </div>
                  
                  <PagesEmptyState onCreatePage={() => setNewPageModalOpen(true)} />
                </div>
              </main>
            </div>
          </div>
        </div>

        {/* New Page Modal */}
        <Dialog open={newPageModalOpen} onOpenChange={setNewPageModalOpen}>
          <DialogContent className="max-w-2xl bg-background border shadow-md z-50">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Plus className="w-5 w-5" />
                Create New Page
              </DialogTitle>
              <DialogDescription>
                Create a new page with customizable properties and hierarchy settings.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6 py-4">
              {/* Title */}
              <div className="space-y-2">
                <Label htmlFor="title">Page Title *</Label>
                <Input
                  id="title"
                  placeholder="Enter page title"
                  value={newPageForm.title}
                  onChange={(e) => handleTitleChange(e.target.value)}
                />
              </div>

              {/* Slug */}
              <div className="space-y-2">
                <Label htmlFor="slug">URL Slug *</Label>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground text-sm">/</span>
                  <Input
                    id="slug"
                    placeholder="page-url-slug"
                    value={newPageForm.slug}
                    onChange={(e) => setNewPageForm(prev => ({ ...prev, slug: e.target.value }))}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  URL-friendly version of the title. Use lowercase letters, numbers, and hyphens only.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* Parent Page */}
                <div className="space-y-2">
                  <Label htmlFor="parent">{t('pages.fields.parent', 'Parent Page')}</Label>
                  <Select
                    value={newPageForm.parentId}
                    onValueChange={(value) => setNewPageForm(prev => ({ ...prev, parentId: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select parent (optional)" />
                    </SelectTrigger>
                    <SelectContent className="bg-background border shadow-md z-50">
                      <SelectItem value="none">No Parent (Root Page)</SelectItem>
                      {pages.filter(page => page.level === 0).map((page) => (
                        <SelectItem key={page.id} value={page.id}>
                          {page.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Language */}
                <div className="space-y-2">
                  <Label htmlFor="locale">Language</Label>
                  <Select
                    value={newPageForm.locale}
                    onValueChange={(value) => setNewPageForm(prev => ({ ...prev, locale: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-background border shadow-md z-50">
                      {locales.filter(locale => locale.is_active).map((locale) => (
                        <SelectItem key={locale.code} value={locale.code}>
                          {locale.native_name} ({locale.code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Status */}
              <div className="space-y-2">
                <Label htmlFor="status">Initial Status</Label>
                <Select
                  value={newPageForm.status}
                  onValueChange={(value) => setNewPageForm(prev => ({ ...prev, status: value as 'draft' | 'published' | 'scheduled' }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-background border shadow-md z-50">
                    <SelectItem value="draft">{t('pages.status.draft', 'Draft')}</SelectItem>
                    <SelectItem value="published">{t('pages.status.published', 'Published')}</SelectItem>
                    <SelectItem value="scheduled">Scheduled</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Page Options */}
              <div className="space-y-4">
                <Label className="text-base font-medium">Page Options</Label>
                
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="inMainMenu"
                      checked={newPageForm.inMainMenu}
                      onCheckedChange={(checked) => 
                        setNewPageForm(prev => ({ ...prev, inMainMenu: checked as boolean }))
                      }
                    />
                    <Label htmlFor="inMainMenu" className="text-sm font-normal cursor-pointer">
                      Include in main navigation menu
                    </Label>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="inFooter"
                      checked={newPageForm.inFooter}
                      onCheckedChange={(checked) => 
                        setNewPageForm(prev => ({ ...prev, inFooter: checked as boolean }))
                      }
                    />
                    <Label htmlFor="inFooter" className="text-sm font-normal cursor-pointer">
                      Include in footer
                    </Label>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="isHomepage"
                      checked={newPageForm.isHomepage}
                      onCheckedChange={(checked) => 
                        setNewPageForm(prev => ({ ...prev, isHomepage: checked as boolean }))
                      }
                    />
                    <Label htmlFor="isHomepage" className="text-sm font-normal cursor-pointer">
                      Set as homepage
                    </Label>
                  </div>
                </div>
              </div>

              {/* Preview Path */}
              {(newPageForm.slug || newPageForm.isHomepage) && (
                <div className="p-3 bg-muted rounded-lg">
                  <Label className="text-sm font-medium">Page URL Preview:</Label>
                  <code className="block text-sm text-primary mt-1">
                    {newPageForm.isHomepage 
                      ? "/" 
                      : newPageForm.parentId !== "none"
                        ? `${pages.find(p => p.id === newPageForm.parentId)?.path}/${newPageForm.slug}`.replace(/\/+/g, '/')
                        : `/${newPageForm.slug}`
                    }
                  </code>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button 
                variant="outline" 
                onClick={handleCloseNewPageModal}
                disabled={isCreatingPage}
              >
                Cancel
              </Button>
              <Button 
                onClick={handleCreatePage}
                disabled={isCreatingPage || !newPageForm.title || (!newPageForm.slug && !newPageForm.isHomepage)}
              >
                {isCreatingPage ? 'Creating...' : 'Create Page'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="flex">
        <Sidebar />
        
        <div className="flex-1 flex flex-col ml-72">
          <TopNavbar />
          
          <main className="flex-1 p-8">
            <div className="max-w-7xl mx-auto space-y-6">
              
              {/* Header */}
              <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold text-foreground">{t('pages.title', 'Pages')}</h1>
                <div className="flex items-center gap-3">
                  {selectedPages.length > 0 && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline">
                          Bulk Actions
                          <ChevronDown className="w-4 h-4 ml-2" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48">
                        <DropdownMenuItem>
                          <Eye className="w-4 h-4 mr-2" />
                          Publish Selected
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <FileText className="w-4 h-4 mr-2" />
                          Unpublish Selected
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Download className="w-4 h-4 mr-2" />
                          Export Selected
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          className="text-destructive"
                          onClick={() => {
                            if (selectedPages.length > 0) {
                              const confirmDelete = window.confirm(
                                `Are you sure you want to delete ${selectedPages.length} page(s)? This action cannot be undone.`
                              );
                              if (confirmDelete) {
                                handleBulkDelete();
                              }
                            }
                          }}
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete Selected
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                  <Button onClick={handleOpenNewPageModal}>
                    <Plus className="w-4 h-4 mr-2" />
                    New Page
                  </Button>
                </div>
              </div>

              {/* Filters */}
              <Card>
                <CardContent className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        placeholder="Search pages..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                    
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger>
                        <SelectValue placeholder="All Statuses" />
                      </SelectTrigger>
                      <SelectContent className="bg-background border shadow-md z-50">
                        <SelectItem value="all">All Statuses</SelectItem>
                        <SelectItem value="draft">{t('pages.status.draft', 'Draft')}</SelectItem>
                        <SelectItem value="published">{t('pages.status.published', 'Published')}</SelectItem>
                        <SelectItem value="scheduled">Scheduled</SelectItem>
                      </SelectContent>
                    </Select>

                    <Select value={localeFilter} onValueChange={setLocaleFilter}>
                      <SelectTrigger>
                        <SelectValue placeholder="All Locales" />
                      </SelectTrigger>
                      <SelectContent className="bg-background border shadow-md z-50">
                        <SelectItem value="all">All Locales</SelectItem>
                        {locales.filter(locale => locale.is_active).map((locale) => (
                          <SelectItem key={locale.code} value={locale.code}>
                            {locale.native_name} ({locale.code})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="Section" />
                      </SelectTrigger>
                      <SelectContent className="bg-background border shadow-md z-50">
                        <SelectItem value="all">All Sections</SelectItem>
                        <SelectItem value="/">Root</SelectItem>
                        <SelectItem value="/blog">/blog</SelectItem>
                        <SelectItem value="/products">/products</SelectItem>
                      </SelectContent>
                    </Select>

                  </div>
                </CardContent>
              </Card>

              {/* Pages Table */}
              <Card>
                <CardContent className="p-0">
                  <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleDragEnd}
                  >
                    <Table>
                      <TableHeader>
                        <TableRow className="border-border">
                          <TableHead className="w-12">
                            <Checkbox
                              checked={selectedPages.length === filteredPages.length && filteredPages.length > 0}
                              onCheckedChange={handleSelectAll}
                            />
                          </TableHead>
                          <TableHead className="w-12"></TableHead>
                          <TableHead>{t('pages.table.title', 'Title')}</TableHead>
                          <TableHead>Path</TableHead>
                          <TableHead>{t('pages.table.status', 'Status')}</TableHead>
                          <TableHead className="w-20">{t('pages.table.actions', 'Actions')}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        <SortableContext items={getHierarchicalPages()} strategy={verticalListSortingStrategy}>
                          {getHierarchicalPages().map((page) => (
                            <SortableRow
                              key={page.id}
                              page={page}
                              isSelected={selectedPages.includes(page.id)}
                              onSelect={() => handlePageSelect(page.id)}
                              onOpenDrawer={() => openPageDrawer(page)}
                              copyToClipboard={copyToClipboard}
                              formatDate={formatDate}
                              statusColors={STATUS_COLORS}
                              onNavigate={(pageId) => navigate(`/dashboard/pages/${pageId}/edit`)}
                              onEdit={openEditModal}
                              onDuplicate={handleDuplicatePage}
                              onDelete={openDeleteModal}
                              onPublish={handlePublishPage}
                              onUnpublish={handleUnpublishPage}
                              hasChildren={hasChildren(page.id)}
                              isExpanded={expandedPages.includes(page.id)}
                              onToggleExpand={() => toggleExpandPage(page.id)}
                            />
                          ))}
                        </SortableContext>
                      </TableBody>
                    </Table>
                  </DndContext>
                </CardContent>
              </Card>

              {selectedPages.length > 0 && (
                <div className="text-sm text-muted-foreground">
                  {selectedPages.length} of {filteredPages.length} pages selected
                </div>
              )}

            </div>
          </main>
        </div>
      </div>

      {/* Right Drawer */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="w-96">
          {selectedPage && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  {selectedPage.title}
                </SheetTitle>
                <SheetDescription>
                  Page details and analytics
                </SheetDescription>
              </SheetHeader>

              <div className="mt-6 space-y-6">
                
                {/* SEO Snippet */}
                <div>
                  <h3 className="font-medium mb-3 flex items-center gap-2">
                    <Search className="w-4 h-4" />
                    SEO Preview
                  </h3>
                  <div className="bg-muted/30 p-4 rounded-lg space-y-2">
                    <div className="text-blue-600 text-sm font-medium hover:underline cursor-pointer">
                      {selectedPage.title}
                    </div>
                    <div className="text-green-700 text-xs">
                      example.com{selectedPage.path}
                    </div>
                    <div className="text-gray-600 text-sm">
                      Meta description for {selectedPage.title} would appear here...
                    </div>
                  </div>
                </div>

                {/* Link Analytics */}
                <div>
                  <h3 className="font-medium mb-3 flex items-center gap-2">
                    <Link className="w-4 h-4" />
                    Link Analytics
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-muted/30 p-3 rounded-lg text-center">
                      <div className="text-2xl font-bold text-primary">{selectedPage.internalLinks}</div>
                      <div className="text-xs text-muted-foreground">Internal Links</div>
                    </div>
                    <div className="bg-muted/30 p-3 rounded-lg text-center">
                      <div className="text-2xl font-bold text-secondary">{selectedPage.incomingLinks}</div>
                      <div className="text-xs text-muted-foreground">Incoming Links</div>
                    </div>
                  </div>
                </div>

                {/* Revisions */}
                <div>
                  <h3 className="font-medium mb-3 flex items-center gap-2">
                    <History className="w-4 h-4" />
                    Recent Revisions
                  </h3>
                  <div className="space-y-2">
                    {/* Display revision data for the current page */}
                    {(() => {
                      // Generate mock revision data based on the selected page
                      const mockRevisions = [
                        { 
                          id: `rev-${selectedPage.id}-1`, 
                          revision_type: 'published', 
                          created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), 
                          created_by_name: 'John Doe', 
                          comment: 'Published latest changes', 
                          is_published_snapshot: true, 
                          is_autosave: false, 
                          block_count: 5 
                        },
                        { 
                          id: `rev-${selectedPage.id}-2`, 
                          revision_type: 'autosave', 
                          created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(), 
                          created_by_name: 'Jane Smith', 
                          comment: '', 
                          is_published_snapshot: false, 
                          is_autosave: true, 
                          block_count: 5 
                        },
                        { 
                          id: `rev-${selectedPage.id}-3`, 
                          revision_type: 'manual', 
                          created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), 
                          created_by_name: 'Admin', 
                          comment: 'Initial version', 
                          is_published_snapshot: false, 
                          is_autosave: false, 
                          block_count: 3 
                        }
                      ];
                      return mockRevisions;
                    })().map((revision: PageRevision, index: number) => (
                        <div key={revision.id} className="flex items-center justify-between p-2 bg-muted/20 rounded">
                          <div>
                            <div className="text-sm font-medium">
                              {revision.revision_type === 'published' ? 'Published Version' : 
                               revision.revision_type === 'autosave' ? 'Auto-saved Draft' : 
                               'Manual Revision'}
                              {index === 0 && ' (Current)'}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {formatRelativeTime(revision.created_at)}
                              {revision.created_by_name && ` by ${revision.created_by_name}`}
                            </div>
                            {revision.comment && (
                              <div className="text-xs text-muted-foreground mt-1 italic">
                                "{revision.comment}"
                              </div>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant={
                              revision.revision_type === 'published' ? 'default' :
                              revision.revision_type === 'autosave' ? 'secondary' : 'outline'
                            }>
                              {revision.revision_type === 'published' ? 'Published' :
                               revision.revision_type === 'autosave' ? 'Auto-save' :
                               'Draft'}
                            </Badge>
                            <Button variant="ghost" size="sm" className="text-xs">
                              View
                            </Button>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>

              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* New Page Modal */}
      <Dialog open={newPageModalOpen} onOpenChange={setNewPageModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col bg-background border shadow-md z-50">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle className="flex items-center gap-2">
              <Plus className="w-5 h-5" />
              Create New Page
            </DialogTitle>
            <DialogDescription>
              Create a new page with customizable properties and hierarchy settings.
            </DialogDescription>
          </DialogHeader>
          
          <div className="flex-1 overflow-y-auto px-1">
            <div className="space-y-6 py-4 pr-2">
            {/* Title */}
            <div className="space-y-2">
              <Label htmlFor="title">Page Title *</Label>
              <Input
                id="title"
                placeholder="Enter page title"
                value={newPageForm.title}
                onChange={(e) => handleTitleChange(e.target.value)}
              />
            </div>

            {/* Slug */}
            <div className="space-y-2">
              <Label htmlFor="slug">URL Slug *</Label>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground text-sm">/</span>
                <Input
                  id="slug"
                  placeholder="page-url-slug"
                  value={newPageForm.slug}
                  onChange={(e) => setNewPageForm(prev => ({ ...prev, slug: e.target.value }))}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                URL-friendly version of the title. Use lowercase letters, numbers, and hyphens only.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Parent Page */}
              <div className="space-y-2">
                <Label htmlFor="parent">Parent Page</Label>
                <Select
                  value={newPageForm.parentId}
                  onValueChange={(value) => setNewPageForm(prev => ({ ...prev, parentId: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select parent (optional)" />
                  </SelectTrigger>
                  <SelectContent className="bg-background border shadow-md z-50">
                    <SelectItem value="none">No Parent (Root Page)</SelectItem>
                    {pages.filter(page => page.level === 0).map((page) => (
                      <SelectItem key={page.id} value={page.id}>
                        {page.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Language */}
              <div className="space-y-2">
                <Label htmlFor="locale">Language</Label>
                <Select
                  value={newPageForm.locale}
                  onValueChange={(value) => setNewPageForm(prev => ({ ...prev, locale: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-background border shadow-md z-50">
                    {locales.filter(locale => locale.is_active).map((locale) => (
                      <SelectItem key={locale.code} value={locale.code}>
                        {locale.native_name} ({locale.code})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Status */}
            <div className="space-y-2">
              <Label htmlFor="status">Initial Status</Label>
              <Select
                value={newPageForm.status}
                onValueChange={(value) => setNewPageForm(prev => ({ ...prev, status: value as 'draft' | 'published' | 'scheduled' }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-popover border border-border z-50">
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="published">Published</SelectItem>
                  <SelectItem value="scheduled">Scheduled</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Scheduling Fields - Show when status is scheduled */}
            {newPageForm.status === 'scheduled' && (
              <div className="p-3 border rounded-lg bg-muted/30">
                <Label className="text-sm font-medium flex items-center gap-2 mb-3">
                  <Calendar className="w-4 h-4" />
                  Scheduling Options
                </Label>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="scheduledPublishAt" className="text-xs">Publish Date & Time *</Label>
                    <Input
                      id="scheduledPublishAt"
                      type="datetime-local"
                      value={newPageForm.scheduledPublishAt}
                      onChange={(e) => setNewPageForm(prev => ({ ...prev, scheduledPublishAt: e.target.value }))}
                      min={new Date().toISOString().slice(0, 16)}
                      className="text-sm"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label htmlFor="scheduledUnpublishAt" className="text-xs">Unpublish Date & Time</Label>
                    <Input
                      id="scheduledUnpublishAt"
                      type="datetime-local"
                      value={newPageForm.scheduledUnpublishAt}
                      onChange={(e) => setNewPageForm(prev => ({ ...prev, scheduledUnpublishAt: e.target.value }))}
                      min={newPageForm.scheduledPublishAt || new Date().toISOString().slice(0, 16)}
                      className="text-sm"
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Content will be automatically published/unpublished at the specified times
                </p>
              </div>
            )}

            {/* Scheduling Fields for Published Pages - Allow scheduling unpublish */}
            {newPageForm.status === 'published' && (
              <div className="p-3 border rounded-lg bg-muted/30">
                <Label className="text-sm font-medium flex items-center gap-2 mb-2">
                  <Calendar className="w-4 h-4" />
                  Auto-Unpublish (Optional)
                </Label>
                <Input
                  id="scheduledUnpublishAt"
                  type="datetime-local"
                  value={newPageForm.scheduledUnpublishAt}
                  onChange={(e) => setNewPageForm(prev => ({ ...prev, scheduledUnpublishAt: e.target.value }))}
                  min={new Date().toISOString().slice(0, 16)}
                  className="text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Automatically unpublish at the specified time
                </p>
              </div>
            )}

            {/* Page Options */}
            <div className="space-y-4">
              <Label className="text-base font-medium">Page Options</Label>
              
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="inMainMenu"
                    checked={newPageForm.inMainMenu}
                    onCheckedChange={(checked) => 
                      setNewPageForm(prev => ({ ...prev, inMainMenu: checked as boolean }))
                    }
                  />
                  <Label htmlFor="inMainMenu" className="text-sm font-normal cursor-pointer">
                    Include in main navigation menu
                  </Label>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="inFooter"
                    checked={newPageForm.inFooter}
                    onCheckedChange={(checked) => 
                      setNewPageForm(prev => ({ ...prev, inFooter: checked as boolean }))
                    }
                  />
                  <Label htmlFor="inFooter" className="text-sm font-normal cursor-pointer">
                    Include in footer
                  </Label>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="isHomepage"
                    checked={newPageForm.isHomepage}
                    onCheckedChange={(checked) => 
                      setNewPageForm(prev => ({ ...prev, isHomepage: checked as boolean }))
                    }
                  />
                  <Label htmlFor="isHomepage" className="text-sm font-normal cursor-pointer">
                    Set as homepage
                  </Label>
                </div>
              </div>
            </div>

            {/* Preview Path */}
            {(newPageForm.slug || newPageForm.isHomepage) && (
              <div className="p-3 bg-muted rounded-lg">
                <Label className="text-sm font-medium">Page URL Preview:</Label>
                <code className="block text-sm text-primary mt-1">
                  {newPageForm.isHomepage 
                    ? "/" 
                    : newPageForm.parentId !== "none"
                      ? `${pages.find(p => p.id === newPageForm.parentId)?.path}/${newPageForm.slug}`.replace(/\/+/g, '/')
                      : `/${newPageForm.slug}`
                  }
                </code>
              </div>
            )}
            </div>
          </div>

          <DialogFooter className="flex-shrink-0">
            <Button 
              variant="outline" 
              onClick={handleCloseNewPageModal}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleCreatePage}
              disabled={
                !newPageForm.title || 
                (!newPageForm.slug && !newPageForm.isHomepage) ||
                (newPageForm.status === 'scheduled' && !newPageForm.scheduledPublishAt)
              }
            >
              Create Page
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Page Modal */}
      <SimpleDialog open={editPageModalOpen} onOpenChange={setEditPageModalOpen}>
        <div className="max-h-[90vh] flex flex-col">
          <SimpleDialogHeader className="flex-shrink-0">
            <SimpleDialogTitle className="flex items-center gap-2">
              <Edit className="w-5 h-5" />
              Edit Page
            </SimpleDialogTitle>
            <p className="text-sm text-muted-foreground mt-2">
              Edit page properties and settings.
            </p>
          </SimpleDialogHeader>
          
          <div className="flex-1 overflow-y-auto px-1">
            <div className="space-y-4 py-4 pr-2">
            <div className="space-y-2">
              <Label htmlFor="edit-title">Page Title</Label>
              <Input
                id="edit-title"
                value={newPageForm.title}
                onChange={(e) => handleTitleChange(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-slug">URL Slug</Label>
              <div className="flex gap-2">
                <Input
                  id="edit-slug"
                  value={newPageForm.slug}
                  onChange={(e) => setNewPageForm(prev => ({ ...prev, slug: e.target.value }))}
                  disabled={newPageForm.isHomepage}
                  placeholder={newPageForm.isHomepage ? '/' : 'page-url-slug'}
                />
                {!newPageForm.isHomepage && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const generatedSlug = generateSlug(newPageForm.title);
                      setNewPageForm(prev => ({ ...prev, slug: generatedSlug }));
                    }}
                  >
                    Generate
                  </Button>
                )}
              </div>
              <div className="text-xs text-muted-foreground">
                URL: {newPageForm.isHomepage ? '/' : `/${newPageForm.slug || 'page-slug'}`}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>{t('pages.fields.status', 'Status')}</Label>
                <Select
                  value={newPageForm.status}
                  onValueChange={(value) => setNewPageForm(prev => ({ ...prev, status: value as 'draft' | 'published' | 'scheduled' }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-background border shadow-md z-50">
                    <SelectItem value="draft">{t('pages.status.draft', 'Draft')}</SelectItem>
                    <SelectItem value="published">{t('pages.status.published', 'Published')}</SelectItem>
                    <SelectItem value="scheduled">Scheduled</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Language</Label>
                <Select
                  value={newPageForm.locale}
                  onValueChange={(value) => setNewPageForm(prev => ({ ...prev, locale: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-background border shadow-md z-50">
                    {locales.filter(locale => locale.is_active).map((locale) => (
                      <SelectItem key={locale.code} value={locale.code}>
                        {locale.native_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Scheduling Fields - Show when status is scheduled */}
            {newPageForm.status === 'scheduled' && (
              <div className="p-3 border rounded-lg bg-muted/30">
                <Label className="text-sm font-medium flex items-center gap-2 mb-3">
                  <Calendar className="w-4 h-4" />
                  Scheduling Options
                </Label>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label htmlFor="edit-scheduledPublishAt" className="text-xs">Publish Date & Time *</Label>
                    <Input
                      id="edit-scheduledPublishAt"
                      type="datetime-local"
                      value={newPageForm.scheduledPublishAt}
                      onChange={(e) => setNewPageForm(prev => ({ ...prev, scheduledPublishAt: e.target.value }))}
                      min={new Date().toISOString().slice(0, 16)}
                      className="text-sm"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label htmlFor="edit-scheduledUnpublishAt" className="text-xs">Unpublish Date & Time</Label>
                    <Input
                      id="edit-scheduledUnpublishAt"
                      type="datetime-local"
                      value={newPageForm.scheduledUnpublishAt}
                      onChange={(e) => setNewPageForm(prev => ({ ...prev, scheduledUnpublishAt: e.target.value }))}
                      min={newPageForm.scheduledPublishAt || new Date().toISOString().slice(0, 16)}
                      className="text-sm"
                    />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Content will be automatically published/unpublished at the specified times
                </p>
              </div>
            )}

            {/* Scheduling Fields for Published Pages - Allow scheduling unpublish */}
            {newPageForm.status === 'published' && (
              <div className="p-3 border rounded-lg bg-muted/30">
                <Label className="text-sm font-medium flex items-center gap-2 mb-2">
                  <Calendar className="w-4 h-4" />
                  Auto-Unpublish (Optional)
                </Label>
                <Input
                  id="edit-scheduledUnpublishAt"
                  type="datetime-local"
                  value={newPageForm.scheduledUnpublishAt}
                  onChange={(e) => setNewPageForm(prev => ({ ...prev, scheduledUnpublishAt: e.target.value }))}
                  min={new Date().toISOString().slice(0, 16)}
                  className="text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Automatically unpublish at the specified time
                </p>
              </div>
            )}

            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox 
                  id="edit-mainmenu"
                  checked={newPageForm.inMainMenu}
                  onCheckedChange={(checked) => 
                    setNewPageForm(prev => ({ ...prev, inMainMenu: checked as boolean }))
                  }
                />
                <Label htmlFor="edit-mainmenu">Include in main menu</Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox 
                  id="edit-footer"
                  checked={newPageForm.inFooter}
                  onCheckedChange={(checked) => 
                    setNewPageForm(prev => ({ ...prev, inFooter: checked as boolean }))
                  }
                />
                <Label htmlFor="edit-footer">Include in footer</Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox 
                  id="edit-homepage"
                  checked={newPageForm.isHomepage}
                  onCheckedChange={(checked) => handleHomepageChange(checked as boolean)}
                />
                <Label htmlFor="edit-homepage">Set as homepage</Label>
                {newPageForm.isHomepage && (
                  <Badge variant="secondary" className="text-xs ml-2">
                    Root URL (/)
                  </Badge>
                )}
              </div>
            </div>
            </div>
          </div>

          <div className="flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 pt-4 flex-shrink-0">
            <Button 
              variant="outline" 
              onClick={handleCloseEditPageModal}
              disabled={isUpdatingPage}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleEditPage}
              disabled={
                isUpdatingPage || 
                !newPageForm.title || 
                (!newPageForm.slug && !newPageForm.isHomepage) ||
                (newPageForm.status === 'scheduled' && !newPageForm.scheduledPublishAt)
              }
              className="sm:ml-2"
            >
              {isUpdatingPage ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </SimpleDialog>

      {/* Delete Confirmation Modal */}
      <SimpleDialog open={deleteModalOpen} onOpenChange={(open) => {
        if (!isDeletingPage) setDeleteModalOpen(open);
      }}>
        <SimpleDialogHeader>
          <SimpleDialogTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="w-5 h-5" />
            Delete Page
          </SimpleDialogTitle>
          <p className="text-sm text-muted-foreground mt-2">
            Are you sure you want to delete this page? This action cannot be undone.
          </p>
        </SimpleDialogHeader>
          
          {pageToDelete && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-destructive/10 rounded-lg border border-destructive/20">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-destructive" />
                    <span className="font-medium text-foreground">{pageToDelete.title}</span>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Path: <code className="px-1 py-0.5 bg-muted rounded">{pageToDelete.path}</code>
                  </div>
                  {hasChildren && hasChildren(pageToDelete.id) && (
                    <div className="mt-3 p-2 bg-warning/10 rounded border border-warning/20">
                      <p className="text-sm text-warning-foreground flex items-center gap-1">
                        <span className="font-medium">⚠️ Warning:</span> This page has child pages that will also be affected.
                      </p>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="text-sm text-muted-foreground">
                <p>This will permanently delete:</p>
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>All page content and blocks</li>
                  <li>SEO settings and metadata</li>
                  <li>All page revisions and history</li>
                  {hasChildren && hasChildren(pageToDelete.id) && (
                    <li className="text-destructive">All child pages under this page</li>
                  )}
                </ul>
              </div>
            </div>
          )}

          <div className="flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 pt-4">
            <Button 
              variant="outline" 
              onClick={() => setDeleteModalOpen(false)}
              disabled={isDeletingPage}
            >
              Cancel
            </Button>
            <Button 
              variant="destructive"
              onClick={handleDeletePage}
              disabled={isDeletingPage}
              className="sm:ml-2"
            >
              {isDeletingPage ? 'Deleting...' : 'Delete Page'}
            </Button>
          </div>
      </SimpleDialog>

    </div>
  );
});

Pages.displayName = 'Pages';
export default Pages;