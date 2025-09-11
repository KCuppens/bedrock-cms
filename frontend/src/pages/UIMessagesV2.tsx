import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
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
  Plus,
  RefreshCw,
  FileDown,
  FileUp,
} from "lucide-react";

interface UIMessage {
  id: number;
  namespace: string;
  key: string;
  default_value: string;
  description?: string;
  created_at: string;
  updated_at: string;
  translations?: UIMessageTranslation[];
}

interface UIMessageTranslation {
  id: number;
  message: number;
  locale: number;
  locale_code?: string;
  locale_name?: string;
  value: string;
  status: 'missing' | 'draft' | 'needs_review' | 'approved' | 'rejected';
  updated_by?: any;
  updated_at: string;
  created_at: string;
}

interface Locale {
  id: number;
  code: string;
  name: string;
  native_name: string;
  is_active: boolean;
  is_default: boolean;
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
  },
  rejected: { 
    label: "Rejected", 
    color: "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400", 
    icon: X 
  }
};

const UIMessages = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [locales, setLocales] = useState<Locale[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedNamespace, setSelectedNamespace] = useState("all");
  const [selectedLocale, setSelectedLocale] = useState<number | "all">("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [editingCell, setEditingCell] = useState<{messageId: number, localeId: number} | null>(null);
  const [editValue, setEditValue] = useState("");
  const [selectedMessages, setSelectedMessages] = useState<number[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [newMessage, setNewMessage] = useState({
    namespace: "common",
    key: "",
    default_value: "",
    description: ""
  });

  // Fetch data on mount
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch locales
      const localesResponse = await api.i18n.locales.list({ active_only: true });
      setLocales(localesResponse.results || []);
      
      // Fetch UI messages
      const messagesResponse = await api.request({
        method: 'GET',
        url: '/api/v1/i18n/ui-messages/',
      });
      
      // Fetch translations for each message
      const messagesWithTranslations = await Promise.all(
        (messagesResponse.results || []).map(async (message: UIMessage) => {
          const translationsResponse = await api.request({
            method: 'GET',
            url: '/api/v1/i18n/ui-message-translations/',
            params: { message: message.id }
          });
          
          // Add locale info to each translation
          const translationsWithLocale = (translationsResponse.results || []).map((trans: UIMessageTranslation) => {
            const locale = locales.find(l => l.id === trans.locale);
            return {
              ...trans,
              locale_code: locale?.code,
              locale_name: locale?.name
            };
          });
          
          return {
            ...message,
            translations: translationsWithLocale
          };
        })
      );
      
      setMessages(messagesWithTranslations);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast({
        title: "Error",
        description: "Failed to load UI messages",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleAddMessage = async () => {
    try {
      await api.request({
        method: 'POST',
        url: '/api/v1/i18n/ui-messages/',
        data: newMessage
      });
      
      toast({
        title: "Message created",
        description: "UI message has been created successfully.",
      });
      
      setShowAddModal(false);
      setNewMessage({
        namespace: "common",
        key: "",
        default_value: "",
        description: ""
      });
      
      await fetchData();
    } catch (error) {
      console.error('Error creating message:', error);
      toast({
        title: "Error",
        description: "Failed to create message",
        variant: "destructive",
      });
    }
  };

  const syncPoFiles = async (direction: 'import' | 'export' | 'sync') => {
    try {
      const response = await api.request({
        method: 'POST',
        url: '/api/v1/i18n/sync-po-files/',
        data: { direction }
      });
      
      toast({
        title: "Sync completed",
        description: `Successfully ${direction}ed .po files`,
      });
      
      if (direction === 'import' || direction === 'sync') {
        await fetchData();
      }
    } catch (error) {
      console.error('Error syncing .po files:', error);
      toast({
        title: "Error",
        description: `Failed to ${direction} .po files`,
        variant: "destructive",
      });
    }
  };

  const importDjangoStrings = async () => {
    try {
      await api.request({
        method: 'POST',
        url: '/api/v1/i18n/import-django-strings/',
      });
      
      toast({
        title: "Import completed",
        description: "Django built-in strings imported successfully",
      });
      
      await fetchData();
    } catch (error) {
      console.error('Error importing Django strings:', error);
      toast({
        title: "Error",
        description: "Failed to import Django strings",
        variant: "destructive",
      });
    }
  };

  const startEdit = (messageId: number, localeId: number) => {
    const message = messages.find(m => m.id === messageId);
    if (message) {
      const translation = message.translations?.find(t => t.locale === localeId);
      setEditingCell({ messageId, localeId });
      setEditValue(translation?.value || "");
    }
  };

  const saveEdit = async () => {
    if (editingCell) {
      try {
        const message = messages.find(m => m.id === editingCell.messageId);
        const translation = message?.translations?.find(t => t.locale === editingCell.localeId);
        
        if (translation) {
          // Update existing translation
          await api.request({
            method: 'PATCH',
            url: `/api/v1/i18n/ui-message-translations/${translation.id}/`,
            data: {
              value: editValue,
              status: editValue ? 'draft' : 'missing'
            }
          });
        } else {
          // Create new translation
          await api.request({
            method: 'POST',
            url: '/api/v1/i18n/ui-message-translations/',
            data: {
              message: editingCell.messageId,
              locale: editingCell.localeId,
              value: editValue,
              status: editValue ? 'draft' : 'missing'
            }
          });
        }
        
        // Refresh data
        await fetchData();
        
        toast({
          title: "Translation saved",
          description: "The translation has been updated successfully.",
        });
      } catch (error) {
        console.error('Error saving translation:', error);
        toast({
          title: "Error",
          description: "Failed to save translation",
          variant: "destructive",
        });
      }
      
      setEditingCell(null);
      setEditValue("");
    }
  };

  const cancelEdit = () => {
    setEditingCell(null);
    setEditValue("");
  };

  const exportMessages = async (localeCode: string) => {
    try {
      const response = await api.request({
        method: 'GET',
        url: `/api/v1/i18n/ui/messages/${localeCode}.json`,
      });
      
      const json = JSON.stringify(response, null, 2);
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ui-messages-${localeCode}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting messages:', error);
      toast({
        title: "Error",
        description: "Failed to export messages",
        variant: "destructive",
      });
    }
  };

  const approveTranslation = async (translationId: number) => {
    try {
      await api.request({
        method: 'PATCH',
        url: `/api/v1/i18n/ui-message-translations/${translationId}/`,
        data: { status: 'approved' }
      });
      
      await fetchData();
      
      toast({
        title: "Translation approved",
        description: "The translation has been approved.",
      });
    } catch (error) {
      console.error('Error approving translation:', error);
      toast({
        title: "Error",
        description: "Failed to approve translation",
        variant: "destructive",
      });
    }
  };

  // Get unique namespaces
  const namespaces = [...new Set(messages.map(m => m.namespace))];
  
  // Filter messages
  const filteredMessages = messages.filter(message => {
    const matchesSearch = 
      message.key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      message.default_value.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (message.description || "").toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesNamespace = selectedNamespace === "all" || message.namespace === selectedNamespace;
    
    const matchesLocale = selectedLocale === "all" || 
      message.translations?.some(t => t.locale === selectedLocale);
    
    const matchesStatus = selectedStatus === "all" ||
      message.translations?.some(t => t.status === selectedStatus);
    
    return matchesSearch && matchesNamespace && matchesLocale && matchesStatus;
  });

  // Calculate statistics
  const totalMessages = messages.length;
  const totalTranslations = messages.reduce((acc, msg) => 
    acc + (msg.translations?.length || 0), 0
  );
  const missingTranslations = messages.reduce((acc, msg) => {
    const expectedTranslations = locales.filter(l => !l.is_default).length;
    const actualTranslations = msg.translations?.filter(t => 
      t.value && t.status !== 'missing'
    ).length || 0;
    return acc + (expectedTranslations - actualTranslations);
  }, 0);
  const approvedTranslations = messages.reduce((acc, msg) => 
    acc + (msg.translations?.filter(t => t.status === 'approved').length || 0), 0
  );

  if (loading) {
    return (
      <div className="min-h-screen">
        <div className="flex">
          <Sidebar />
          <div className="flex-1 flex flex-col ml-72">
            <TopNavbar />
            <main className="flex-1 p-8">
              <div className="text-center py-12">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-primary" />
                <p className="text-muted-foreground">Loading UI messages...</p>
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
            <div className="max-w-7xl mx-auto space-y-6">
              
              {/* Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-foreground">UI Messages</h1>
                  <p className="text-muted-foreground mt-1">
                    Manage user interface translations and strings
                  </p>
                </div>
                <div className="flex gap-2">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline">
                        <FileDown className="w-4 h-4 mr-2" />
                        Import/Export
                        <ChevronDown className="w-4 h-4 ml-2" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => syncPoFiles('import')}>
                        <FileUp className="w-4 h-4 mr-2" />
                        Import from .po files
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => syncPoFiles('export')}>
                        <FileDown className="w-4 h-4 mr-2" />
                        Export to .po files
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => syncPoFiles('sync')}>
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Sync (bidirectional)
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={importDjangoStrings}>
                        <Code className="w-4 h-4 mr-2" />
                        Import Django strings
                      </DropdownMenuItem>
                      {locales.map(locale => (
                        <DropdownMenuItem 
                          key={locale.id}
                          onClick={() => exportMessages(locale.code)}
                        >
                          <Download className="w-4 h-4 mr-2" />
                          Export {locale.name} JSON
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                  <Button onClick={() => setShowAddModal(true)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Add Message
                  </Button>
                </div>
              </div>

              {/* Statistics */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <Globe className="w-8 h-8 text-primary" />
                      <div>
                        <p className="text-2xl font-bold">{totalMessages}</p>
                        <p className="text-sm text-muted-foreground">Total Messages</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <Edit className="w-8 h-8 text-blue-500" />
                      <div>
                        <p className="text-2xl font-bold">{totalTranslations}</p>
                        <p className="text-sm text-muted-foreground">Translations</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <AlertCircle className="w-8 h-8 text-orange-500" />
                      <div>
                        <p className="text-2xl font-bold">{missingTranslations}</p>
                        <p className="text-sm text-muted-foreground">Missing</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="w-8 h-8 text-green-500" />
                      <div>
                        <p className="text-2xl font-bold">{approvedTranslations}</p>
                        <p className="text-sm text-muted-foreground">Approved</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Filters */}
              <Card>
                <CardContent className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <Label>Search</Label>
                      <Input
                        placeholder="Search messages..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="mt-1"
                      />
                    </div>
                    
                    <div>
                      <Label>Namespace</Label>
                      <Select value={selectedNamespace} onValueChange={setSelectedNamespace}>
                        <SelectTrigger className="mt-1">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All namespaces</SelectItem>
                          {namespaces.map(ns => (
                            <SelectItem key={ns} value={ns}>{ns}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label>Locale</Label>
                      <Select 
                        value={selectedLocale.toString()} 
                        onValueChange={(v) => setSelectedLocale(v === "all" ? "all" : parseInt(v))}
                      >
                        <SelectTrigger className="mt-1">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All locales</SelectItem>
                          {locales.map(locale => (
                            <SelectItem key={locale.id} value={locale.id.toString()}>
                              {locale.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label>Status</Label>
                      <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                        <SelectTrigger className="mt-1">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All statuses</SelectItem>
                          {Object.entries(statusConfig).map(([key, config]) => (
                            <SelectItem key={key} value={key}>{config.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Messages Table */}
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">
                          <Checkbox 
                            checked={selectedMessages.length === filteredMessages.length && filteredMessages.length > 0}
                            onCheckedChange={() => {
                              if (selectedMessages.length === filteredMessages.length) {
                                setSelectedMessages([]);
                              } else {
                                setSelectedMessages(filteredMessages.map(m => m.id));
                              }
                            }}
                          />
                        </TableHead>
                        <TableHead>Key</TableHead>
                        <TableHead>Default Value</TableHead>
                        {locales.filter(l => !l.is_default).map(locale => (
                          <TableHead key={locale.id}>{locale.name}</TableHead>
                        ))}
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredMessages.map((message) => (
                        <TableRow key={message.id}>
                          <TableCell>
                            <Checkbox 
                              checked={selectedMessages.includes(message.id)}
                              onCheckedChange={() => {
                                if (selectedMessages.includes(message.id)) {
                                  setSelectedMessages(prev => prev.filter(id => id !== message.id));
                                } else {
                                  setSelectedMessages(prev => [...prev, message.id]);
                                }
                              }}
                            />
                          </TableCell>
                          
                          <TableCell>
                            <div>
                              <Badge variant="outline" className="mb-1">
                                {message.namespace}
                              </Badge>
                              <div className="font-mono text-sm">{message.key}</div>
                              {message.description && (
                                <p className="text-xs text-muted-foreground mt-1">
                                  {message.description}
                                </p>
                              )}
                            </div>
                          </TableCell>
                          
                          <TableCell>
                            <div className="max-w-xs truncate" title={message.default_value}>
                              {message.default_value}
                            </div>
                          </TableCell>
                          
                          {locales.filter(l => !l.is_default).map(locale => {
                            const translation = message.translations?.find(t => t.locale === locale.id);
                            const isEditing = editingCell?.messageId === message.id && 
                                            editingCell?.localeId === locale.id;
                            
                            return (
                              <TableCell key={locale.id}>
                                {isEditing ? (
                                  <div className="flex items-center gap-1">
                                    <Input
                                      value={editValue}
                                      onChange={(e) => setEditValue(e.target.value)}
                                      className="h-8"
                                      autoFocus
                                      onKeyDown={(e) => {
                                        if (e.key === 'Enter') saveEdit();
                                        if (e.key === 'Escape') cancelEdit();
                                      }}
                                    />
                                    <Button size="sm" variant="ghost" onClick={saveEdit}>
                                      <Check className="w-4 h-4" />
                                    </Button>
                                    <Button size="sm" variant="ghost" onClick={cancelEdit}>
                                      <X className="w-4 h-4" />
                                    </Button>
                                  </div>
                                ) : (
                                  <div 
                                    className="group cursor-pointer"
                                    onClick={() => startEdit(message.id, locale.id)}
                                  >
                                    {translation ? (
                                      <div>
                                        <div className="max-w-xs truncate" title={translation.value}>
                                          {translation.value || <span className="text-muted-foreground italic">Empty</span>}
                                        </div>
                                        <Badge 
                                          variant="outline" 
                                          className={`mt-1 ${statusConfig[translation.status].color}`}
                                        >
                                          {statusConfig[translation.status].label}
                                        </Badge>
                                      </div>
                                    ) : (
                                      <div className="text-muted-foreground italic">
                                        Click to add
                                      </div>
                                    )}
                                    <Edit className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity inline ml-2" />
                                  </div>
                                )}
                              </TableCell>
                            );
                          })}
                          
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm">
                                  <ChevronDown className="w-4 h-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                {message.translations?.map(trans => (
                                  trans.status === 'draft' && (
                                    <DropdownMenuItem 
                                      key={trans.id}
                                      onClick={() => approveTranslation(trans.id)}
                                    >
                                      <Check className="w-4 h-4 mr-2" />
                                      Approve {locales.find(l => l.id === trans.locale)?.name}
                                    </DropdownMenuItem>
                                  )
                                ))}
                                <DropdownMenuItem>
                                  <Eye className="w-4 h-4 mr-2" />
                                  View History
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          </main>
        </div>
      </div>

      {/* Add Message Modal */}
      <Dialog open={showAddModal} onOpenChange={setShowAddModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add UI Message</DialogTitle>
            <DialogDescription>
              Create a new UI message for translation
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <Label>Namespace</Label>
              <Input
                value={newMessage.namespace}
                onChange={(e) => setNewMessage(prev => ({ ...prev, namespace: e.target.value }))}
                placeholder="e.g., common, auth, validation"
              />
            </div>
            
            <div>
              <Label>Key</Label>
              <Input
                value={newMessage.key}
                onChange={(e) => setNewMessage(prev => ({ ...prev, key: e.target.value }))}
                placeholder="e.g., buttons.save, errors.required"
              />
            </div>
            
            <div>
              <Label>Default Value</Label>
              <Textarea
                value={newMessage.default_value}
                onChange={(e) => setNewMessage(prev => ({ ...prev, default_value: e.target.value }))}
                placeholder="The default text in the primary language"
                rows={3}
              />
            </div>
            
            <div>
              <Label>Description (optional)</Label>
              <Input
                value={newMessage.description}
                onChange={(e) => setNewMessage(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Context or usage notes"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddMessage}>
              Create Message
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default UIMessages;