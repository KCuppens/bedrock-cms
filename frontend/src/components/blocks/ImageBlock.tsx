import React, { useMemo, useState, useEffect } from 'react';
import { BlockComponentProps } from './types';
import { ImagePreset, getPreset, getAllPresets, DEFAULT_PRESET } from '@/config/imagePresets';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Settings, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

interface ThumbnailConfig {
  preset?: string;
  customSizes?: {
    mobile: { width: number; height?: number; quality: number };
    tablet?: { width: number; height?: number; quality: number };
    desktop: { width: number; height?: number; quality: number };
  };
  formats?: ('webp' | 'jpeg' | 'avif')[];
  placeholder?: 'blurhash' | 'dominant-color' | 'blur';
  priority?: boolean;
}

interface ImageBlockProps extends BlockComponentProps {
  content: {
    src?: string;
    alt?: string;
    caption?: string;
    width?: number;
    height?: number;
    alignment?: 'left' | 'center' | 'right';
    className?: string;
    thumbnailConfig?: ThumbnailConfig;
    fileId?: string;
    useThumbnails?: boolean;
  };
}

const ImageBlock: React.FC<ImageBlockProps> = React.memo(({ content, isEditing, onChange }) => {
  const {
    src,
    alt = '',
    caption,
    width,
    height,
    alignment = 'center',
    className = '',
    thumbnailConfig,
    fileId,
    useThumbnails = false
  } = content;

  if (!src) {
    return null;
  }

  const alignmentClasses = useMemo(() => ({
    left: 'text-left',
    center: 'text-center',
    right: 'text-right'
  }), []);

  const imageAlignmentClasses = useMemo(() => ({
    left: 'mr-auto',
    center: 'mx-auto',
    right: 'ml-auto'
  }), []);

  return (
    <figure className={`image-block ${alignmentClasses[alignment]} ${className}`.trim()}>
      {useThumbnails && fileId && thumbnailConfig ? (
        <ResponsiveImage
          fileId={fileId}
          thumbnailConfig={thumbnailConfig}
          alt={alt}
          width={width}
          height={height}
          className={`max-w-full h-auto ${imageAlignmentClasses[alignment]}`.trim()}
          priority={thumbnailConfig.priority || false}
        />
      ) : (
        <img
          src={src}
          alt={alt}
          width={width}
          height={height}
          className={`max-w-full h-auto ${imageAlignmentClasses[alignment]}`.trim()}
          loading="lazy"
        />
      )}
      {caption && (
        <figcaption className="mt-2 text-sm text-gray-600 italic">
          {caption}
        </figcaption>
      )}

      {isEditing && (
        <ImageBlockSettings
          content={content}
          onChange={onChange}
        />
      )}
    </figure>
  );
});

ImageBlock.displayName = 'ImageBlock';

// ResponsiveImage Component with CDN Support
interface ResponsiveImageProps {
  fileId: string;
  thumbnailConfig: ThumbnailConfig;
  alt: string;
  width?: number;
  height?: number;
  className?: string;
  priority?: boolean;
}

const ResponsiveImage: React.FC<ResponsiveImageProps> = ({
  fileId,
  thumbnailConfig,
  alt,
  width,
  height,
  className,
  priority = false
}) => {
  const [thumbnailUrls, setThumbnailUrls] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [placeholderData, setPlaceholderData] = useState<{ blurhash?: string; dominantColor?: string }>({});

  useEffect(() => {
    const generateThumbnails = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Get preset configuration
        const preset = thumbnailConfig.preset ? getPreset(thumbnailConfig.preset) : null;
        const config = preset ? {
          sizes: preset.sizes,
          formats: preset.formats,
          placeholder: preset.placeholder,
          priority: thumbnailConfig.priority || preset.priority
        } : {
          sizes: thumbnailConfig.customSizes || {},
          formats: thumbnailConfig.formats || ['webp', 'jpeg'],
          placeholder: thumbnailConfig.placeholder || 'blurhash',
          priority: thumbnailConfig.priority || false
        };

        // Generate thumbnails via API
        const response = await api.post(`/files/${fileId}/generate-thumbnails/`, config);

        if (response.data.status === 'processing') {
          // Poll for completion
          const pollStatus = async () => {
            const statusResponse = await api.get(`/files/${fileId}/thumbnail-status/${response.data.config_hash}/`);

            if (statusResponse.data.status === 'completed') {
              setThumbnailUrls(statusResponse.data.urls || {});
              setIsLoading(false);
            } else if (statusResponse.data.status === 'failed') {
              setError(statusResponse.data.error || 'Thumbnail generation failed');
              setIsLoading(false);
            } else {
              // Still processing, poll again in 2 seconds
              setTimeout(pollStatus, 2000);
            }
          };

          pollStatus();
        } else if (response.data.status === 'completed') {
          setThumbnailUrls(response.data.urls || {});
          setIsLoading(false);
        } else {
          setError(response.data.error || 'Thumbnail generation failed');
          setIsLoading(false);
        }

        // Get file metadata for placeholder
        const fileResponse = await api.get(`/files/${fileId}/`);
        setPlaceholderData({
          blurhash: fileResponse.data.blurhash,
          dominantColor: fileResponse.data.dominant_color
        });

      } catch (err: any) {
        setError(err.message || 'Failed to generate thumbnails');
        setIsLoading(false);
      }
    };

    generateThumbnails();
  }, [fileId, thumbnailConfig]);

  // Build srcset from thumbnail URLs
  const buildSrcSet = () => {
    const srcsetEntries: string[] = [];

    Object.entries(thumbnailUrls).forEach(([key, url]) => {
      if (key.includes('_webp')) {
        const sizeName = key.replace('_webp', '');
        const preset = thumbnailConfig.preset ? getPreset(thumbnailConfig.preset) : null;
        const sizeConfig = preset?.sizes[sizeName] || thumbnailConfig.customSizes?.[sizeName];

        if (sizeConfig) {
          srcsetEntries.push(`${url} ${sizeConfig.width}w`);
        }
      }
    });

    return srcsetEntries.join(', ');
  };

  // Generate sizes attribute for responsive behavior
  const buildSizes = () => {
    const preset = thumbnailConfig.preset ? getPreset(thumbnailConfig.preset) : null;
    if (!preset) return '100vw';

    const breakpoints: string[] = [];
    if (preset.sizes.mobile) {
      breakpoints.push(`(max-width: 640px) ${preset.sizes.mobile.width}px`);
    }
    if (preset.sizes.tablet) {
      breakpoints.push(`(max-width: 1024px) ${preset.sizes.tablet.width}px`);
    }
    if (preset.sizes.desktop) {
      breakpoints.push(`${preset.sizes.desktop.width}px`);
    }

    return breakpoints.length > 0 ? breakpoints.join(', ') : '100vw';
  };

  // Show loading state
  if (isLoading) {
    return (
      <div
        className={`${className} bg-gray-100 animate-pulse flex items-center justify-center`}
        style={{
          width: width || 'auto',
          height: height || 200,
          backgroundColor: placeholderData.dominantColor || '#f3f4f6'
        }}
      >
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className={`${className} bg-red-50 border border-red-200 p-4 text-red-600 text-sm`}>
        Failed to load image: {error}
      </div>
    );
  }

  // Get primary image URL (prefer WebP, fallback to JPEG)
  const primaryImageUrl = thumbnailUrls.desktop_webp || thumbnailUrls.desktop_jpeg || thumbnailUrls.desktop || Object.values(thumbnailUrls)[0];
  const srcSet = buildSrcSet();
  const sizes = buildSizes();

  return (
    <picture>
      {/* WebP sources with srcset */}
      {srcSet && (
        <source
          srcSet={srcSet}
          sizes={sizes}
          type="image/webp"
        />
      )}

      {/* Fallback image */}
      <img
        src={primaryImageUrl}
        srcSet={srcSet || undefined}
        sizes={sizes}
        alt={alt}
        width={width}
        height={height}
        className={className}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        style={{
          backgroundColor: placeholderData.dominantColor || 'transparent'
        }}
      />
    </picture>
  );
};

// ImageBlock Settings Component
interface ImageBlockSettingsProps {
  content: ImageBlockProps['content'];
  onChange?: (content: Record<string, any>) => void;
}

const ImageBlockSettings: React.FC<ImageBlockSettingsProps> = ({ content, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const availablePresets = getAllPresets();

  const handleThumbnailToggle = (enabled: boolean) => {
    onChange?.({
      ...content,
      useThumbnails: enabled,
      thumbnailConfig: enabled ? {
        preset: DEFAULT_PRESET,
        priority: false
      } : undefined
    });
  };

  const handlePresetChange = (presetName: string) => {
    const preset = getPreset(presetName);
    if (preset) {
      onChange?.({
        ...content,
        thumbnailConfig: {
          ...content.thumbnailConfig,
          preset: presetName,
          formats: preset.formats,
          placeholder: preset.placeholder,
          priority: preset.priority
        }
      });
    }
  };

  const handlePriorityChange = (priority: boolean) => {
    onChange?.({
      ...content,
      thumbnailConfig: {
        ...content.thumbnailConfig,
        priority
      }
    });
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="absolute top-2 right-2 p-2 bg-white rounded-md shadow-md hover:bg-gray-50 transition-colors"
        title="Image Settings"
      >
        <Settings className="w-4 h-4 text-gray-600" />
      </button>
    );
  }

  return (
    <Card className="absolute top-2 right-2 w-80 z-10 shadow-lg">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Image Settings</CardTitle>
          <button
            onClick={() => setIsOpen(false)}
            className="text-gray-400 hover:text-gray-600"
          >
            ×
          </button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Thumbnail Toggle */}
        <div className="flex items-center justify-between">
          <Label htmlFor="use-thumbnails" className="text-sm font-medium">
            Use Thumbnails
          </Label>
          <Switch
            id="use-thumbnails"
            checked={content.useThumbnails || false}
            onCheckedChange={handleThumbnailToggle}
          />
        </div>

        {content.useThumbnails && (
          <>
            <Separator />

            {/* Preset Selection */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Image Preset</Label>
              <Select
                value={content.thumbnailConfig?.preset || DEFAULT_PRESET}
                onValueChange={handlePresetChange}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select preset" />
                </SelectTrigger>
                <SelectContent>
                  {availablePresets.map((preset) => (
                    <SelectItem key={preset.name} value={preset.name.toLowerCase().replace(/\s+/g, '_')}>
                      <div className="flex flex-col">
                        <span className="font-medium">{preset.name}</span>
                        <span className="text-xs text-gray-500">{preset.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Priority Loading */}
            <div className="flex items-center justify-between">
              <Label htmlFor="priority-loading" className="text-sm font-medium">
                Priority Loading
              </Label>
              <Switch
                id="priority-loading"
                checked={content.thumbnailConfig?.priority || false}
                onCheckedChange={handlePriorityChange}
              />
            </div>

            {/* Current Preset Info */}
            {content.thumbnailConfig?.preset && (
              <div className="p-3 bg-gray-50 rounded-md">
                <div className="text-xs font-medium text-gray-700 mb-2">Current Configuration:</div>
                <div className="space-y-1">
                  {(() => {
                    const preset = getPreset(content.thumbnailConfig.preset);
                    if (!preset) return null;

                    return (
                      <>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(preset.sizes).map(([sizeName, sizeConfig]) => (
                            <Badge key={sizeName} variant="secondary" className="text-xs">
                              {sizeName}: {sizeConfig.width}px
                            </Badge>
                          ))}
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {preset.formats.map((format) => (
                            <Badge key={format} variant="outline" className="text-xs">
                              {format.toUpperCase()}
                            </Badge>
                          ))}
                        </div>
                      </>
                    );
                  })()}
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default ImageBlock;
