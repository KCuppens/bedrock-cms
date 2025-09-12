import React, { useMemo } from 'react';
import { BlockProps } from '../BlockRenderer';

interface TextBlockProps extends BlockProps {
  props: {
    content?: string;
    alignment?: 'left' | 'center' | 'right';
    size?: 'sm' | 'base' | 'lg' | 'xl';
    className?: string;
  };
}

const TextBlock: React.FC<TextBlockProps> = React.memo(({ props }) => {
  const {
    content,
    alignment = 'left',
    size = 'base',
    className = ''
  } = props;

  if (!content) {
    return null;
  }

  const alignmentClasses = useMemo(() => ({
    left: 'text-left',
    center: 'text-center',
    right: 'text-right'
  }), []);

  const sizeClasses = useMemo(() => ({
    sm: 'text-sm',
    base: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl'
  }), []);

  return (
    <div
      className={`text-block ${alignmentClasses[alignment]} ${sizeClasses[size]} ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: content }}
    />
  );
});

TextBlock.displayName = 'TextBlock';

export default TextBlock;