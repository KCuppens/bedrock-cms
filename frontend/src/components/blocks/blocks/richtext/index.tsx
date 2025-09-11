import React from 'react';
import type { BlockComponentProps } from '../../types';

export const RichtextBlock: React.FC<BlockComponentProps> = ({
  content,
  isEditing = false,
  isSelected = false,
  onChange,
  onSelect,
  className = ''
}) => {
  const { content: richContent = '', alignment = 'left' } = content;

  const handleContentChange = (value: string) => {
    if (onChange) {
      onChange({
        ...content,
        content: value
      });
    }
  };

  const alignmentClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
    justify: 'text-justify'
  };

  return (
    <div 
      className={`prose prose-lg max-w-none ${alignmentClasses[alignment as keyof typeof alignmentClasses] || 'text-left'} ${className}`}
      onClick={onSelect}
    >
      {isEditing ? (
        <div className="space-y-4">
          <div className="flex gap-2 mb-4">
            <select
              value={alignment}
              onChange={(e) => onChange && onChange({ ...content, alignment: e.target.value })}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="left">Left Align</option>
              <option value="center">Center Align</option>
              <option value="right">Right Align</option>
              <option value="justify">Justify</option>
            </select>
          </div>
          <textarea
            value={richContent}
            onChange={(e) => handleContentChange(e.target.value)}
            placeholder="Enter your rich text content here... You can use HTML tags for formatting."
            rows={10}
            className="w-full p-4 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-vertical"
          />
          <div className="text-xs text-gray-500">
            Tip: You can use HTML tags like &lt;strong&gt;, &lt;em&gt;, &lt;u&gt;, &lt;h1&gt;-&lt;h6&gt;, &lt;p&gt;, &lt;ul&gt;, &lt;ol&gt;, &lt;li&gt;, &lt;a&gt;, etc.
          </div>
        </div>
      ) : (
        <div 
          className="rich-content"
          dangerouslySetInnerHTML={{ 
            __html: richContent || '<p>Add your rich text content here...</p>' 
          }} 
        />
      )}
    </div>
  );
};

export default RichtextBlock;