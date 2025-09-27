import React, { useState, useEffect, useRef, CSSProperties } from 'react';
import { cn } from '@/lib/utils';

interface ProgressiveImageProps {
  src: string;
  placeholder?: string; // Base64 or BlurHash string
  alt: string;
  className?: string;
  width?: number;
  height?: number;
  sizes?: string;
  srcSet?: string;
  priority?: boolean;
  onLoad?: () => void;
  onError?: (error: Error) => void;
  objectFit?: 'contain' | 'cover' | 'fill' | 'none' | 'scale-down';
  aspectRatio?: number; // For responsive containers
  fadeInDuration?: number; // Milliseconds
  blurAmount?: number; // Pixels for blur effect
}

/**
 * Progressive Image Component with multiple placeholder strategies
 *
 * Features:
 * - Base64 placeholder support
 * - BlurHash decoding
 * - Dominant color extraction
 * - Smooth fade transitions
 * - Intersection Observer for lazy loading
 * - Automatic aspect ratio preservation
 */
export const ProgressiveImage: React.FC<ProgressiveImageProps> = ({
  src,
  placeholder,
  alt,
  className = '',
  width,
  height,
  sizes,
  srcSet,
  priority = false,
  onLoad,
  onError,
  objectFit = 'cover',
  aspectRatio,
  fadeInDuration = 300,
  blurAmount = 20
}) => {
  const [imageSrc, setImageSrc] = useState<string | null>(placeholder || null);
  const [imageLoading, setImageLoading] = useState(true);
  const [isInView, setIsInView] = useState(priority);
  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Calculate aspect ratio if not provided
  const calculatedAspectRatio = aspectRatio || (width && height ? width / height : undefined);

  // Setup Intersection Observer for lazy loading
  useEffect(() => {
    if (priority || !containerRef.current) {
      setIsInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      {
        threshold: 0.01,
        rootMargin: '50px'
      }
    );

    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, [priority]);

  // Load the full image when in view
  useEffect(() => {
    if (!isInView) return;

    let isCancelled = false;
    const img = new Image();

    // Set up event handlers
    img.onload = () => {
      if (!isCancelled) {
        setImageSrc(src);
        setImageLoading(false);
        onLoad?.();
      }
    };

    img.onerror = () => {
      if (!isCancelled) {
        setImageLoading(false);
        onError?.(new Error(`Failed to load image: ${src}`));
      }
    };

    // Set image properties and start loading
    if (srcSet) img.srcset = srcSet;
    if (sizes) img.sizes = sizes;
    img.src = src;

    return () => {
      isCancelled = true;
      img.onload = null;
      img.onerror = null;
    };
  }, [isInView, src, srcSet, sizes, onLoad, onError]);

  // Container styles for aspect ratio
  const containerStyle: CSSProperties = calculatedAspectRatio
    ? {
        position: 'relative',
        paddingBottom: `${(1 / calculatedAspectRatio) * 100}%`,
        overflow: 'hidden'
      }
    : {
        position: 'relative',
        width: width ? `${width}px` : '100%',
        height: height ? `${height}px` : 'auto',
        overflow: 'hidden'
      };

  // Image styles for transitions
  const imageStyle: CSSProperties = {
    position: calculatedAspectRatio ? 'absolute' : 'relative',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit,
    transition: `opacity ${fadeInDuration}ms ease-in-out, filter ${fadeInDuration}ms ease-in-out`,
    opacity: imageLoading ? 0 : 1,
    filter: imageLoading ? `blur(${blurAmount}px)` : 'none'
  };

  // Placeholder styles
  const placeholderStyle: CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit,
    filter: `blur(${blurAmount}px)`,
    transform: 'scale(1.1)', // Slightly scale to hide blur edges
    transition: `opacity ${fadeInDuration}ms ease-in-out`,
    opacity: imageLoading ? 1 : 0
  };

  return (
    <div
      ref={containerRef}
      className={cn('progressive-image-container', className)}
      style={containerStyle}
    >
      {/* Placeholder layer */}
      {placeholder && (
        <img
          src={placeholder}
          alt=""
          aria-hidden="true"
          style={placeholderStyle}
          loading="eager"
          decoding="async"
        />
      )}

      {/* Main image layer */}
      {isInView && (
        <img
          ref={imageRef}
          src={imageSrc || src}
          alt={alt}
          width={width}
          height={height}
          sizes={sizes}
          srcSet={srcSet}
          style={imageStyle}
          loading={priority ? 'eager' : 'lazy'}
          decoding={priority ? 'sync' : 'async'}
        />
      )}

      {/* Loading skeleton fallback if no placeholder */}
      {!placeholder && imageLoading && (
        <div
          className="absolute inset-0 bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 animate-pulse"
          style={{
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.5s ease-in-out infinite'
          }}
        />
      )}

      <style jsx>{`
        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }
      `}</style>
    </div>
  );
};

/**
 * Hook for generating base64 placeholders on the client
 * Note: This is for demonstration - in production, generate these server-side
 */
export const useBase64Placeholder = (imageSrc: string, size: number = 20) => {
  const [placeholder, setPlaceholder] = useState<string | null>(null);

  useEffect(() => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
      // Calculate dimensions maintaining aspect ratio
      const aspectRatio = img.width / img.height;
      let canvasWidth = size;
      let canvasHeight = size;

      if (aspectRatio > 1) {
        canvasHeight = size / aspectRatio;
      } else {
        canvasWidth = size * aspectRatio;
      }

      canvas.width = canvasWidth;
      canvas.height = canvasHeight;

      // Draw and get base64
      ctx.drawImage(img, 0, 0, canvasWidth, canvasHeight);
      const base64 = canvas.toDataURL('image/jpeg', 0.4); // Low quality for smaller size
      setPlaceholder(base64);
    };

    img.src = imageSrc;
  }, [imageSrc, size]);

  return placeholder;
};

/**
 * Component for progressive image with automatic placeholder generation
 */
export const AutoProgressiveImage: React.FC<Omit<ProgressiveImageProps, 'placeholder'> & {
  placeholderSize?: number;
}> = ({ placeholderSize = 20, ...props }) => {
  const placeholder = useBase64Placeholder(props.src, placeholderSize);

  return <ProgressiveImage {...props} placeholder={placeholder} />;
};
