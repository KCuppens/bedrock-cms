import React, { useState, useEffect } from "react";
import { api } from '@/lib/api';
import { useToast } from "@/components/ui/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import DeleteConfirmModal from "@/components/modals/DeleteConfirmModal";
import SEOSettingsForm from "@/components/SEOSettingsForm";
import {
  Search,
  Globe,
  MoreHorizontal,
  Plus,
  AlertTriangle,
  Link2,
  FileText,
  Eye,
  Settings,
  BarChart3,
  ExternalLink,
  Upload,
  Download,
  RefreshCw,
  Check,
  X,
  Info,
  TestTube
} from "lucide-react";
import TopNavbar from "@/components/TopNavbar";
import Sidebar from "@/components/Sidebar";

const SEORedirects = () => {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("settings");
  const [redirectDialogOpen, setRedirectDialogOpen] = useState(false);
  const [editRedirectDialogOpen, setEditRedirectDialogOpen] = useState(false);
  const [csvImportDialogOpen, setCsvImportDialogOpen] = useState(false);
  const [deleteRedirectDialogOpen, setDeleteRedirectDialogOpen] = useState(false);
  const [redirectToDelete, setRedirectToDelete] = useState<any>(null);
  const [isDeletingRedirect, setIsDeletingRedirect] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvPreview, setCsvPreview] = useState<any[]>([]);
  const [editingRedirect, setEditingRedirect] = useState<any>(null);
  const [redirects, setRedirects] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [isUpdatingRedirect, setIsUpdatingRedirect] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Load redirects on component mount
  useEffect(() => {
    loadRedirects();
  }, []);

  const loadRedirects = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (searchQuery) params.search = searchQuery;

      const response = await api.redirects.list(params);
      setRedirects(response.results || response.data || []);
    } catch (error: any) {
      console.error('Failed to load redirects:', error);
      toast({
        title: "Error",
        description: "Failed to load redirects. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  // Reload redirects when search query changes
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      loadRedirects();
    }, 300); // Debounce search
    return () => clearTimeout(timeoutId);
  }, [searchQuery]);


  // API handler functions
  const handleCreateRedirect = async (formData: FormData) => {
    try {
      const redirectData = {
        from_path: formData.get('fromPath') as string,
        to_path: formData.get('toPath') as string,
        status: parseInt(formData.get('status') as string),
        notes: formData.get('notes') as string,
        is_active: true,
      };

      await api.redirects.create(redirectData);
      toast({
        title: "Success",
        description: "Redirect created successfully.",
      });
      setRedirectDialogOpen(false);
      loadRedirects();
    } catch (error: any) {
      console.error('Failed to create redirect:', error);
      toast({
        title: "Error",
        description: "Failed to create redirect. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleUpdateRedirect = async (formData: FormData) => {
    if (!editingRedirect) return;

    try {
      setIsUpdatingRedirect(true);
      const redirectData = {
        from_path: formData.get('fromPath') as string,
        to_path: formData.get('toPath') as string,
        status: parseInt(formData.get('status') as string),
        notes: formData.get('notes') as string,
      };

      await api.redirects.update(editingRedirect.id, redirectData);
      toast({
        title: "Success",
        description: "Redirect updated successfully.",
      });

      // Defer state updates to next tick to avoid React batching issues
      setTimeout(() => {
        setEditRedirectDialogOpen(false);
        setEditingRedirect(null);
        setIsUpdatingRedirect(false);
      }, 0);

      // Load redirects after a slight delay to ensure dialog closes smoothly
      setTimeout(() => {
        loadRedirects();
      }, 100);
    } catch (error: any) {
      console.error('Failed to update redirect:', error);
      toast({
        title: "Error",
        description: error?.response?.data?.detail || "Failed to update redirect. Please try again.",
        variant: "destructive",
      });
      setIsUpdatingRedirect(false);
    }
  };

  const handleDeleteRedirect = async () => {
    if (!redirectToDelete) return;

    try {
      setIsDeletingRedirect(true);
      await api.redirects.delete(redirectToDelete.id);
      toast({
        title: "Success",
        description: "Redirect deleted successfully.",
      });

      // Defer state updates to next tick to avoid React batching issues
      setTimeout(() => {
        setDeleteRedirectDialogOpen(false);
        setRedirectToDelete(null);
        setIsDeletingRedirect(false);
      }, 0);

      // Load redirects after a slight delay to ensure dialog closes smoothly
      setTimeout(() => {
        loadRedirects();
      }, 100);
    } catch (error: any) {
      console.error('Failed to delete redirect:', error);
      toast({
        title: "Error",
        description: error?.response?.data?.error || "Failed to delete redirect. Please try again.",
        variant: "destructive",
      });
      setIsDeletingRedirect(false);
    }
  };


  const handleTestRedirectLocally = (redirect: any) => {
    // Get the current site's base URL
    const baseUrl = window.location.origin;

    // Construct the full URL with the from_path
    const testUrl = `${baseUrl}${redirect.from_path}`;

    // Open in a new tab
    window.open(testUrl, '_blank');

    // Show a toast notification
    toast({
      title: "Testing Redirect",
      description: `Opening ${redirect.from_path} in a new tab. It should redirect to ${redirect.to_path}`,
    });
  };

  const handleCSVImport = async () => {
    if (!csvFile) return;

    try {
      setLoading(true);
      const result = await api.redirects.importCSV(csvFile);
      toast({
        title: "Import Completed",
        description: `${result.successful_imports} redirects imported successfully. ${result.failed_imports} failed.`,
      });
      setCsvImportDialogOpen(false);
      setCsvFile(null);
      loadRedirects();
    } catch (error: any) {
      console.error('Failed to import CSV:', error);
      toast({
        title: "Import Failed",
        description: "Failed to import redirects. Please check the CSV format.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const brokenLinks = [
    {
      id: 1,
      page: "/blog/seo-tips",
      brokenLink: "/old-resource",
      type: "internal",
      lastChecked: "2024-01-20",
      status: 404
    },
    {
      id: 2,
      page: "/products/item-1",
      brokenLink: "https://external-site.com/deleted",
      type: "external",
      lastChecked: "2024-01-19",
      status: 404
    }
  ];

  const orphanPages = [
    {
      id: 1,
      path: "/forgotten-page",
      title: "Forgotten Page",
      lastModified: "2023-12-01",
      hasBacklinks: false,
      inSitemap: true
    },
    {
      id: 2,
      path: "/draft-content",
      title: "Draft Content",
      lastModified: "2024-01-15",
      hasBacklinks: false,
      inSitemap: false
    }
  ];

  const locales = ["en", "de", "fr", "es"];

  const handleCSVUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === "text/csv") {
      setCsvFile(file);

      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const lines = text.split('\n');
        const headers = lines[0].split(',').map(h => h.trim());

        const data = lines.slice(1, 6).map(line => { // Preview first 5 rows
          const values = line.split(',').map(v => v.trim());
          const row: any = {};
          headers.forEach((header, index) => {
            row[header] = values[index] || '';
          });
          return row;
        }).filter(row => Object.values(row).some(v => v !== ''));

        setCsvPreview(data);
      };
      reader.readAsText(file);
    }
  };


  const handleEditRedirect = (redirect: any) => {
    console.log('handleEditRedirect called with:', redirect);
    setEditingRedirect(redirect);
    setEditRedirectDialogOpen(true);
    console.log('Dialog should open now');
  };



  return (
    <div className="min-h-screen">
      <div className="flex">
        <Sidebar />

        <div className="flex-1 flex flex-col ml-72">
          <TopNavbar />

          <main className="flex-1 p-8">
            <div className="max-w-7xl mx-auto">
              <div className="mb-8">
                <h1 className="text-3xl font-bold text-foreground mb-2">SEO & Redirects</h1>
                <p className="text-muted-foreground">Manage search engine optimization and URL redirections</p>
              </div>

              <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                <TabsList className="grid w-full grid-cols-3 max-w-xl">
                  <TabsTrigger value="settings">SEO Settings</TabsTrigger>
                  <TabsTrigger value="redirects">Redirects</TabsTrigger>
                  <TabsTrigger value="sitemaps">Sitemaps</TabsTrigger>
                </TabsList>

                <TabsContent value="settings" className="space-y-6">
                  <SEOSettingsForm
                    onSave={() => {
                      toast({
                        title: "Settings Saved",
                        description: "SEO settings have been updated successfully"
                      });
                    }}
                  />
                </TabsContent>

                <TabsContent value="redirects" className="space-y-6">
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                      <CardTitle className="flex items-center gap-2">
                        <Link2 className="h-5 w-5" />
                        URL Redirects
                      </CardTitle>
                      <div className="flex gap-2">
                        <Dialog open={csvImportDialogOpen} onOpenChange={setCsvImportDialogOpen}>
                          <DialogTrigger asChild>
                            <Button variant="outline">
                              <Upload className="h-4 w-4 mr-2" />
                              Import CSV
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-2xl">
                            <DialogHeader>
                              <DialogTitle>Import Redirects from CSV</DialogTitle>
                            </DialogHeader>
                            <div className="space-y-4">
                              <div>
                                <Label htmlFor="csvFile">Select CSV File</Label>
                                <Input
                                  id="csvFile"
                                  type="file"
                                  accept=".csv"
                                  onChange={handleCSVUpload}
                                  className="mt-1"
                                />
                                <p className="text-sm text-muted-foreground mt-1">
                                  Expected format: from_path, to_path, status_code, locale
                                </p>
                              </div>

                              {csvPreview.length > 0 && (
                                <div>
                                  <Label>Preview (first 5 rows)</Label>
                                  <div className="border rounded-lg mt-2">
                                    <Table>
                                      <TableHeader>
                                        <TableRow>
                                          <TableHead>From Path</TableHead>
                                          <TableHead>To Path</TableHead>
                                          <TableHead>Status</TableHead>
                                          <TableHead>Locale</TableHead>
                                        </TableRow>
                                      </TableHeader>
                                      <TableBody>
                                        {csvPreview.map((row, index) => (
                                          <TableRow key={index}>
                                            <TableCell className="font-mono text-sm">{row.from_path || row['From Path'] || ''}</TableCell>
                                            <TableCell className="font-mono text-sm">{row.to_path || row['To Path'] || ''}</TableCell>
                                            <TableCell>{row.status_code || row['Status Code'] || row.status || ''}</TableCell>
                                            <TableCell>{row.locale || row['Locale'] || 'All'}</TableCell>
                                          </TableRow>
                                        ))}
                                      </TableBody>
                                    </Table>
                                  </div>
                                </div>
                              )}

                              <div className="flex gap-2">
                                <Button
                                  className="flex-1"
                                  onClick={handleCSVImport}
                                  disabled={!csvFile || loading}
                                >
                                  {loading ? 'Importing...' : `Import ${csvPreview.length} Redirects`}
                                </Button>
                                <Button variant="outline" onClick={() => {
                                  setCsvImportDialogOpen(false);
                                  setCsvFile(null);
                                  setCsvPreview([]);
                                }}>
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          </DialogContent>
                          </Dialog>

                        <Dialog open={editRedirectDialogOpen} onOpenChange={(open) => {
                          setEditRedirectDialogOpen(open);
                          if (!open) {
                            setEditingRedirect(null);
                          }
                        }}>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Edit Redirect</DialogTitle>
                            </DialogHeader>
                            {editingRedirect && (
                              <div className="space-y-4">
                                <div>
                                  <Label htmlFor="editFromPath">From Path</Label>
                                  <Input
                                    id="editFromPath"
                                    name="fromPath"
                                    defaultValue={editingRedirect.from_path}
                                    placeholder="/old-path or /old-path/*"
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="editToPath">To Path</Label>
                                  <Input
                                    id="editToPath"
                                    name="toPath"
                                    defaultValue={editingRedirect.to_path}
                                    placeholder="/new-path or /new-path/*"
                                  />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                  <div>
                                    <Label htmlFor="editStatus">Status Code</Label>
                                    <Select name="status" key={editingRedirect.id} defaultValue={editingRedirect.status.toString()}>
                                      <SelectTrigger>
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem value="301">301 (Permanent)</SelectItem>
                                        <SelectItem value="302">302 (Temporary)</SelectItem>
                                        <SelectItem value="307">307 (Temporary Preserve)</SelectItem>
                                        <SelectItem value="308">308 (Permanent Preserve)</SelectItem>
                                      </SelectContent>
                                    </Select>
                                  </div>
                                  <div>
                                    <Label className="text-sm text-muted-foreground">Notes (Optional)</Label>
                                    <Textarea
                                      name="notes"
                                      defaultValue={editingRedirect.notes || ''}
                                      placeholder="Add notes about this redirect..."
                                      rows={2}
                                    />
                                  </div>
                                </div>
                                <div className="flex gap-2">
                                  <Button
                                    className="flex-1"
                                    disabled={isUpdatingRedirect}
                                    onClick={() => {
                                      const formData = new FormData();
                                      const fromInput = document.getElementById('editFromPath') as HTMLInputElement;
                                      const toInput = document.getElementById('editToPath') as HTMLInputElement;
                                      const statusSelect = document.querySelector('[name="status"]') as HTMLSelectElement;
                                      const notesTextarea = document.querySelector('[name="notes"]') as HTMLTextAreaElement;

                                      formData.append('fromPath', fromInput?.value || editingRedirect.from_path);
                                      formData.append('toPath', toInput?.value || editingRedirect.to_path);
                                      formData.append('status', statusSelect?.value || editingRedirect.status);
                                      formData.append('notes', notesTextarea?.value || '');

                                      handleUpdateRedirect(formData);
                                    }}
                                  >
                                    {isUpdatingRedirect ? 'Updating...' : 'Update Redirect'}
                                  </Button>
                                  <Button
                                    variant="outline"
                                    disabled={isUpdatingRedirect}
                                    onClick={() => {
                                      setEditRedirectDialogOpen(false);
                                      setEditingRedirect(null);
                                    }}
                                  >
                                    Cancel
                                  </Button>
                                </div>
                              </div>
                            )}
                          </DialogContent>
                        </Dialog>

                        <Dialog open={redirectDialogOpen} onOpenChange={setRedirectDialogOpen}>
                          <DialogTrigger asChild>
                            <Button>
                              <Plus className="h-4 w-4 mr-2" />
                              Add Redirect
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Add New Redirect</DialogTitle>
                            </DialogHeader>
                            <form onSubmit={(e) => {
                              e.preventDefault();
                              const formData = new FormData(e.target as HTMLFormElement);
                              handleCreateRedirect(formData);
                            }}>
                              <div className="space-y-4">
                                <div>
                                  <Label htmlFor="fromPath">From Path</Label>
                                  <Input
                                    id="fromPath"
                                    name="fromPath"
                                    placeholder="/old-path or /old-path/*"
                                    required
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="toPath">To Path</Label>
                                  <Input
                                    id="toPath"
                                    name="toPath"
                                    placeholder="/new-path or /new-path/*"
                                    required
                                  />
                                </div>
                                <div>
                                  <Label htmlFor="status">Status Code</Label>
                                  <Select name="status" defaultValue="301">
                                    <SelectTrigger>
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="301">301 (Permanent)</SelectItem>
                                      <SelectItem value="302">302 (Temporary)</SelectItem>
                                      <SelectItem value="307">307 (Temporary Preserve)</SelectItem>
                                      <SelectItem value="308">308 (Permanent Preserve)</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>
                                <div>
                                  <Label htmlFor="notes">Notes (Optional)</Label>
                                  <Textarea
                                    id="notes"
                                    name="notes"
                                    placeholder="Add notes about this redirect..."
                                    rows={2}
                                  />
                                </div>
                                <div className="flex gap-2">
                                  <Button type="submit" className="flex-1">Create Redirect</Button>
                                  <Button type="button" variant="outline" onClick={() => setRedirectDialogOpen(false)}>
                                    Cancel
                                  </Button>
                                </div>
                              </div>
                            </form>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-4 mb-6">
                        <div className="relative flex-1 max-w-sm">
                          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                          <Input
                            placeholder="Search redirects..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-10"
                          />
                        </div>
                        <Button
                          variant="outline"
                          onClick={async () => {
                            try {
                              const blob = await api.redirects.exportCSV();
                              const url = window.URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = 'redirects.csv';
                              document.body.appendChild(a);
                              a.click();
                              window.URL.revokeObjectURL(url);
                              document.body.removeChild(a);
                            } catch (error) {
                              toast({
                                title: "Export Failed",
                                description: "Failed to export redirects.",
                                variant: "destructive",
                              });
                            }
                          }}
                        >
                          <Download className="h-4 w-4 mr-2" />
                          Export CSV
                        </Button>
                      </div>
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>From Path</TableHead>
                            <TableHead>To Path</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Hits</TableHead>
                            <TableHead>Created</TableHead>
                            <TableHead className="w-[50px]"></TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {loading ? (
                            <TableRow>
                              <TableCell colSpan={6} className="text-center py-8">
                                <div className="flex items-center justify-center space-x-2">
                                  <RefreshCw className="w-4 h-4 animate-spin" />
                                  <span>Loading redirects...</span>
                                </div>
                              </TableCell>
                            </TableRow>
                          ) : redirects.length === 0 ? (
                            <TableRow>
                              <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                No redirects found. Create your first redirect to get started.
                              </TableCell>
                            </TableRow>
                          ) : (
                            redirects.map(redirect => (
                              <TableRow key={redirect.id}>
                                <TableCell className="font-mono text-sm">{redirect.from_path}</TableCell>
                                <TableCell className="font-mono text-sm">{redirect.to_path}</TableCell>
                                <TableCell>
                                  <Badge variant={redirect.status === 301 ? "default" : "secondary"}>
                                    {redirect.status}
                                  </Badge>
                                </TableCell>
                                <TableCell>{redirect.hits?.toLocaleString() || 0}</TableCell>
                                <TableCell className="text-muted-foreground">
                                  {redirect.created_at ? new Date(redirect.created_at).toLocaleDateString() : '-'}
                                </TableCell>
                                <TableCell>
                                  <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                      <Button variant="ghost" size="sm">
                                        <MoreHorizontal className="h-4 w-4" />
                                      </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                      <DropdownMenuItem onClick={() => handleEditRedirect(redirect)}>
                                        Edit
                                      </DropdownMenuItem>
                                      <DropdownMenuItem onClick={() => handleTestRedirectLocally(redirect)}>
                                        <TestTube className="h-4 w-4 mr-2" />
                                        Test Locally
                                      </DropdownMenuItem>
                                      <DropdownMenuItem
                                        className="text-destructive"
                                        onClick={() => {
                                          setRedirectToDelete(redirect);
                                          setDeleteRedirectDialogOpen(true);
                                        }}
                                      >
                                        Delete
                                      </DropdownMenuItem>
                                    </DropdownMenuContent>
                                  </DropdownMenu>
                                </TableCell>
                            </TableRow>
                          ))
                          )}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="sitemaps" className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <FileText className="h-5 w-5" />
                          Sitemap Status
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {locales.map(locale => (
                          <div key={locale} className="flex items-center justify-between p-3 border rounded-lg">
                            <div>
                              <p className="font-medium">/sitemap-{locale}.xml</p>
                              <p className="text-sm text-muted-foreground">Last updated: 2 hours ago</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant="secondary">142 URLs</Badge>
                              <Button variant="outline" size="sm">
                                <ExternalLink className="h-4 w-4 mr-1" />
                                View
                              </Button>
                            </div>
                          </div>
                        ))}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <Settings className="h-5 w-5" />
                          Sitemap Settings
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div>
                          <Label htmlFor="changeFreq">Default Change Frequency</Label>
                          <Select defaultValue="weekly">
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="always">Always</SelectItem>
                              <SelectItem value="hourly">Hourly</SelectItem>
                              <SelectItem value="daily">Daily</SelectItem>
                              <SelectItem value="weekly">Weekly</SelectItem>
                              <SelectItem value="monthly">Monthly</SelectItem>
                              <SelectItem value="yearly">Yearly</SelectItem>
                              <SelectItem value="never">Never</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label htmlFor="priority">Default Priority</Label>
                          <Select defaultValue="0.5">
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="1.0">1.0 (Highest)</SelectItem>
                              <SelectItem value="0.8">0.8</SelectItem>
                              <SelectItem value="0.5">0.5 (Default)</SelectItem>
                              <SelectItem value="0.3">0.3</SelectItem>
                              <SelectItem value="0.1">0.1 (Lowest)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Switch id="autoUpdate" defaultChecked />
                          <Label htmlFor="autoUpdate">Auto-update on publish</Label>
                        </div>
                        <div className="pt-2">
                          <Button>
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Regenerate All Sitemaps
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </TabsContent>

                {/* Reports section removed for now */}
              </Tabs>
            </div>
          </main>
        </div>
      </div>

      {/* Delete Redirect Confirmation Modal */}
      <DeleteConfirmModal
        open={deleteRedirectDialogOpen}
        onOpenChange={(open) => {
          // Don't allow closing while deleting
          if (!isDeletingRedirect) {
            setDeleteRedirectDialogOpen(open);
            if (!open) {
              setRedirectToDelete(null);
            }
          }
        }}
        title="Delete Redirect"
        description="Are you sure you want to permanently delete this redirect?"
        itemName={redirectToDelete ? `${redirectToDelete.from_path} → ${redirectToDelete.to_path}` : ''}
        warningMessage="This action cannot be undone. Any existing links using this redirect will result in 404 errors."
        onConfirm={handleDeleteRedirect}
        isDestructive={true}
        isLoading={isDeletingRedirect}
      />
    </div>
  );
};

export default SEORedirects;
