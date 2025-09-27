import React, { useMemo } from 'react';
import { BlockComponentProps } from './types';

interface TextBlockProps extends BlockComponentProps {
  content: {
    content?: string;
    alignment?: 'left' | 'center' | 'right';
    size?: 'sm' | 'base' | 'lg' | 'xl';
    className?: string;
  };
}

const TextBlock: React.FC<TextBlockProps> = React.memo(({ content }) => {
  const {
    content: textContent,
    alignment = 'left',
    size = 'base',
    className = ''
  } = content;

  if (!textContent) {
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
      dangerouslySetInnerHTML={{ __html: textContent }}
    />
  );
});

TextBlock.displayName = 'TextBlock';

export default TextBlock;
