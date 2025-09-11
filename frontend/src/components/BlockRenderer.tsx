import React, { lazy, Suspense, useMemo } from 'react';
import { ErrorBoundary } from 'react-error-boundary';

// Block component interfaces for type safety
export interface BlockProps {
  id?: string;
  type: string;
  props: Record<string, any>;
  index?: number;
  isEditable?: boolean;
}

interface BlockComponentProps extends BlockProps {
  className?: string;
  style?: React.CSSProperties;
}

// Fallback component for unknown block types
const UnknownBlock: React.FC<BlockProps> = ({ type, props }) => {
  if (process.env.NODE_ENV === 'development') {
    return (
      <div className="border-2 border-dashed border-orange-300 bg-orange-50 p-4 rounded-lg">
        <p className="text-orange-800 font-medium">Unknown Block: {type}</p>
        <pre className="text-xs text-orange-600 mt-2 overflow-auto">
          {JSON.stringify(props, null, 2)}
        </pre>
      </div>
    );
  }
  
  // In production, render nothing for unknown blocks
  return null;
};

// Loading fallback for lazy-loaded block components
const BlockLoadingFallback: React.FC<{ type: string }> = ({ type }) => (
  <div className="animate-pulse bg-gray-100 rounded-lg p-4 min-h-[100px] flex items-center justify-center">
    <span className="text-gray-500 text-sm">Loading {type} block...</span>
  </div>
);

// Error fallback for block components
const BlockErrorFallback: React.FC<{ error: Error; type: string; resetError: () => void }> = ({ 
  error, 
  type, 
  resetError 
}) => {
  if (process.env.NODE_ENV === 'development') {
    return (
      <div className="border-2 border-red-300 bg-red-50 p-4 rounded-lg">
        <p className="text-red-800 font-medium">Error in {type} block:</p>
        <p className="text-red-600 text-sm mt-1">{error.message}</p>
        <button 
          onClick={resetError}
          className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }
  
  // In production, render nothing for errored blocks
  return null;
};

// Dynamic block component registry with lazy loading
const getBlockComponent = (blockType: string) => {
  // Normalize block type to component name (e.g., 'hero' -> 'HeroBlock')
  const componentName = blockType
    .split('_')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join('') + 'Block';

  try {
    // Dynamic import with error handling
    return lazy(async () => {
      try {
        // Try to import from blocks directory
        const module = await import(`@/components/blocks/${componentName}`);
        return { default: module.default || module[componentName] };
      } catch (importError) {
        console.warn(`Block component ${componentName} not found, falling back to UnknownBlock`);
        return { default: UnknownBlock };
      }
    });
  } catch (error) {
    console.warn(`Failed to create lazy component for ${blockType}:`, error);
    return () => <UnknownBlock type={blockType} props={{}} />;
  }
};

// Individual block wrapper with error boundary
const BlockWrapper: React.FC<BlockProps & { className?: string }> = ({ 
  type, 
  props, 
  index, 
  isEditable = false,
  className = ''
}) => {
  const BlockComponent = useMemo(() => getBlockComponent(type), [type]);
  
  return (
    <ErrorBoundary
      fallbackRender={({ error, resetErrorBoundary }) => (
        <BlockErrorFallback 
          error={error} 
          type={type} 
          resetError={resetErrorBoundary} 
        />
      )}
      resetKeys={[type, props]} // Reset error boundary when props change
    >
      <Suspense fallback={<BlockLoadingFallback type={type} />}>
        <div className={`block-${type} ${className}`.trim()} data-block-type={type} data-block-index={index}>
          <BlockComponent
            type={type}
            props={props}
            index={index}
            isEditable={isEditable}
          />
        </div>
      </Suspense>
    </ErrorBoundary>
  );
};

// Main block renderer props
interface BlockRendererProps {
  blocks: BlockProps[];
  className?: string;
  isEditable?: boolean;
  onBlockError?: (error: Error, blockType: string, blockIndex: number) => void;
  maxConcurrentLoads?: number; // Limit concurrent lazy loads for performance
}

/**
 * High-performance block renderer component.
 * 
 * Features:
 * - Lazy loading of block components
 * - Error boundaries for individual blocks
 * - Performance optimizations with memoization
 * - Development vs production behavior
 * - Accessible markup with proper semantics
 */
export const BlockRenderer: React.FC<BlockRendererProps> = ({
  blocks = [],
  className = '',
  isEditable = false,
  onBlockError,
  maxConcurrentLoads = 3
}) => {
  // Memoize processed blocks to avoid unnecessary re-renders
  const processedBlocks = useMemo(() => {
    return blocks
      .filter(block => block && block.type) // Filter out invalid blocks
      .map((block, index) => ({
        ...block,
        id: block.id || `block-${index}`,
        index
      }));
  }, [blocks]);

  // Render nothing if no valid blocks
  if (!processedBlocks.length) {
    return null;
  }

  return (
    <div 
      className={`block-renderer ${className}`.trim()}
      role="main"
      aria-label="Page content"
    >
      {processedBlocks.map((block) => (
        <BlockWrapper
          key={block.id}
          type={block.type}
          props={block.props || {}}
          index={block.index}
          isEditable={isEditable}
          className="block-wrapper"
        />
      ))}
    </div>
  );
};

// Hook for prefetching block components
export const usePrefetchBlocks = () => {
  const prefetchedTypes = useMemo(() => new Set<string>(), []);

  return React.useCallback((blockTypes: string[]) => {
    blockTypes.forEach(type => {
      if (!prefetchedTypes.has(type)) {
        prefetchedTypes.add(type);
        // Prefetch block component
        getBlockComponent(type);
      }
    });
  }, [prefetchedTypes]);
};

// Export utility functions
export { getBlockComponent, UnknownBlock };

export default BlockRenderer;