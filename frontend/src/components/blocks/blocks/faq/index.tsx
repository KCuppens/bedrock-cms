import React, { useState } from 'react';
import type { BlockComponentProps } from '../../types';

interface FAQItem {
  question: string;
  answer: string;
}

export const FaqBlock: React.FC<BlockComponentProps> = ({
  content,
  isEditing = false,
  isSelected = false,
  onChange,
  onSelect,
  className = ''
}) => {
  const { title = 'Frequently Asked Questions', items = [] } = content;
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const handleTitleChange = (newTitle: string) => {
    if (onChange) {
      onChange({
        ...content,
        title: newTitle
      });
    }
  };

  const handleItemChange = (index: number, field: 'question' | 'answer', value: string) => {
    if (onChange) {
      const newItems = [...items];
      newItems[index] = { ...newItems[index], [field]: value };
      onChange({
        ...content,
        items: newItems
      });
    }
  };

  const addItem = () => {
    if (onChange) {
      onChange({
        ...content,
        items: [...items, { question: '', answer: '' }]
      });
    }
  };

  const removeItem = (index: number) => {
    if (onChange) {
      const newItems = items.filter((_: any, i: number) => i !== index);
      onChange({
        ...content,
        items: newItems
      });
    }
  };

  const toggleAccordion = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <div className={`py-12 ${className}`} onClick={onSelect}>
      <div className="mx-auto max-w-4xl px-6 lg:px-8">
        {isEditing ? (
          <input
            type="text"
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
            placeholder="FAQ Section Title"
            className="w-full text-2xl font-bold text-gray-900 mb-8 border-none outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1 bg-gray-50"
          />
        ) : (
          <h2 className="text-2xl font-bold leading-10 text-gray-900 mb-8">
            {title}
          </h2>
        )}

        <div className="space-y-4">
          {items.map((item: FAQItem, index: number) => (
            <div key={index} className="border border-gray-200 rounded-lg">
              {isEditing ? (
                <div className="p-4 space-y-3">
                  <div className="flex justify-between items-start">
                    <input
                      type="text"
                      value={item.question}
                      onChange={(e) => handleItemChange(index, 'question', e.target.value)}
                      placeholder="Enter question"
                      className="flex-1 text-base font-semibold text-gray-900 border-none outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1 bg-gray-50 mr-2"
                    />
                    <button
                      onClick={() => removeItem(index)}
                      className="text-red-500 hover:text-red-700 px-2 py-1 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                  <textarea
                    value={item.answer}
                    onChange={(e) => handleItemChange(index, 'answer', e.target.value)}
                    placeholder="Enter answer"
                    rows={3}
                    className="w-full text-base text-gray-700 border-none outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1 bg-gray-50 resize-none"
                  />
                </div>
              ) : (
                <div>
                  <button
                    onClick={() => toggleAccordion(index)}
                    className="flex w-full items-start justify-between px-4 py-6 text-left"
                  >
                    <span className="text-base font-semibold text-gray-900">
                      {item.question || `Question ${index + 1}`}
                    </span>
                    <span className="ml-6 flex h-7 items-center">
                      <svg
                        className={`h-6 w-6 transform transition-transform ${
                          openIndex === index ? 'rotate-180' : ''
                        }`}
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth="1.5"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                      </svg>
                    </span>
                  </button>
                  {openIndex === index && (
                    <div className="px-4 pb-6">
                      <p className="text-base text-gray-700">
                        {item.answer || 'Answer will appear here...'}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {isEditing && (
            <button
              onClick={addItem}
              className="w-full py-4 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-gray-400 hover:text-gray-600 transition-colors"
            >
              + Add FAQ Item
            </button>
          )}

          {!isEditing && items.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No FAQ items yet. Add some in edit mode.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FaqBlock;
