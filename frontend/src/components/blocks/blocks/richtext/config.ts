import type { BlockConfig } from '../../types';

export const config: BlockConfig = {
  type: 'richtext',
  label: 'Rich Text',
  category: 'content',
  icon: 'text',
  description: 'Rich text content with HTML formatting support',
  preload: false,
  editingMode: 'inline',
  defaultProps: {
    content: '<p>Enter your rich text content here. You can use <strong>bold</strong>, <em>italic</em>, and other HTML formatting.</p>',
    alignment: 'left'
  }
};

export default config;