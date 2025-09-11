export default {
  type: 'blog_detail',
  label: 'Blog Post Detail',
  category: 'Dynamic Content',
  icon: 'article',
  description: 'Displays blog post content (automatically injected based on URL)',
  defaultProps: {
    show_author: true,
    show_date: true,
    show_tags: true,
    show_reading_time: true,
    show_category: true,
    layout: 'article'
  },
  editableProps: [
    {
      name: 'layout',
      label: 'Layout Style',
      type: 'select',
      options: [
        { value: 'article', label: 'Article (Classic blog layout)' },
        { value: 'minimal', label: 'Minimal (Just title and content)' },
        { value: 'magazine', label: 'Magazine (Sidebar meta layout)' }
      ]
    },
    {
      name: 'show_author',
      label: 'Show Author',
      type: 'boolean'
    },
    {
      name: 'show_date',
      label: 'Show Publish Date',
      type: 'boolean'
    },
    {
      name: 'show_category',
      label: 'Show Category',
      type: 'boolean'
    },
    {
      name: 'show_tags',
      label: 'Show Tags',
      type: 'boolean'
    },
    {
      name: 'show_reading_time',
      label: 'Show Reading Time',
      type: 'boolean'
    }
  ],
  contentType: 'blog.BlogPost',
  urlPattern: '/blog/:slug',
  preload: false
};