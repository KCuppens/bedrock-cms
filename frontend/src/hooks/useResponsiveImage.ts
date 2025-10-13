/**
 * Hook for fetching and managing responsive image data
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import type {
  ResponsiveImageData,
  FileUploadImage,
  UseResponsiveImageOptions,
  UseResponsiveImageResult,
} from '@/types/image';
import { generateSrcSet } from '@/utils/image-utils';

/**
 * Hook to fetch responsive image data from the API
 *
 * @param options - Options including fileId or file object
 * @returns Responsive image data, loading state, and error
 */
export function useResponsiveImage(
  options: UseResponsiveImageOptions
): UseResponsiveImageResult {
  const { fileId, file, enabled = true } = options;

  const [data, setData] = useState<ResponsiveImageData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchResponsiveData = useCallback(async () => {
    if (!enabled) return;

    // If we have file object with thumbnails, build data from it
    if (file && file.thumbnails?.config_hashes) {
      try {
        // Collect all thumbnails from all configurations
        const allThumbnails: Record<string, string> = {};
        Object.values(file.thumbnails.config_hashes).forEach(configThumbs => {
          Object.assign(allThumbnails, configThumbs);
        });

        // Build srcsets
        const srcsets = {
          webp: generateSrcSet(allThumbnails, 'webp'),
          jpeg: generateSrcSet(allThumbnails, 'jpeg'),
          avif: generateSrcSet(allThumbnails, 'avif'),
        };

        // Build responsive data from file object
        const responsiveData: ResponsiveImageData = {
          id: file.id,
          originalUrl: file.download_url || '',
          width: file.width || 0,
          height: file.height || 0,
          aspectRatio: file.width && file.height ? file.width / file.height : 1,
          srcsets,
          sizes: '(max-width: 640px) 100vw, (max-width: 1024px) 80vw, 1200px',
          thumbnails: allThumbnails,
          placeholders: {
            blurhash: file.blurhash,
            base64: file.base64_micro,
            dominantColor: file.dominant_color,
          },
          alt: file.description || file.original_filename,
        };

        setData(responsiveData);
        setError(null);
        return;
      } catch (err) {
        console.error('Error building responsive data from file object:', err);
      }
    }

    // Otherwise fetch from API
    const id = fileId || file?.id;
    if (!id) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/files/${id}/responsive/`);
      setData(response.data as ResponsiveImageData);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch responsive image data');
      setError(error);
      console.error('Error fetching responsive image data:', error);
    } finally {
      setIsLoading(false);
    }
  }, [fileId, file, enabled]);

  useEffect(() => {
    fetchResponsiveData();
  }, [fetchResponsiveData]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchResponsiveData,
  };
}

/**
 * Hook to get placeholder data URL from file
 *
 * @param file - File upload object
 * @returns Placeholder data URL (blurhash > base64 > color)
 */
export function usePlaceholder(file?: FileUploadImage | null): string {
  const [placeholder, setPlaceholder] = useState<string>('');

  useEffect(() => {
    if (!file) {
      setPlaceholder('');
      return;
    }

    // Priority: base64_micro > blurhash > dominant_color
    if (file.base64_micro) {
      setPlaceholder(file.base64_micro);
      return;
    }

    if (file.blurhash) {
      // Decode blurhash on demand
      import('@/utils/image-utils').then(({ blurHashToDataURL }) => {
        try {
          const dataUrl = blurHashToDataURL(file.blurhash!);
          if (dataUrl) {
            setPlaceholder(dataUrl);
          }
        } catch (error) {
          console.error('Failed to decode blurhash:', error);
        }
      });
      return;
    }

    if (file.dominant_color) {
      import('@/utils/image-utils').then(({ colorPlaceholderToDataURL }) => {
        const dataUrl = colorPlaceholderToDataURL(file.dominant_color!);
        if (dataUrl) {
          setPlaceholder(dataUrl);
        }
      });
      return;
    }

    setPlaceholder('');
  }, [file]);

  return placeholder;
}
