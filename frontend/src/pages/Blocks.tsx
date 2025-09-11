import { useState, useEffect, useMemo, useCallback, useRef, lazy, Suspense } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useDebounce } from "@/hooks/useDebounce";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
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
  Plus,
  Search,
  MoreHorizontal,
  Edit,
  Copy,
  Trash2,
  Eye,
  EyeOff,
  Blocks as BlocksIcon,
  BarChart3
} from "lucide-react";

// Lazy load modal components
const CreateBlockModal = lazy(() => import("./blocks/CreateBlockModal"));
const EditBlockModal = lazy(() => import("./blocks/EditBlockModal"));
const DeleteBlockModal = lazy(() => import("./blocks/DeleteBlockModal"));

interface BlockType {
  id: number;
  type: string;
  component: string;
  label: string;
  description: string;
  category: string;
  category_display: string;
  icon: string;
  is_active: boolean;
  preload: boolean;
  editing_mode: string;
  schema: Record<string, any>;
  default_props: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by?: number;
  created_by_name?: string;
  updated_by?: number;
  updated_by_name?: string;
}

interface BlockTypeCategory {
  value: string;
  label: string;
}

interface Stats {
  total: number;
  active: number;
  inactive: number;
  by_category: Record<string, { label: string; count: number; active: number }>;
  preload_enabled: number;
}

export default function Blocks() {
  const [blockTypes, setBlockTypes] = useState<BlockType[]>([]);
  const [categories, setCategories] = useState<BlockTypeCategory[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearchTerm = useDebounce(searchTerm, 300);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedBlockType, setSelectedBlockType] = useState<BlockType | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  // Create abort controller for cleanup
  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch data with proper abort handling
  const fetchData = useCallback(async () => {
    // Cancel any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      setLoading(true);
      
      // Use the API with abort signal
      const response = await api.blockTypes.dashboardData(abortController.signal);
      
      // Check if request was aborted
      if (abortController.signal.aborted) return;
      
      setBlockTypes(response.block_types || []);
      setCategories(response.categories || []);
      setStats(response.stats || null);
    } catch (error: any) {
      // Don't show error if request was aborted
      if (error.name === 'AbortError') return;
      
      console.error('Failed to fetch data:', error);
      toast.error('Failed to load blocks data');
    } finally {
      // Only update loading state if not aborted
      if (!abortController.signal.aborted) {
        setLoading(false);
      }
    }
  }, []);

  // Initial data fetch with cleanup - run only once on mount
  useEffect(() => {
    fetchData();
    
    // Cleanup function
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []); // Empty dependency array - run only once!

  // Filter block types
  const filteredBlockTypes = useMemo(() => {
    return blockTypes.filter(block => {
      if (categoryFilter && categoryFilter !== "all" && block.category !== categoryFilter) return false;
      if (activeFilter && activeFilter !== "all") {
        if (activeFilter === "active" && !block.is_active) return false;
        if (activeFilter === "inactive" && block.is_active) return false;
      }
      
      if (debouncedSearchTerm) {
        const searchLower = debouncedSearchTerm.toLowerCase();
        const matchesSearch = 
          block.label.toLowerCase().includes(searchLower) ||
          block.type.toLowerCase().includes(searchLower) ||
          block.component.toLowerCase().includes(searchLower) ||
          (block.description && block.description.toLowerCase().includes(searchLower));
        
        if (!matchesSearch) return false;
      }
      
      return true;
    });
  }, [blockTypes, debouncedSearchTerm, categoryFilter, activeFilter]);

  // Paginated results
  const paginatedBlockTypes = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredBlockTypes.slice(startIndex, endIndex);
  }, [filteredBlockTypes, currentPage]);

  const totalPages = Math.ceil(filteredBlockTypes.length / itemsPerPage);

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [debouncedSearchTerm, categoryFilter, activeFilter]);

  // Handlers
  const handleCreate = async (formData: any) => {
    const abortController = new AbortController();
    
    try {
      await api.blockTypes.create(formData, abortController.signal);
      toast.success('Block type created successfully');
      setShowCreateModal(false);
      fetchData();
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Failed to create block type:', error);
        toast.error(error.message || 'Failed to create block type');
      }
    }
  };

  const handleEdit = async (formData: any) => {
    if (!selectedBlockType) return;
    
    const abortController = new AbortController();
    
    try {
      await api.blockTypes.update(selectedBlockType.id, formData, abortController.signal);
      toast.success('Block type updated successfully');
      setShowEditModal(false);
      setSelectedBlockType(null);
      fetchData();
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Failed to update block type:', error);
        toast.error(error.message || 'Failed to update block type');
      }
    }
  };

  const handleDelete = async () => {
    if (!selectedBlockType) return;
    
    const abortController = new AbortController();
    
    try {
      await api.blockTypes.delete(selectedBlockType.id, abortController.signal);
      toast.success('Block type deleted successfully');
      setShowDeleteModal(false);
      setSelectedBlockType(null);
      fetchData();
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Failed to delete block type:', error);
        toast.error(error.message || 'Failed to delete block type');
      }
    }
  };

  const handleToggleActive = async (blockType: BlockType) => {
    const abortController = new AbortController();
    
    try {
      await api.blockTypes.toggleActive(blockType.id, abortController.signal);
      toast.success(`Block type ${blockType.is_active ? 'deactivated' : 'activated'} successfully`);
      fetchData();
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Failed to toggle block type:', error);
        toast.error('Failed to toggle block type status');
      }
    }
  };

  const handleDuplicate = async (blockType: BlockType) => {
    const abortController = new AbortController();
    
    try {
      await api.blockTypes.duplicate(blockType.id, abortController.signal);
      toast.success('Block type duplicated successfully');
      fetchData();
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Failed to duplicate block type:', error);
        toast.error('Failed to duplicate block type');
      }
    }
  };

  const getCategoryBadgeVariant = (category: string): "default" | "secondary" | "outline" | "destructive" => {
    // Return standard badge variants instead of custom colors
    return "secondary";
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
                <div className="mb-8">
                  <h1 className="text-3xl font-bold text-foreground mb-2">Block Types</h1>
                  <p className="text-muted-foreground">Loading block types...</p>
                </div>
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <BlocksIcon className="mx-auto h-12 w-12 text-muted-foreground animate-pulse" />
                    <p className="mt-2 text-sm text-muted-foreground">Loading...</p>
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
            <div className="max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div className="mb-8">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-foreground">Block Types</h1>
                  <p className="text-muted-foreground">Manage your content blocks and components</p>
                </div>
                <Button 
                  onClick={() => setShowCreateModal(true)} 
                  className="flex items-center gap-2"
                >
                  <Plus className="h-4 w-4" />
                  Create Block Type
                </Button>
              </div>
            </div>

            {/* Stats Cards */}
            {stats && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3">
                      <BlocksIcon className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="text-sm text-muted-foreground">Total Blocks</p>
                        <p className="text-2xl font-semibold">{stats.total}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3">
                      <Eye className="h-5 w-5 text-green-600" />
                      <div>
                        <p className="text-sm text-muted-foreground">Active</p>
                        <p className="text-2xl font-semibold">{stats.active}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3">
                      <EyeOff className="h-5 w-5 text-red-600" />
                      <div>
                        <p className="text-sm text-muted-foreground">Inactive</p>
                        <p className="text-2xl font-semibold">{stats.inactive}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-center gap-3">
                      <BarChart3 className="h-5 w-5 text-purple-600" />
                      <div>
                        <p className="text-sm text-muted-foreground">Preloaded</p>
                        <p className="text-2xl font-semibold">{stats.preload_enabled}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Filters */}
            <div className="flex flex-wrap gap-4 items-center">
              <div className="relative flex-1 min-w-64">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search block types..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="All Categories" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {categories.map(category => (
                    <SelectItem key={category.value} value={category.value}>
                      {category.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={activeFilter} onValueChange={setActiveFilter}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Table */}
            <Card>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Block Type</TableHead>
                    <TableHead>Component</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Settings</TableHead>
                    <TableHead>Last Updated</TableHead>
                    <TableHead className="w-20">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedBlockTypes.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                        No block types found
                      </TableCell>
                    </TableRow>
                  ) : (
                    paginatedBlockTypes.map((blockType) => (
                      <TableRow key={blockType.id}>
                        <TableCell>
                          <div>
                            <div className="font-medium">{blockType.label}</div>
                            <div className="text-sm text-muted-foreground">{blockType.type}</div>
                            {blockType.description && (
                              <div className="text-xs text-gray-400 mt-1 max-w-xs truncate">
                                {blockType.description}
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {blockType.component}
                          </code>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getCategoryBadgeVariant(blockType.category)}>
                            {blockType.category_display || blockType.category}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={blockType.is_active ? "default" : "secondary"}>
                            {blockType.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {blockType.preload && (
                              <Badge variant="outline" className="text-xs">
                                Preload
                              </Badge>
                            )}
                            <Badge variant="outline" className="text-xs">
                              {blockType.editing_mode}
                            </Badge>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-600">
                            {new Date(blockType.updated_at).toLocaleDateString()}
                          </div>
                          {blockType.updated_by_name && (
                            <div className="text-xs text-gray-400">
                              by {blockType.updated_by_name}
                            </div>
                          )}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" className="h-8 w-8 p-0">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => {
                                setSelectedBlockType(blockType);
                                setShowEditModal(true);
                              }}>
                                <Edit className="h-4 w-4 mr-2" />
                                Edit
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleDuplicate(blockType)}>
                                <Copy className="h-4 w-4 mr-2" />
                                Duplicate
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleToggleActive(blockType)}>
                                {blockType.is_active ? (
                                  <><EyeOff className="h-4 w-4 mr-2" /> Deactivate</>
                                ) : (
                                  <><Eye className="h-4 w-4 mr-2" /> Activate</>
                                )}
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                onClick={() => {
                                  setSelectedBlockType(blockType);
                                  setShowDeleteModal(true);
                                }}
                                className="text-red-600"
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
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
            </Card>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-700">
                  Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, filteredBlockTypes.length)} of {filteredBlockTypes.length} results
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </Button>
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map(page => (
                      <Button
                        key={page}
                        variant={currentPage === page ? "default" : "outline"}
                        size="sm"
                        onClick={() => setCurrentPage(page)}
                        className="w-8 h-8 p-0"
                      >
                        {page}
                      </Button>
                    ))}
                    {totalPages > 5 && (
                      <>
                        <span className="text-gray-500">...</span>
                        <Button
                          variant={currentPage === totalPages ? "default" : "outline"}
                          size="sm"
                          onClick={() => setCurrentPage(totalPages)}
                          className="w-8 h-8 p-0"
                        >
                          {totalPages}
                        </Button>
                      </>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>

    {/* Modals */}
    <Suspense fallback={null}>
        {showCreateModal && (
          <CreateBlockModal
            open={showCreateModal}
            onOpenChange={setShowCreateModal}
            onSubmit={handleCreate}
            categories={categories}
          />
        )}
      </Suspense>

      <Suspense fallback={null}>
        {showEditModal && selectedBlockType && (
          <EditBlockModal
            open={showEditModal}
            onOpenChange={setShowEditModal}
            onSubmit={handleEdit}
            blockType={selectedBlockType}
            categories={categories}
          />
        )}
      </Suspense>

      <Suspense fallback={null}>
        {showDeleteModal && selectedBlockType && (
          <DeleteBlockModal
            open={showDeleteModal}
            onOpenChange={setShowDeleteModal}
            onConfirm={handleDelete}
            blockType={selectedBlockType}
          />
        )}
      </Suspense>
    </div>
  );
}