import React, { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Search,
  Upload,
  Image as ImageIcon,
  FileImage,
  X,
  Check,
  Loader2,
  AlertCircle
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api.ts";

interface MediaAsset {
  id: string;
  filename: string;
  file: string;
  kind: 'image' | 'video' | 'file';
  width?: number;
  height?: number;
  size: number;
  created_at: string;
  description?: string;
  tags?: string;
}

interface MediaPickerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (asset: MediaAsset) => void;
  selectedAssetId?: string;
  title?: string;
  description?: string;
  allowedTypes?: ('image' | 'video' | 'file')[];
  multiple?: boolean;
}

export const MediaPicker: React.FC<MediaPickerProps> = ({
  open,
  onOpenChange,
  onSelect,
  selectedAssetId,
  title = "Select Media",
  description = "Choose an image from your media library or upload a new one.",
  allowedTypes = ['image'],
  multiple = false
}) => {
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAsset, setSelectedAsset] = useState<MediaAsset | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [activeTab, setActiveTab] = useState('browse');

  // Load assets when modal opens
  const loadAssets = useCallback(async () => {
    setLoading(true);
    try {
      const filters: any = {
        page: 1,
        limit: 50
      };

      if (searchQuery) {
        filters.search = searchQuery;
      }

      if (allowedTypes.length === 1) {
        filters.file_type = allowedTypes[0];
      }

      // Use files API which is the correct endpoint
      const response = await api.files.list({
        file_type: allowedTypes.includes('image') ? 'image' : undefined,
        search: searchQuery || undefined,
        page: 1,
        limit: 50
      });

      console.log('API Response:', response); // Debug log

      if (response?.results || response?.data) {
        const rawAssets = response.results || response.data || [];
        console.log('Raw assets:', rawAssets); // Debug log

        // Convert API response to our MediaAsset interface
        const convertedAssets = rawAssets.map((asset: any) => {
          console.log('Raw asset from API:', asset);
          console.log('Asset ID type:', typeof asset.id, 'Value:', asset.id);

          // The backend returns UUID strings for file IDs
          const assetId = String(asset.id); // Keep as UUID string

          return {
          id: assetId, // UUID string from backend
          filename: asset.filename || asset.original_filename || asset.name || 'Unknown',
          file: asset.download_url || asset.file || asset.url || `/api/v1/files/${assetId}/download/`,
          kind: asset.file_type === 'image' ? 'image' : (asset.kind || 'file'),
          width: asset.width || undefined,
          height: asset.height || undefined,
          size: asset.file_size || asset.size || 0,
          created_at: asset.created_at,
          description: asset.description || '',
          tags: Array.isArray(asset.tags) ? asset.tags.join(', ') : asset.tags || ''
        };
        });

        console.log('Converted assets:', convertedAssets); // Debug log
        setAssets(convertedAssets);

        // Pre-select current asset if provided
        if (selectedAssetId) {
          const currentAsset = convertedAssets.find((asset: MediaAsset) => asset.id === selectedAssetId);
          if (currentAsset) {
            setSelectedAsset(currentAsset);
          }
        }
      } else {
        // No assets found, set empty array
        setAssets([]);
      }
    } catch (error) {
      console.error('Failed to load assets:', error);
      setAssets([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  }, [searchQuery, allowedTypes, selectedAssetId]);

  useEffect(() => {
    if (open) {
      loadAssets();
    }
  }, [open]); // Remove loadAssets from dependency to prevent infinite loop

  // Handle search with debounce
  useEffect(() => {
    if (!open || !searchQuery) return; // Only run if modal is open and there's a search query

    const timeoutId = setTimeout(() => {
      loadAssets();
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery]); // Remove loadAssets from dependency to prevent infinite loop

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setUploadFile(file);
      setActiveTab('upload');
    }
  };

  const handleUpload = async () => {
    if (!uploadFile) return;

    setUploading(true);
    try {
      const uploadData = {
        file: uploadFile,
        description: 'SEO Image',
        tags: 'seo,media',
        is_public: true
      };

      console.log('Uploading file:', uploadFile.name);
      const response = await api.files.upload(uploadData);
      console.log('Upload response:', response);

      if (response?.data || response) {
        const rawAsset = response?.data || response;

        // Convert uploaded asset to MediaAsset format
        const assetId = String(rawAsset.id); // Keep UUID as string
        const newAsset: MediaAsset = {
          id: assetId,
          filename: rawAsset.filename || rawAsset.original_filename || uploadFile.name,
          file: rawAsset.download_url || rawAsset.file || `/api/v1/files/${assetId}/download/`,
          kind: rawAsset.file_type === 'image' ? 'image' : (rawAsset.kind || 'image'),
          width: rawAsset.width || undefined,
          height: rawAsset.height || undefined,
          size: rawAsset.file_size || rawAsset.size || uploadFile.size,
          created_at: rawAsset.created_at || new Date().toISOString(),
          description: rawAsset.description || 'SEO Image',
          tags: rawAsset.tags || 'seo,media'
        };

        console.log('Converted new asset:', newAsset);

        // Add to assets list immediately for instant feedback
        setAssets(prev => [newAsset, ...prev]);

        // Auto-select uploaded asset
        setSelectedAsset(newAsset);
        setActiveTab('browse');
        setUploadFile(null);

        // Refresh the assets list in the background to sync with server
        setTimeout(() => {
          // Store the selected asset ID before refresh
          const selectedId = newAsset.id;
          loadAssets().then(() => {
            // Re-select the uploaded asset after refresh
            const uploadedAsset = assets.find(a => a.id === selectedId);
            if (uploadedAsset) {
              setSelectedAsset(uploadedAsset);
            }
          });
        }, 500);

        console.log('Upload completed successfully');
      } else {
        console.error('No data in upload response:', response);
      }
    } catch (error) {
      console.error('Failed to upload file:', error);
      // You might want to show a toast notification here
    } finally {
      setUploading(false);
    }
  };

  const handleSelect = () => {
    if (selectedAsset) {
      onSelect(selectedAsset);
      onOpenChange(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getImageUrl = (asset: MediaAsset): string => {
    // Handle different possible URL formats
    if (asset.file.startsWith('http')) {
      return asset.file;
    }
    // If it starts with /, it's an absolute path on the server
    if (asset.file.startsWith('/')) {
      return `http://localhost:8000${asset.file}`;
    }
    // Otherwise it's a relative path
    return `http://localhost:8000/${asset.file}`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="browse">Browse Media</TabsTrigger>
            <TabsTrigger value="upload">Upload New</TabsTrigger>
          </TabsList>

          <TabsContent value="browse" className="space-y-4">
            <div className="flex items-center space-x-2">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search images..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => document.getElementById('file-upload')?.click()}
              >
                <Upload className="h-4 w-4 mr-2" />
                Quick Upload
              </Button>
              <input
                id="file-upload"
                type="file"
                accept={allowedTypes.includes('image') ? 'image/*' : undefined}
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>

            <ScrollArea className="h-96">
              {loading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="h-8 w-8 animate-spin" />
                </div>
              ) : assets.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
                  <FileImage className="h-12 w-12 mb-2" />
                  <p>No images found</p>
                  <p className="text-sm">Upload some images to get started</p>
                </div>
              ) : (
                <div className="grid grid-cols-4 gap-4">
                  {assets.map((asset) => (
                    <div
                      key={asset.id}
                      className={cn(
                        "relative cursor-pointer rounded-lg border-2 border-transparent hover:border-primary/50 transition-colors",
                        selectedAsset?.id === asset.id && "border-primary bg-primary/5"
                      )}
                      onClick={() => setSelectedAsset(asset)}
                    >
                      <div className="aspect-square rounded-lg overflow-hidden bg-muted relative">
                        {asset.kind === 'image' ? (
                          <img
                            src={getImageUrl(asset)}
                            alt={asset.filename}
                            className="w-full h-full object-cover"
                            onLoad={() => console.log('Image loaded:', getImageUrl(asset))}
                            onError={(e) => {
                              console.error('Failed to load image:', getImageUrl(asset));
                              // Show fallback icon
                              (e.target as HTMLImageElement).style.display = 'none';
                            }}
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <FileImage className="h-8 w-8 text-muted-foreground" />
                          </div>
                        )}
                        {/* Fallback icon for failed image loads */}
                        <div className="absolute inset-0 flex items-center justify-center">
                          <ImageIcon className="h-8 w-8 text-muted-foreground" />
                        </div>
                      </div>

                      {selectedAsset?.id === asset.id && (
                        <div className="absolute top-2 right-2 bg-primary text-primary-foreground rounded-full p-1">
                          <Check className="h-3 w-3" />
                        </div>
                      )}

                      <div className="mt-2">
                        <p className="text-xs truncate" title={asset.filename}>
                          {asset.filename}
                        </p>
                        <div className="flex items-center justify-between text-xs text-muted-foreground mt-1">
                          <span>{formatFileSize(asset.size)}</span>
                          {asset.width && asset.height ? (
                            <span>{asset.width}×{asset.height}</span>
                          ) : asset.kind === 'image' ? (
                            <span>Image</span>
                          ) : (
                            <span className="capitalize">{asset.kind}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="upload" className="space-y-4">
            <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-8 text-center">
              {uploadFile ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-center">
                    {uploadFile.type.startsWith('image/') ? (
                      <img
                        src={URL.createObjectURL(uploadFile)}
                        alt="Upload preview"
                        className="max-w-32 max-h-32 object-cover rounded"
                      />
                    ) : (
                      <FileImage className="h-16 w-16 text-muted-foreground" />
                    )}
                  </div>
                  <div>
                    <p className="font-medium">{uploadFile.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatFileSize(uploadFile.size)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 justify-center">
                    <Button
                      onClick={handleUpload}
                      disabled={uploading}
                    >
                      {uploading ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Uploading...
                        </>
                      ) : (
                        'Upload File'
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setUploadFile(null)}
                      disabled={uploading}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                  <div>
                    <p className="text-lg font-medium">Upload a new image</p>
                    <p className="text-muted-foreground">
                      Click to browse or drag and drop
                    </p>
                  </div>
                  <Button
                    onClick={() => document.getElementById('main-file-upload')?.click()}
                  >
                    Choose File
                  </Button>
                  <input
                    id="main-file-upload"
                    type="file"
                    accept={allowedTypes.includes('image') ? 'image/*' : undefined}
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSelect}
            disabled={!selectedAsset}
          >
            Select Image
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};