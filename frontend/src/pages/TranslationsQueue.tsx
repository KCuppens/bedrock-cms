import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api.ts";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import { TranslationsEmptyState } from "@/components/EmptyStates";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
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
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Search,
  Filter,
  Languages,
  User,
  ExternalLink,
  UserCheck,
  Sparkles,
  ChevronDown,
  Download,
  CheckCircle2,
  MessageSquare,
  Calendar,
  Clock,
  AlertCircle,
  Edit,
  Eye,
  Save,
  X,
  Check,
  RotateCcw,
  Loader2,
  RefreshCw,
} from "lucide-react";

interface TranslationUnit {
  id: string;
  key: string; // e.g., "page#1.title"
  model: string; // e.g., "page", "block", "asset"
  objectId: string;
  field: string;
  sourceLocale: string;
  targetLocale: string;
  sourceText: string;
  targetText: string;
  status: 'missing' | 'draft' | 'needs_review' | 'approved';
  assignee?: string;
  lastModified: string;
  modifiedBy: string;
  priority: 'low' | 'medium' | 'high';
  context?: string;
  comments: {
    id: string;
    author: string;
    text: string;
    timestamp: string;
  }[];
  history: {
    id: string;
    action: string;
    author: string;
    timestamp: string;
    oldValue?: string;
    newValue?: string;
  }[];
}

const mockTranslationUnits: TranslationUnit[] = [
  {
    id: "1",
    key: "page#1.title",
    model: "page",
    objectId: "1",
    field: "title",
    sourceLocale: "EN",
    targetLocale: "ES",
    sourceText: "Welcome to Our Amazing Platform",
    targetText: "Bienvenido a Nuestra Increíble Plataforma",
    status: "approved",
    assignee: "Maria Garcia",
    lastModified: "2024-01-15T10:30:00Z",
    modifiedBy: "Maria Garcia",
    priority: "high",
    context: "Homepage main heading",
    comments: [
      {
        id: "c1",
        author: "Maria Garcia",
        text: "Updated to match brand voice guidelines",
        timestamp: "2024-01-15T10:30:00Z"
      }
    ],
    history: [
      {
        id: "h1",
        action: "status_changed",
        author: "Maria Garcia",
        timestamp: "2024-01-15T10:30:00Z",
        oldValue: "needs_review",
        newValue: "approved"
      }
    ]
  },
  {
    id: "2",
    key: "page#2.meta_description",
    model: "page",
    objectId: "2",
    field: "meta_description",
    sourceLocale: "EN",
    targetLocale: "ES",
    sourceText: "Learn more about our company, our mission, and the team behind our innovative solutions.",
    targetText: "",
    status: "missing",
    priority: "medium",
    context: "About page meta description",
    comments: [],
    history: [],
    lastModified: "2024-01-14T14:22:00Z",
    modifiedBy: "System"
  },
  {
    id: "3",
    key: "block#hero_1.subtitle",
    model: "block",
    objectId: "hero_1",
    field: "subtitle",
    sourceLocale: "EN",
    targetLocale: "FR",
    sourceText: "Discover the power of modern web development with our cutting-edge tools and services.",
    targetText: "Découvrez la puissance du développement web moderne avec nos outils et services de pointe.",
    status: "needs_review",
    assignee: "Pierre Dubois",
    lastModified: "2024-01-13T16:45:00Z",
    modifiedBy: "Pierre Dubois",
    priority: "high",
    context: "Hero section subtitle",
    comments: [
      {
        id: "c2",
        author: "Sarah Johnson",
        text: "Please review for technical terminology accuracy",
        timestamp: "2024-01-13T17:00:00Z"
      }
    ],
    history: [
      {
        id: "h2",
        action: "translation_updated",
        author: "Pierre Dubois",
        timestamp: "2024-01-13T16:45:00Z",
        oldValue: "Découvrez la puissance du développement web moderne...",
        newValue: "Découvrez la puissance du développement web moderne avec nos outils et services de pointe."
      }
    ]
  },
  {
    id: "4",
    key: "asset#3.alt_text",
    model: "asset",
    objectId: "3",
    field: "alt_text",
    sourceLocale: "EN",
    targetLocale: "DE",
    sourceText: "Team photo showing our diverse group of developers collaborating",
    targetText: "Teamfoto zeigt unsere vielfältige Gruppe von Entwicklern bei der Zusammenarbeit",
    status: "draft",
    assignee: "Hans Mueller",
    lastModified: "2024-01-12T09:15:00Z",
    modifiedBy: "Hans Mueller",
    priority: "low",
    context: "Team page hero image",
    comments: [],
    history: [
      {
        id: "h3",
        action: "translation_created",
        author: "Hans Mueller",
        timestamp: "2024-01-12T09:15:00Z"
      }
    ]
  }
];

const statusConfig = {
  missing: { label: "Missing", color: "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400", icon: AlertCircle },
  draft: { label: "Draft", color: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400", icon: Edit },
  needs_review: { label: "Needs Review", color: "bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400", icon: Eye },
  approved: { label: "Approved", color: "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400", icon: CheckCircle2 }
};

const TranslationsQueue = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [units, setUnits] = useState<TranslationUnit[]>([]);
  const [selectedUnits, setSelectedUnits] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [targetLocaleFilter, setTargetLocaleFilter] = useState<string>("all");
  const [sourceLocaleFilter, setSourceLocaleFilter] = useState<string>("all");
  const [modelFilter, setModelFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [assigneeFilter, setAssigneeFilter] = useState<string>("all");
  const [isLoading, setIsLoading] = useState(true);
  const [locales, setLocales] = useState<any[]>([]);
  const [pagination, setPagination] = useState({ page: 1, limit: 50, total: 0 });

  // Load more functionality
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const [selectedUnit, setSelectedUnit] = useState<TranslationUnit | null>(null);
  const [detailsPanelOpen, setDetailsPanelOpen] = useState(false);
  const [bulkActionsOpen, setBulkActionsOpen] = useState(false);

  // Assignment state
  const [users, setUsers] = useState<any[]>([]);
  const [assignmentOpen, setAssignmentOpen] = useState(false);
  const [bulkAssignmentOpen, setBulkAssignmentOpen] = useState(false);
  const [selectedAssignee, setSelectedAssignee] = useState<number | null>(null);
  const [assignmentComment, setAssignmentComment] = useState('');

  // Inline editing state
  const [editingUnits, setEditingUnits] = useState<Set<string>>(new Set());
  const [editingValues, setEditingValues] = useState<Record<string, string>>({});

  // Function to fetch translations
  const fetchTranslations = async (page: number = 1, append: boolean = false) => {
    if (page === 1) {
      setIsLoading(true);
    } else {
      setLoadingMore(true);
    }

    try {
      // Use the translations.list endpoint which maps to translation-units
      const response = await api.translations.list({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        page: page,
        limit: pagination.limit
      });

      // Handle both paginated and non-paginated responses
      const items = response.results || response.data || response;
      const totalItems = response.count || response.total || items?.length || 0;

      // Map API response to our TranslationUnit format
      const mappedUnits: TranslationUnit[] = (Array.isArray(items) ? items : []).map((item: any) => ({
        id: item.id?.toString() || '',
        key: item.key || `${item.content_type || item.model}#${item.object_id}.${item.field}`,
        model: item.model_label || 'page',
        objectId: item.object_id?.toString() || '',
        field: item.field || '',
        sourceLocale: item.source_locale_code || item.source_locale?.code || 'EN',
        targetLocale: item.target_locale_code || item.target_locale?.code || 'ES',
        sourceText: item.source_text || '',
        targetText: item.target_text || '',
        status: item.status || 'missing',
        assignee: item.assignee_name || item.assignee?.name || item.assignee || '',
        lastModified: item.updated_at || new Date().toISOString(),
        modifiedBy: item.updated_by_email || 'System',
        priority: item.priority || 'medium',
        context: item.context || item.description || '',
        comments: item.comments || [],
        history: item.history || item.revisions || []
      }));

      // Either append or replace units
      if (append) {
        setUnits(prev => [...prev, ...mappedUnits]);
      } else {
        setUnits(mappedUnits);
      }

      // Update pagination and hasMore state
      setPagination(prev => ({ ...prev, page, total: totalItems }));
      setHasMore(page * pagination.limit < totalItems);

    } catch (error) {
      console.error('Failed to fetch translations:', error);
      // Use mock data as fallback only on initial load
      if (page === 1) {
        setUnits(mockTranslationUnits);
        setPagination(prev => ({ ...prev, total: mockTranslationUnits.length }));
        setHasMore(false);
      }
    } finally {
      setIsLoading(false);
      setLoadingMore(false);
    }
  };

  // Fetch users for assignment
  const fetchUsers = async () => {
    try {
      const response = await api.users.list();
      const usersList = response.results || response.data || response;
      setUsers(Array.isArray(usersList) ? usersList : []);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      // Fallback users for development
      setUsers([
        { id: 1, email: 'admin@example.com', first_name: 'Admin', last_name: 'User' },
        { id: 2, email: 'translator@example.com', first_name: 'Translation', last_name: 'Team' },
        { id: 3, email: 'reviewer@example.com', first_name: 'Review', last_name: 'Team' },
      ]);
    }
  };

  // Fetch translations and locales on mount
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        // Fetch users first
        await fetchUsers();

        // Fetch locales first
        let localesResponse;
        try {
          localesResponse = await api.i18n.locales.list({ active_only: true });
        } catch (localeError) {
          console.error('Failed to fetch locales with i18n endpoint:', localeError);
          // Try alternate endpoints if the primary one fails
          try {
            const response = await fetch('/api/v1/i18n/locales/', {
              headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
              },
              credentials: 'include'
            });
            if (response.ok) {
              localesResponse = await response.json();
            }
          } catch (fetchError) {
            console.error('Failed to fetch locales directly:', fetchError);
          }
        }

        // Log the locales response to debug
        console.log('Locales response:', localesResponse);

        // Handle various response formats
        let localesList = [];
        if (localesResponse) {
          if (Array.isArray(localesResponse)) {
            localesList = localesResponse;
          } else if (localesResponse.results && Array.isArray(localesResponse.results)) {
            localesList = localesResponse.results;
          } else if (localesResponse.data && Array.isArray(localesResponse.data)) {
            localesList = localesResponse.data;
          }
        }

        // If still no locales, use defaults
        if (localesList.length === 0) {
          localesList = [
            { code: 'en', name: 'English', id: 1 },
            { code: 'es', name: 'Spanish', id: 2 },
            { code: 'fr', name: 'French', id: 3 },
            { code: 'de', name: 'German', id: 4 },
          ];
        }

        setLocales(localesList);
        console.log('Locales set to:', localesList);

        // Fetch translations
        await fetchTranslations();
      } catch (error: any) {
        console.error('Failed to fetch data:', error);

        // Show appropriate error message based on the error type
        if (error?.response?.status === 401) {
          toast({
            title: "Authentication Required",
            description: "Please log in to access translations.",
            variant: "destructive",
          });
        } else if (error?.response?.status === 403) {
          toast({
            title: "Access Denied",
            description: "You don't have permission to access translations.",
            variant: "destructive",
          });
        } else {
          toast({
            title: "Warning",
            description: "Using sample data. Backend may not be available.",
            variant: "destructive",
          });
        }

        // Fallback to mock data if API fails
        setUnits(mockTranslationUnits);
        // Also set some default locales as fallback
        setLocales([
          { code: 'en', name: 'English', id: 1 },
          { code: 'es', name: 'Spanish', id: 2 },
          { code: 'fr', name: 'French', id: 3 },
          { code: 'de', name: 'German', id: 4 },
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [toast]);

  // Load more handler
  const handleLoadMore = () => {
    if (!loadingMore && hasMore) {
      fetchTranslations(pagination.page + 1, true);
    }
  };

  // Refetch translations when filters change
  useEffect(() => {
    // Skip on initial mount
    if (!isLoading) {
      fetchTranslations(1, false);
    }
  }, [statusFilter, targetLocaleFilter, sourceLocaleFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  // Filter units
  const filteredUnits = units.filter(unit => {
    const matchesSearch = unit.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         unit.sourceText.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         unit.targetText.toLowerCase().includes(searchQuery.toLowerCase());
    // Compare locale codes case-insensitively - ensure we're comparing strings
    const unitTargetLocale = typeof unit.targetLocale === 'string' ? unit.targetLocale : String(unit.targetLocale || '');
    const unitSourceLocale = typeof unit.sourceLocale === 'string' ? unit.sourceLocale : String(unit.sourceLocale || '');
    const matchesTargetLocale = targetLocaleFilter === "all" ||
                                unitTargetLocale.toUpperCase() === targetLocaleFilter?.toUpperCase();
    const matchesSourceLocale = sourceLocaleFilter === "all" ||
                                unitSourceLocale.toUpperCase() === sourceLocaleFilter?.toUpperCase();
    const matchesModel = modelFilter === "all" || unit.model === modelFilter;
    const matchesStatus = statusFilter === "all" || unit.status === statusFilter;
    const matchesAssignee = assigneeFilter === "all" || unit.assignee === assigneeFilter;

    return matchesSearch && matchesTargetLocale && matchesSourceLocale && matchesModel && matchesStatus && matchesAssignee;
  });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleUnitSelect = (unitId: string) => {
    setSelectedUnits(prev =>
      prev.includes(unitId)
        ? prev.filter(id => id !== unitId)
        : [...prev, unitId]
    );
  };

  const handleSelectAll = () => {
    if (selectedUnits.length === filteredUnits.length && filteredUnits.length > 0) {
      setSelectedUnits([]);
    } else {
      setSelectedUnits(filteredUnits.map(unit => unit.id));
    }
  };

  const openUnitDetails = (unit: TranslationUnit) => {
    setSelectedUnit(unit);
    setDetailsPanelOpen(true);
  };

  const openTranslator = (unit: TranslationUnit) => {
    navigate(`/translations/workspace?unit=${unit.id}`);
  };

  // Inline editing functions
  const startInlineEdit = (unitId: string, currentText: string) => {
    setEditingUnits(prev => new Set([...prev, unitId]));
    // Ensure currentText is always a string, not an array
    const textValue = Array.isArray(currentText) ? '' : (currentText || '');
    setEditingValues(prev => ({ ...prev, [unitId]: textValue }));
  };

  const cancelInlineEdit = (unitId: string) => {
    setEditingUnits(prev => {
      const newSet = new Set(prev);
      newSet.delete(unitId);
      return newSet;
    });
    setEditingValues(prev => {
      const newValues = { ...prev };
      delete newValues[unitId];
      return newValues;
    });
  };

  const saveInlineEdit = async (unitId: string) => {
    const newText = editingValues[unitId];
    if (newText !== undefined) {
      try {
        // Ensure we're sending a string, not an array
        const textToSend = Array.isArray(newText) ? '' : (newText || '');
        // Update translation via API using the translations endpoint
        await api.translations.update(unitId, {
          target_text: textToSend,
          status: textToSend.trim() ? 'draft' : 'missing'
        });

        // Update local state
        setUnits(prev => prev.map(unit =>
          unit.id === unitId
            ? {
                ...unit,
                targetText: newText,
                status: newText.trim() ? (unit.status === 'missing' ? 'draft' : unit.status) : 'missing',
                lastModified: new Date().toISOString(),
                modifiedBy: 'Current User'
              }
            : unit
        ));

        toast({
          title: "Translation updated",
          description: "The translation has been saved successfully.",
        });
      } catch (error: any) {
        console.error('Failed to save translation:', error);
        const errorMessage = error?.response?.data?.detail ||
                           error?.response?.data?.message ||
                           "Failed to save translation. Please try again.";
        toast({
          title: "Error",
          description: errorMessage,
          variant: "destructive",
        });
      }
    }

    cancelInlineEdit(unitId);
  };

  const updateInlineEditValue = (unitId: string, value: string) => {
    setEditingValues(prev => ({ ...prev, [unitId]: value }));
  };

  const quickStatusChange = async (unitId: string, newStatus: TranslationUnit['status']) => {
    const unit = units.find(u => u.id === unitId);

    try {
      // Validate status change requirements
      if (newStatus === 'needs_review' && !unit?.targetText?.trim()) {
        toast({
          title: "Cannot mark as needs review",
          description: "Please add translation text before marking for review.",
          variant: "destructive",
        });
        return;
      }

      if (newStatus === 'approved' && !unit?.targetText?.trim()) {
        toast({
          title: "Cannot approve",
          description: "Please add translation text before approving.",
          variant: "destructive",
        });
        return;
      }

      // Handle different status changes with appropriate API calls
      if (newStatus === 'approved') {
        await api.i18n.translations.approve(unitId);
      } else if (newStatus === 'needs_review') {
        await api.i18n.translations.markNeedsReview(unitId);
      } else if (newStatus === 'draft') {
        await api.i18n.translations.markAsDraft(unitId);
      } else {
        await api.translations.update(unitId, { status: newStatus });
      }

      // Update local state
      setUnits(prev => prev.map(unit =>
        unit.id === unitId
          ? {
              ...unit,
              status: newStatus,
              lastModified: new Date().toISOString(),
              modifiedBy: 'Current User'
            }
          : unit
      ));

      toast({
        title: "Status updated",
        description: `Translation status changed to ${statusConfig[newStatus].label}.`,
      });
    } catch (error: any) {
      console.error('Failed to update status:', error);
      const errorMessage = error?.response?.data?.detail ||
                         error?.response?.data?.message ||
                         "Failed to update status. Please try again.";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const suggestTranslation = async (unitId: string) => {
    const unit = units.find(u => u.id === unitId);
    if (!unit) return;

    try {
      // Get MT suggestion from API
      const response = await api.i18n.translations.mtSuggest(
        unitId,
        unit.sourceText,
        unit.sourceLocale || 'en',
        unit.targetLocale || 'en',
        'deepl'
      );
      const suggestion = response.data?.suggestion || response.suggestion;

      if (suggestion) {
        startInlineEdit(unitId, suggestion);
        toast({
          title: "MT suggestion applied",
          description: "Machine translation suggestion has been applied. Please review and edit as needed.",
        });
      } else {
        toast({
          title: "No suggestion available",
          description: "Machine translation is not available for this text.",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error('Failed to get MT suggestion:', error);
      // Fallback to mock suggestions if API fails
      const mockSuggestions = {
        'ES': {
          'Welcome to Our Amazing Platform': 'Bienvenido a Nuestra Increíble Plataforma',
          'Learn more about our company, our mission, and the team behind our innovative solutions.': 'Aprende más sobre nuestra empresa, nuestra misión y el equipo detrás de nuestras soluciones innovadoras.',
        },
        'FR': {
          'Discover the power of modern web development with our cutting-edge tools and services.': 'Découvrez la puissance du développement web moderne avec nos outils et services de pointe.',
        },
        'DE': {
          'Team photo showing our diverse group of developers collaborating': 'Teamfoto zeigt unsere vielfältige Gruppe von Entwicklern bei der Zusammenarbeit',
        }
      };

      const fallbackSuggestion = mockSuggestions[unit.targetLocale as keyof typeof mockSuggestions]?.[unit.sourceText as keyof typeof mockSuggestions[keyof typeof mockSuggestions]];

      if (fallbackSuggestion) {
        startInlineEdit(unitId, fallbackSuggestion);
        toast({
          title: "MT suggestion applied (offline)",
          description: "Using offline suggestion. Please review and edit as needed.",
        });
      } else {
        toast({
          title: "Error",
          description: "Failed to get machine translation suggestion.",
          variant: "destructive",
        });
      }
    }
  };

  // Assignment functions
  const assignTranslation = async (unitId: string, assignedToId?: number, comment?: string) => {
    try {
      await api.i18n.translations.assign(unitId, assignedToId, comment);

      // Update local state
      setUnits(prev => prev.map(unit => {
        if (unit.id === unitId) {
          const assignedUser = assignedToId ? users.find(u => u.id === assignedToId) : null;
          return {
            ...unit,
            assignee: assignedUser ? `${assignedUser.first_name} ${assignedUser.last_name}` : '',
            lastModified: new Date().toISOString(),
            modifiedBy: 'Current User'
          };
        }
        return unit;
      }));

      const assignedUser = assignedToId ? users.find(u => u.id === assignedToId) : null;
      toast({
        title: "Assignment updated",
        description: assignedUser
          ? `Translation assigned to ${assignedUser.first_name} ${assignedUser.last_name}`
          : "Translation unassigned",
      });
    } catch (error: any) {
      console.error('Failed to assign translation:', error);
      const errorMessage = error?.response?.data?.detail ||
                         error?.response?.data?.message ||
                         "Failed to assign translation. Please try again.";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const bulkAssignTranslations = async (unitIds: string[], assignedToId?: number, comment?: string) => {
    try {
      const numericIds = unitIds.map(id => parseInt(id)).filter(id => !isNaN(id));
      await api.i18n.translations.bulkAssign(numericIds, assignedToId, comment);

      // Update local state
      setUnits(prev => prev.map(unit => {
        if (unitIds.includes(unit.id)) {
          const assignedUser = assignedToId ? users.find(u => u.id === assignedToId) : null;
          return {
            ...unit,
            assignee: assignedUser ? `${assignedUser.first_name} ${assignedUser.last_name}` : '',
            lastModified: new Date().toISOString(),
            modifiedBy: 'Current User'
          };
        }
        return unit;
      }));

      const assignedUser = assignedToId ? users.find(u => u.id === assignedToId) : null;
      toast({
        title: "Bulk assignment complete",
        description: assignedUser
          ? `${unitIds.length} translations assigned to ${assignedUser.first_name} ${assignedUser.last_name}`
          : `${unitIds.length} translations unassigned`,
      });

      setSelectedUnits([]);
    } catch (error: any) {
      console.error('Failed to bulk assign translations:', error);
      const errorMessage = error?.response?.data?.detail ||
                         error?.response?.data?.message ||
                         "Failed to assign translations. Please try again.";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const getUserDisplayName = (user: any) => {
    if (user.first_name && user.last_name) {
      return `${user.first_name} ${user.last_name}`;
    }
    return user.email || user.username || 'Unknown User';
  };

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
                <div>
                  <h1 className="text-3xl font-bold text-foreground">Translation Queue</h1>
                  <p className="text-muted-foreground mt-1">
                    Manage content translations across all locales • Click any target text to translate inline
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {selectedUnits.length > 0 && (
                    <DropdownMenu open={bulkActionsOpen} onOpenChange={setBulkActionsOpen}>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline">
                          Bulk Actions ({selectedUnits.length})
                          <ChevronDown className="w-4 h-4 ml-2" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-56">
                        <DropdownMenuItem onClick={async () => {
                          // Bulk MT suggest
                          for (const unitId of selectedUnits) {
                            await suggestTranslation(unitId);
                          }
                          setBulkActionsOpen(false);
                        }}>
                          <Sparkles className="w-4 h-4 mr-2" />
                          MT Suggest
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => {
                          setBulkActionsOpen(false);
                          setBulkAssignmentOpen(true);
                        }}>
                          <UserCheck className="w-4 h-4 mr-2" />
                          Assign
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => {
                          // Export selected translations to CSV
                          const selectedData = units.filter(u => selectedUnits.includes(u.id));
                          const csv = [
                            ['Key', 'Source Locale', 'Target Locale', 'Source Text', 'Target Text', 'Status', 'Priority'],
                            ...selectedData.map(u => [
                              u.key,
                              u.sourceLocale,
                              u.targetLocale,
                              u.sourceText,
                              u.targetText,
                              u.status,
                              u.priority
                            ])
                          ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');

                          const blob = new Blob([csv], { type: 'text/csv' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `translations_${new Date().toISOString().split('T')[0]}.csv`;
                          document.body.appendChild(a);
                          a.click();
                          document.body.removeChild(a);
                          URL.revokeObjectURL(url);

                          toast({
                            title: "Export complete",
                            description: `Exported ${selectedData.length} translations to CSV.`,
                          });
                          setBulkActionsOpen(false);
                        }}>
                          <Download className="w-4 h-4 mr-2" />
                          Export CSV
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={async () => {
                          // Bulk approve - only approve units that have target text
                          const unitsToApprove = selectedUnits.filter(unitId => {
                            const unit = units.find(u => u.id === unitId);
                            return unit?.targetText?.trim();
                          });

                          if (unitsToApprove.length === 0) {
                            toast({
                              title: "No translations to approve",
                              description: "Selected translations need target text before they can be approved.",
                              variant: "destructive",
                            });
                            setBulkActionsOpen(false);
                            return;
                          }

                          if (unitsToApprove.length < selectedUnits.length) {
                            const skipped = selectedUnits.length - unitsToApprove.length;
                            toast({
                              title: "Some translations skipped",
                              description: `${skipped} translations were skipped because they don't have target text.`,
                            });
                          }

                          try {
                            await Promise.all(
                              unitsToApprove.map(unitId => api.i18n.translations.approve(unitId))
                            );

                            setUnits(prev => prev.map(unit =>
                              unitsToApprove.includes(unit.id)
                                ? { ...unit, status: 'approved' as TranslationUnit['status'] }
                                : unit
                            ));

                            toast({
                              title: "Bulk approval complete",
                              description: `Approved ${unitsToApprove.length} translations.`,
                            });
                            setSelectedUnits([]);
                          } catch (error: any) {
                            console.error('Bulk approval failed:', error);
                            const errorMessage = error?.response?.data?.detail ||
                                               "Failed to approve some translations.";
                            toast({
                              title: "Error",
                              description: errorMessage,
                              variant: "destructive",
                            });
                          }
                          setBulkActionsOpen(false);
                        }}>
                          <CheckCircle2 className="w-4 h-4 mr-2" />
                          Approve
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
              </div>

              {/* Filters */}
              <Card>
                <CardContent className="p-4">
                  <div className="space-y-4">
                    {/* Search */}
                    <div className="relative max-w-sm">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        placeholder="Search translations..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                      />
                    </div>

                    {/* Filter Row */}
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                      <Select value={targetLocaleFilter} onValueChange={setTargetLocaleFilter}>
                        <SelectTrigger>
                          <SelectValue placeholder="Target Locale" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Target Locales</SelectItem>
                          {locales.length === 0 ? (
                            <>
                              <SelectItem value="EN">English (EN)</SelectItem>
                              <SelectItem value="ES">Spanish (ES)</SelectItem>
                              <SelectItem value="FR">French (FR)</SelectItem>
                              <SelectItem value="DE">German (DE)</SelectItem>
                            </>
                          ) : (
                            locales.map((locale: any) => {
                              const code = locale.code || locale.locale_code || locale.id?.toString() || '';
                              const name = locale.name || locale.display_name || code;
                              return (
                                <SelectItem key={code} value={code.toUpperCase()}>
                                  {name} ({code.toUpperCase()})
                                </SelectItem>
                              );
                            })
                          )}
                        </SelectContent>
                      </Select>

                      <Select value={sourceLocaleFilter} onValueChange={setSourceLocaleFilter}>
                        <SelectTrigger>
                          <SelectValue placeholder="Source Locale" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Source Locales</SelectItem>
                          {locales.length === 0 ? (
                            <>
                              <SelectItem value="EN">English (EN)</SelectItem>
                              <SelectItem value="ES">Spanish (ES)</SelectItem>
                              <SelectItem value="FR">French (FR)</SelectItem>
                              <SelectItem value="DE">German (DE)</SelectItem>
                            </>
                          ) : (
                            locales.map((locale: any) => {
                              const code = locale.code || locale.locale_code || locale.id?.toString() || '';
                              const name = locale.name || locale.display_name || code;
                              return (
                                <SelectItem key={`source-${code}`} value={code.toUpperCase()}>
                                  {name} ({code.toUpperCase()})
                                </SelectItem>
                              );
                            })
                          )}
                        </SelectContent>
                      </Select>

                      <Select value={modelFilter} onValueChange={setModelFilter}>
                        <SelectTrigger>
                          <SelectValue placeholder="Model" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Models</SelectItem>
                          <SelectItem value="page">Page</SelectItem>
                          <SelectItem value="block">Block</SelectItem>
                          <SelectItem value="asset">Asset</SelectItem>
                        </SelectContent>
                      </Select>

                      <Select value={statusFilter} onValueChange={setStatusFilter}>
                        <SelectTrigger>
                          <SelectValue placeholder="Status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Statuses</SelectItem>
                          <SelectItem value="missing">Missing</SelectItem>
                          <SelectItem value="draft">Draft</SelectItem>
                          <SelectItem value="needs_review">Needs Review</SelectItem>
                          <SelectItem value="approved">Approved</SelectItem>
                        </SelectContent>
                      </Select>

                      <Select value={assigneeFilter} onValueChange={setAssigneeFilter}>
                        <SelectTrigger>
                          <SelectValue placeholder="Assignee" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Assignees</SelectItem>
                          {/* Dynamic assignee list from data */}
                          {Array.from(new Set(
                            units
                              .map(unit => unit.assignee)
                              .filter(Boolean)
                          )).map(assignee => (
                            <SelectItem key={assignee} value={assignee}>
                              {assignee}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      <div className="flex items-center">
                        <Checkbox
                          id="select-all"
                          checked={selectedUnits.length === filteredUnits.length && filteredUnits.length > 0}
                          onCheckedChange={handleSelectAll}
                        />
                        <Label htmlFor="select-all" className="ml-2 text-sm">
                          Select All ({filteredUnits.length})
                        </Label>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Translation Units List */}
              <Card>
                <CardContent className="p-0">
                  {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="text-center">
                        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent mx-auto mb-4" />
                        <p className="text-muted-foreground">Loading translations...</p>
                      </div>
                    </div>
                  ) : filteredUnits.length === 0 ? (
                    <TranslationsEmptyState />
                  ) : (
                  <div className="divide-y">
                    {filteredUnits.map((unit) => {
                      const isSelected = selectedUnits.includes(unit.id);
                      const statusInfo = statusConfig[unit.status];
                      const StatusIcon = statusInfo.icon;
                      const isEditing = editingUnits.has(unit.id);
                      const editValue = editingValues[unit.id] || unit.targetText;

                      return (
                        <div
                          key={unit.id}
                          className={`p-4 space-y-4 ${
                            isSelected ? 'bg-primary/5' : ''
                          } ${isEditing ? 'bg-accent/20' : 'hover:bg-muted/30'}`}
                        >
                          {/* Header Row */}
                          <div className="flex items-center gap-4">
                            <Checkbox
                              checked={isSelected}
                              onCheckedChange={() => handleUnitSelect(unit.id)}
                            />

                            <div className="flex-1 flex items-center gap-2">
                              <code className="text-sm font-mono bg-muted px-2 py-1 rounded">
                                {unit.key}
                              </code>
                              <Badge variant="secondary" className="text-xs">
                                {unit.model}
                              </Badge>
                              {unit.priority === 'high' && (
                                <Badge variant="destructive" className="text-xs">
                                  High Priority
                                </Badge>
                              )}
                            </div>

                            {/* Status and Actions */}
                            <div className="flex items-center gap-2">
                              <Badge className={statusInfo.color}>
                                <StatusIcon className="w-3 h-3 mr-1" />
                                {statusInfo.label}
                              </Badge>

                              {!isEditing && (
                                <div className="flex gap-1">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => startInlineEdit(unit.id, unit.targetText)}
                                    title="Edit inline"
                                  >
                                    <Edit className="w-3 h-3" />
                                  </Button>

                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => suggestTranslation(unit.id)}
                                    title="Get MT suggestion"
                                  >
                                    <Sparkles className="w-3 h-3" />
                                  </Button>

                                  <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                      <Button variant="ghost" size="sm">
                                        <ChevronDown className="w-3 h-3" />
                                      </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                      <DropdownMenuItem onClick={() => quickStatusChange(unit.id, 'draft')}>
                                        <Edit className="w-3 h-3 mr-2" />
                                        Mark as Draft
                                      </DropdownMenuItem>
                                      <DropdownMenuItem
                                        onClick={() => quickStatusChange(unit.id, 'needs_review')}
                                        disabled={!unit.targetText?.trim()}
                                      >
                                        <Eye className="w-3 h-3 mr-2" />
                                        Needs Review
                                        {!unit.targetText?.trim() && (
                                          <span className="text-xs text-muted-foreground ml-1">(requires text)</span>
                                        )}
                                      </DropdownMenuItem>
                                      <DropdownMenuItem
                                        onClick={() => quickStatusChange(unit.id, 'approved')}
                                        disabled={!unit.targetText?.trim()}
                                      >
                                        <CheckCircle2 className="w-3 h-3 mr-2" />
                                        Approve
                                        {!unit.targetText?.trim() && (
                                          <span className="text-xs text-muted-foreground ml-1">(requires text)</span>
                                        )}
                                      </DropdownMenuItem>
                                      <DropdownMenuItem onClick={() => {
                                        setSelectedUnit(unit);
                                        setAssignmentOpen(true);
                                      }}>
                                        <UserCheck className="w-3 h-3 mr-2" />
                                        Assign
                                      </DropdownMenuItem>
                                      <DropdownMenuItem onClick={() => openUnitDetails(unit)}>
                                        <MessageSquare className="w-3 h-3 mr-2" />
                                        View Details
                                      </DropdownMenuItem>
                                    </DropdownMenuContent>
                                  </DropdownMenu>
                                </div>
                              )}

                              {isEditing && (
                                <div className="flex gap-1">
                                  <Button
                                    variant="default"
                                    size="sm"
                                    onClick={() => saveInlineEdit(unit.id)}
                                    title="Save translation"
                                  >
                                    <Save className="w-3 h-3" />
                                  </Button>

                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => cancelInlineEdit(unit.id)}
                                    title="Cancel editing"
                                  >
                                    <X className="w-3 h-3" />
                                  </Button>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Translation Content */}
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {/* Source */}
                            <div className="space-y-2">
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-xs">
                                  {unit.sourceLocale}
                                </Badge>
                                <span className="text-muted-foreground text-xs">Source</span>
                              </div>
                              <div className="p-3 bg-muted/30 rounded-md">
                                <p className="text-sm text-foreground leading-relaxed">
                                  {unit.sourceText}
                                </p>
                              </div>
                            </div>

                            {/* Target */}
                            <div className="space-y-2">
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="text-xs">
                                  {unit.targetLocale}
                                </Badge>
                                <span className="text-muted-foreground text-xs">Target</span>
                                {isEditing && (
                                  <Badge variant="secondary" className="text-xs">
                                    Editing
                                  </Badge>
                                )}
                              </div>

                              {isEditing ? (
                                <div className="space-y-2">
                                  <Textarea
                                    value={editValue}
                                    onChange={(e) => updateInlineEditValue(unit.id, e.target.value)}
                                    className="min-h-[100px] resize-none"
                                    placeholder="Enter translation..."
                                    autoFocus
                                  />
                                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                                    <span>{editValue.length} characters</span>
                                    <div className="flex gap-2">
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => updateInlineEditValue(unit.id, unit.targetText)}
                                        title="Reset to original"
                                      >
                                        <RotateCcw className="w-3 h-3 mr-1" />
                                        Reset
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => suggestTranslation(unit.id)}
                                        title="Get MT suggestion"
                                      >
                                        <Sparkles className="w-3 h-3 mr-1" />
                                        Suggest
                                      </Button>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div
                                  className="p-3 bg-background border rounded-md cursor-text min-h-[60px] flex items-start hover:border-primary/50 transition-colors"
                                  onClick={() => startInlineEdit(unit.id, Array.isArray(unit.targetText) ? '' : unit.targetText)}
                                >
                                  {unit.targetText ? (
                                    <p className="text-sm text-foreground leading-relaxed">
                                      {unit.targetText}
                                    </p>
                                  ) : (
                                    <p className="text-sm text-muted-foreground italic">
                                      Click to add translation...
                                    </p>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Context and Metadata */}
                          <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
                            <div className="flex items-center gap-4">
                              {unit.context && (
                                <span>Context: {unit.context}</span>
                              )}
                              {unit.assignee && (
                                <div className="flex items-center gap-1">
                                  <User className="w-3 h-3" />
                                  {unit.assignee}
                                </div>
                              )}
                            </div>
                            <div className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {formatDate(unit.lastModified)}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  )}
                </CardContent>
              </Card>

              {/* Load More Button */}
              {hasMore && (
                <div className="flex flex-col items-center gap-2 py-6">
                  <p className="text-sm text-muted-foreground">
                    Showing {units.length} of {pagination.total} translations
                  </p>
                  <Button
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    variant="outline"
                    className="w-full max-w-xs"
                  >
                    {loadingMore ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Loading more...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Load More ({Math.min(pagination.limit, pagination.total - units.length)} more)
                      </>
                    )}
                  </Button>
                </div>
              )}

            </div>
          </main>
        </div>
      </div>

      {/* Unit Details Sheet */}
      <Sheet open={detailsPanelOpen} onOpenChange={setDetailsPanelOpen}>
        <SheetContent className="sm:max-w-lg">
          {selectedUnit && (
            <>
              <SheetHeader>
                <SheetTitle>{selectedUnit.key}</SheetTitle>
                <SheetDescription>
                  Translation details and history
                </SheetDescription>
              </SheetHeader>

              <div className="space-y-6 py-6">
                {/* Unit Info */}
                <div>
                  <h3 className="font-medium mb-3">Unit Information</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Model:</span>
                      <Badge variant="secondary">{selectedUnit.model}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Object ID:</span>
                      <code className="text-xs bg-muted px-1 rounded">{selectedUnit.objectId}</code>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Field:</span>
                      <code className="text-xs bg-muted px-1 rounded">{selectedUnit.field}</code>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Priority:</span>
                      <Badge variant={selectedUnit.priority === 'high' ? 'destructive' : 'secondary'}>
                        {selectedUnit.priority}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Status:</span>
                      <Badge className={statusConfig[selectedUnit.status].color}>
                        {statusConfig[selectedUnit.status].label}
                      </Badge>
                    </div>
                    {selectedUnit.assignee && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Assignee:</span>
                        <span>{selectedUnit.assignee}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Source and Target */}
                <div>
                  <h3 className="font-medium mb-3">Translation</h3>
                  <div className="space-y-4">
                    <div>
                      <Label className="text-xs text-muted-foreground">
                        Source ({selectedUnit.sourceLocale})
                      </Label>
                      <div className="mt-1 p-3 bg-muted/30 rounded-lg text-sm">
                        {selectedUnit.sourceText}
                      </div>
                    </div>

                    <div>
                      <Label className="text-xs text-muted-foreground">
                        Target ({selectedUnit.targetLocale})
                      </Label>
                      <div className="mt-1 p-3 bg-muted/30 rounded-lg text-sm">
                        {selectedUnit.targetText || (
                          <span className="text-muted-foreground italic">No translation yet</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Context */}
                {selectedUnit.context && (
                  <div>
                    <h3 className="font-medium mb-3">Context</h3>
                    <p className="text-sm text-muted-foreground bg-muted/30 p-3 rounded-lg">
                      {selectedUnit.context}
                    </p>
                  </div>
                )}

                {/* Comments */}
                <div>
                  <h3 className="font-medium mb-3">Comments ({selectedUnit.comments.length})</h3>
                  {selectedUnit.comments.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No comments yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {selectedUnit.comments.map((comment) => (
                        <div key={comment.id} className="bg-muted/30 p-3 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium">{comment.author}</span>
                            <span className="text-xs text-muted-foreground">
                              {formatDate(comment.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm">{comment.text}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* History */}
                <div>
                  <h3 className="font-medium mb-3">History ({selectedUnit.history.length})</h3>
                  {selectedUnit.history.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No history yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {selectedUnit.history.map((entry) => (
                        <div key={entry.id} className="text-sm border-l-2 border-muted pl-3">
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{entry.action.replace('_', ' ')}</span>
                            <span className="text-xs text-muted-foreground">
                              {formatDate(entry.timestamp)}
                            </span>
                          </div>
                          <div className="text-muted-foreground">by {entry.author}</div>
                          {entry.oldValue && entry.newValue && (
                            <div className="mt-1 text-xs">
                              <div className="text-red-600">- {entry.oldValue.length > 50 ? entry.oldValue.substring(0, 50) + "..." : entry.oldValue}</div>
                              <div className="text-green-600">+ {entry.newValue.length > 50 ? entry.newValue.substring(0, 50) + "..." : entry.newValue}</div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="space-y-2">
                  <Button
                    className="w-full"
                    onClick={() => openTranslator(selectedUnit)}
                  >
                    <Languages className="w-4 h-4 mr-2" />
                    Open in Translator
                  </Button>

                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setAssignmentOpen(true)}
                    >
                      <UserCheck className="w-4 h-4 mr-2" />
                      Assign
                    </Button>
                    <Button variant="outline" size="sm">
                      <Sparkles className="w-4 h-4 mr-2" />
                      MT Suggest
                    </Button>
                  </div>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Assignment Modal */}
      <Sheet open={assignmentOpen} onOpenChange={(open) => {
        setAssignmentOpen(open);
        if (!open) {
          setSelectedAssignee(null);
          setAssignmentComment('');
        }
      }}>
        <SheetContent className="sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Assign Translation</SheetTitle>
            <SheetDescription>
              {selectedUnit ? `Assign ${selectedUnit.key}` : 'Assign translation to a user'}
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-4 py-6">
            <div>
              <Label htmlFor="assignee">Assignee</Label>
              <Select value={selectedAssignee?.toString() || 'none'} onValueChange={(value) => setSelectedAssignee(value === 'none' ? null : parseInt(value))}>
                <SelectTrigger>
                  <SelectValue placeholder="Select user..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Unassigned</SelectItem>
                  {users.map((user) => (
                    <SelectItem key={user.id} value={user.id.toString()}>
                      {getUserDisplayName(user)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="comment">Comment (optional)</Label>
              <Textarea
                id="comment"
                value={assignmentComment}
                onChange={(e) => setAssignmentComment(e.target.value)}
                placeholder="Add a note about this assignment..."
                className="mt-1"
              />
            </div>

            <div className="flex gap-2 pt-4">
              <Button
                onClick={async () => {
                  if (selectedUnit) {
                    await assignTranslation(selectedUnit.id, selectedAssignee || undefined, assignmentComment || undefined);
                    setAssignmentOpen(false);
                    setSelectedAssignee(null);
                    setAssignmentComment('');
                  }
                }}
                className="flex-1"
              >
                Assign
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setAssignmentOpen(false);
                  setSelectedAssignee(null);
                  setAssignmentComment('');
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>

      {/* Bulk Assignment Modal */}
      <Sheet open={bulkAssignmentOpen} onOpenChange={(open) => {
        setBulkAssignmentOpen(open);
        if (!open) {
          setSelectedAssignee(null);
          setAssignmentComment('');
        }
      }}>
        <SheetContent className="sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Bulk Assign Translations</SheetTitle>
            <SheetDescription>
              Assign {selectedUnits.length} selected translations
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-4 py-6">
            <div>
              <Label htmlFor="bulk-assignee">Assignee</Label>
              <Select value={selectedAssignee?.toString() || 'none'} onValueChange={(value) => setSelectedAssignee(value === 'none' ? null : parseInt(value))}>
                <SelectTrigger>
                  <SelectValue placeholder="Select user..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Unassigned</SelectItem>
                  {users.map((user) => (
                    <SelectItem key={user.id} value={user.id.toString()}>
                      {getUserDisplayName(user)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="bulk-comment">Comment (optional)</Label>
              <Textarea
                id="bulk-comment"
                value={assignmentComment}
                onChange={(e) => setAssignmentComment(e.target.value)}
                placeholder="Add a note about this bulk assignment..."
                className="mt-1"
              />
            </div>

            <div className="bg-muted/30 p-3 rounded-lg">
              <p className="text-sm text-muted-foreground">
                {selectedUnits.length} translations will be assigned
              </p>
            </div>

            <div className="flex gap-2 pt-4">
              <Button
                onClick={async () => {
                  await bulkAssignTranslations(selectedUnits, selectedAssignee || undefined, assignmentComment || undefined);
                  setBulkAssignmentOpen(false);
                  setSelectedAssignee(null);
                  setAssignmentComment('');
                }}
                className="flex-1"
              >
                Assign All
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setBulkAssignmentOpen(false);
                  setSelectedAssignee(null);
                  setAssignmentComment('');
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>

    </div>
  );
};

export default TranslationsQueue;
