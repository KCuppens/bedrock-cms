import React from 'react';
import { DynamicBlockRenderer } from './DynamicBlockRenderer';
import type { BlockData } from './types';

interface DynamicBlocksRendererProps {
  blocks: BlockData[];
  className?: string;
  isEditing?: boolean;
  onChange?: (blocks: BlockData[]) => void;
  onBlockChange?: (index: number, block: BlockData) => void;
  onBlockSelect?: (index: number) => void;
  selectedIndex?: number;
}

export const DynamicBlocksRenderer: React.FC<DynamicBlocksRendererProps> = ({
  blocks,
  className = '',
  isEditing = false,
  onChange,
  onBlockChange,
  onBlockSelect,
  selectedIndex
}) => {
  const handleBlockChange = (index: number) => (updatedBlock: BlockData) => {
    if (onChange) {
      const newBlocks = [...blocks];
      newBlocks[index] = updatedBlock;
      onChange(newBlocks);
    }
    if (onBlockChange) {
      onBlockChange(index, updatedBlock);
    }
  };

  if (!blocks || blocks.length === 0) {
    return null;
  }

  return (
    <div className={`blocks-container ${className}`}>
      {blocks.map((block, index) => (
        <div key={block.id || `block-${index}`} className="block-wrapper">
          <DynamicBlockRenderer
            block={block}
            isEditing={isEditing}
            isSelected={selectedIndex === index}
            onChange={isEditing ? handleBlockChange(index) : undefined}
            onSelect={onBlockSelect ? () => onBlockSelect(index) : undefined}
          />
        </div>
      ))}
    </div>
  );
};

// For backward compatibility with pages expecting default export
export default DynamicBlocksRenderer;

// Export a hook for prefetching block components
export const usePrefetchBlocks = (blockTypes: string[]) => {
  React.useEffect(() => {
    if (!blockTypes || blockTypes.length === 0) return;

    import('./BlockRegistry').then(({ BlockRegistry }) => {
      const registry = BlockRegistry.getInstance();
      blockTypes.forEach(type => {
        const componentName = type.charAt(0).toUpperCase() + type.slice(1) + 'Block';
        registry.getComponent(componentName).catch(() => {
          // Silently fail for missing components during prefetch
        });
      });
    });
  }, [blockTypes]);
};
