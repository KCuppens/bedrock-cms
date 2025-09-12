import React from 'react';
import type { BlockComponentProps } from '../../types';

export const CTABlock: React.FC<BlockComponentProps> = ({
  content,
  isEditing = false,
  onChange,
  className = ''
}) => {
  const {
    title = 'Ready to get started?',
    description = '',
    primaryButtonText = '',
    primaryButtonUrl = '#',
    secondaryButtonText = '',
    secondaryButtonUrl = '#'
  } = content;

  const handleChange = (field: string, value: string) => {
    if (onChange) {
      onChange({
        ...content,
        [field]: value
      });
    }
  };

  return (
    <div className={`bg-gradient-to-r from-blue-600 to-blue-700 ${className}`}>
      <div className="px-6 py-16 sm:px-6 sm:py-24 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          {isEditing ? (
            <input
              type="text"
              value={title}
              onChange={(e) => handleChange('title', e.target.value)}
              placeholder="CTA Title"
              className="w-full bg-transparent text-3xl font-bold text-white placeholder-gray-300 border-b-2 border-white border-opacity-50 outline-none focus:border-opacity-100 px-2 py-1"
            />
          ) : (
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              {title}
            </h2>
          )}

          {isEditing ? (
            <textarea
              value={description}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder="Add a description to provide more context (optional)"
              rows={3}
              className="mt-6 w-full bg-transparent text-lg text-gray-200 placeholder-gray-400 border border-white border-opacity-20 rounded-md outline-none focus:border-opacity-40 px-3 py-2 resize-none"
            />
          ) : description ? (
            <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-gray-200">
              {description}
            </p>
          ) : null}

          <div className="mt-10 flex items-center justify-center gap-x-6">
            {isEditing ? (
              <div className="flex flex-col gap-4 w-full max-w-2xl">
                <div className="flex flex-col sm:flex-row gap-2">
                  <input
                    type="text"
                    value={primaryButtonText}
                    onChange={(e) => handleChange('primaryButtonText', e.target.value)}
                    placeholder="Primary Button Text (leave empty to hide)"
                    className="flex-1 bg-white text-gray-900 px-4 py-2 rounded-md outline-none focus:ring-2 focus:ring-white"
                  />
                  <input
                    type="url"
                    value={primaryButtonUrl}
                    onChange={(e) => handleChange('primaryButtonUrl', e.target.value)}
                    placeholder="Primary Button URL"
                    className="flex-1 bg-transparent text-white px-4 py-2 rounded-md border border-white border-opacity-50 outline-none focus:border-opacity-100"
                  />
                </div>
                <div className="flex flex-col sm:flex-row gap-2">
                  <input
                    type="text"
                    value={secondaryButtonText}
                    onChange={(e) => handleChange('secondaryButtonText', e.target.value)}
                    placeholder="Secondary Button Text (optional)"
                    className="flex-1 bg-transparent text-white px-4 py-2 rounded-md border border-white border-opacity-50 outline-none focus:border-opacity-100"
                  />
                  <input
                    type="url"
                    value={secondaryButtonUrl}
                    onChange={(e) => handleChange('secondaryButtonUrl', e.target.value)}
                    placeholder="Secondary Button URL"
                    className="flex-1 bg-transparent text-white px-4 py-2 rounded-md border border-white border-opacity-50 outline-none focus:border-opacity-100"
                  />
                </div>
              </div>
            ) : (
              <>
                {primaryButtonText && (
                  <a
                    href={primaryButtonUrl}
                    className="rounded-md bg-white px-3.5 py-2.5 text-sm font-semibold text-gray-900 shadow-sm hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                  >
                    {primaryButtonText}
                  </a>
                )}
                {secondaryButtonText && (
                  <a
                    href={secondaryButtonUrl}
                    className="text-sm font-semibold leading-6 text-white hover:text-gray-300"
                  >
                    {secondaryButtonText} <span aria-hidden="true">→</span>
                  </a>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CTABlock;