import React, { useState, useRef, useEffect, useMemo, useCallback, memo } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "@/components/Sidebar";
import TopNavbar from "@/components/TopNavbar";
import { MediaEmptyState } from "@/components/EmptyStates";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";
import { useTranslation } from "@/contexts/TranslationContext";
import {
  Upload,
  Search,
  Grid3X3,
  List,
  FileImage,
  Download,
  Trash2,
  Edit3,
  Eye,
  Copy,
  Tag,
  Calendar,
  User,
  HardDrive,
  Globe,
  AlertTriangle,
  RotateCw,
  Crop,
  RefreshCw,
  FileVideo,
  FileText,
  Image as ImageIcon,
  X,
  ChevronDown,
  SortAsc,
  SortDesc,
} from "lucide-react";

// Types
interface MediaAsset {
  id: string;
  name: string;
  type: 'image' | 'video' | 'file';
  size: number;
  url: string;
  thumbnail: string;
  uploadedAt: Date;
  uploader: string;
  tags: string[];
  title: string;
  altTexts: Record<string, string>;
  usage: { pageId: string; pageName: string; blockId?: string }[];
  renditions: { size: string; url: string; format: string }[];
  license?: string;
  sourceUrl?: string;
  isUsed: boolean;
  hasMissingAlt: boolean;
}

interface UploadItem {
  id: string;
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'processing' | 'complete' | 'error';
  error?: string;
  preview?: string;
}

// Convert backend file data to frontend MediaAsset interface
// Moved outside component to prevent recreation on every render
const convertFileToMediaAsset = (file: any): MediaAsset => {
  if (import.meta.env.DEV) {
    console.log('Converting file:', file);
  }
  
  const converted = {
    id: file.id,
    name: file.original_filename || file.filename,
    type: file.file_type === 'image' ? 'image' : file.file_type === 'video' ? 'video' : 'file',
    size: file.file_size,
    url: file.download_url || `/api/v1/files/${file.id}/download/`,
    thumbnail: file.download_url || `/api/v1/files/${file.id}/download/`,
    uploadedAt: new Date(file.created_at),
    uploader: file.created_by_name || 'Unknown',
    tags: file.tags ? file.tags.split(',').map((tag: string) => tag.trim()).filter(Boolean) : [],
    title: file.description || file.original_filename || file.filename,
    altTexts: { en: file.description || '' }, // Backend doesn't have alt texts yet
    usage: [], // Backend doesn't track usage yet
    renditions: [], // Backend doesn't have renditions yet
    license: '',
    sourceUrl: '',
    isUsed: false, // Backend doesn't track usage yet
    hasMissingAlt: !file.description
  };
  
  if (import.meta.env.DEV) {
    console.log('Converted to:', converted);
  }
  return converted;
};

const Media = memo(() => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);
  
  // Component-level memory management
  const abortControllerRef = useRef<AbortController>(new AbortController());
  const isMountedRef = useRef(true);
  const objectUrlsRef = useRef<Set<string>>(new Set());
  const timersRef = useRef<Set<NodeJS.Timeout>>(new Set());

  // Safe state setter to prevent updates on unmounted components
  const safeSetState = useCallback((setState: Function) => {
    return (...args: any[]) => {
      if (isMountedRef.current && !abortControllerRef.current.signal.aborted) {
        setState(...args);
      }
    };
  }, []);

  // Helper to track object URLs for cleanup
  const createObjectURL = useCallback((file: File): string => {
    const url = URL.createObjectURL(file);
    objectUrlsRef.current.add(url);
    return url;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      abortControllerRef.current.abort();
      
      // Clear any pending timers
      timersRef.current.forEach(timer => clearTimeout(timer));
      timersRef.current.clear();
      
      // Revoke all object URLs to prevent memory leaks
      objectUrlsRef.current.forEach(url => URL.revokeObjectURL(url));
      objectUrlsRef.current.clear();
    };
  }, []);

  // State
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'name' | 'size'>('newest');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedAsset, setSelectedAsset] = useState<MediaAsset | null>(null);
  const [showAssetDetail, setShowAssetDetail] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<UploadItem[]>([]);
  const [showUploadQueue, setShowUploadQueue] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [deleteAssetId, setDeleteAssetId] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [editFormData, setEditFormData] = useState<{
    title: string;
    altTexts: Record<string, string>;
    tags: string;
    license: string;
    sourceUrl: string;
  }>({
    title: '',
    altTexts: {},
    tags: '',
    license: '',
    sourceUrl: ''
  });
  const [isSaving, setIsSaving] = useState(false);

  // API state
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);


  // Load files from API
  const loadFiles = useCallback(async () => {
    if (!isMountedRef.current) return;
    
    try {
      safeSetState(setLoading)(true);
      safeSetState(setError)(null);
      
      // Check authentication first
      try {
        const user = await api.request({
          method: 'GET',
          url: '/auth/users/me/',
          signal: abortControllerRef.current.signal
        });
        
        if (!user || !isMountedRef.current) {
          safeSetState(setError)('Please log in to view files.');
          return;
        }
      } catch (authError: any) {
        if (authError.name === 'AbortError' || !isMountedRef.current) return;
        safeSetState(setError)('Please log in to view files.');
        return;
      }
      
      const response = await api.request({
        method: 'GET',
        url: '/api/v1/files/',
        signal: abortControllerRef.current.signal
      });
      
      if (!isMountedRef.current || abortControllerRef.current.signal.aborted) return;
      
      if (import.meta.env.DEV) {
        console.log('API Response:', response);
      }
      
      // Convert backend files to MediaAsset format
      const convertedAssets = response.results.map(convertFileToMediaAsset);
      
      if (import.meta.env.DEV) {
        console.log('Converted assets:', convertedAssets);
      }
      
      safeSetState(setAssets)(convertedAssets);
    } catch (err: any) {
      if (err.name === 'AbortError' || !isMountedRef.current) return;
      
      console.error('Failed to load files:', err);
      if (err.message.includes('Authentication')) {
        safeSetState(setError)('Please log in to view files.');
      } else {
        safeSetState(setError)('Failed to load files. Please try again.');
      }
      toast({
        title: t('media.error.loading_files', "Error loading files"),
        description: t('media.error.loading_files_desc', "Failed to load files. Please try again."),
        variant: "destructive",
      });
    } finally {
      if (!abortControllerRef.current.signal.aborted && isMountedRef.current) {
        safeSetState(setLoading)(false);
      }
    }
  }, [safeSetState, t, toast]);

  // Load files on component mount
  useEffect(() => {
    loadFiles();
  }, []);

  // Memoized utility functions
  const formatFileSize = useCallback((bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }, []);

  const getFileIcon = useCallback((type: string) => {
    switch (type) {
      case 'image': return ImageIcon;
      case 'video': return FileVideo;
      default: return FileText;
    }
  }, []);

  // Memoized helper function to check if a file is an image based on filename or mime type
  const isImageFile = useCallback((asset: MediaAsset) => {
    if (asset.type === 'image') return true;
    
    // Check file extension for common image formats (including WebP)
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.avif', '.tiff', '.ico'];
    const fileName = asset.name.toLowerCase();
    return imageExtensions.some(ext => fileName.endsWith(ext));
  }, []);

  // Memoized Asset Grid Item to prevent unnecessary re-renders
  const AssetGridItem = React.memo<{
    asset: MediaAsset;
    onEdit: (asset: MediaAsset) => void;
    onDelete: (id: string) => void;
  }>(({ asset, onEdit, onDelete }) => {
    const Icon = getFileIcon(asset.type);
    
    const handleCardClick = useCallback((e: React.MouseEvent) => {
      console.log('Card clicked for asset:', asset.id);
      onEdit(asset);
    }, [asset, onEdit]);


    const handleEditClick = useCallback((e: React.MouseEvent) => {
      console.log('Edit button clicked');
      e.preventDefault();
      e.stopPropagation();
      onEdit(asset);
    }, [asset, onEdit]);

    const handleDeleteClick = useCallback((e: React.MouseEvent) => {
      console.log('Delete button clicked, preventing propagation');
      e.preventDefault();
      e.stopPropagation();
      onDelete(asset.id);
    }, [asset.id, onDelete]);

    return (
      <Card 
        className="group relative cursor-pointer transition-all hover:ring-2 hover:ring-primary/20"
        onClick={handleCardClick}
      >
        <CardContent className="p-3">

          {/* Hover actions */}
          <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
            <Button size="sm" variant="secondary" onClick={handleEditClick}>
              <Edit3 className="w-3 h-3" />
            </Button>
            <Button 
              size="sm" 
              variant="destructive"
              onClick={handleDeleteClick}
              disabled={asset.isUsed}
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>

          {/* Thumbnail */}
          <div className="aspect-square bg-muted rounded-lg mb-3 flex items-center justify-center overflow-hidden">
            {isImageFile(asset) ? (
              <MediaImage 
                src={asset.thumbnail} 
                alt={asset.altTexts.en || asset.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <Icon className="w-8 h-8 text-muted-foreground" />
            )}
          </div>

          {/* File info */}
          <div className="space-y-1">
            <h3 className="font-medium text-sm truncate" title={asset.name}>
              {asset.name}
            </h3>
            <p className="text-xs text-muted-foreground">
              {formatFileSize(asset.size)}
            </p>
            
            {/* Alt text locales */}
            <div className="flex gap-1">
              {Object.entries(asset.altTexts).map(([locale, alt]) => (
                <Badge 
                  key={locale}
                  variant={alt ? "secondary" : "destructive"}
                  className="text-xs px-1.5 py-0.5"
                >
                  {locale.toUpperCase()}
                </Badge>
              ))}
            </div>

            {/* Status indicators */}
            <div className="flex items-center gap-1 pt-1">
              {asset.hasMissingAlt && (
                <AlertTriangle className="w-3 h-3 text-warning" />
              )}
              {asset.isUsed && (
                <Badge variant="outline" className="text-xs">
                  Used
                </Badge>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }, (prevProps, nextProps) => {
    // Only re-render if essential props change
    const prevAsset = prevProps.asset;
    const nextAsset = nextProps.asset;
    
    // Shallow comparison for performance
    if (
      prevAsset.id !== nextAsset.id ||
      prevAsset.name !== nextAsset.name ||
      prevAsset.size !== nextAsset.size ||
      prevAsset.type !== nextAsset.type ||
      prevAsset.isUsed !== nextAsset.isUsed ||
      prevAsset.hasMissingAlt !== nextAsset.hasMissingAlt
    ) {
      return false;
    }
    
    // Compare altTexts efficiently without JSON.stringify
    const prevAltTexts = prevAsset.altTexts || {};
    const nextAltTexts = nextAsset.altTexts || {};
    const prevKeys = Object.keys(prevAltTexts);
    const nextKeys = Object.keys(nextAltTexts);
    
    if (prevKeys.length !== nextKeys.length) return false;
    
    for (const key of prevKeys) {
      if (prevAltTexts[key] !== nextAltTexts[key]) return false;
    }
    
    return true;
  });

  // Separate preview component that's completely isolated from form state
  const MediaPreview: React.FC<{ 
    asset: MediaAsset;
  }> = React.memo(({ asset }) => {
    return (
      <div className="space-y-3">
        <h3 className="font-medium">Preview</h3>
        <div className="aspect-video bg-muted rounded-lg flex items-center justify-center overflow-hidden">
          {isImageFile(asset) ? (
            <MediaImage 
              key={asset.id}
              src={asset.url} 
              alt={asset.name}
              className="max-w-full max-h-full object-contain"
            />
          ) : (
            <div className="text-center">
              {React.createElement(getFileIcon(asset.type), { 
                className: "w-16 h-16 text-muted-foreground mx-auto mb-2" 
              })}
              <p className="text-sm text-muted-foreground">{asset.type.toUpperCase()} file</p>
            </div>
          )}
        </div>
      </div>
    );
  }, (prevProps, nextProps) => {
    // Only re-render if the asset id, url, name, or type changes
    return (
      prevProps.asset.id === nextProps.asset.id &&
      prevProps.asset.url === nextProps.asset.url &&
      prevProps.asset.name === nextProps.asset.name &&
      prevProps.asset.type === nextProps.asset.type
    );
  });

  // Component for handling image loading with fallbacks
  const MediaImage: React.FC<{ 
    src: string; 
    alt: string; 
    className?: string; 
    onError?: () => void;
  }> = React.memo(({ src, alt, className = "", onError }) => {
    const [imageError, setImageError] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    const handleImageError = () => {
      console.warn('Failed to load image:', src);
      setImageError(true);
      setIsLoading(false);
      onError?.();
    };

    const handleImageLoad = () => {
      setIsLoading(false);
    };

    // If there was an error loading the image, show an icon instead
    if (imageError) {
      return (
        <div className={`flex items-center justify-center bg-muted ${className}`}>
          <ImageIcon className="w-8 h-8 text-muted-foreground" />
        </div>
      );
    }

    return (
      <div className={`relative ${className}`}>
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-muted">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
          </div>
        )}
        <img 
          src={src} 
          alt={alt}
          className={`w-full h-full object-cover ${isLoading ? 'opacity-0' : 'opacity-100'} transition-opacity`}
          onError={handleImageError}
          onLoad={handleImageLoad}
          loading="lazy"
          // Add support for modern image formats
          style={{ imageRendering: 'auto' }}
        />
      </div>
    );
  });

  // Memoized filter and sort assets
  const filteredAssets = useMemo(() => {
    return assets.filter(asset => {
      if (searchQuery && !asset.name.toLowerCase().includes(searchQuery.toLowerCase()) && 
          !asset.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    });
  }, [assets, searchQuery]);

  const sortedAssets = useMemo(() => {
    return [...filteredAssets].sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'newest':
          comparison = b.uploadedAt.getTime() - a.uploadedAt.getTime();
          break;
        case 'oldest':
          comparison = a.uploadedAt.getTime() - b.uploadedAt.getTime();
          break;
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'size':
          comparison = a.size - b.size;
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });
  }, [filteredAssets, sortBy, sortOrder]);

  // Memoized drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!dropZoneRef.current?.contains(e.relatedTarget as Node)) {
      setIsDragOver(false);
    }
  }, []);

  const handleFileUpload = useCallback(async (files: File[]) => {
    if (!isMountedRef.current) return;
    
    // Limit upload queue size to prevent memory issues
    const MAX_QUEUE_SIZE = 50;
    if (files.length + uploadQueue.length > MAX_QUEUE_SIZE) {
      toast({
        title: "Too many files",
        description: `Maximum ${MAX_QUEUE_SIZE} files can be queued at once`,
        variant: "destructive",
      });
      return;
    }
    
    const newUploadItems: UploadItem[] = files.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      progress: 0,
      status: 'pending',
      preview: file.type.startsWith('image/') ? createObjectURL(file) : undefined
    }));

    safeSetState(setUploadQueue)(prev => [...prev, ...newUploadItems]);
    safeSetState(setShowUploadQueue)(true);

    // Upload files to API
    for (const item of newUploadItems) {
      if (!isMountedRef.current) break;
      await uploadFile(item);
    }
  }, [uploadQueue.length, createObjectURL, safeSetState, toast]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    handleFileUpload(files);
  }, [handleFileUpload]);

  const uploadFile = async (uploadItem: UploadItem) => {
    if (!isMountedRef.current) return;
    
    try {
      // Update status to uploading
      safeSetState(setUploadQueue)(prev => prev.map(item => 
        item.id === uploadItem.id ? { ...item, status: 'uploading', progress: 0 } : item
      ));

      // Check if user is authenticated first
      try {
        const user = await api.request({
          method: 'GET',
          url: '/auth/users/me/',
          signal: abortControllerRef.current.signal
        });
        
        if (!user || !isMountedRef.current) {
          throw new Error('Authentication required');
        }
      } catch (authError: any) {
        if (authError.name === 'AbortError' || !isMountedRef.current) return;
        throw new Error('Please log in to upload files');
      }

      // Upload file with abort signal
      const response = await api.request({
        method: 'POST',
        url: '/api/v1/files/',
        data: {
          file: uploadItem.file,
          description: '',
          is_public: false
        },
        signal: abortControllerRef.current.signal
      });

      if (!isMountedRef.current) return;

      // Update progress to complete
      safeSetState(setUploadQueue)(prev => prev.map(item => 
        item.id === uploadItem.id ? { ...item, status: 'complete', progress: 100 } : item
      ));

      toast({
        title: "Upload complete",
        description: `${uploadItem.file.name} has been uploaded successfully.`,
      });

      // Reload files list to show new upload
      await loadFiles();

    } catch (err: any) {
      if (err.name === 'AbortError' || !isMountedRef.current) return;
      
      console.error('Upload failed:', err);
      
      safeSetState(setUploadQueue)(prev => prev.map(item => 
        item.id === uploadItem.id ? { 
          ...item, 
          status: 'error', 
          error: 'Upload failed' 
        } : item
      ));

      toast({
        title: "Upload failed",
        description: `Failed to upload ${uploadItem.file.name}. Please try again.`,
        variant: "destructive",
      });
    }
  };





  const handleDeleteAsset = (assetId: string) => {
    console.log('Delete button clicked for asset:', assetId);
    const asset = assets.find(a => a.id === assetId);
    if (asset?.isUsed) {
      toast({
        title: "Cannot delete asset",
        description: "This asset is currently in use and cannot be deleted.",
        variant: "destructive",
      });
      return;
    }
    
    setDeleteAssetId(assetId);
    setShowDeleteConfirm(true);
  };

  const confirmDeleteAsset = async () => {
    if (deleteAssetId) {
      try {
        const asset = assets.find(a => a.id === deleteAssetId);
        await api.files.delete(deleteAssetId);
        
        toast({
          title: "Asset deleted",
          description: `${asset?.name} has been deleted successfully.`,
        });

        // Remove from local state
        setAssets(prev => prev.filter(a => a.id !== deleteAssetId));
        
        // Close asset detail if this asset was being viewed
        if (selectedAsset?.id === deleteAssetId) {
          setShowAssetDetail(false);
          setSelectedAsset(null);
        }
      } catch (err) {
        console.error('Delete failed:', err);
        toast({
          title: "Delete failed",
          description: "Failed to delete the asset. Please try again.",
          variant: "destructive",
        });
      }
    }
    setDeleteAssetId(null);
    setShowDeleteConfirm(false);
  };

  const initializeEditForm = useCallback((asset: MediaAsset) => {
    setEditFormData({
      title: asset.title || '',
      altTexts: asset.altTexts || { en: '' },
      tags: asset.tags.join(', '),
      license: asset.license || '',
      sourceUrl: asset.sourceUrl || ''
    });
  }, []);

  const handleSaveAsset = async () => {
    if (!selectedAsset) return;
    
    setIsSaving(true);
    try {
      // Convert tags string back to array
      const tagsArray = editFormData.tags
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0);
      
      // Update via API
      await api.files.update(selectedAsset.id, {
        description: editFormData.title,
        tags: tagsArray.join(', '),
        is_public: true // You might want to make this configurable
      });
      
      // Update local state
      const updatedAsset = {
        ...selectedAsset,
        title: editFormData.title,
        tags: tagsArray,
        license: editFormData.license,
        sourceUrl: editFormData.sourceUrl,
        altTexts: editFormData.altTexts
      };
      
      setAssets(prev => prev.map(asset => 
        asset.id === selectedAsset.id ? updatedAsset : asset
      ));
      setSelectedAsset(updatedAsset);
      
      toast({
        title: "Asset updated",
        description: "Your changes have been saved successfully.",
      });
      
    } catch (err) {
      console.error('Save failed:', err);
      toast({
        title: "Save failed",
        description: "Failed to save changes. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownloadAsset = useCallback((asset: MediaAsset) => {
    // Create a temporary link and trigger download
    const link = document.createElement('a');
    link.href = asset.url;
    link.download = asset.name;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    toast({
      title: "Download started",
      description: `Downloading ${asset.name}`,
    });
  }, [toast]);

  // Memoized handlers for AssetGridItem
  const handleAssetEdit = useCallback((asset: MediaAsset) => {
    setSelectedAsset(asset);
    initializeEditForm(asset);
    setShowAssetDetail(true);
  }, [initializeEditForm]);

  const handleAssetDelete = useCallback((assetId: string) => {
    handleDeleteAsset(assetId);
  }, []);

  return (
    <div className="min-h-screen">
      <div className="flex">
        <Sidebar />
        
        <div className="flex-1 flex flex-col ml-72">
          <TopNavbar />
          
          <main 
            className="flex-1 p-8"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="max-w-7xl mx-auto space-y-6" ref={dropZoneRef}>
              
              {/* Drag overlay */}
              {isDragOver && (
                <div className="fixed inset-0 bg-primary/10 backdrop-blur-sm z-50 flex items-center justify-center">
                  <div className="bg-card p-8 rounded-lg border-2 border-dashed border-primary">
                    <Upload className="w-12 h-12 text-primary mx-auto mb-4" />
                    <p className="text-lg font-medium text-center">Drop files here to upload</p>
                  </div>
                </div>
              )}

              {/* Header */}
              <div className="mb-8">
                <h1 className="text-3xl font-bold text-foreground">{t('media.title', 'Media')}</h1>
                <p className="text-muted-foreground">
                  Manage your media assets and files
                </p>
              </div>

              <div className="flex items-center justify-between mb-6">
                <div></div>
                <div className="flex items-center gap-3">
                  <Button onClick={() => fileInputRef.current?.click()}>
                    <Upload className="w-4 h-4 mr-2" />
                    Upload
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept="image/*,video/*,.pdf,.doc,.docx"
                    className="hidden"
                    onChange={(e) => e.target.files && handleFileUpload(Array.from(e.target.files))}
                  />
                </div>
              </div>


              {/* Search, Filters, and Controls */}
              <Card>
                <CardContent className="p-4">
                  <div className="space-y-4">
                    {/* Top row: Search, View toggle, Sort */}
                    <div className="flex items-center justify-between gap-4">
                      <div className="relative flex-1 max-w-sm">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                          placeholder={t('media.search_placeholder', 'Search media...')}
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="pl-10"
                        />
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
                          <SelectTrigger className="w-32">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="newest">{t('media.sort.newest', 'Newest')}</SelectItem>
                            <SelectItem value="oldest">{t('media.sort.oldest', 'Oldest')}</SelectItem>
                            <SelectItem value="name">{t('media.sort.name', 'Name')}</SelectItem>
                            <SelectItem value="size">{t('media.sort.size', 'Size')}</SelectItem>
                          </SelectContent>
                        </Select>

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                        >
                          {sortOrder === 'asc' ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />}
                        </Button>

                        <div className="flex border rounded-lg">
                          <Button
                            variant={viewMode === 'grid' ? 'default' : 'ghost'}
                            size="sm"
                            onClick={() => setViewMode('grid')}
                            className="rounded-r-none"
                          >
                            <Grid3X3 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant={viewMode === 'list' ? 'default' : 'ghost'}
                            size="sm"
                            onClick={() => setViewMode('list')}
                            className="rounded-l-none"
                          >
                            <List className="w-4 h-4" />
                          </Button>
                        </div>

                      </div>
                    </div>

                  </div>
                </CardContent>
              </Card>

              {/* Accessibility Guardrails */}
              {assets.some(asset => asset.hasMissingAlt && asset.isUsed) && (
                <Card className="border-warning bg-warning/5">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <AlertTriangle className="w-5 h-5 text-warning" />
                      <div className="flex-1">
                        <h3 className="font-medium text-warning">Missing Alt Text</h3>
                        <p className="text-sm text-muted-foreground">
                          Some published assets are missing alt text in some locales
                        </p>
                      </div>
                      <Button size="sm" variant="outline">
                        <Edit3 className="w-4 h-4 mr-1" />
                        Quick Edit
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Loading/Error States */}
              {loading && (
                <Card>
                  <CardContent className="p-8">
                    <div className="flex items-center justify-center">
                      <div className="text-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
                        <p className="text-muted-foreground">Loading files...</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {error && (
                <Card className="border-destructive bg-destructive/5">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <AlertTriangle className="w-5 h-5 text-destructive" />
                      <div className="flex-1">
                        <h3 className="font-medium text-destructive">Error Loading Files</h3>
                        <p className="text-sm text-muted-foreground">{error}</p>
                      </div>
                      {error.includes('log in') ? (
                        <Button size="sm" variant="outline" onClick={() => navigate('/login')}>
                          <User className="w-4 h-4 mr-1" />
                          Login
                        </Button>
                      ) : (
                        <Button size="sm" variant="outline" onClick={loadFiles}>
                          <RefreshCw className="w-4 h-4 mr-1" />
                          Retry
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Asset Grid/List */}
              {!loading && !error && (viewMode === 'grid' ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                  {sortedAssets.map((asset) => (
                    <AssetGridItem
                      key={asset.id}
                      asset={asset}
                      onEdit={handleAssetEdit}
                      onDelete={handleAssetDelete}
                    />
                  ))}
                </div>
              ) : (
                /* List View */
                <Card>
                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <div className="flex-1">Name</div>
                      <div className="w-20">Size</div>
                      <div className="w-24">Type</div>
                      <div className="w-32">Uploaded</div>
                      <div className="w-24">Status</div>
                      <div className="w-20">Actions</div>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0">
                    {sortedAssets.map((asset) => {
                      const Icon = getFileIcon(asset.type);
                      
                      return (
                        <div 
                          key={asset.id}
                          className="flex items-center gap-4 p-4 border-b last:border-b-0 hover:bg-muted/50 transition-colors"
                        >
                          
                          <div className="flex-1 flex items-center gap-3">
                            <div className="w-10 h-10 bg-muted rounded flex items-center justify-center overflow-hidden">
                              {isImageFile(asset) ? (
                                <MediaImage 
                                  src={asset.thumbnail} 
                                  alt={asset.altTexts.en || asset.name}
                                  className="w-full h-full object-cover rounded"
                                />
                              ) : (
                                <Icon className="w-5 h-5 text-muted-foreground" />
                              )}
                            </div>
                            <div>
                              <p className="font-medium">{asset.name}</p>
                              <p className="text-sm text-muted-foreground">{asset.title}</p>
                            </div>
                          </div>
                          
                          <div className="w-20 text-sm text-muted-foreground">
                            {formatFileSize(asset.size)}
                          </div>
                          
                          <div className="w-24">
                            <Badge variant="outline" className="capitalize">
                              {asset.type}
                            </Badge>
                          </div>
                          
                          <div className="w-32 text-sm text-muted-foreground">
                            {asset.uploadedAt.toLocaleDateString()}
                          </div>
                          
                          <div className="w-24">
                            <div className="flex items-center gap-1">
                              {asset.hasMissingAlt && (
                                <AlertTriangle className="w-3 h-3 text-warning" />
                              )}
                              {asset.isUsed ? (
                                <Badge variant="secondary" className="text-xs">Used</Badge>
                              ) : (
                                <Badge variant="outline" className="text-xs">Unused</Badge>
                              )}
                            </div>
                          </div>
                          
                          <div className="w-20 flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                console.log('List view: View button clicked');
                                e.preventDefault();
                                e.stopPropagation();
                                setSelectedAsset(asset);
                                initializeEditForm(asset);
                                setShowAssetDetail(true);
                              }}
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                console.log('List view: Delete button clicked');
                                e.preventDefault();
                                e.stopPropagation();
                                handleDeleteAsset(asset.id);
                              }}
                              disabled={asset.isUsed}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              ))}

              {/* Upload Queue */}
              {showUploadQueue && uploadQueue.length > 0 && (
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <h3 className="font-medium">Upload Queue</h3>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setShowUploadQueue(false)}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {uploadQueue.map((item) => (
                      <div key={item.id} className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-muted rounded flex items-center justify-center">
                          {item.preview ? (
                            <MediaImage src={item.preview} alt="" className="w-full h-full object-cover rounded" />
                          ) : (
                            <FileImage className="w-6 h-6 text-muted-foreground" />
                          )}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium">{item.file.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {formatFileSize(item.file.size)} • {item.status}
                          </p>
                          {item.status === 'uploading' && (
                            <Progress value={item.progress} className="h-1 mt-1" />
                          )}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {item.status === 'complete' ? '✓' : `${item.progress}%`}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {/* Empty state */}
              {!loading && !error && sortedAssets.length === 0 && (
                <MediaEmptyState 
                  onUpload={() => fileInputRef.current?.click()}
                  isDragActive={isDragOver}
                />
              )}

            </div>
          </main>
        </div>
      </div>

      {/* Asset Detail Panel */}
      <Sheet open={showAssetDetail} onOpenChange={setShowAssetDetail}>
        <SheetContent className="sm:max-w-lg">
          {selectedAsset && (
            <>
              <SheetHeader>
                <SheetTitle>{selectedAsset.name}</SheetTitle>
              </SheetHeader>
              
              <div className="space-y-6 py-6">
                {/* Preview - Isolated from form state */}
                <MediaPreview asset={selectedAsset} />
                  
                  {/* Renditions */}
                  {selectedAsset.renditions.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-sm font-medium">Renditions</h4>
                      {selectedAsset.renditions.map((rendition, index) => (
                        <div key={index} className="flex items-center justify-between text-sm">
                          <span>{rendition.size} ({rendition.format})</span>
                          <Button size="sm" variant="ghost">
                            <Copy className="w-3 h-3 mr-1" />
                            Copy URL
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Edit Form */}
                <div className="space-y-4">
                  <div className="space-y-3">
                    <div>
                      <Label htmlFor="title">Title</Label>
                      <Input 
                        id="title" 
                        value={editFormData.title}
                        onChange={(e) => setEditFormData(prev => ({ ...prev, title: e.target.value }))}
                      />
                    </div>
                    
                    <div>
                      <Label>Alt Text</Label>
                      <div className="space-y-2">
                        {Object.entries(editFormData.altTexts).map(([locale, alt]) => (
                          <div key={locale}>
                            <Label htmlFor={`alt-${locale}`} className="text-xs">
                              {locale.toUpperCase()}
                              {selectedAsset.isUsed && !alt && (
                                <Badge variant="destructive" className="ml-1 text-xs">Required</Badge>
                              )}
                            </Label>
                            <Textarea 
                              id={`alt-${locale}`}
                              value={alt}
                              onChange={(e) => setEditFormData(prev => ({
                                ...prev,
                                altTexts: { ...prev.altTexts, [locale]: e.target.value }
                              }))}
                              placeholder={`Alt text for ${locale.toUpperCase()}`}
                              className="min-h-[60px]"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    <div>
                      <Label htmlFor="tags">Tags</Label>
                      <Input 
                        id="tags" 
                        value={editFormData.tags}
                        onChange={(e) => setEditFormData(prev => ({ ...prev, tags: e.target.value }))}
                        placeholder="Enter tags separated by commas"
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="license">License</Label>
                      <Input 
                        id="license" 
                        value={editFormData.license}
                        onChange={(e) => setEditFormData(prev => ({ ...prev, license: e.target.value }))}
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="source">Source URL</Label>
                      <Input 
                        id="source" 
                        value={editFormData.sourceUrl}
                        onChange={(e) => setEditFormData(prev => ({ ...prev, sourceUrl: e.target.value }))}
                      />
                    </div>
                  </div>
                </div>

                <div className="flex gap-2 pt-4">
                  <Button 
                    className="flex-1" 
                    onClick={handleSaveAsset}
                    disabled={isSaving}
                  >
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </Button>
                  <Button variant="outline" onClick={() => setShowAssetDetail(false)}>
                    Cancel
                  </Button>
                </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('media.delete.title', 'Delete Asset')}</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this asset? This action cannot be undone.
              {deleteAssetId && assets.find(a => a.id === deleteAssetId)?.isUsed && (
                <div className="mt-2 p-2 bg-destructive/10 rounded text-destructive text-sm">
                  <AlertTriangle className="w-4 h-4 inline mr-1" />
                  This asset is currently in use and cannot be deleted.
                </div>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel', 'Cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDeleteAsset}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteAssetId ? assets.find(a => a.id === deleteAssetId)?.isUsed : false}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
});

Media.displayName = 'Media';
export default Media;