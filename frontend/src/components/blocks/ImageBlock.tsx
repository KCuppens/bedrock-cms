import React, { useMemo } from 'react';
import { BlockProps } from '../BlockRenderer';

interface ImageBlockProps extends BlockProps {
  props: {
    src?: string;
    alt?: string;
    caption?: string;
    width?: number;
    height?: number;
    alignment?: 'left' | 'center' | 'right';
    className?: string;
  };
}

const ImageBlock: React.FC<ImageBlockProps> = React.memo(({ props }) => {
  const {
    src,
    alt = '',
    caption,
    width,
    height,
    alignment = 'center',
    className = ''
  } = props;

  if (!src) {
    return null;
  }

  const alignmentClasses = useMemo(() => ({
    left: 'text-left',
    center: 'text-center',
    right: 'text-right'
  }), []);

  const imageAlignmentClasses = useMemo(() => ({
    left: 'mr-auto',
    center: 'mx-auto',
    right: 'ml-auto'
  }), []);

  return (
    <figure className={`image-block ${alignmentClasses[alignment]} ${className}`.trim()}>
      <img
        src={src}
        alt={alt}
        width={width}
        height={height}
        className={`max-w-full h-auto ${imageAlignmentClasses[alignment]}`.trim()}
        loading="lazy"
      />
      {caption && (
        <figcaption className="mt-2 text-sm text-gray-600 italic">
          {caption}
        </figcaption>
      )}
    </figure>
  );
});

ImageBlock.displayName = 'ImageBlock';

export default ImageBlock;
