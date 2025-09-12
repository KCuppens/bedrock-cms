import type { BlockConfig } from '../../types';

export const config: BlockConfig = {
  type: 'hero',
  label: 'Hero Section',
  category: 'layout',
  icon: 'hero',
  description: 'Large banner section with title, subtitle, and call-to-action button',
  preload: true,
  editingMode: 'inline',
  defaultProps: {
    title: 'Welcome to Our Website',
    subtitle: 'Discover amazing content and services that will transform your experience',
    buttonText: 'Get Started',
    buttonUrl: '#',
    backgroundImage: ''
  }
};

export default config;
