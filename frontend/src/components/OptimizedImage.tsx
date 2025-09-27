import React, { useState, useEffect, useRef, CSSProperties } from 'react';
import { cn } from '@/lib/utils';

interface OptimizedImageProps {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  sizes?: string;
  priority?: boolean;
  className?: string;
  style?: CSSProperties;
  objectFit?: 'contain' | 'cover' | 'fill' | 'none' | 'scale-down';
  onLoad?: () => void;
  onError?: () => void;
  placeholder?: 'blur' | 'empty';
  blurDataURL?: string;
}

/**
 * Optimized image component with lazy loading, modern formats, and responsive images
 */
export const OptimizedImage: React.FC<OptimizedImageProps> = ({
  src,
  alt,
  width,
  height,
  sizes = '100vw',
  priority = false,
  className,
  style,
  objectFit = 'cover',
  onLoad,
  onError,
  placeholder = 'blur',
  blurDataURL,
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(priority);
  const [error, setError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Generate optimized URLs for different formats
  const getOptimizedUrl = (url: string, params: Record<string, any> = {}) => {
    // If it's already a full URL with query params, return as is
    if (url.includes('?')) return url;

    // For local images, append query params for the image optimization service
    const searchParams = new URLSearchParams(params as any);
    return `${url}?${searchParams.toString()}`;
  };

  // Generate srcSet for responsive images
  const generateSrcSet = (baseUrl: string, format?: string) => {
    const widths = [640, 750, 828, 1080, 1200, 1920, 2048, 3840];
    return widths
      .map(w => {
        const url = getOptimizedUrl(baseUrl, { w, ...(format && { fm: format }) });
        return `${url} ${w}w`;
      })
      .join(', ');
  };

  // Check WebP and AVIF support
  const supportsWebP = typeof window !== 'undefined' && window.WebPSupport !== false;
  const supportsAvif = typeof window !== 'undefined' && window.AvifSupport !== false;

  // Set up Intersection Observer for lazy loading
  useEffect(() => {
    if (priority || isInView) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInView(true);
          }
        });
      },
      {
        rootMargin: '50px', // Start loading 50px before entering viewport
        threshold: 0.01,
      }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => {
      if (containerRef.current) {
        observer.unobserve(containerRef.current);
      }
    };
  }, [priority, isInView]);

  const handleLoad = () => {
    setIsLoaded(true);
    onLoad?.();
  };

  const handleError = () => {
    setError(true);
    onError?.();
  };

  // Base64 placeholder for blur effect
  const defaultBlurDataURL = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"%3E%3Crect width="1" height="1" fill="%23f3f4f6"/%3E%3C/svg%3E';

  const aspectRatio = width && height ? width / height : undefined;

  return (
    <div
      ref={containerRef}
      className={cn('relative overflow-hidden', className)}
      style={{
        ...style,
        ...(aspectRatio && {
          aspectRatio: `${width} / ${height}`,
        }),
      }}
    >
      {/* Placeholder while loading */}
      {placeholder === 'blur' && !isLoaded && (
        <div
          className="absolute inset-0 z-0"
          style={{
            backgroundImage: `url(${blurDataURL || defaultBlurDataURL})`,
            backgroundSize: 'cover',
            filter: 'blur(20px)',
            transform: 'scale(1.1)',
          }}
        />
      )}

      {/* Error state */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
          <div className="text-center">
            <svg
              className="w-12 h-12 mx-auto text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <p className="mt-2 text-sm text-gray-500">Failed to load image</p>
          </div>
        </div>
      )}

      {/* Main image with picture element for modern formats */}
      {isInView && !error && (
        <picture>
          {/* AVIF format (best compression) */}
          {supportsAvif && (
            <source
              type="image/avif"
              srcSet={generateSrcSet(src, 'avif')}
              sizes={sizes}
            />
          )}

          {/* WebP format (good compression) */}
          {supportsWebP && (
            <source
              type="image/webp"
              srcSet={generateSrcSet(src, 'webp')}
              sizes={sizes}
            />
          )}

          {/* Original format fallback */}
          <img
            ref={imgRef}
            src={src}
            alt={alt}
            width={width}
            height={height}
            srcSet={generateSrcSet(src)}
            sizes={sizes}
            loading={priority ? 'eager' : 'lazy'}
            decoding={priority ? 'sync' : 'async'}
            onLoad={handleLoad}
            onError={handleError}
            className={cn(
              'transition-opacity duration-300',
              isLoaded ? 'opacity-100' : 'opacity-0',
              className
            )}
            style={{
              objectFit,
              ...style,
            }}
            // @ts-ignore - fetchpriority is not in React types yet
            fetchpriority={priority ? 'high' : 'auto'}
          />
        </picture>
      )}
    </div>
  );
};

/**
 * Background image component with optimization
 */
export const OptimizedBackgroundImage: React.FC<{
  src: string;
  className?: string;
  children?: React.ReactNode;
  overlay?: boolean;
  overlayOpacity?: number;
}> = ({ src, className, children, overlay = false, overlayOpacity = 0.5 }) => {
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const img = new Image();
    img.src = src;
    img.onload = () => setIsLoaded(true);
  }, [src]);

  return (
    <div
      className={cn('relative', className)}
      style={{
        backgroundImage: isLoaded ? `url(${src})` : undefined,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      {overlay && (
        <div
          className="absolute inset-0 bg-black"
          style={{ opacity: overlayOpacity }}
        />
      )}
      {children}
    </div>
  );
};

// Check for modern image format support
if (typeof window !== 'undefined') {
  // Check WebP support
  const webP = new Image();
  webP.onload = webP.onerror = () => {
    (window as any).WebPSupport = webP.height === 2;
  };
  webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';

  // Check AVIF support
  const avif = new Image();
  avif.onload = avif.onerror = () => {
    (window as any).AvifSupport = avif.height === 2;
  };
  avif.src = 'data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADybWV0YQAAAAAAAAAoaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAGxpYmF2aWYAAAAADnBpdG0AAAAAAAEAAAAeaWxvYwAAAABEAAABAAEAAAABAAABGgAAAB0AAAAoaWluZgAAAAAAAQAAABppbmZlAgAAAAABAABhdjAxQ29sb3IAAAAAamlwcnAAAABLaXBjbwAAABRpc3BlAAAAAAAAAAIAAAACAAAAEHBpeGkAAAAAAwgICAAAAAxhdjFDgQ0MAAAAABNjb2xybmNseAACAAIAAYAAAAAXaXBtYQAAAAAAAAABAAEEAQKDBAAAACVtZGF0EgAKCBgANogQEAwgMg8f8D///8WfhwB8+ErK42A=';
}
