import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api.ts";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
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
  Plus,
  Edit,
  Trash2,
  MoreHorizontal,
  Globe,
  AlertTriangle,
  CheckCircle2,
  Languages,
  Settings,
} from "lucide-react";

interface Locale {
  id: number;
  code: string;
  name: string;
  native_name: string;
  is_active: boolean;
  is_default: boolean;
  fallback?: number;
  fallback_code?: string;
  fallback_name?: string;
  rtl: boolean;
  created_at: string;
  updated_at: string;
}


interface LocaleFormData {
  code: string;
  name: string;
  native_name: string;
  rtl: boolean;
  is_default: boolean;
  fallback?: number;
  is_active: boolean;
}

const LocalesManagement = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [locales, setLocales] = useState<Locale[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingLocale, setEditingLocale] = useState<Locale | null>(null);
  const [deleteLocale, setDeleteLocale] = useState<Locale | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  
  const [formData, setFormData] = useState<LocaleFormData>({
    code: "",
    name: "",
    native_name: "",
    rtl: false,
    is_default: false,
    fallback: undefined,
    is_active: true
  });

  // Load locales from API
  useEffect(() => {
    const loadLocales = async () => {
      try {
        const response = await api.i18n.locales.list();
        // Ensure we have a valid array and filter out any undefined/null values
        const validLocales = (response.results || []).filter((locale: any) => locale !== null && locale !== undefined);
        setLocales(validLocales);
      } catch (error) {
        console.error('Error loading locales:', error);
        toast({
          title: "Error loading locales",
          description: "Failed to load locales from the server.",
          variant: "destructive",
        });
        setLocales([]); // Set empty array on error
      } finally {
        setLoading(false);
      }
    };

    loadLocales();
  }, [toast]);

  // Safe filtering with null/undefined checks
  const activeLocales = locales.filter(l => l && l.is_active);
  const defaultLocale = locales.find(l => l && l.is_default);
  const sortedLocales = [...locales].filter(l => l !== null && l !== undefined);

  const resetForm = () => {
    setFormData({
      code: "",
      name: "",
      native_name: "",
      rtl: false,
      is_default: false,
      fallback: undefined,
      is_active: true
    });
  };

  const handleAddLocale = () => {
    setEditingLocale(null);
    resetForm();
    setShowAddModal(true);
  };

  const handleEditLocale = (locale: Locale) => {
    setEditingLocale(locale);
    setFormData({
      code: locale.code,
      name: locale.name,
      native_name: locale.native_name,
      rtl: locale.rtl,
      is_default: locale.is_default,
      fallback: locale.fallback,
      is_active: locale.is_active
    });
    setShowAddModal(true);
  };

  const handleDeleteLocale = (locale: Locale) => {
    if (locale.is_default) {
      toast({
        title: "Cannot delete default locale",
        description: "You cannot delete the default locale. Set another locale as default first.",
        variant: "destructive",
      });
      return;
    }
    
    setDeleteLocale(locale);
    setShowDeleteConfirm(true);
  };

  const confirmDelete = async () => {
    if (!deleteLocale) return;
    
    setIsDeleting(true);
    try {
      await api.i18n.locales.delete(deleteLocale.id);
      
      // Remove the deleted locale from state
      setLocales(prev => prev.filter(l => l && l.id !== deleteLocale.id));
      
      toast({
        title: "Locale deleted",
        description: `${deleteLocale.name} has been removed.`,
      });
      
      // Close dialog and reset state
      setShowDeleteConfirm(false);
      setDeleteLocale(null);
    } catch (error) {
      console.error('Error deleting locale:', error);
      toast({
        title: "Error",
        description: "Failed to delete locale.",
        variant: "destructive",
      });
      // Keep dialog open on error so user can retry
    } finally {
      setIsDeleting(false);
    }
  };

  const validateForm = (): string | null => {
    if (!formData.code.trim()) return "Locale code is required";
    if (!formData.name.trim()) return "Locale name is required";
    if (!formData.native_name.trim()) return "Native name is required";
    
    // Check for duplicate codes (excluding current locale when editing)
    const existingLocale = locales.find(l => 
      l && l.code && l.code.toLowerCase() === formData.code.toLowerCase() && 
      l.id !== editingLocale?.id
    );
    
    if (existingLocale) return "Locale code already exists";
    
    // Check for fallback cycles  
    if (formData.fallback) {
      const fallbackLocale = locales.find(l => l && l.id === formData.fallback);
      if (fallbackLocale?.code === formData.code) {
        return "A locale cannot fallback to itself";
      }
      
      // Check for circular fallbacks
      const checkCircular = (id: number, visited: Set<number> = new Set()): boolean => {
        if (visited.has(id)) return true;
        visited.add(id);
        
        const locale = locales.find(l => l && l.id === id);
        if (locale?.fallback) {
          return checkCircular(locale.fallback, visited);
        }
        return false;
      };
      
      if (checkCircular(formData.fallback)) {
        return "Fallback creates a circular dependency";
      }
    }
    
    return null;
  };

  const handleSaveLocale = async () => {
    const error = validateForm();
    if (error) {
      toast({
        title: "Validation Error",
        description: error,
        variant: "destructive",
      });
      return;
    }

    setIsSaving(true);
    try {
      if (editingLocale) {
        // Update existing locale
        const response = await api.i18n.locales.update(editingLocale.id, formData);
        // Handle response - ensure we have a valid locale object
        const updatedLocale = response?.data || response;
        
        if (!updatedLocale || typeof updatedLocale !== 'object') {
          throw new Error('Invalid response from server');
        }
        
        setLocales(prev => prev.map(locale => 
          locale && locale.id === editingLocale.id ? { ...updatedLocale, id: editingLocale.id } : locale
        ));
        
        toast({
          title: "Locale updated",
          description: `${formData.name} has been updated successfully.`,
        });
        
        // Close modal and reset form after successful update
        setShowAddModal(false);
        setEditingLocale(null);
        resetForm();
      } else {
        // Create new locale
        const response = await api.i18n.locales.create(formData);
        // Handle response - ensure we have a valid locale object
        const newLocale = response?.data || response;
        
        if (!newLocale || typeof newLocale !== 'object') {
          throw new Error('Invalid response from server');
        }
        
        setLocales(prev => [...prev.filter(l => l !== null && l !== undefined), newLocale]);

        toast({
          title: "Locale created",
          description: `${formData.name} has been added successfully.`,
        });
        
        // Close modal and reset form after successful creation
        setShowAddModal(false);
        resetForm();
      }
    } catch (error) {
      console.error('Error saving locale:', error);
      toast({
        title: "Error",
        description: editingLocale ? "Failed to update locale." : "Failed to create locale.",
        variant: "destructive",
      });
      // Don't close modal on error so user can retry
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleActive = async (locale: Locale) => {
    if (locale.is_default && locale.is_active) {
      toast({
        title: "Cannot deactivate default locale",
        description: "You cannot deactivate the default locale. Set another locale as default first.",
        variant: "destructive",
      });
      return;
    }

    try {
      const response = await api.i18n.locales.toggleActive(locale.id);
      
      // Update local state with the response
      setLocales(prev => prev.map(l => 
        l.id === locale.id ? response.locale : l
      ));

      toast({
        title: "Locale updated",
        description: response.message,
      });
    } catch (error) {
      console.error('Failed to toggle locale active status:', error);
      toast({
        title: "Error",
        description: "Failed to update locale status. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleSetDefault = async (locale: Locale) => {
    try {
      const response = await api.i18n.locales.setDefault(locale.id);
      
      // Update local state with the response - ensure we handle null/undefined
      setLocales(prev => prev.map(l => {
        if (!l) return l; // Skip null/undefined entries
        return {
          ...l,
          is_default: l.id === locale.id,
          is_active: l.id === locale.id ? true : l.is_active // Auto-activate if setting as default
        };
      }));
      
      toast({
        title: "Default locale updated",
        description: `${locale.name} is now the default locale.`,
      });
    } catch (error) {
      console.error('Failed to set default locale:', error);
      toast({
        title: "Error",
        description: "Failed to set default locale. Please try again.",
        variant: "destructive",
      });
    }
  };


  const availableFallbacks = locales.filter(l => 
    l && l.is_active && l.code !== formData.code
  );

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
                  <h1 className="text-3xl font-bold text-foreground">Locales</h1>
                  <p className="text-muted-foreground mt-1">
                    Manage supported languages and regional settings
                  </p>
                </div>
                <Button onClick={handleAddLocale}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Locale
                </Button>
              </div>

              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <Globe className="w-8 h-8 text-primary" />
                      <div>
                        <p className="text-2xl font-bold">{locales.length}</p>
                        <p className="text-sm text-muted-foreground">Total Locales</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="w-8 h-8 text-green-500" />
                      <div>
                        <p className="text-2xl font-bold">{activeLocales.length}</p>
                        <p className="text-sm text-muted-foreground">Active Locales</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <Settings className="w-8 h-8 text-blue-500" />
                      <div>
                        <p className="text-2xl font-bold">{defaultLocale?.code.toUpperCase()}</p>
                        <p className="text-sm text-muted-foreground">Default Locale</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <Languages className="w-8 h-8 text-purple-500" />
                      <div>
                        <p className="text-2xl font-bold">
                          -
                        </p>
                        <p className="text-sm text-muted-foreground">Translation Units</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Locales Table */}
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Code</TableHead>
                        <TableHead>Name</TableHead>
                        <TableHead>Native Name</TableHead>
                        <TableHead>Active</TableHead>
                        <TableHead>Default</TableHead>
                        <TableHead>Fallback</TableHead>
                        <TableHead>RTL</TableHead>
                        <TableHead>Stats</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sortedLocales.filter(locale => locale).map((locale) => (
                        <TableRow key={locale.id}>
                          <TableCell>
                            <code className="font-mono font-medium">
                              {locale.code}
                            </code>
                          </TableCell>
                          
                          <TableCell>
                            <div className="font-medium">{locale.name}</div>
                          </TableCell>
                          
                          <TableCell>
                            <div className="font-medium" dir={locale.rtl ? 'rtl' : 'ltr'}>
                              {locale.native_name}
                            </div>
                          </TableCell>
                          
                          <TableCell>
                            <Switch
                              checked={locale.is_active}
                              onCheckedChange={() => handleToggleActive(locale)}
                              disabled={locale.is_default}
                            />
                          </TableCell>
                          
                          <TableCell>
                            <RadioGroup
                              value={locale.is_default ? locale.id : ""}
                              onValueChange={() => !locale.is_default && handleSetDefault(locale)}
                            >
                              <div className="flex items-center space-x-2">
                                <RadioGroupItem value={locale.id} id={`default-${locale.id}`} />
                              </div>
                            </RadioGroup>
                          </TableCell>
                          
                          <TableCell>
                            {locale.fallback ? (
                              <Badge variant="outline">
                                {locales.find(l => l && l.id === locale.fallback)?.code || 'Unknown'}
                              </Badge>
                            ) : (
                              <span className="text-muted-foreground">None</span>
                            )}
                          </TableCell>
                          
                          <TableCell>
                            {locale.rtl ? (
                              <Badge variant="secondary">RTL</Badge>
                            ) : (
                              <span className="text-muted-foreground">LTR</span>
                            )}
                          </TableCell>
                          
                          
                          <TableCell>
                            <div className="text-sm space-y-1">
                              <div>-</div>
                              <div className="text-muted-foreground">
                                -
                              </div>
                            </div>
                          </TableCell>
                          
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm">
                                  <MoreHorizontal className="w-4 h-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => handleEditLocale(locale)}>
                                  <Edit className="w-4 h-4 mr-2" />
                                  Edit
                                </DropdownMenuItem>
                                <DropdownMenuItem 
                                  onClick={() => handleDeleteLocale(locale)}
                                  disabled={locale.is_default}
                                  className="text-destructive"
                                >
                                  <Trash2 className="w-4 h-4 mr-2" />
                                  Delete
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

      {/* Add/Edit Modal */}
      <Dialog open={showAddModal} onOpenChange={(open) => {
        setShowAddModal(open);
        if (!open) {
          // Clean up when closing
          setEditingLocale(null);
          resetForm();
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingLocale ? "Edit Locale" : "Add New Locale"}
            </DialogTitle>
            <DialogDescription>
              {editingLocale 
                ? "Update the locale settings below."
                : "Create a new locale for your application."
              }
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="code">Locale Code *</Label>
                <Input
                  id="code"
                  value={formData.code}
                  onChange={(e) => setFormData(prev => ({ ...prev, code: e.target.value }))}
                  placeholder="en, es, de-CH"
                  className="text-base min-h-[40px]"
                />
              </div>
              
              <div>
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="English"
                  className="text-base min-h-[40px]"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="nativeName">Native Name *</Label>
              <Input
                id="nativeName"
                value={formData.native_name}
                onChange={(e) => setFormData(prev => ({ ...prev, native_name: e.target.value }))}
                placeholder="English"
                className="text-base min-h-[40px]"
              />
            </div>

            <div>
              <Label htmlFor="fallback">Fallback Locale</Label>
              <Select 
                value={formData.fallback ? String(formData.fallback) : "none"} 
                onValueChange={(value) => setFormData(prev => ({ 
                  ...prev, 
                  fallback: value === "none" ? undefined : Number(value) 
                }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select fallback locale" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  {availableFallbacks.filter(locale => locale).map(locale => (
                    <SelectItem key={locale.id} value={String(locale.id)}>
                      {locale.name} ({locale.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="rtl"
                  checked={formData.rtl}
                  onCheckedChange={(checked) => setFormData(prev => ({ ...prev, rtl: !!checked }))}
                />
                <Label htmlFor="rtl">Right-to-left (RTL) language</Label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="default"
                  checked={formData.is_default}
                  onCheckedChange={(checked) => setFormData(prev => ({ ...prev, is_default: !!checked }))}
                />
                <Label htmlFor="default">Set as default locale</Label>
              </div>

            </div>
          </div>

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setShowAddModal(false)}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSaveLocale}
              disabled={isSaving}
            >
              {isSaving ? "Saving..." : editingLocale ? "Update Locale" : "Create Locale"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={(open) => {
        setShowDeleteConfirm(open);
        if (!open) {
          setDeleteLocale(null);
        }
      }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Locale</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{deleteLocale?.name}</strong>?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default LocalesManagement;