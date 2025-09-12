import React from 'react';
import type { BlockComponentProps } from '../../types';

export const ContentBlock: React.FC<BlockComponentProps> = ({
  content,
  isEditing = false,
  onChange,
  className = ''
}) => {
  const {
    title = '',
    content: textContent = '',
    alignment = 'left',
    imageUrl = '',
    imagePosition = 'right',
    imageCaption = ''
  } = content;

  const handleChange = (field: string, value: string) => {
    if (onChange) {
      onChange({
        ...content,
        [field]: value
      });
    }
  };

  const alignmentClass = alignment === 'center' ? 'text-center' : alignment === 'right' ? 'text-right' : 'text-left';
  const hasImage = imageUrl || isEditing;

  return (
    <div className={`py-12 sm:py-16 ${className}`}>
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className={`${hasImage ? 'lg:grid lg:grid-cols-2 lg:gap-x-8 lg:items-center' : 'max-w-3xl mx-auto'}`}>
          {/* Text Content */}
          <div className={`${hasImage && imagePosition === 'left' ? 'lg:order-2' : ''}`}>
            <div className={`${alignmentClass}`}>
              {isEditing ? (
                <input
                  type="text"
                  value={title}
                  onChange={(e) => handleChange('title', e.target.value)}
                  placeholder="Content Title (optional)"
                  className="w-full text-3xl font-bold text-gray-900 border-b-2 border-gray-300 outline-none focus:border-blue-500 px-2 py-1 mb-4"
                />
              ) : title ? (
                <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl mb-6">
                  {title}
                </h2>
              ) : null}

              {isEditing ? (
                <textarea
                  value={textContent}
                  onChange={(e) => handleChange('content', e.target.value)}
                  placeholder="Your content goes here..."
                  rows={8}
                  className="w-full text-base text-gray-600 border border-gray-200 rounded-lg outline-none focus:border-blue-500 px-4 py-3 resize-none"
                />
              ) : (
                <div
                  className="prose prose-lg text-gray-600 max-w-none"
                  dangerouslySetInnerHTML={{ __html: textContent }}
                />
              )}
            </div>
          </div>

          {/* Image Section */}
          {hasImage && (
            <div className={`mt-10 lg:mt-0 ${imagePosition === 'left' ? 'lg:order-1' : ''}`}>
              {isEditing ? (
                <div className="space-y-4">
                  <input
                    type="url"
                    value={imageUrl}
                    onChange={(e) => handleChange('imageUrl', e.target.value)}
                    placeholder="Image URL (optional)"
                    className="w-full text-sm text-gray-600 border border-gray-200 rounded outline-none focus:border-blue-500 px-3 py-2"
                  />
                  {imageUrl && (
                    <>
                      <img
                        src={imageUrl}
                        alt={imageCaption || 'Content image'}
                        className="w-full rounded-lg shadow-lg"
                      />
                      <input
                        type="text"
                        value={imageCaption}
                        onChange={(e) => handleChange('imageCaption', e.target.value)}
                        placeholder="Image caption (optional)"
                        className="w-full text-sm text-gray-500 border border-gray-200 rounded outline-none focus:border-blue-500 px-3 py-1"
                      />
                    </>
                  )}
                  <div className="flex gap-4">
                    <label className="text-sm text-gray-600">
                      Position:
                      <select
                        value={imagePosition}
                        onChange={(e) => handleChange('imagePosition', e.target.value)}
                        className="ml-2 border border-gray-200 rounded px-2 py-1"
                      >
                        <option value="right">Right</option>
                        <option value="left">Left</option>
                      </select>
                    </label>
                  </div>
                </div>
              ) : imageUrl ? (
                <figure>
                  <img
                    src={imageUrl}
                    alt={imageCaption || 'Content image'}
                    className="w-full rounded-lg shadow-lg"
                  />
                  {imageCaption && (
                    <figcaption className="mt-3 text-sm text-center text-gray-500">
                      {imageCaption}
                    </figcaption>
                  )}
                </figure>
              ) : null}
            </div>
          )}
        </div>

        {/* Alignment Controls in Edit Mode */}
        {isEditing && (
          <div className="mt-6 flex justify-center gap-4">
            <label className="text-sm text-gray-600">
              Text Alignment:
              <select
                value={alignment}
                onChange={(e) => handleChange('alignment', e.target.value)}
                className="ml-2 border border-gray-200 rounded px-2 py-1"
              >
                <option value="left">Left</option>
                <option value="center">Center</option>
                <option value="right">Right</option>
              </select>
            </label>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContentBlock;
