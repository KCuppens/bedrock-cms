import type { BlockConfig } from '../../types';

export const config: BlockConfig = {
  type: 'faq',
  label: 'FAQ Section',
  category: 'content',
  icon: 'question',
  description: 'Frequently Asked Questions with expandable accordion items',
  preload: false,
  editingMode: 'inline',
  defaultProps: {
    title: 'Frequently Asked Questions',
    items: [
      {
        question: 'What is this service about?',
        answer: 'This is a sample FAQ answer that explains the service in detail.'
      },
      {
        question: 'How do I get started?',
        answer: 'Getting started is easy! Simply follow these steps...'
      }
    ]
  }
};

export default config;