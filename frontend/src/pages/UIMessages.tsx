import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api.ts";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Alert,
  AlertDescription,
} from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import {
  Search,
  Filter,
  Download,
  Upload,
  ExternalLink,
  Eye,
  Edit,
  Save,
  X,
  Check,
  AlertCircle,
  CheckCircle2,
  Clock,
  ChevronDown,
  Code,
  Globe,
  RefreshCw,
  Loader2,
  Languages,
  FileCode2,
  GitPullRequest,
  Database,
  Zap,
} from "lucide-react";

interface UIMessage {
  id: number;
  key: string;
  namespace: string;
  description: string;
  default_value: string;
  created_at: string;
  updated_at: string;
}

interface UIMessageTranslation {
  id: number;
  message: number;
  locale: number;
  locale_code?: string;
  value: string;
  status: 'missing' | 'draft' | 'needs_review' | 'approved';
  updated_by?: string;
  updated_at: string;
}

interface MessageWithTranslations extends UIMessage {
  translations: Record<string, UIMessageTranslation>;
}

const statusConfig = {
  missing: {
    label: "Missing",
    color: "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400",
    icon: AlertCircle
  },
  draft: {
    label: "Draft",
    color: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400",
    icon: Edit
  },
  needs_review: {
    label: "Needs Review",
    color: "bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400",
    icon: Clock
  },
  approved: {
    label: "Approved",
    color: "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400",
    icon: CheckCircle2
  }
};

const UIMessages = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [messages, setMessages] = useState<MessageWithTranslations[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedMessages, setSelectedMessages] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [namespaceFilter, setNamespaceFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [localeFilter, setLocaleFilter] = useState<string>("all");
  const [locales, setLocales] = useState<any[]>([]);
  const [namespaces, setNamespaces] = useState<string[]>([]);
  const [selectedLocale, setSelectedLocale] = useState<string>("");

  const [editingCell, setEditingCell] = useState<{messageId: number, localeCode: string} | null>(null);
  const [editingValue, setEditingValue] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [syncDirection, setSyncDirection] = useState<'import' | 'export' | 'sync'>('import');
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [autoTranslating, setAutoTranslating] = useState(false);
  const [autoTranslateTaskId, setAutoTranslateTaskId] = useState<string | null>(null);
  const [autoTranslateProgress, setAutoTranslateProgress] = useState({
    current: 0,
    total: 0,
    percentage: 0,
    translated: 0,
    errors: 0,
    skipped: 0
  });

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const pageSize = 50; // Messages per page

  // Stats from API
  const [stats, setStats] = useState({
    totalMessages: 0,
    totalTranslations: 0,
    translated: 0,
    missing: 0,
    needsReview: 0,
    draft: 0
  });

  // Fetch data on component mount
  useEffect(() => {
    loadData(1, false);
  }, []);

  const loadData = async (page = 1, append = false) => {
    if (page === 1) {
      setLoading(true);
    } else {
      setLoadingMore(true);
    }

    try {
      // Fetch locales first (only on initial load)
      if (page === 1) {
        const localesResponse = await api.i18n.locales.list({ active_only: true });
        const activeLocales = localesResponse.results || [];
        setLocales(activeLocales);
        console.log('Loaded locales:', activeLocales);

        // Set default selected locale (first non-default locale)
        if (activeLocales.length > 0) {
          const nonDefaultLocale = activeLocales.find((l: any) => !l.is_default) || activeLocales[0];
          setSelectedLocale(nonDefaultLocale.code);
        }
      }

      // Fetch UI messages with pagination
      const offset = (page - 1) * pageSize;
      const messagesResponse = await api.request<any>({
        method: 'GET',
        url: '/api/v1/i18n/ui-messages/',
        params: {
          limit: pageSize,
          offset: offset
        }
      });

      const messagesList = messagesResponse.results || messagesResponse || [];
      const totalMessages = messagesResponse.count || messagesList.length;
      console.log(`Loaded messages: ${messagesList.length} (page ${page})`);

      setTotalCount(totalMessages);
      setHasMore(offset + messagesList.length < totalMessages);

      // Fetch translation statistics (only on first page load)
      if (page === 1) {
        try {
          const statsResponse = await api.request<any>({
            method: 'GET',
            url: '/api/v1/i18n/ui-message-translations/',
            params: {
              limit: 1 // We only need the count, not the data
            }
          });

          // Get all translations to calculate stats
          const allTranslationsForStats = await api.request<any>({
            method: 'GET',
            url: '/api/v1/i18n/ui-message-translations/',
            params: {
              limit: 5000 // Large limit to get all translations for stats
            }
          });

          const allTranslations = allTranslationsForStats.results || allTranslationsForStats || [];
          const totalTranslationsCount = allTranslationsForStats.count || allTranslations.length;

          // Calculate status counts
          const statusCounts = {
            totalMessages: totalMessages,
            totalTranslations: totalTranslationsCount,
            translated: 0,
            missing: 0,
            needsReview: 0,
            draft: 0
          };

          allTranslations.forEach((translation: any) => {
            switch (translation.status) {
              case 'approved':
                statusCounts.translated++;
                break;
              case 'missing':
                statusCounts.missing++;
                break;
              case 'needs_review':
                statusCounts.needsReview++;
                break;
              case 'draft':
                statusCounts.draft++;
                break;
              default:
                if (!translation.value || translation.value.trim() === '') {
                  statusCounts.missing++;
                } else {
                  statusCounts.draft++;
                }
                break;
            }
          });

          setStats(statusCounts);
        } catch (error) {
          console.error('Failed to fetch translation stats:', error);
        }
      }

      // Fetch translations for these messages
      const messageIds = messagesList.map((m: any) => m.id);
      if (messageIds.length > 0) {
        console.log('Fetching translations for message IDs:', messageIds);

        // Fetch all translations with a higher limit
        // We'll filter them client-side for the messages we need
        const allTranslationsResponse = await api.request<any>({
          method: 'GET',
          url: '/api/v1/i18n/ui-message-translations/',
          params: {
            limit: 5000,  // Get more translations at once (increased from 1000)
            offset: 0
          }
        });

        const allTranslationsRaw = allTranslationsResponse.results || allTranslationsResponse || [];

        // Filter translations for only the messages we're displaying
        const messageIdSet = new Set(messageIds);
        const allTranslations = allTranslationsRaw.filter((t: any) => messageIdSet.has(t.message));
        console.log('Loaded translations:', allTranslations.length);
        console.log('Sample translation:', allTranslations[0]);
        console.log('All translations raw count:', allTranslationsRaw.length);
        console.log('First 5 raw translations:', allTranslationsRaw.slice(0, 5));

        // Get current locales (use existing if available)
        const activeLocales = locales.length > 0 ? locales : (await api.i18n.locales.list({ active_only: true })).results || [];

        // Create a map of translations by message ID and locale ID
        const translationsByMessage: Record<number, Record<string, UIMessageTranslation>> = {};

        for (const translation of allTranslations) {
          const locale = activeLocales.find((l: any) => l.id === translation.locale);
          if (locale) {
            if (!translationsByMessage[translation.message]) {
              translationsByMessage[translation.message] = {};
            }

            // Log French translations to debug
            if (locale.code === 'fr' && translation.value) {
              console.log(`French translation found: Message ID ${translation.message}, Value: "${translation.value}"`);
            }

            translationsByMessage[translation.message][locale.code] = {
              ...translation,
              locale_code: locale.code
            };
          }
        }

        // Combine messages with their translations
        const messagesWithTranslations: MessageWithTranslations[] = messagesList.map((message: any) => {
          const translations = translationsByMessage[message.id] || {};

          // Add missing translations for locales that don't have one
          for (const locale of activeLocales) {
            if (!translations[locale.code] && !locale.is_default) {
              translations[locale.code] = {
                id: 0,
                message: message.id,
                locale: locale.id,
                locale_code: locale.code,
                value: '',
                status: 'missing',
                updated_at: ''
              };
            }
          }

          return {
            ...message,
            translations
          };
        });

        // Either append or replace messages
        if (append) {
          setMessages(prev => [...prev, ...messagesWithTranslations]);
        } else {
          setMessages(messagesWithTranslations);
        }

        console.log('Final messages with translations:', messagesWithTranslations.length);
        if (messagesWithTranslations.length > 0) {
          console.log('Sample message with translations:', messagesWithTranslations[0]);
          console.log('Translations for first message:', messagesWithTranslations[0].translations);
        }
      }

      // Get unique namespaces (only update on initial load)
      if (page === 1) {
        const uniqueNamespaces = [...new Set(messagesList.map((msg: any) => msg.namespace))];
        setNamespaces(uniqueNamespaces);
      }

      setCurrentPage(page);

    } catch (error) {
      console.error('Failed to load data:', error);
      toast({
        title: "Error",
        description: "Failed to load UI messages. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const handleLoadMore = () => {
    if (!loadingMore && hasMore) {
      loadData(currentPage + 1, true);
    }
  };

  // Filter messages
  const filteredMessages = messages.filter(message => {
    const matchesSearch =
      message.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
      message.default_value.toLowerCase().includes(searchQuery.toLowerCase()) ||
      Object.values(message.translations).some(trans =>
        trans.value && trans.value.toLowerCase().includes(searchQuery.toLowerCase())
      );

    const matchesNamespace = namespaceFilter === "all" || message.namespace === namespaceFilter;

    const matchesStatus = statusFilter === "all" ||
      Object.values(message.translations).some(trans => trans.status === statusFilter);

    const matchesLocale = localeFilter === "all" ||
      (localeFilter === "missing" && Object.values(message.translations).some(trans =>
        trans.status === "missing" || !trans.value
      ));

    return matchesSearch && matchesNamespace && matchesStatus && matchesLocale;
  });

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleMessageSelect = (messageId: string) => {
    setSelectedMessages(prev =>
      prev.includes(messageId)
        ? prev.filter(id => id !== messageId)
        : [...prev, messageId]
    );
  };

  const handleSelectAll = () => {
    if (selectedMessages.length === filteredMessages.length && filteredMessages.length > 0) {
      setSelectedMessages([]);
    } else {
      setSelectedMessages(filteredMessages.map(msg => msg.id.toString()));
    }
  };

  const startEditingCell = (messageId: number, localeCode: string, currentValue: string) => {
    setEditingCell({ messageId, localeCode });
    setEditingValue(currentValue || '');
  };

  const cancelEditing = () => {
    setEditingCell(null);
    setEditingValue("");
  };

  const saveTranslation = async () => {
    if (!editingCell) return;

    setSaving(true);
    try {
      const message = messages.find(m => m.id === editingCell.messageId);
      const locale = locales.find(l => l.code === editingCell.localeCode);

      if (!message || !locale) {
        throw new Error('Message or locale not found');
      }

      const translation = message.translations[editingCell.localeCode];

      if (translation && translation.id > 0) {
        // Update existing translation
        await api.request({
          method: 'PATCH',
          url: `/api/v1/i18n/ui-message-translations/${translation.id}/`,
          data: {
            value: editingValue,
            status: editingValue ? 'draft' : 'missing'
          }
        });
      } else {
        // Create new translation
        await api.request({
          method: 'POST',
          url: '/api/v1/i18n/ui-message-translations/',
          data: {
            message: message.id,
            locale: locale.id,
            value: editingValue,
            status: editingValue ? 'draft' : 'missing'
          }
        });
      }

      toast({
        title: "Translation saved",
        description: `Translation for ${message.key} in ${editingCell.localeCode} has been saved.`,
      });

      // Reload data to get updated translations
      await loadData();

      cancelEditing();
    } catch (error) {
      console.error('Failed to save translation:', error);
      toast({
        title: "Error",
        description: "Failed to save translation. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleBulkApprove = async () => {
    if (selectedMessages.length === 0) {
      toast({
        title: "No messages selected",
        description: "Please select messages to approve.",
        variant: "destructive",
      });
      return;
    }

    try {
      setSaving(true);

      const updates = [];
      for (const messageId of selectedMessages) {
        const message = messages.find(m => m.id.toString() === messageId);
        if (message) {
          for (const translation of Object.values(message.translations)) {
            if (translation.id > 0 && translation.status === 'draft') {
              updates.push({
                id: translation.id,
                status: 'approved'
              });
            }
          }
        }
      }

      if (updates.length > 0) {
        // Use bulk update endpoint
        await api.request({
          method: 'POST',
          url: '/api/v1/i18n/ui-message-translations/bulk_update/',
          data: {
            updates: updates.map(u => ({
              message_id: u.id,
              locale_id: locales.find(l => l.code === selectedLocale)?.id,
              value: '',
              status: u.status
            }))
          }
        });

        toast({
          title: "Translations approved",
          description: `${updates.length} translations have been approved.`,
        });

        await loadData();
        setSelectedMessages([]);
      }
    } catch (error) {
      console.error('Failed to approve translations:', error);
      toast({
        title: "Error",
        description: "Failed to approve translations. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async () => {
    try {
      // Get messages bundle for export
      const locale = locales.find(l => l.code === selectedLocale);
      if (!locale) {
        throw new Error('No locale selected');
      }

      const response = await api.request<Record<string, string>>({
        method: 'GET',
        url: `/api/v1/i18n/ui/messages/${locale.code}.json`,
      });

      // Convert to JSON and download
      const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ui-messages-${locale.code}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast({
        title: "Export successful",
        description: `UI messages exported for ${locale.code}`,
      });
    } catch (error) {
      console.error('Failed to export messages:', error);
      toast({
        title: "Error",
        description: "Failed to export messages. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleSyncPoFiles = async () => {
    setSyncing(true);
    try {
      const response = await api.request({
        method: 'POST',
        url: '/api/v1/i18n/ui-messages/sync_po_files/',
        data: {
          direction: syncDirection,
          locale: selectedLocale || undefined,
          namespace: namespaceFilter !== 'all' ? namespaceFilter : 'django'
        }
      });

      if (response.status === 'success') {
        toast({
          title: "Sync successful",
          description: response.message,
        });

        // Show details if available
        if (response.details) {
          console.log('Sync details:', response.details);
        }

        // Reload data to show new/updated messages
        await loadData();
      } else {
        throw new Error(response.message);
      }
    } catch (error: any) {
      console.error('Failed to sync PO files:', error);
      toast({
        title: "Sync failed",
        description: error.message || "Failed to sync with .po files",
        variant: "destructive",
      });
    } finally {
      setSyncing(false);
      setShowSyncModal(false);
    }
  };

  const handleImportDjangoStrings = async () => {
    setSyncing(true);
    try {
      const response = await api.request({
        method: 'POST',
        url: '/api/v1/i18n/ui-messages/import_django_strings/',
        data: {
          locale: selectedLocale || undefined,
          namespace: 'django'
        }
      });

      if (response.status === 'success') {
        toast({
          title: "Import successful",
          description: "Django built-in strings imported successfully",
        });

        // Reload data to show new messages
        await loadData();
      } else {
        throw new Error(response.message);
      }
    } catch (error: any) {
      console.error('Failed to import Django strings:', error);
      toast({
        title: "Import failed",
        description: error.message || "Failed to import Django strings",
        variant: "destructive",
      });
    } finally {
      setSyncing(false);
    }
  };

  const checkTaskStatus = async (taskId: string) => {
    try {
      const response = await api.request({
        method: 'GET',
        url: '/api/v1/i18n/ui-message-translations/task_status/',
        params: { task_id: taskId }
      });

      const { status, progress, message, results, error } = response;

      if (progress) {
        setAutoTranslateProgress(progress);
      }

      if (status === 'SUCCESS') {
        setAutoTranslating(false);
        setAutoTranslateTaskId(null);

        toast({
          title: "Auto-translation completed",
          description: message,
        });

        // Reload data to show new translations
        await loadData();
      } else if (status === 'FAILURE') {
        setAutoTranslating(false);
        setAutoTranslateTaskId(null);

        toast({
          title: "Auto-translation failed",
          description: error || message,
          variant: "destructive",
        });
      } else if (status === 'PROGRESS' || status === 'PENDING') {
        // Continue polling
        setTimeout(() => checkTaskStatus(taskId), 2000);
      }
    } catch (error: any) {
      console.error('Failed to check task status:', error);
      setAutoTranslating(false);
      setAutoTranslateTaskId(null);

      toast({
        title: "Status check failed",
        description: "Failed to check auto-translation progress",
        variant: "destructive",
      });
    }
  };

  const handleAutoTranslate = async () => {
    if (!selectedLocale) {
      toast({
        title: "No locale selected",
        description: "Please select a locale for auto-translation",
        variant: "destructive",
      });
      return;
    }

    setAutoTranslating(true);
    setAutoTranslateProgress({
      current: 0,
      total: 0,
      percentage: 0,
      translated: 0,
      errors: 0,
      skipped: 0
    });

    try {
      const response = await api.request({
        method: 'POST',
        url: '/api/v1/i18n/ui-message-translations/bulk_auto_translate/',
        data: {
          locale: selectedLocale,
          source_locale: 'en',
          namespace: namespaceFilter !== 'all' ? namespaceFilter : undefined,
          max_translations: undefined // Translate all missing messages
        }
      });

      if (response.status === 'started') {
        const taskId = response.task_id;
        setAutoTranslateTaskId(taskId);

        toast({
          title: "Auto-translation started",
          description: response.message,
        });

        // Start polling for task status
        setTimeout(() => checkTaskStatus(taskId), 1000);
      } else if (response.status === 'success') {
        // Task completed (either no messages to translate or eager mode)
        setAutoTranslating(false);

        if (response.eager_mode && response.results) {
          // Show detailed results for eager mode
          const details = response.results;
          toast({
            title: "Auto-translation completed",
            description: `${details.translated || 0} translations created, ${details.errors || 0} errors, ${details.skipped || 0} skipped`,
          });
        } else {
          toast({
            title: "Auto-translation completed",
            description: response.message,
          });
        }

        // Reload data to show new translations
        await loadData();
      } else {
        throw new Error(response.message);
      }
    } catch (error: any) {
      console.error('Failed to start auto-translation:', error);
      setAutoTranslating(false);
      toast({
        title: "Auto-translation failed",
        description: error.response?.data?.message || error.message || "Failed to start auto-translation",
        variant: "destructive",
      });
    }
  };

  const handleImportJSON = async () => {
    if (!importFile) {
      toast({
        title: "No file selected",
        description: "Please select a JSON file to import",
        variant: "destructive",
      });
      return;
    }

    if (!selectedLocale) {
      toast({
        title: "No locale selected",
        description: "Please select a locale for the import",
        variant: "destructive",
      });
      return;
    }

    setImporting(true);
    try {
      // Prepare FormData for file upload
      const formData = new FormData();
      formData.append('file', importFile);
      formData.append('locale', selectedLocale);
      formData.append('namespace', namespaceFilter !== 'all' ? namespaceFilter : 'general');
      formData.append('flatten_keys', 'true');

      // Use the new import endpoint
      const response = await api.request({
        method: 'POST',
        url: '/api/v1/i18n/ui-messages/import_json/',
        data: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.status === 'success') {
        const details = response.details;
        toast({
          title: "Import successful",
          description: `Imported ${details.total_keys} translations (${details.messages_created} messages created, ${details.translations_created} translations created, ${details.messages_updated + details.translations_updated} updated)`,
        });
      } else if (response.status === 'warning') {
        const details = response.details;
        toast({
          title: "Import partially successful",
          description: response.message,
          variant: "destructive",
        });

        // Show errors in console
        if (details.errors && details.errors.length > 0) {
          console.error('Import errors:', details.errors);
        }
      } else {
        // Error case
        const details = response.details;
        if (details && details.errors && details.errors.length > 0) {
          console.error('Import errors:', details.errors);
          // Show first few errors to user
          const errorSummary = details.errors.slice(0, 3).join(', ');
          throw new Error(`${response.message}. Errors: ${errorSummary}`);
        } else {
          throw new Error(response.message || 'Import failed');
        }
      }

      // Reload data to show imported messages
      await loadData();

      // Close modal and reset
      setShowImportModal(false);
      setImportFile(null);
    } catch (error: any) {
      console.error('Failed to import JSON:', error);
      toast({
        title: "Import failed",
        description: error.response?.data?.message || error.message || "Failed to import JSON file",
        variant: "destructive",
      });
    } finally {
      setImporting(false);
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
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
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
            <div className="max-w-full mx-auto space-y-6">

              {/* Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-foreground">UI Messages</h1>
                  <p className="text-muted-foreground mt-1">
                    Manage interface translations for all locales
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" onClick={loadData} disabled={loading}>
                    <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    {loading ? 'Loading...' : 'Refresh'}
                  </Button>

                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline" disabled={syncing}>
                        {syncing ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                          <GitPullRequest className="w-4 h-4 mr-2" />
                        )}
                        Sync .po Files
                        <ChevronDown className="w-4 h-4 ml-2" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                      <DropdownMenuItem onClick={() => {
                        setSyncDirection('import');
                        handleSyncPoFiles();
                      }} disabled={syncing}>
                        <FileCode2 className="w-4 h-4 mr-2" />
                        Import from .po files
                        <span className="ml-auto text-xs text-muted-foreground">
                          Backend → DB
                        </span>
                      </DropdownMenuItem>

                      <DropdownMenuItem onClick={() => {
                        setSyncDirection('export');
                        handleSyncPoFiles();
                      }} disabled={syncing}>
                        <Upload className="w-4 h-4 mr-2" />
                        Export to .po files
                        <span className="ml-auto text-xs text-muted-foreground">
                          DB → Backend
                        </span>
                      </DropdownMenuItem>

                      <DropdownMenuItem onClick={() => {
                        setSyncDirection('sync');
                        handleSyncPoFiles();
                      }} disabled={syncing}>
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Bidirectional sync
                        <span className="ml-auto text-xs text-muted-foreground">
                          Merge both
                        </span>
                      </DropdownMenuItem>

                      <DropdownMenuItem
                        className="border-t"
                        onClick={handleImportDjangoStrings}
                        disabled={syncing}
                      >
                        <Database className="w-4 h-4 mr-2" />
                        Import Django strings
                        <span className="ml-auto text-xs text-muted-foreground">
                          Built-in
                        </span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>

                  <Button variant="outline" onClick={handleExport}>
                    <Download className="w-4 h-4 mr-2" />
                    Export JSON
                  </Button>

                  <Button variant="outline" onClick={() => setShowImportModal(true)}>
                    <Upload className="w-4 h-4 mr-2" />
                    Import JSON
                  </Button>

                  <Button
                    variant="outline"
                    onClick={handleAutoTranslate}
                    disabled={autoTranslating || !selectedLocale}
                  >
                    {autoTranslating ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Zap className="w-4 h-4 mr-2" />
                    )}
                    {autoTranslating ? (
                      autoTranslateProgress.total > 0
                        ? `Translating... ${autoTranslateProgress.percentage}%`
                        : 'Starting translation...'
                    ) : 'Auto-translate All'}
                  </Button>
                </div>
              </div>

              {/* Auto-translation Progress */}
              {autoTranslating && autoTranslateProgress.total > 0 && (
                <Card className="bg-primary/5 border-primary/20">
                  <CardContent className="p-4">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="font-medium">Auto-translating UI Messages</h3>
                        <Badge variant="outline" className="text-primary">
                          {autoTranslateProgress.percentage}% Complete
                        </Badge>
                      </div>

                      <div className="w-full bg-muted rounded-full h-2">
                        <div
                          className="bg-primary h-2 rounded-full transition-all duration-500"
                          style={{ width: `${autoTranslateProgress.percentage}%` }}
                        />
                      </div>

                      <div className="grid grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Progress:</span>
                          <div className="font-medium">
                            {autoTranslateProgress.current} / {autoTranslateProgress.total}
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Translated:</span>
                          <div className="font-medium text-green-600">
                            {autoTranslateProgress.translated}
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Errors:</span>
                          <div className="font-medium text-red-600">
                            {autoTranslateProgress.errors}
                          </div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Skipped:</span>
                          <div className="font-medium text-yellow-600">
                            {autoTranslateProgress.skipped}
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Overview Stats */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="w-5 h-5" />
                    Translation Overview
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    <div className="space-y-1">
                      <div className="text-2xl font-bold text-foreground">{stats.totalMessages.toLocaleString()}</div>
                      <div className="text-sm text-muted-foreground">UI Messages</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-2xl font-bold text-foreground">{stats.totalTranslations.toLocaleString()}</div>
                      <div className="text-sm text-muted-foreground">Total Translations</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-2xl font-bold text-green-600">{stats.translated.toLocaleString()}</div>
                      <div className="text-sm text-muted-foreground">Translated</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-2xl font-bold text-red-600">{stats.missing.toLocaleString()}</div>
                      <div className="text-sm text-muted-foreground">Missing</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-2xl font-bold text-orange-600">{stats.needsReview.toLocaleString()}</div>
                      <div className="text-sm text-muted-foreground">Needs Review</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-2xl font-bold text-yellow-600">{stats.draft.toLocaleString()}</div>
                      <div className="text-sm text-muted-foreground">Draft</div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {stats.totalTranslations > 0 && (
                    <div className="mt-4 space-y-2">
                      <div className="flex justify-between text-sm text-muted-foreground">
                        <span>Translation Progress</span>
                        <span>{Math.round((stats.translated / stats.totalTranslations) * 100)}% Complete</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div
                          className="bg-green-600 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${(stats.translated / stats.totalTranslations) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Filters */}
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-4 flex-wrap">
                    <div className="flex-1 min-w-[200px]">
                      <div className="relative">
                        <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                        <Input
                          placeholder="Search messages..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="pl-10"
                        />
                      </div>
                    </div>

                    <Select value={selectedLocale} onValueChange={setSelectedLocale}>
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="Select locale" />
                      </SelectTrigger>
                      <SelectContent>
                        {locales.filter(l => !l.is_default && l.is_active).length === 0 ? (
                          <SelectItem value="no-locales" disabled>
                            No active locales available
                          </SelectItem>
                        ) : (
                          locales.filter(l => !l.is_default && l.is_active).map(locale => (
                            <SelectItem key={locale.code} value={locale.code}>
                              <div className="flex items-center gap-2">
                                <Globe className="w-4 h-4" />
                                {locale.name} ({locale.code})
                                {locale.native_name && locale.native_name !== locale.name && (
                                  <span className="text-xs text-muted-foreground ml-1">
                                    {locale.native_name}
                                  </span>
                                )}
                              </div>
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>

                    <Select value={namespaceFilter} onValueChange={setNamespaceFilter}>
                      <SelectTrigger className="w-[150px]">
                        <SelectValue placeholder="Namespace" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Namespaces</SelectItem>
                        {namespaces.map(ns => (
                          <SelectItem key={ns} value={ns}>{ns}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger className="w-[150px]">
                        <SelectValue placeholder="Status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Status</SelectItem>
                        <SelectItem value="missing">Missing</SelectItem>
                        <SelectItem value="draft">Draft</SelectItem>
                        <SelectItem value="needs_review">Needs Review</SelectItem>
                        <SelectItem value="approved">Approved</SelectItem>
                      </SelectContent>
                    </Select>

                    <Button
                      variant="outline"
                      onClick={() => {
                        setSearchQuery("");
                        setNamespaceFilter("all");
                        setStatusFilter("all");
                        setLocaleFilter("all");
                      }}
                    >
                      Clear Filters
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Bulk Actions */}
              {selectedMessages.length > 0 && (
                <Card className="bg-primary/5 border-primary/20">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">
                        {selectedMessages.length} message{selectedMessages.length !== 1 ? 's' : ''} selected
                      </p>
                      <div className="flex items-center gap-2">
                        <Button size="sm" variant="outline" onClick={handleBulkApprove}>
                          <Check className="w-4 h-4 mr-1" />
                          Approve Selected
                        </Button>
                        <Button size="sm" variant="outline">
                          <Clock className="w-4 h-4 mr-1" />
                          Mark for Review
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleAutoTranslate}
                          disabled={autoTranslating || !selectedLocale}
                        >
                          <Zap className="w-4 h-4 mr-1" />
                          Auto-translate Missing
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setSelectedMessages([])}>
                          Clear Selection
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}


              {/* Messages Table */}
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[40px]">
                          <Checkbox
                            checked={selectedMessages.length === filteredMessages.length && filteredMessages.length > 0}
                            onCheckedChange={handleSelectAll}
                          />
                        </TableHead>
                        <TableHead>Key</TableHead>
                        <TableHead>Default</TableHead>
                        <TableHead>{selectedLocale} Translation</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Last Modified</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredMessages.map((message) => {
                        // Debug logging
                        if (message.key === 'common.save') {
                          console.log('Message:', message);
                          console.log('Selected locale:', selectedLocale);
                          console.log('Message translations:', message.translations);
                          console.log('Translation for selected locale:', message.translations[selectedLocale]);
                        }

                        const translation = message.translations[selectedLocale] || {
                          value: '',
                          status: 'missing',
                          updated_at: ''
                        };
                        const StatusIcon = statusConfig[translation.status]?.icon || AlertCircle;
                        const isEditing = editingCell?.messageId === message.id &&
                                        editingCell?.localeCode === selectedLocale;

                        return (
                          <TableRow key={message.id}>
                            <TableCell>
                              <Checkbox
                                checked={selectedMessages.includes(message.id.toString())}
                                onCheckedChange={() => handleMessageSelect(message.id.toString())}
                              />
                            </TableCell>

                            <TableCell>
                              <div>
                                <code className="text-sm font-mono">
                                  {message.key}
                                </code>
                                <div className="flex items-center gap-2 mt-1">
                                  <Badge variant="outline" className="text-xs">
                                    {message.namespace}
                                  </Badge>
                                </div>
                              </div>
                            </TableCell>

                            <TableCell className="max-w-xs">
                              <p className="text-sm truncate" title={message.default_value}>
                                {message.default_value}
                              </p>
                              {message.description && (
                                <p className="text-xs text-muted-foreground mt-1">
                                  {message.description}
                                </p>
                              )}
                            </TableCell>

                            <TableCell className="max-w-xs">
                              {isEditing ? (
                                <div className="flex items-center gap-2">
                                  <Input
                                    value={editingValue}
                                    onChange={(e) => setEditingValue(e.target.value)}
                                    className="text-sm"
                                    autoFocus
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') saveTranslation();
                                      if (e.key === 'Escape') cancelEditing();
                                    }}
                                  />
                                  <Button size="sm" onClick={saveTranslation} disabled={saving}>
                                    <Save className="w-4 h-4" />
                                  </Button>
                                  <Button size="sm" variant="ghost" onClick={cancelEditing}>
                                    <X className="w-4 h-4" />
                                  </Button>
                                </div>
                              ) : (
                                <div
                                  className="group cursor-pointer p-1 -m-1 rounded hover:bg-accent"
                                  onClick={() => startEditingCell(message.id, selectedLocale, translation.value || message.default_value)}
                                >
                                  <p className="text-sm truncate" title={translation.value || message.default_value}>
                                    {translation.value ? (
                                      translation.value
                                    ) : (
                                      <span className="text-muted-foreground italic">
                                        {message.default_value ? `Click to translate: "${message.default_value}"` : 'Click to add translation'}
                                      </span>
                                    )}
                                  </p>
                                  <Edit className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity inline ml-2" />
                                </div>
                              )}
                            </TableCell>

                            <TableCell>
                              <Badge className={statusConfig[translation.status]?.color}>
                                <StatusIcon className="w-3 h-3 mr-1" />
                                {statusConfig[translation.status]?.label}
                              </Badge>
                            </TableCell>

                            <TableCell>
                              <div className="text-sm text-muted-foreground">
                                {formatDate(translation.updated_at || message.updated_at)}
                              </div>
                            </TableCell>

                            <TableCell>
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="sm">
                                    <ChevronDown className="w-4 h-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem
                                    onClick={() => startEditingCell(message.id, selectedLocale, translation.value || message.default_value)}
                                  >
                                    <Edit className="w-4 h-4 mr-2" />
                                    Edit Translation
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </CardContent>

                {/* Load More Button */}
                {hasMore && (
                  <div className="p-4 border-t">
                    <div className="flex flex-col items-center gap-2">
                      <p className="text-sm text-muted-foreground">
                        Showing {messages.length} of {totalCount} messages
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
                            Load More ({Math.min(pageSize, totalCount - messages.length)} more)
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            </div>
          </main>
        </div>
      </div>

      {/* Sync Confirmation Dialog */}
      <Dialog open={showSyncModal} onOpenChange={setShowSyncModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <GitPullRequest className="w-5 h-5" />
              Sync with .po Files
            </DialogTitle>
            <DialogDescription>
              Choose how you want to synchronize translation files between the database and backend .po files.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                This operation will sync messages for the <strong>{selectedLocale || 'all locales'}</strong>
                {namespaceFilter !== 'all' && ` in the ${namespaceFilter} namespace`}.
              </AlertDescription>
            </Alert>

            <div className="space-y-3">
              <div className="flex items-start space-x-3">
                <FileCode2 className="w-5 h-5 mt-0.5 text-muted-foreground" />
                <div className="flex-1">
                  <p className="font-medium">Import from .po files</p>
                  <p className="text-sm text-muted-foreground">
                    Import messages from backend .po files into the database
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <Upload className="w-5 h-5 mt-0.5 text-muted-foreground" />
                <div className="flex-1">
                  <p className="font-medium">Export to .po files</p>
                  <p className="text-sm text-muted-foreground">
                    Export database messages to backend .po files
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <RefreshCw className="w-5 h-5 mt-0.5 text-muted-foreground" />
                <div className="flex-1">
                  <p className="font-medium">Bidirectional sync</p>
                  <p className="text-sm text-muted-foreground">
                    Merge messages from both sources, preserving the latest changes
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Sync Direction</Label>
              <Select value={syncDirection} onValueChange={(value: any) => setSyncDirection(value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="import">Import (Backend → Database)</SelectItem>
                  <SelectItem value="export">Export (Database → Backend)</SelectItem>
                  <SelectItem value="sync">Bidirectional Sync</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSyncModal(false)} disabled={syncing}>
              Cancel
            </Button>
            <Button onClick={handleSyncPoFiles} disabled={syncing}>
              {syncing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <GitPullRequest className="w-4 h-4 mr-2" />
                  Start Sync
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import JSON Modal */}
      <Dialog open={showImportModal} onOpenChange={setShowImportModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Import JSON Translations
            </DialogTitle>
            <DialogDescription>
              Import translations from a JSON file. The file should contain key-value pairs where keys are message keys and values are translations.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Locale Selection */}
            <div className="space-y-2">
              <Label>Target Locale *</Label>
              <Select value={selectedLocale} onValueChange={setSelectedLocale}>
                <SelectTrigger>
                  <SelectValue placeholder="Select locale for import" />
                </SelectTrigger>
                <SelectContent>
                  {locales.length === 0 ? (
                    <SelectItem value="loading" disabled>
                      Loading locales...
                    </SelectItem>
                  ) : locales.filter(l => !l.is_default && l.is_active).length > 0 ? (
                    locales.filter(l => !l.is_default && l.is_active).map(locale => (
                      <SelectItem key={locale.code} value={locale.code}>
                        <div className="flex items-center justify-between w-full">
                          <div className="flex items-center gap-2">
                            <Globe className="w-4 h-4" />
                            {locale.name} ({locale.code})
                          </div>
                          <div className="flex items-center gap-1">
                            <Badge variant="outline" className="text-xs">
                              Active
                            </Badge>
                            {locale.native_name && locale.native_name !== locale.name && (
                              <span className="text-xs text-muted-foreground ml-2">
                                {locale.native_name}
                              </span>
                            )}
                          </div>
                        </div>
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="no-locales" disabled>
                      <div className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4" />
                        No active locales available
                      </div>
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Select which locale these translations are for. Only active non-default locales are shown.
              </p>
            </div>

            {/* File Upload */}
            <div className="space-y-2">
              <Label htmlFor="json-file">JSON File</Label>
              <Input
                id="json-file"
                type="file"
                accept=".json,application/json"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    // Validate file type
                    if (!file.name.endsWith('.json')) {
                      toast({
                        title: "Invalid file",
                        description: "Please select a JSON file",
                        variant: "destructive",
                      });
                      e.target.value = '';
                      return;
                    }
                    setImportFile(file);
                  }
                }}
                disabled={importing}
              />
              {importFile && (
                <p className="text-sm text-muted-foreground">
                  Selected: {importFile.name} ({(importFile.size / 1024).toFixed(2)} KB)
                </p>
              )}
            </div>

            {/* Format Example */}
            <Alert>
              <Code className="h-4 w-4" />
              <AlertDescription>
                <p className="font-medium mb-2">Expected JSON format:</p>
                <pre className="text-xs bg-muted p-2 rounded mt-2">
{`{
  "buttons.save": "Save",
  "buttons.cancel": "Cancel",
  "navigation.home": "Home",
  "validation.required": "This field is required"
}`}
                </pre>
              </AlertDescription>
            </Alert>

            {/* Import Options */}
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <ul className="text-sm space-y-1">
                  <li>• New keys will create new messages</li>
                  <li>• Existing keys will update translations</li>
                  <li>• Imported translations will have "draft" status</li>
                  <li>• Namespace: {namespaceFilter !== 'all' ? namespaceFilter : 'general'}</li>
                </ul>
              </AlertDescription>
            </Alert>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowImportModal(false);
                setImportFile(null);
              }}
              disabled={importing}
            >
              Cancel
            </Button>
            <Button
              onClick={handleImportJSON}
              disabled={importing || !importFile || !selectedLocale || locales.filter(l => !l.is_default && l.is_active).length === 0}
            >
              {importing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Import
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default UIMessages;
