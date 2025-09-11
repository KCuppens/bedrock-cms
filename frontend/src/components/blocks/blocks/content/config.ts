import type { BlockConfig } from '../../types';

export const config: BlockConfig = {
  type: 'content',
  label: 'Content Section',
  category: 'content',
  icon: 'content',
  description: 'Flexible content section with text and optional image',
  preload: false,
  editingMode: 'inline',
  defaultProps: {
    title: 'Content Section',
    content: '<p>Add your content here. This block supports rich text formatting and can include images alongside your text.</p>',
    alignment: 'left',
    imageUrl: '',
    imagePosition: 'right',
    imageCaption: ''
  }
};

export default config;