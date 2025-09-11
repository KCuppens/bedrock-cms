import type { BlockConfig } from '../../types';

const config: BlockConfig = {
  type: 'blog_list',
  label: 'Blog List',
  category: 'dynamic',
  icon: 'list',
  description: 'Display a list of blog posts',
  defaultContent: {
    title: 'Latest Blog Posts',
    description: '',
    limit: 6,
    columns: 3,
    show_excerpt: true,
    show_author: true,
    show_date: true,
    show_categories: true,
    show_tags: false,
    cta_text: 'Read More',
    ordering: '-created_at'
  }
};

export default config;