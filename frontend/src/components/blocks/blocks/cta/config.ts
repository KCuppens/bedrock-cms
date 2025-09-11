import type { BlockConfig } from '../../types';

export const config: BlockConfig = {
  type: 'cta',
  label: 'Call to Action',
  category: 'marketing',
  icon: 'cta',
  description: 'Call-to-action section with title, description, and buttons',
  preload: false,
  editingMode: 'inline',
  defaultProps: {
    title: 'Ready to get started?',
    description: 'Join thousands of satisfied customers using our platform.',
    primaryButtonText: 'Get Started',
    primaryButtonUrl: '#',
    secondaryButtonText: 'Learn More',
    secondaryButtonUrl: '#',
    backgroundColor: 'blue'
  }
};

export default config;