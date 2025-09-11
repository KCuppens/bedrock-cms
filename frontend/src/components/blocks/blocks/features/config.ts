import type { BlockConfig } from '../../types';

export const config: BlockConfig = {
  type: 'features',
  label: 'Features Grid',
  category: 'content',
  icon: 'features',
  description: 'Grid layout showcasing multiple features or benefits',
  preload: false,
  editingMode: 'inline',
  defaultProps: {
    title: 'Features',
    subtitle: 'Everything you need to succeed',
    features: [
      {
        id: '1',
        title: 'Fast Performance',
        description: 'Lightning-fast load times and smooth interactions'
      },
      {
        id: '2',
        title: 'Secure & Reliable',
        description: 'Bank-level security with 99.9% uptime guarantee'
      },
      {
        id: '3',
        title: '24/7 Support',
        description: 'Round-the-clock customer support when you need it'
      }
    ],
    columns: 3
  }
};

export default config;