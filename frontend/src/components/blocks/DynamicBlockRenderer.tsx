import React, { Suspense, useMemo } from 'react';
import { BlockRegistry } from './BlockRegistry';
import { ErrorBoundary } from './ui/ErrorBoundary';
import { BlockSkeleton } from './ui/BlockSkeleton';
import type { BlockComponentProps, BlockData } from './types';

interface DynamicBlockRendererProps extends Omit<BlockComponentProps, 'content'> {
  block: BlockData;
}

const DynamicComponent: React.FC<{ componentName: string; props: BlockComponentProps }> = ({
  componentName,
  props
}) => {
  const Component = useMemo(() => {
    const registry = BlockRegistry.getInstance();
    return React.lazy(() =>
      registry.getComponent(componentName).then(comp => {
        if (!comp) {
          throw new Error(`Block component ${componentName} not found`);
        }
        return { default: comp };
      })
    );
  }, [componentName]);

  return (
    <Suspense fallback={<BlockSkeleton />}>
      <Component {...props} />
    </Suspense>
  );
};

const ErrorFallback: React.FC<{ blockType: string; componentName?: string }> = ({ blockType, componentName }) => {
  const registry = BlockRegistry.getInstance();
  const availableComponents = registry.getAllComponentNames();

  return (
    <div className="p-4 border border-red-200 rounded-lg bg-red-50">
      <div className="text-red-700 font-medium">Block Component Not Found</div>
      <div className="text-red-600 text-sm mt-1">
        The block component '{componentName || blockType}' is not installed or registered.
      </div>
      {availableComponents.length > 0 && (
        <div className="mt-2 text-xs text-red-500">
          <div className="font-medium">Available components:</div>
          <div className="mt-1">{availableComponents.join(', ')}</div>
        </div>
      )}
      <div className="mt-2 text-xs text-gray-600">
        To fix this, ensure the component exists in /components/blocks/blocks/{componentName || blockType}/
      </div>
    </div>
  );
};

export const DynamicBlockRenderer: React.FC<DynamicBlockRendererProps> = ({
  block,
  isEditing = false,
  isSelected = false,
  onChange,
  onSelect,
  className = ''
}) => {
  const componentName = useMemo(() => {
    // Use the explicit component field if provided
    if (block.component) {
      return block.component;
    }

    // Fall back to using the type field as component name
    // This is common when blocks use type to identify the component
    if (block.type) {
      console.log(`[DynamicBlockRenderer] Using type '${block.type}' as component name`);
      return block.type;
    }

    console.warn(`Block missing both 'component' and 'type' fields`);
    return null;
  }, [block.type, block.component]);

  const blockProps: BlockComponentProps = useMemo(() => ({
    content: block.props || {},
    isEditing,
    isSelected,
    onChange: onChange ? (newContent: Record<string, any>) => {
      onChange({
        ...block,
        props: newContent
      });
    } : undefined,
    onSelect,
    className
  }), [block, isEditing, isSelected, onChange, onSelect, className]);

  // If no component name is resolved, show error
  if (!componentName) {
    return <ErrorFallback blockType={block.type} componentName={block.component} />;
  }

  return (
    <ErrorBoundary fallback={<ErrorFallback blockType={block.type} componentName={componentName} />}>
      <DynamicComponent
        componentName={componentName}
        props={blockProps}
      />
    </ErrorBoundary>
  );
};
