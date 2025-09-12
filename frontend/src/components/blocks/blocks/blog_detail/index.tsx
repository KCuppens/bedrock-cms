import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Badge } from '@/components/ui/badge';
import { Calendar, Clock, User } from 'lucide-react';

interface BlogDetailProps {
  // Block configuration (from page editor)
  show_author?: boolean;
  show_date?: boolean;
  show_tags?: boolean;
  show_reading_time?: boolean;
  show_category?: boolean;
  layout?: 'article' | 'minimal' | 'magazine';

  // System props
  isEditing?: boolean;
  onChange?: (props: any) => void;

  // Injected content (runtime only)
  __injectedContent?: BlogPost;
}

interface BlogPost {
  id: string;
  title: string;
  content: string;
  excerpt: string;
  author_name?: string;
  published_at: string;
  reading_time?: number;
  tags?: Array<{ id: string; name: string }>;
  tag_data?: Array<{ id: string; name: string }>;
  category?: { id: string; name: string };
  category_data?: { id: string; name: string; color?: string };
}

const BlogDetail: React.FC<BlogDetailProps> = ({
  show_author = true,
  show_date = true,
  show_tags = true,
  show_reading_time = true,
  show_category = true,
  layout = 'article',
  isEditing = false,
  onChange,
  __injectedContent
}) => {
  // Editing mode - show placeholder and settings
  if (isEditing && !__injectedContent) {
    return (
      <div className="border-2 border-dashed border-purple-300 bg-purple-50 rounded-lg p-8">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-6">
            <h3 className="text-lg font-semibold text-purple-900 mb-2">
              Blog Post Detail
            </h3>
            <p className="text-purple-700 mb-4">
              Blog post content will be displayed here when viewed
            </p>
            <div className="text-sm text-purple-600 space-y-1">
              <p>URL Pattern: /blog/[slug]</p>
              <p>Current Layout: {layout}</p>
            </div>
          </div>

          {/* Settings panel */}
          <div className="p-4 bg-white rounded border border-purple-200">
            <h4 className="font-medium mb-3 text-gray-900">Display Settings</h4>

            {/* Layout selector */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Layout Style
              </label>
              <select
                value={layout}
                onChange={(e) => onChange?.({ layout: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="article">Article (Classic)</option>
                <option value="minimal">Minimal</option>
                <option value="magazine">Magazine</option>
              </select>
            </div>

            {/* Display options */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={show_author}
                  onChange={(e) => onChange?.({ show_author: e.target.checked })}
                  className="rounded"
                />
                <span>Show author</span>
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={show_date}
                  onChange={(e) => onChange?.({ show_date: e.target.checked })}
                  className="rounded"
                />
                <span>Show publish date</span>
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={show_category}
                  onChange={(e) => onChange?.({ show_category: e.target.checked })}
                  className="rounded"
                />
                <span>Show category</span>
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={show_tags}
                  onChange={(e) => onChange?.({ show_tags: e.target.checked })}
                  className="rounded"
                />
                <span>Show tags</span>
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={show_reading_time}
                  onChange={(e) => onChange?.({ show_reading_time: e.target.checked })}
                  className="rounded"
                />
                <span>Show reading time</span>
              </label>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // No content injected (loading or error state)
  if (!__injectedContent) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    );
  }

  // Render actual blog post
  const post = __injectedContent;
  const tags = post.tag_data || post.tags || [];
  const category = post.category_data || post.category;

  // Minimal layout
  if (layout === 'minimal') {
    return (
      <article className="prose prose-lg max-w-none">
        <h1>{post.title}</h1>
        <div dangerouslySetInnerHTML={{ __html: post.content }} />
      </article>
    );
  }

  // Magazine layout
  if (layout === 'magazine') {
    return (
      <article className="magazine-layout">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-2">
            {/* Sidebar meta */}
            <div className="sticky top-4 space-y-4 text-sm">
              {show_author && post.author_name && (
                <div>
                  <div className="font-semibold text-gray-500 uppercase tracking-wide mb-1">Author</div>
                  <div>{post.author_name}</div>
                </div>
              )}
              {show_date && post.published_at && (
                <div>
                  <div className="font-semibold text-gray-500 uppercase tracking-wide mb-1">Published</div>
                  <div>{formatDistanceToNow(new Date(post.published_at), { addSuffix: true })}</div>
                </div>
              )}
              {show_reading_time && post.reading_time && (
                <div>
                  <div className="font-semibold text-gray-500 uppercase tracking-wide mb-1">Reading Time</div>
                  <div>{post.reading_time} min</div>
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-10">
            <header className="mb-8">
              {show_category && category && (
                <Badge
                  className="mb-4"
                  style={{ backgroundColor: category.color || '#6366f1' }}
                >
                  {category.name}
                </Badge>
              )}
              <h1 className="text-5xl font-bold mb-4">{post.title}</h1>
              {post.excerpt && (
                <p className="text-xl text-gray-600">{post.excerpt}</p>
              )}
            </header>

            <div
              className="prose prose-lg max-w-none mb-8"
              dangerouslySetInnerHTML={{ __html: post.content }}
            />

            {show_tags && tags.length > 0 && (
              <footer className="border-t pt-6">
                <div className="flex flex-wrap gap-2">
                  {tags.map(tag => (
                    <Badge key={tag.id} variant="secondary">
                      {tag.name}
                    </Badge>
                  ))}
                </div>
              </footer>
            )}
          </div>
        </div>
      </article>
    );
  }

  // Default article layout
  return (
    <article className="blog-detail blog-detail--article">
      <header className="mb-8">
        {show_category && category && (
          <Badge
            className="mb-4"
            style={{
              backgroundColor: category.color ? `${category.color}20` : '#6366f120',
              color: category.color || '#6366f1',
              borderColor: category.color || '#6366f1'
            }}
          >
            {category.name}
          </Badge>
        )}

        <h1 className="text-4xl font-bold mb-4">{post.title}</h1>

        {post.excerpt && (
          <p className="text-xl text-gray-600 mb-4">{post.excerpt}</p>
        )}

        <div className="flex flex-wrap items-center gap-4 text-gray-600">
          {show_author && post.author_name && (
            <div className="flex items-center gap-2">
              <User className="w-4 h-4" />
              <span>{post.author_name}</span>
            </div>
          )}

          {show_date && post.published_at && (
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              <time dateTime={post.published_at}>
                {new Date(post.published_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </time>
            </div>
          )}

          {show_reading_time && post.reading_time && (
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              <span>{post.reading_time} min read</span>
            </div>
          )}
        </div>
      </header>

      <div
        className="prose prose-lg max-w-none mb-8"
        dangerouslySetInnerHTML={{ __html: post.content }}
      />

      {show_tags && tags.length > 0 && (
        <footer className="border-t pt-6">
          <div className="flex flex-wrap gap-2">
            {tags.map(tag => (
              <Badge key={tag.id} variant="secondary">
                {tag.name}
              </Badge>
            ))}
          </div>
        </footer>
      )}
    </article>
  );
};

export default BlogDetail;
