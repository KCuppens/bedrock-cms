import React from 'react';
import { BlockComponentProps } from './types';

interface RichtextBlockProps extends BlockComponentProps {
  content: {
    content?: string;
    className?: string;
  };
}

const RichtextBlock: React.FC<RichtextBlockProps> = ({ content }) => {
  const { content: richContent, className = '' } = content;

  if (!richContent) {
    return null;
  }

  return (
    <div
      className={`richtext-block prose prose-lg max-w-none ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: richContent }}
    />
  );
};

export default RichtextBlock;
