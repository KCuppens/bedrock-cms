import React, { useState } from 'react';
import { ProgressiveImage } from './ProgressiveImage';
import { VirtualizedGrid } from './VirtualizedList';
import { useBlurHash } from '@/utils/blurhash-utils';

/**
 * Demonstration of all progressive image loading techniques
 */

interface ImageData {
  id: string;
  url: string;
  thumbnailUrl?: string;
  placeholder?: {
    base64?: string;
    blurhash?: string;
    dominantColor?: string;
    lqip?: string;
  };
  width: number;
  height: number;
  alt: string;
  title?: string;
}

interface ImageGalleryProps {
  images: ImageData[];
  technique?: 'base64' | 'blurhash' | 'color' | 'lqip' | 'auto';
  columns?: number;
}

/**
 * Advanced Image Gallery with multiple placeholder strategies
 */
export const ImageGalleryWithPlaceholders: React.FC<ImageGalleryProps> = ({
  images,
  technique = 'auto',
  columns = 3
}) => {
  const [selectedImage, setSelectedImage] = useState<ImageData | null>(null);

  // Render a single image with the appropriate placeholder technique
  const renderImage = (image: ImageData, index: number, style: React.CSSProperties) => {
    // Choose placeholder based on technique
    let placeholder: string | undefined;

    switch (technique) {
      case 'base64':
        placeholder = image.placeholder?.base64;
        break;
      case 'blurhash':
        // Convert BlurHash to data URL on the fly
        if (image.placeholder?.blurhash) {
          placeholder = useBlurHashPlaceholder(image.placeholder.blurhash);
        }
        break;
      case 'color':
        // Use dominant color as a simple placeholder
        if (image.placeholder?.dominantColor) {
          placeholder = generateColorPlaceholder(
            image.placeholder.dominantColor,
            image.width,
            image.height
          );
        }
        break;
      case 'lqip':
        placeholder = image.placeholder?.lqip;
        break;
      case 'auto':
        // Use the best available placeholder
        placeholder = image.placeholder?.lqip ||
                     image.placeholder?.base64 ||
                     (image.placeholder?.blurhash ? useBlurHashPlaceholder(image.placeholder.blurhash) : undefined) ||
                     (image.placeholder?.dominantColor ? generateColorPlaceholder(image.placeholder.dominantColor, image.width, image.height) : undefined);
        break;
    }

    return (
      <div
        key={image.id}
        style={style}
        className="cursor-pointer transition-transform hover:scale-105"
        onClick={() => setSelectedImage(image)}
      >
        <ProgressiveImage
          src={image.url}
          placeholder={placeholder}
          alt={image.alt}
          width={image.width}
          height={image.height}
          className="rounded-lg shadow-md"
          objectFit="cover"
          fadeInDuration={400}
        />
        {image.title && (
          <p className="mt-2 text-sm text-gray-600 truncate">{image.title}</p>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Virtualized grid for performance */}
      <VirtualizedGrid
        items={images}
        columnCount={columns}
        height={600}
        rowHeight={250}
        renderItem={renderImage}
        gap={16}
        className="image-gallery"
      />

      {/* Lightbox for selected image */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-90"
          onClick={() => setSelectedImage(null)}
        >
          <div className="relative max-w-5xl max-h-screen p-4">
            <ProgressiveImage
              src={selectedImage.url}
              placeholder={selectedImage.placeholder?.lqip || selectedImage.placeholder?.base64}
              alt={selectedImage.alt}
              className="max-w-full max-h-full object-contain"
              priority
            />
            <button
              className="absolute top-4 right-4 text-white text-2xl"
              onClick={() => setSelectedImage(null)}
            >
              ×
            </button>
          </div>
        </div>
      )}
    </>
  );
};

/**
 * Hook to convert BlurHash to data URL
 */
function useBlurHashPlaceholder(hash: string): string | undefined {
  const [dataUrl, setDataUrl] = useState<string>();

  React.useEffect(() => {
    // Import blurhash utilities dynamically
    import('@/utils/blurhash-utils').then(({ blurHashToDataURL }) => {
      try {
        const url = blurHashToDataURL(hash, 32, 32);
        setDataUrl(url);
      } catch (error) {
        console.error('Failed to decode BlurHash:', error);
      }
    });
  }, [hash]);

  return dataUrl;
}

/**
 * Generate a simple color placeholder
 */
function generateColorPlaceholder(color: string, width: number, height: number): string {
  const svg = `
    <svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
      <rect width="100%" height="100%" fill="${color}"/>
    </svg>
  `;
  return `data:image/svg+xml;base64,${btoa(svg)}`;
}

/**
 * Example usage with different techniques
 */
export const ProgressiveImageExamples: React.FC = () => {
  const exampleImages: ImageData[] = [
    {
      id: '1',
      url: '/images/landscape-1.jpg',
      width: 1920,
      height: 1080,
      alt: 'Mountain landscape',
      title: 'Base64 Placeholder',
      placeholder: {
        base64: 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...', // Truncated for example
        dominantColor: '#3498db'
      }
    },
    {
      id: '2',
      url: '/images/portrait-1.jpg',
      width: 800,
      height: 1200,
      alt: 'Portrait photo',
      title: 'BlurHash Placeholder',
      placeholder: {
        blurhash: 'LEHV6nWB2yk8pyo0adR*.7kCMdnj',
        dominantColor: '#e74c3c'
      }
    },
    {
      id: '3',
      url: '/images/product-1.jpg',
      width: 1000,
      height: 1000,
      alt: 'Product photo',
      title: 'Color Placeholder',
      placeholder: {
        dominantColor: '#2ecc71'
      }
    }
  ];

  const [currentTechnique, setCurrentTechnique] = useState<'base64' | 'blurhash' | 'color' | 'auto'>('auto');

  return (
    <div className="space-y-8">
      <div className="flex gap-4">
        <button
          onClick={() => setCurrentTechnique('base64')}
          className={`px-4 py-2 rounded ${currentTechnique === 'base64' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          Base64
        </button>
        <button
          onClick={() => setCurrentTechnique('blurhash')}
          className={`px-4 py-2 rounded ${currentTechnique === 'blurhash' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          BlurHash
        </button>
        <button
          onClick={() => setCurrentTechnique('color')}
          className={`px-4 py-2 rounded ${currentTechnique === 'color' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          Dominant Color
        </button>
        <button
          onClick={() => setCurrentTechnique('auto')}
          className={`px-4 py-2 rounded ${currentTechnique === 'auto' ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
        >
          Auto (Best Available)
        </button>
      </div>

      <ImageGalleryWithPlaceholders
        images={exampleImages}
        technique={currentTechnique}
        columns={3}
      />

      <div className="bg-gray-100 p-4 rounded-lg">
        <h3 className="font-bold mb-2">Current Technique: {currentTechnique}</h3>
        <p className="text-sm text-gray-600">
          {currentTechnique === 'base64' && 'Using base64-encoded thumbnails (20x20px, ~500 bytes)'}
          {currentTechnique === 'blurhash' && 'Using BlurHash strings (20-30 characters, ~30 bytes)'}
          {currentTechnique === 'color' && 'Using dominant color placeholders (7 characters)'}
          {currentTechnique === 'auto' && 'Automatically selecting the best available placeholder'}
        </p>
      </div>
    </div>
  );
};
