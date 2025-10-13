/**
 * TypeScript types for responsive images and image optimization
 */

export interface ImagePlaceholders {
  blurhash?: string;
  base64?: string;
  dominantColor?: string;
}

export interface ImageSrcsets {
  webp?: string;
  jpeg?: string;
  avif?: string;
}

export interface ImageThumbnails {
  [key: string]: string;
}

export interface ResponsiveImageData {
  id: string;
  originalUrl: string;
  width: number;
  height: number;
  aspectRatio: number;
  srcsets: ImageSrcsets;
  sizes: string;
  thumbnails: ImageThumbnails;
  placeholders: ImagePlaceholders;
  alt: string;
}

export interface FileUploadImage {
  id: string;
  original_filename: string;
  file_type: string;
  mime_type: string;
  width?: number;
  height?: number;
  blurhash?: string;
  dominant_color?: string;
  base64_micro?: string;
  thumbnails?: {
    config_hashes?: {
      [hash: string]: ImageThumbnails;
    };
  };
  download_url?: string;
  description?: string;
}

export interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  sizes?: string;
  priority?: boolean;
  className?: string;
  style?: React.CSSProperties;
  objectFit?: 'contain' | 'cover' | 'fill' | 'none' | 'scale-down';
  onLoad?: () => void;
  onError?: () => void;
  placeholder?: 'blur' | 'empty';
  blurDataURL?: string;
}

export interface ResponsiveImageProps {
  fileId?: string;
  file?: FileUploadImage;
  src?: string;
  alt: string;
  width?: number;
  height?: number;
  className?: string;
  priority?: boolean;
  objectFit?: 'contain' | 'cover' | 'fill' | 'none' | 'scale-down';
  onLoad?: () => void;
  onError?: (error: Error) => void;
  sizes?: string;
  loading?: 'lazy' | 'eager';
}

export interface UseResponsiveImageOptions {
  fileId?: string;
  file?: FileUploadImage;
  enabled?: boolean;
}

export interface UseResponsiveImageResult {
  data: ResponsiveImageData | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}
