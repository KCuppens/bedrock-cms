import React, { useMemo } from 'react';
import DOMPurify from 'dompurify';
import { BlockComponentProps } from './types';

interface RichtextBlockProps extends BlockComponentProps {
  content: {
    content?: string;
    className?: string;
  };
}

// Security: Configure DOMPurify with safe defaults
const DOMPURIFY_CONFIG = {
  ALLOWED_TAGS: [
    'p', 'div', 'span', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'b', 'em', 'i', 'u', 's', 'sub', 'sup',
    'ul', 'ol', 'li',
    'a', 'img',
    'blockquote', 'pre', 'code',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'figure', 'figcaption'
  ],
  ALLOWED_ATTR: [
    'class', 'id',
    'href', 'title', 'target', 'rel',
    'src', 'alt', 'width', 'height',
    'cite', 'cellpadding', 'cellspacing', 'border',
    'scope', 'rowspan', 'colspan'
  ],
  ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|data):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
  KEEP_CONTENT: true,
  RETURN_TRUSTED_TYPE: false,
};

const RichtextBlock: React.FC<RichtextBlockProps> = ({ content }) => {
  const { content: richContent, className = '' } = content;

  // Security: Sanitize HTML content with DOMPurify to prevent XSS attacks
  const sanitizedContent = useMemo(() => {
    if (!richContent) return '';
    return DOMPurify.sanitize(richContent, DOMPURIFY_CONFIG);
  }, [richContent]);

  if (!richContent) {
    return null;
  }

  return (
    <div
      className={`richtext-block prose prose-lg max-w-none ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: sanitizedContent }}
    />
  );
};

export default RichtextBlock;
