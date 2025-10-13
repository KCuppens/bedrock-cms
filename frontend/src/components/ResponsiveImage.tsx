/**
 * ResponsiveImage component with automatic optimization and lazy loading
 *
 * Features:
 * - Automatic srcset/sizes generation from API or file object
 * - Multiple format support (AVIF, WebP, JPEG)
 * - BlurHash/Base64 placeholders for smooth loading
 * - Native lazy loading with Intersection Observer fallback
 * - Aspect ratio preservation for layout stability
 */

import React, { useState, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { useResponsiveImage, usePlaceholder } from '@/hooks/useResponsiveImage';
import type { ResponsiveImageProps, FileUploadImage } from '@/types/image';
import { buildPictureSources } from '@/utils/image-utils';

export const ResponsiveImage: React.FC<ResponsiveImageProps> = ({
  fileId,
  file,
  src,
  alt,
  width,
  height,
  className,
  priority = false,
  objectFit = 'cover',
  onLoad,
  onError,
  sizes,
  loading = 'lazy',
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(priority);
  const [hasError, setHasError] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  // Fetch responsive data if fileId or file is provided
  const { data: responsiveData, isLoading, error } = useResponsiveImage({
    fileId,
    file,
    enabled: !!(fileId || file),
  });

  // Get placeholder
  const placeholder = usePlaceholder(file);

  // Calculate aspect ratio
  const aspectRatio =
    responsiveData?.aspectRatio ||
    (width && height ? width / height : undefined) ||
    (file?.width && file?.height ? file.width / file.height : undefined);

  // Setup Intersection Observer for lazy loading
  useEffect(() => {
    if (priority || loading === 'eager') {
      setIsInView(true);
      return;
    }

    if (!containerRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInView(true);
            observer.disconnect();
          }
        });
      },
      {
        rootMargin: '50px',
        threshold: 0.01,
      }
    );

    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, [priority, loading]);

  const handleLoad = () => {
    setIsLoaded(true);
    onLoad?.();
  };

  const handleError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    setHasError(true);
    onError?.(new Error('Failed to load image'));
  };

  // Determine image source
  const imageSrc = src || responsiveData?.originalUrl || file?.download_url;

  // Build picture sources if we have responsive data
  const pictureSources = responsiveData ? buildPictureSources(responsiveData) : [];

  // Determine srcset and sizes
  const imgSrcset = responsiveData?.srcsets?.jpeg || responsiveData?.srcsets?.webp;
  const imgSizes = sizes || responsiveData?.sizes || '100vw';

  // Container styles for aspect ratio
  const containerStyle: React.CSSProperties = aspectRatio
    ? {
        position: 'relative',
        paddingBottom: `${(1 / aspectRatio) * 100}%`,
        overflow: 'hidden',
      }
    : {
        position: 'relative',
        overflow: 'hidden',
      };

  // Image styles
  const imageStyle: React.CSSProperties = {
    position: aspectRatio ? 'absolute' : 'relative',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit,
    transition: 'opacity 300ms ease-in-out',
    opacity: isLoaded ? 1 : 0,
  };

  // Placeholder styles
  const placeholderStyle: React.CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit,
    filter: 'blur(20px)',
    transform: 'scale(1.1)',
    transition: 'opacity 300ms ease-in-out',
    opacity: isLoaded ? 0 : 1,
  };

  if (isLoading) {
    return (
      <div ref={containerRef} className={cn('relative', className)} style={containerStyle}>
        <div className="absolute inset-0 bg-gray-200 animate-pulse" />
      </div>
    );
  }

  if (error || hasError || !imageSrc) {
    return (
      <div ref={containerRef} className={cn('relative', className)} style={containerStyle}>
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
          <svg
            className="w-12 h-12 text-gray-400"
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
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className={cn('relative', className)} style={containerStyle}>
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

      {/* Main image with picture element for format selection */}
      {isInView && (
        <picture>
          {/* Modern formats */}
          {pictureSources.map((source, index) => (
            <source
              key={index}
              type={source.type}
              srcSet={source.srcset}
              sizes={source.sizes}
            />
          ))}

          {/* Fallback img element */}
          <img
            ref={imgRef}
            src={imageSrc}
            alt={alt || responsiveData?.alt || ''}
            width={width || responsiveData?.width}
            height={height || responsiveData?.height}
            srcSet={imgSrcset}
            sizes={imgSizes}
            loading={priority || loading === 'eager' ? 'eager' : 'lazy'}
            decoding={priority ? 'sync' : 'async'}
            onLoad={handleLoad}
            onError={handleError}
            style={imageStyle}
            // @ts-ignore - fetchpriority not in React types yet
            fetchpriority={priority ? 'high' : 'auto'}
          />
        </picture>
      )}
    </div>
  );
};

/**
 * Simple responsive image for when you just have a URL
 */
export const SimpleResponsiveImage: React.FC<{
  src: string;
  alt: string;
  width?: number;
  height?: number;
  className?: string;
  priority?: boolean;
  objectFit?: 'contain' | 'cover' | 'fill' | 'none' | 'scale-down';
}> = ({ src, alt, width, height, className, priority = false, objectFit = 'cover' }) => {
  return (
    <ResponsiveImage
      src={src}
      alt={alt}
      width={width}
      height={height}
      className={className}
      priority={priority}
      objectFit={objectFit}
    />
  );
};
