/**
 * Image utility functions for responsive images and placeholders
 */

import { decode } from 'blurhash';

/**
 * Decode a BlurHash string to a data URL
 *
 * @param hash - BlurHash string
 * @param width - Canvas width (default: 32)
 * @param height - Canvas height (default: 32)
 * @returns Base64 data URL
 */
export function blurHashToDataURL(
  hash: string,
  width: number = 32,
  height: number = 32
): string {
  try {
    const pixels = decode(hash, width, height);

    // Create canvas and draw pixels
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('Failed to get canvas context');
    }

    const imageData = ctx.createImageData(width, height);
    imageData.data.set(pixels);
    ctx.putImageData(imageData, 0, 0);

    return canvas.toDataURL('image/png');
  } catch (error) {
    console.error('Failed to decode BlurHash:', error);
    return '';
  }
}

/**
 * Generate srcset string from thumbnail URLs
 *
 * @param thumbnails - Object with thumbnail URLs (e.g., {mobile_sm_webp: 'url', ...})
 * @param format - Image format to filter by ('webp', 'jpeg', 'avif')
 * @returns srcset string (e.g., "url1 640w, url2 1200w")
 */
export function generateSrcSet(
  thumbnails: Record<string, string>,
  format: 'webp' | 'jpeg' | 'avif' = 'webp'
): string {
  const formatSuffix = format === 'jpeg' ? ['_jpeg', '_jpg', ''] : [`_${format}`];
  const widthMap: Record<string, number> = {
    'micro': 20,
    'thumb': 150,
    'mobile_sm': 640,
    'mobile_md': 750,
    'tablet': 828,
    'tablet_lg': 1080,
    'desktop': 1200,
    'desktop_lg': 1920,
    'desktop_xl': 2560,
    'desktop_xxl': 3840,
  };

  const srcsetItems: Array<{ url: string; width: number }> = [];

  Object.entries(thumbnails).forEach(([key, url]) => {
    // Check if this thumbnail matches the format
    const matchesFormat = formatSuffix.some(suffix =>
      suffix === '' ? !key.includes('_webp') && !key.includes('_jpeg') && !key.includes('_avif') : key.endsWith(suffix)
    );

    if (!matchesFormat) return;

    // Extract base name (remove format suffix)
    let baseName = key;
    formatSuffix.forEach(suffix => {
      if (suffix && key.endsWith(suffix)) {
        baseName = key.replace(suffix, '');
      }
    });

    // Get width from mapping
    const width = widthMap[baseName];
    if (width) {
      srcsetItems.push({ url, width });
    }
  });

  // Sort by width and build srcset string
  return srcsetItems
    .sort((a, b) => a.width - b.width)
    .map(item => `${item.url} ${item.width}w`)
    .join(', ');
}

/**
 * Generate sizes attribute for responsive images
 *
 * @param breakpoints - Custom breakpoints (default: standard responsive)
 * @returns sizes attribute string
 */
export function generateSizesAttribute(
  breakpoints?: Array<{ maxWidth: number; size: string }>
): string {
  const defaultBreakpoints = [
    { maxWidth: 640, size: '100vw' },
    { maxWidth: 1024, size: '80vw' },
    { maxWidth: 1920, size: '1200px' },
  ];

  const points = breakpoints || defaultBreakpoints;

  const sizesArray = points.map(
    bp => `(max-width: ${bp.maxWidth}px) ${bp.size}`
  );

  // Add default size (largest breakpoint's size or fallback)
  const defaultSize = points[points.length - 1]?.size || '1200px';
  sizesArray.push(defaultSize);

  return sizesArray.join(', ');
}

/**
 * Get optimal thumbnail URL for a given viewport width
 *
 * @param thumbnails - Object with thumbnail URLs
 * @param viewportWidth - Current viewport width
 * @param format - Preferred image format
 * @returns Best matching thumbnail URL
 */
export function getOptimalThumbnail(
  thumbnails: Record<string, string>,
  viewportWidth: number,
  format: 'webp' | 'jpeg' | 'avif' = 'webp'
): string | undefined {
  const widthMap: Record<string, number> = {
    'mobile_sm': 640,
    'mobile_md': 750,
    'tablet': 828,
    'tablet_lg': 1080,
    'desktop': 1200,
    'desktop_lg': 1920,
    'desktop_xl': 2560,
    'desktop_xxl': 3840,
  };

  const formatSuffix = format === 'jpeg' ? '_jpeg' : `_${format}`;

  // Find thumbnails matching the format
  const candidates = Object.entries(thumbnails)
    .filter(([key]) => key.endsWith(formatSuffix))
    .map(([key, url]) => {
      const baseName = key.replace(formatSuffix, '');
      const width = widthMap[baseName] || 0;
      return { url, width };
    })
    .filter(item => item.width > 0)
    .sort((a, b) => a.width - b.width);

  // Find the smallest thumbnail that's >= viewport width
  const optimal = candidates.find(item => item.width >= viewportWidth);

  // Return optimal or largest available
  return optimal?.url || candidates[candidates.length - 1]?.url;
}

/**
 * Create a placeholder from dominant color
 *
 * @param color - Hex color (e.g., '#FF5733')
 * @param width - Canvas width
 * @param height - Canvas height
 * @returns Base64 data URL
 */
export function colorPlaceholderToDataURL(
  color: string,
  width: number = 32,
  height: number = 32
): string {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext('2d');
  if (!ctx) return '';

  ctx.fillStyle = color;
  ctx.fillRect(0, 0, width, height);

  return canvas.toDataURL('image/png');
}

/**
 * Check if WebP format is supported
 */
export function supportsWebP(): Promise<boolean> {
  return new Promise((resolve) => {
    const webP = new Image();
    webP.onload = webP.onerror = () => {
      resolve(webP.height === 2);
    };
    webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
  });
}

/**
 * Check if AVIF format is supported
 */
export function supportsAVIF(): Promise<boolean> {
  return new Promise((resolve) => {
    const avif = new Image();
    avif.onload = avif.onerror = () => {
      resolve(avif.height === 2);
    };
    avif.src = 'data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADybWV0YQAAAAAAAAAoaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAGxpYmF2aWYAAAAADnBpdG0AAAAAAAEAAAAeaWxvYwAAAABEAAABAAEAAAABAAABGgAAAB0AAAAoaWluZgAAAAAAAQAAABppbmZlAgAAAAABAABhdjAxQ29sb3IAAAAAamlwcnAAAABLaXBjbwAAABRpc3BlAAAAAAAAAAIAAAACAAAAEHBpeGkAAAAAAwgICAAAAAxhdjFDgQ0MAAAAABNjb2xybmNseAACAAIAAYAAAAAXaXBtYQAAAAAAAAABAAEEAQKDBAAAACVtZGF0EgAKCBgANogQEAwgMg8f8D///8WfhwB8+ErK42A=';
  });
}

/**
 * Get best supported image format
 */
export async function getBestFormat(): Promise<'avif' | 'webp' | 'jpeg'> {
  if (await supportsAVIF()) return 'avif';
  if (await supportsWebP()) return 'webp';
  return 'jpeg';
}

/**
 * Calculate aspect ratio from width and height
 */
export function calculateAspectRatio(width: number, height: number): number {
  return width / height;
}

/**
 * Get responsive image data from file object
 */
export interface ResponsiveImageData {
  id: string;
  originalUrl: string;
  width: number;
  height: number;
  aspectRatio: number;
  srcsets: {
    webp?: string;
    jpeg?: string;
    avif?: string;
  };
  sizes: string;
  thumbnails: Record<string, string>;
  placeholders: {
    blurhash?: string;
    base64?: string;
    dominantColor?: string;
  };
  alt: string;
}

/**
 * Build picture element sources from responsive data
 */
export function buildPictureSources(data: ResponsiveImageData): Array<{
  type: string;
  srcset: string;
  sizes: string;
}> {
  const sources: Array<{ type: string; srcset: string; sizes: string }> = [];

  // AVIF (best compression)
  if (data.srcsets.avif) {
    sources.push({
      type: 'image/avif',
      srcset: data.srcsets.avif,
      sizes: data.sizes,
    });
  }

  // WebP (good compression, wide support)
  if (data.srcsets.webp) {
    sources.push({
      type: 'image/webp',
      srcset: data.srcsets.webp,
      sizes: data.sizes,
    });
  }

  // JPEG (fallback)
  if (data.srcsets.jpeg) {
    sources.push({
      type: 'image/jpeg',
      srcset: data.srcsets.jpeg,
      sizes: data.sizes,
    });
  }

  return sources;
}

/**
 * Preload critical images
 */
export function preloadImage(url: string, options?: { as?: string; fetchpriority?: string }): void {
  const link = document.createElement('link');
  link.rel = 'preload';
  link.as = options?.as || 'image';
  link.href = url;

  if (options?.fetchpriority) {
    link.setAttribute('fetchpriority', options.fetchpriority);
  }

  document.head.appendChild(link);
}
