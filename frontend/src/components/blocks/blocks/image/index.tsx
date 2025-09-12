import React from 'react';
import type { BlockComponentProps } from '../../types';

interface ImageContent {
  src?: string;
  alt?: string;
  caption?: string;
  width?: number;
  height?: number;
  alignment?: 'left' | 'center' | 'right';
}

const ImageBlock: React.FC<BlockComponentProps<ImageContent>> = ({
  content = {},
  isEditing = false
}) => {
  const {
    src,
    alt = '',
    caption,
    alignment = 'center'
  } = content;

  const alignmentClass = {
    left: 'text-left',
    center: 'text-center mx-auto',
    right: 'text-right ml-auto'
  }[alignment];

  if (!src && isEditing) {
    return (
      <div className="p-8 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900">Image Block</h3>
          <p className="mt-2 text-sm text-gray-600">
            Configure this block to display an image
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`my-8 ${alignmentClass}`}>
      {src && (
        <img
          src={src}
          alt={alt}
          className="max-w-full h-auto rounded-lg shadow-lg"
        />
      )}
      {caption && (
        <p className="mt-3 text-sm text-gray-600 italic">{caption}</p>
      )}
    </div>
  );
};

export default ImageBlock;