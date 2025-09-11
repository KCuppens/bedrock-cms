import React from 'react';
import type { BlockComponentProps } from '../../types';

interface PlaceholderContent {
  [key: string]: any;
}

const PlaceholderBlock: React.FC<BlockComponentProps<PlaceholderContent>> = ({ 
  content = {},
  isEditing = false,
  blockType = 'placeholder' 
}) => {
  return (
    <div className="p-8 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
      <div className="text-center">
        <h3 className="text-lg font-medium text-gray-900">{blockType} Block</h3>
        <p className="mt-2 text-sm text-gray-600">
          This is a placeholder for the {blockType} block component
        </p>
        {isEditing && (
          <p className="mt-1 text-xs text-gray-500">
            Component implementation coming soon
          </p>
        )}
      </div>
    </div>
  );
};

export default PlaceholderBlock;