import React from 'react';
import type { BlockComponentProps } from '../../types';

export const HeroBlock: React.FC<BlockComponentProps> = ({
  content,
  isEditing = false,
  isSelected = false,
  onChange,
  onSelect,
  className = ''
}) => {
  const { title = '', subtitle = '', buttonText = '', buttonUrl = '', backgroundImage = '' } = content;

  const handleChange = (field: string, value: string) => {
    if (onChange) {
      onChange({
        ...content,
        [field]: value
      });
    }
  };

  return (
    <div
      className={`relative overflow-hidden bg-gray-900 ${className}`}
      onClick={onSelect}
      style={{
        backgroundImage: backgroundImage ? `url(${backgroundImage})` : undefined,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        minHeight: '400px'
      }}
    >
      {backgroundImage && (
        <div className="absolute inset-0 bg-black bg-opacity-40" />
      )}

      <div className="relative px-6 py-24 sm:px-12 sm:py-32 lg:px-16">
        <div className="mx-auto max-w-2xl text-center">
          {isEditing ? (
            <input
              type="text"
              value={title}
              onChange={(e) => handleChange('title', e.target.value)}
              placeholder="Hero Title"
              className="w-full bg-transparent text-4xl font-bold text-white placeholder-gray-300 border-none outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1"
            />
          ) : (
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-6xl">
              {title || 'Your Hero Title'}
            </h1>
          )}

          {isEditing ? (
            <textarea
              value={subtitle}
              onChange={(e) => handleChange('subtitle', e.target.value)}
              placeholder="Hero Subtitle"
              rows={3}
              className="mt-6 w-full bg-transparent text-lg text-gray-300 placeholder-gray-400 border-none outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1 resize-none"
            />
          ) : (
            <p className="mt-6 text-lg leading-8 text-gray-300">
              {subtitle || 'Your compelling subtitle goes here'}
            </p>
          )}

          <div className="mt-10 flex items-center justify-center gap-x-6">
            {(buttonText || isEditing) && (
              isEditing ? (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={buttonText}
                    onChange={(e) => handleChange('buttonText', e.target.value)}
                    placeholder="Button Text"
                    className="bg-blue-600 text-white px-4 py-2 rounded-md border-none outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <input
                    type="url"
                    value={buttonUrl}
                    onChange={(e) => handleChange('buttonUrl', e.target.value)}
                    placeholder="Button URL"
                    className="bg-transparent text-white px-4 py-2 rounded-md border border-white border-opacity-50 outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ) : (
                <a
                  href={buttonUrl || '#'}
                  className="rounded-md bg-blue-600 px-3.5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 transition-colors"
                >
                  {buttonText}
                </a>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HeroBlock;