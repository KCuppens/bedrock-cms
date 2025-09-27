import { encode, decode } from 'blurhash';

/**
 * BlurHash utilities for generating ultra-small image placeholders
 *
 * BlurHash is a compact representation of a placeholder for an image.
 * Example: "LEHV6nWB2yk8pyo0adR*.7kCMdnj" (28 bytes) represents a full blurred image!
 */

interface BlurHashConfig {
  componentX?: number; // 1-9, horizontal complexity (default: 4)
  componentY?: number; // 1-9, vertical complexity (default: 3)
  punch?: number;      // 0-1, contrast (default: 1)
}

/**
 * Generate a BlurHash string from an image
 * This should typically be done server-side during image upload
 */
export const generateBlurHash = async (
  imageSrc: string,
  config: BlurHashConfig = {}
): Promise<string> => {
  const { componentX = 4, componentY = 3 } = config;

  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      if (!ctx) {
        reject(new Error('Could not get canvas context'));
        return;
      }

      // Use a small canvas for performance (BlurHash doesn't need high res)
      const width = 32;
      const height = 32;
      canvas.width = width;
      canvas.height = height;

      // Draw and get image data
      ctx.drawImage(img, 0, 0, width, height);
      const imageData = ctx.getImageData(0, 0, width, height);

      // Encode to BlurHash
      const blurhash = encode(
        imageData.data,
        width,
        height,
        componentX,
        componentY
      );

      resolve(blurhash);
    };

    img.onerror = () => reject(new Error(`Failed to load image: ${imageSrc}`));
    img.src = imageSrc;
  });
};

/**
 * Convert a BlurHash string to a base64 data URL
 */
export const blurHashToDataURL = (
  hash: string,
  width: number = 32,
  height: number = 32,
  punch: number = 1
): string => {
  const pixels = decode(hash, width, height, punch);
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  if (!ctx) {
    throw new Error('Could not get canvas context');
  }

  canvas.width = width;
  canvas.height = height;

  const imageData = ctx.createImageData(width, height);
  imageData.data.set(pixels);
  ctx.putImageData(imageData, 0, 0);

  return canvas.toDataURL();
};

/**
 * React hook for BlurHash placeholders
 */
export const useBlurHash = (
  hash: string | undefined,
  width: number = 32,
  height: number = 32,
  punch: number = 1
): string | null => {
  const [dataUrl, setDataUrl] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!hash) {
      setDataUrl(null);
      return;
    }

    try {
      const url = blurHashToDataURL(hash, width, height, punch);
      setDataUrl(url);
    } catch (error) {
      console.error('Failed to decode BlurHash:', error);
      setDataUrl(null);
    }
  }, [hash, width, height, punch]);

  return dataUrl;
};

/**
 * Common BlurHash patterns for different image types
 */
export const BlurHashPresets = {
  // Generic placeholders
  GRAY: 'L00000fQfQfQfQfQfQfQfQfQfQfQ',
  GRADIENT_BLUE: 'LGF5]+Yk^6#M@-5c,1J5@[or[Q6.',
  GRADIENT_PURPLE: 'L6PZfSjE.AyE_3t7t7R**0o#DgR4',

  // Common photo patterns
  PORTRAIT: 'LEHV6nWB2yk8pyo0adR*.7kCMdnj',
  LANDSCAPE: 'LKO2?U%2Tw=w]~RBVZRi};RPxuwH',
  SUNSET: 'LNFFX[D%M{s:_4WBofWB-;s:WBWB',

  // UI patterns
  DARK_MODE: 'L03IqLt700t7~qj[fQj[00j[D%ay',
  LIGHT_MODE: 'L$O|FfWBWBWB_4WBWBWBRjWBWBWB',
};

/**
 * Generate a dominant color placeholder from an image
 */
export const generateDominantColor = async (imageSrc: string): Promise<string> => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      if (!ctx) {
        reject(new Error('Could not get canvas context'));
        return;
      }

      // Sample a small area for performance
      canvas.width = 1;
      canvas.height = 1;
      ctx.drawImage(img, 0, 0, 1, 1);

      const pixel = ctx.getImageData(0, 0, 1, 1).data;
      const rgb = `rgb(${pixel[0]}, ${pixel[1]}, ${pixel[2]})`;

      resolve(rgb);
    };

    img.onerror = () => reject(new Error(`Failed to load image: ${imageSrc}`));
    img.src = imageSrc;
  });
};

/**
 * Generate an SVG placeholder with gradient
 */
export const generateSVGPlaceholder = (
  width: number,
  height: number,
  colors: string[] = ['#f0f0f0', '#e0e0e0']
): string => {
  const svg = `
    <svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
          ${colors.map((color, i) =>
            `<stop offset="${(i * 100) / (colors.length - 1)}%" stop-color="${color}"/>`
          ).join('')}
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#g)"/>
    </svg>
  `;

  const encoded = btoa(svg);
  return `data:image/svg+xml;base64,${encoded}`;
};

// TypeScript fix for React import
import * as React from 'react';
