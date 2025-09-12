import React from 'react';
import { BlockProps } from '../BlockRenderer';

interface RichtextBlockProps extends BlockProps {
  props: {
    content?: string;
    className?: string;
  };
}

const RichtextBlock: React.FC<RichtextBlockProps> = ({ props }) => {
  const { content, className = '' } = props;

  if (!content) {
    return null;
  }

  return (
    <div
      className={`richtext-block prose prose-lg max-w-none ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: content }}
    />
  );
};

export default RichtextBlock;
