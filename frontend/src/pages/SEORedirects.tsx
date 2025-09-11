import React, { useState, useMemo, lazy, Suspense } from "react";
import { flushSync } from "react-dom";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { SimpleDialog, SimpleDialogHeader, SimpleDialogTitle } from "@/components/ui/simple-dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import DeleteConfirmModal from "@/components/modals/DeleteConfirmModal";
import SEOSettingsForm from "@/components/SEOSettingsForm";
import { 
  Search, 
  MoreHorizontal, 
  Plus, 
  Link2, 
  FileText,
  Settings,
  ExternalLink,
  Upload,
  Download,
  RefreshCw,
  TestTube,
  Loader2
} from "lucide-react";
import TopNavbar from "@/components/TopNavbar";
import Sidebar from "@/components/Sidebar";
import {
  useRedirects,
  useCreateRedirect,
  useUpdateRedirect,
  useDeleteRedirect,
  useTestRedirect,
  useImportRedirectsCSV,
  useExportRedirectsCSV,
  type Redirect
} from "@/hooks/queries/use-redirects";

// Lazy load the Sitemap tab component
const SitemapTab = lazy(() => import("@/components/seo/SitemapTab"));

const SEORedirects = () => {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("settings");
  const [searchQuery, setSearchQuery] = useState("");
  const [redirectDialogOpen, setRedirectDialogOpen] = useState(false);
  const [editRedirectDialogOpen, setEditRedirectDialogOpen] = useState(false);
  const [deleteRedirectDialogOpen, setDeleteRedirectDialogOpen] = useState(false);
  const [csvImportDialogOpen, setCsvImportDialogOpen] = useState(false);
  const [editingRedirect, setEditingRedirect] = useState<Redirect | null>(null);
  const [redirectToDelete, setRedirectToDelete] = useState<Redirect | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvPreview, setCsvPreview] = useState<any[]>([]);

  // React Query hooks
  const { data: redirects = [], isLoading, refetch } = useRedirects({ search: searchQuery });
  const createRedirect = useCreateRedirect();
  const updateRedirect = useUpdateRedirect();
  const deleteRedirect = useDeleteRedirect();
  const testRedirect = useTestRedirect();
  const importCSV = useImportRedirectsCSV();
  const exportCSV = useExportRedirectsCSV();

  // Handle create redirect
  const handleCreateRedirect = (formData: FormData) => {
    const redirectData = {
      from_path: formData.get('fromPath') as string,
      to_path: formData.get('toPath') as string,
      status: parseInt(formData.get('status') as string),
      notes: formData.get('notes') as string,
      is_active: true,
    };

    createRedirect.mutate(redirectData, {
      onSuccess: () => {
        setRedirectDialogOpen(false);
      }
    });
  };

  // Handle update redirect
  const handleUpdateRedirect = (formData: FormData) => {
    console.log('🔥 handleUpdateRedirect called', { 
      editingRedirect: !!editingRedirect,
      isPending: updateRedirect.isPending 
    });
    
    if (!editingRedirect) return;

    const redirectData = {
      id: editingRedirect.id,
      from_path: formData.get('fromPath') as string,
      to_path: formData.get('toPath') as string,
      status: parseInt(formData.get('status') as string),
      notes: formData.get('notes') as string,
    };

    console.log('🔥 About to call mutate', redirectData);

    // Store current redirect before clearing
    const currentRedirect = editingRedirect;

    // Close dialog immediately (optimistic update)
    setEditRedirectDialogOpen(false);
    setEditingRedirect(null);

    updateRedirect.mutate(redirectData, {
      onSuccess: () => {
        console.log('🔥 Mutation successful');
        toast({
          title: "Success",
          description: "Redirect updated successfully.",
        });
      },
      onError: (error) => {
        console.log('🔥 Mutation failed, reopening dialog', error);
        // Reopen dialog on error
        setEditRedirectDialogOpen(true);
        setEditingRedirect(currentRedirect);
        toast({
          title: "Error",
          description: error?.response?.data?.detail || "Failed to update redirect.",
          variant: "destructive",
        });
      }
    });
  };

  // Handle delete redirect
  const handleDeleteRedirect = () => {
    if (!redirectToDelete) return;
    
    deleteRedirect.mutate(redirectToDelete.id, {
      onSuccess: () => {
        setDeleteRedirectDialogOpen(false);
        setRedirectToDelete(null);
      }
    });
  };

  // Handle test redirect locally
  const handleTestRedirectLocally = (redirect: Redirect) => {
    const baseUrl = window.location.origin;
    const testUrl = `${baseUrl}${redirect.from_path}`;
    window.open(testUrl, '_blank');
    
    toast({
      title: "Testing Redirect",
      description: `Opening ${redirect.from_path} in a new tab. It should redirect to ${redirect.to_path}`,
    });
  };

  // Handle CSV upload
  const handleCSVUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === "text/csv") {
      setCsvFile(file);
      
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const lines = text.split('\n');
        const headers = lines[0].split(',').map(h => h.trim());
        
        const data = lines.slice(1, 6).map(line => {
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

  // Handle CSV import
  const handleCSVImport = () => {
    if (!csvFile) return;
    
    importCSV.mutate(csvFile, {
      onSuccess: () => {
        setCsvImportDialogOpen(false);
        setCsvFile(null);
        setCsvPreview([]);
      }
    });
  };

  // Handle edit redirect
  const handleEditRedirect = (redirect: Redirect) => {
    setEditingRedirect(redirect);
    setEditRedirectDialogOpen(true);
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
                        <Button 
                          variant="outline"
                          onClick={() => exportCSV.mutate()}
                          disabled={exportCSV.isPending}
                        >
                          {exportCSV.isPending ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          ) : (
                            <Download className="h-4 w-4 mr-2" />
                          )}
                          Export CSV
                        </Button>

                        <Button variant="outline" onClick={() => setCsvImportDialogOpen(true)}>
                          <Upload className="h-4 w-4 mr-2" />
                          Import CSV
                        </Button>

                        <SimpleDialog open={csvImportDialogOpen} onOpenChange={setCsvImportDialogOpen}>
                          <SimpleDialogHeader>
                            <SimpleDialogTitle>Import Redirects from CSV</SimpleDialogTitle>
                          </SimpleDialogHeader>
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
                                  disabled={!csvFile || importCSV.isPending}
                                >
                                  {importCSV.isPending ? (
                                    <>
                                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                      Importing...
                                    </>
                                  ) : (
                                    `Import ${csvPreview.length} Redirects`
                                  )}
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
                        </SimpleDialog>

                        {/* Edit Redirect Dialog */}
                        <SimpleDialog 
                          open={editRedirectDialogOpen} 
                          onOpenChange={(open) => {
                            if (!updateRedirect.isPending) {
                              setEditRedirectDialogOpen(open);
                            }
                          }}
                        >
                          <SimpleDialogHeader>
                            <SimpleDialogTitle>Edit Redirect</SimpleDialogTitle>
                          </SimpleDialogHeader>
                            {editingRedirect && (
                              <form onSubmit={(e) => {
                                e.preventDefault();
                                console.log('🔥 Form submitted');
                                const formData = new FormData(e.target as HTMLFormElement);
                                // Use setTimeout to defer execution and avoid blocking
                                setTimeout(() => {
                                  handleUpdateRedirect(formData);
                                }, 0);
                              }}>
                                <div className="space-y-4">
                                  <div>
                                    <Label htmlFor="editFromPath">From Path</Label>
                                    <Input 
                                      id="editFromPath" 
                                      name="fromPath"
                                      defaultValue={editingRedirect.from_path}
                                      placeholder="/old-path or /old-path/*" 
                                      required
                                    />
                                  </div>
                                  <div>
                                    <Label htmlFor="editToPath">To Path</Label>
                                    <Input 
                                      id="editToPath" 
                                      name="toPath"
                                      defaultValue={editingRedirect.to_path}
                                      placeholder="/new-path or /new-path/*" 
                                      required
                                    />
                                  </div>
                                  <div className="grid grid-cols-2 gap-4">
                                    <div>
                                      <Label htmlFor="editStatus">Status Code</Label>
                                      <Select name="status" defaultValue={editingRedirect.status.toString()}>
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
                                      <Label>Notes (Optional)</Label>
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
                                      type="submit"
                                      className="flex-1" 
                                      disabled={updateRedirect.isPending}
                                    >
                                      {updateRedirect.isPending ? (
                                        <>
                                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                          Updating...
                                        </>
                                      ) : (
                                        'Update Redirect'
                                      )}
                                    </Button>
                                    <Button 
                                      type="button"
                                      variant="outline" 
                                      onClick={() => {
                                        setEditRedirectDialogOpen(false);
                                        setEditingRedirect(null);
                                      }}
                                      disabled={updateRedirect.isPending}
                                    >
                                      Cancel
                                    </Button>
                                  </div>
                                </div>
                              </form>
                            )}
                        </SimpleDialog>

                        <Button onClick={() => setRedirectDialogOpen(true)}>
                          <Plus className="h-4 w-4 mr-2" />
                          Add Redirect
                        </Button>
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
                          onClick={() => refetch()}
                          disabled={isLoading}
                        >
                          {isLoading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <RefreshCw className="h-4 w-4" />
                          )}
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
                          {isLoading ? (
                            <TableRow>
                              <TableCell colSpan={6} className="text-center py-8">
                                <div className="flex items-center justify-center space-x-2">
                                  <Loader2 className="w-4 h-4 animate-spin" />
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
                            redirects.map((redirect: Redirect) => (
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
                                        onClick={() => testRedirect.mutate(redirect.id)}
                                        disabled={testRedirect.isPending}
                                      >
                                        Verify Redirect
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
                  <Suspense fallback={
                    <div className="space-y-6">
                      <Skeleton className="h-32 w-full" />
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Skeleton className="h-48 w-full" />
                        <Skeleton className="h-48 w-full" />
                      </div>
                    </div>
                  }>
                    <SitemapTab />
                  </Suspense>
                </TabsContent>
              </Tabs>
            </div>
          </main>
        </div>
      </div>

      {/* Create Redirect Dialog */}
      <SimpleDialog 
        open={redirectDialogOpen} 
        onOpenChange={(open) => {
          if (!createRedirect.isPending) {
            setRedirectDialogOpen(open);
          }
        }}
      >
        <SimpleDialogHeader>
          <SimpleDialogTitle>Add New Redirect</SimpleDialogTitle>
        </SimpleDialogHeader>
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
              <Button 
                type="submit" 
                className="flex-1"
                disabled={createRedirect.isPending}
              >
                {createRedirect.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Redirect'
                )}
              </Button>
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => setRedirectDialogOpen(false)}
                disabled={createRedirect.isPending}
              >
                Cancel
              </Button>
            </div>
          </div>
        </form>
      </SimpleDialog>
      
      {/* Delete Redirect Confirmation Modal */}
      <DeleteConfirmModal
        open={deleteRedirectDialogOpen}
        onOpenChange={setDeleteRedirectDialogOpen}
        title="Delete Redirect"
        description="Are you sure you want to permanently delete this redirect?"
        itemName={redirectToDelete ? `${redirectToDelete.from_path} → ${redirectToDelete.to_path}` : ''}
        warningMessage="This action cannot be undone. Any existing links using this redirect will result in 404 errors."
        onConfirm={handleDeleteRedirect}
        isDestructive={true}
        isLoading={deleteRedirect.isPending}
      />
    </div>
  );
};

export default SEORedirects;