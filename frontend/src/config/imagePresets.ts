/**
 * Image optimization presets for different use cases
 * These presets define thumbnail configurations for various block types
 */

export interface ThumbnailSize {
  width: number;
  height?: number;
  quality: number;
}

export interface ImagePreset {
  name: string;
  description: string;
  sizes: {
    mobile: ThumbnailSize;
    tablet?: ThumbnailSize;
    desktop: ThumbnailSize;
  };
  formats: ('webp' | 'jpeg' | 'avif')[];
  placeholder: 'blurhash' | 'dominant-color' | 'blur';
  priority: boolean;
  useCase: string[];
}

export const IMAGE_PRESETS: Record<string, ImagePreset> = {
  hero: {
    name: 'Hero Image',
    description: 'Large banner images for hero sections with high quality',
    sizes: {
      mobile: { width: 375, quality: 75 },
      tablet: { width: 768, quality: 80 },
      desktop: { width: 1920, quality: 85 }
    },
    formats: ['webp', 'jpeg'],
    placeholder: 'blurhash',
    priority: true,
    useCase: ['Hero sections', 'Full-width banners', 'Page headers']
  },

  content: {
    name: 'Content Image',
    description: 'Standard content images for articles and pages',
    sizes: {
      mobile: { width: 300, quality: 70 },
      tablet: { width: 500, quality: 75 },
      desktop: { width: 800, quality: 80 }
    },
    formats: ['webp', 'jpeg'],
    placeholder: 'blurhash',
    priority: false,
    useCase: ['Article images', 'Content blocks', 'Inline images']
  },

  gallery: {
    name: 'Gallery Item',
    description: 'Square or rectangular images for galleries and grids',
    sizes: {
      mobile: { width: 300, height: 300, quality: 70 },
      tablet: { width: 400, height: 400, quality: 75 },
      desktop: { width: 600, height: 600, quality: 80 }
    },
    formats: ['webp', 'jpeg'],
    placeholder: 'dominant-color',
    priority: false,
    useCase: ['Image galleries', 'Product grids', 'Portfolio items']
  },

  thumbnail: {
    name: 'Thumbnail',
    description: 'Small images for previews and listings',
    sizes: {
      mobile: { width: 150, height: 150, quality: 65 },
      desktop: { width: 200, height: 200, quality: 70 }
    },
    formats: ['webp', 'jpeg'],
    placeholder: 'dominant-color',
    priority: false,
    useCase: ['Card previews', 'List items', 'Navigation thumbnails']
  },

  avatar: {
    name: 'Avatar',
    description: 'Profile pictures and user avatars',
    sizes: {
      mobile: { width: 64, height: 64, quality: 75 },
      desktop: { width: 128, height: 128, quality: 80 }
    },
    formats: ['webp', 'jpeg'],
    placeholder: 'dominant-color',
    priority: false,
    useCase: ['User profiles', 'Author avatars', 'Team member photos']
  },

  icon: {
    name: 'Icon',
    description: 'Small icons and decorative images',
    sizes: {
      mobile: { width: 32, height: 32, quality: 85 },
      desktop: { width: 64, height: 64, quality: 85 }
    },
    formats: ['webp', 'jpeg'],
    placeholder: 'dominant-color',
    priority: false,
    useCase: ['Feature icons', 'Decorative elements', 'Small graphics']
  },

  blog_featured: {
    name: 'Blog Featured',
    description: 'Featured images for blog posts and articles',
    sizes: {
      mobile: { width: 375, quality: 75 },
      tablet: { width: 600, quality: 80 },
      desktop: { width: 1200, quality: 85 }
    },
    formats: ['webp', 'jpeg'],
    placeholder: 'blurhash',
    priority: false,
    useCase: ['Blog post headers', 'Article featured images', 'News thumbnails']
  },

  product: {
    name: 'Product Image',
    description: 'E-commerce product images with high quality',
    sizes: {
      mobile: { width: 300, height: 300, quality: 80 },
      tablet: { width: 500, height: 500, quality: 85 },
      desktop: { width: 800, height: 800, quality: 90 }
    },
    formats: ['webp', 'jpeg'],
    placeholder: 'dominant-color',
    priority: false,
    useCase: ['Product galleries', 'E-commerce listings', 'Catalog images']
  }
};

/**
 * Get preset configuration by name
 */
export const getPreset = (presetName: string): ImagePreset | null => {
  return IMAGE_PRESETS[presetName] || null;
};

/**
 * Get all available presets
 */
export const getAllPresets = (): ImagePreset[] => {
  return Object.values(IMAGE_PRESETS);
};

/**
 * Get presets suitable for a specific use case
 */
export const getPresetsForUseCase = (useCase: string): ImagePreset[] => {
  return getAllPresets().filter(preset =>
    preset.useCase.some(uc => uc.toLowerCase().includes(useCase.toLowerCase()))
  );
};

/**
 * Create a custom preset configuration
 */
export const createCustomPreset = (
  name: string,
  sizes: ImagePreset['sizes'],
  options: Partial<Omit<ImagePreset, 'name' | 'sizes'>> = {}
): ImagePreset => {
  return {
    name,
    description: options.description || 'Custom image configuration',
    sizes,
    formats: options.formats || ['webp', 'jpeg'],
    placeholder: options.placeholder || 'blurhash',
    priority: options.priority || false,
    useCase: options.useCase || ['Custom use case']
  };
};

/**
 * Convert preset to API format
 */
export const presetToApiFormat = (preset: ImagePreset) => {
  return {
    sizes: preset.sizes,
    formats: preset.formats,
    placeholder: preset.placeholder,
    priority: preset.priority
  };
};

/**
 * Get estimated file sizes for a preset (rough approximation)
 */
export const estimateFileSizes = (preset: ImagePreset, originalSize: number = 1000000): Record<string, number> => {
  const estimates: Record<string, number> = {};

  Object.entries(preset.sizes).forEach(([sizeName, sizeConfig]) => {
    const { width, quality } = sizeConfig;

    // Rough estimation based on dimensions and quality
    const pixelCount = width * (sizeConfig.height || width);
    const qualityFactor = quality / 100;
    const compressionFactor = preset.formats.includes('webp') ? 0.6 : 1; // WebP is ~40% smaller

    // Base estimation: ~3 bytes per pixel for JPEG, adjusted for quality and format
    const estimatedSize = Math.round(pixelCount * 3 * qualityFactor * compressionFactor);

    estimates[sizeName] = estimatedSize;
  });

  return estimates;
};

/**
 * Performance score calculation based on preset configuration
 */
export const calculatePerformanceScore = (preset: ImagePreset): {
  score: number;
  factors: Record<string, number>;
} => {
  const factors = {
    modernFormats: preset.formats.includes('webp') || preset.formats.includes('avif') ? 20 : 0,
    appropriateSizes: Object.keys(preset.sizes).length >= 2 ? 15 : 5,
    qualityOptimization: Math.max(0, 20 - (Math.max(...Object.values(preset.sizes).map(s => s.quality)) - 70)),
    placeholder: preset.placeholder === 'blurhash' ? 15 : 10,
    prioritization: preset.priority ? 10 : 5,
    responsiveBreakpoints: Object.keys(preset.sizes).length * 5
  };

  const score = Math.min(100, Object.values(factors).reduce((sum, val) => sum + val, 0));

  return { score, factors };
};

/**
 * Default preset for new image blocks
 */
export const DEFAULT_PRESET = 'content';

/**
 * Validate preset configuration
 */
export const validatePreset = (preset: Partial<ImagePreset>): { valid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (!preset.sizes || Object.keys(preset.sizes).length === 0) {
    errors.push('At least one size configuration is required');
  }

  if (preset.sizes) {
    Object.entries(preset.sizes).forEach(([sizeName, sizeConfig]) => {
      if (!sizeConfig.width || sizeConfig.width < 1 || sizeConfig.width > 3840) {
        errors.push(`Invalid width for ${sizeName}: must be between 1 and 3840`);
      }

      if (sizeConfig.height && (sizeConfig.height < 1 || sizeConfig.height > 3840)) {
        errors.push(`Invalid height for ${sizeName}: must be between 1 and 3840`);
      }

      if (!sizeConfig.quality || sizeConfig.quality < 1 || sizeConfig.quality > 100) {
        errors.push(`Invalid quality for ${sizeName}: must be between 1 and 100`);
      }
    });
  }

  if (preset.formats && preset.formats.length === 0) {
    errors.push('At least one format is required');
  }

  return {
    valid: errors.length === 0,
    errors
  };
};
