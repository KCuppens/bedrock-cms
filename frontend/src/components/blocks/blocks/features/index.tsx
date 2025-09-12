import React from 'react';
import type { BlockComponentProps } from '../../types';

interface Feature {
  id: string;
  title: string;
  description: string;
  icon?: string;
}

export const FeaturesBlock: React.FC<BlockComponentProps> = ({
  content,
  isEditing = false,
  onChange,
  className = ''
}) => {
  const {
    title = 'Features',
    subtitle = '',
    features = [] as Feature[],
    columns = 3
  } = content;

  const handleChange = (field: string, value: any) => {
    if (onChange) {
      onChange({
        ...content,
        [field]: value
      });
    }
  };

  const handleFeatureChange = (index: number, field: string, value: string) => {
    if (onChange) {
      const updatedFeatures = [...(features || [])];
      updatedFeatures[index] = {
        ...updatedFeatures[index],
        [field]: value
      };
      onChange({
        ...content,
        features: updatedFeatures
      });
    }
  };

  const addFeature = () => {
    const newFeature: Feature = {
      id: Date.now().toString(),
      title: 'New Feature',
      description: 'Feature description'
    };
    handleChange('features', [...(features || []), newFeature]);
  };

  const removeFeature = (index: number) => {
    const updatedFeatures = features.filter((_: Feature, i: number) => i !== index);
    handleChange('features', updatedFeatures);
  };

  return (
    <div className={`py-12 sm:py-16 ${className}`}>
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl lg:text-center">
          {isEditing ? (
            <input
              type="text"
              value={title}
              onChange={(e) => handleChange('title', e.target.value)}
              placeholder="Features Title"
              className="w-full text-3xl font-bold text-gray-900 border-b-2 border-gray-300 outline-none focus:border-blue-500 px-2 py-1"
            />
          ) : (
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              {title}
            </h2>
          )}

          {isEditing ? (
            <input
              type="text"
              value={subtitle}
              onChange={(e) => handleChange('subtitle', e.target.value)}
              placeholder="Features Subtitle (optional)"
              className="mt-2 w-full text-lg text-gray-600 border-b border-gray-200 outline-none focus:border-blue-500 px-2 py-1"
            />
          ) : subtitle ? (
            <p className="mt-2 text-lg leading-8 text-gray-600">
              {subtitle}
            </p>
          ) : null}
        </div>

        <div className={`mx-auto mt-10 max-w-2xl sm:mt-16 lg:mt-20 lg:max-w-none`}>
          <dl className={`grid max-w-xl gap-x-8 gap-y-10 lg:max-w-none lg:grid-cols-${columns} lg:gap-y-16`}>
            {features && features.map((feature: Feature, index: number) => (
              <div key={feature.id || index} className="relative">
                {isEditing ? (
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={feature.title}
                      onChange={(e) => handleFeatureChange(index, 'title', e.target.value)}
                      placeholder="Feature Title"
                      className="w-full text-lg font-semibold text-gray-900 border-b border-gray-300 outline-none focus:border-blue-500 px-2 py-1"
                    />
                    <textarea
                      value={feature.description}
                      onChange={(e) => handleFeatureChange(index, 'description', e.target.value)}
                      placeholder="Feature Description"
                      rows={3}
                      className="w-full text-base text-gray-600 border border-gray-200 rounded outline-none focus:border-blue-500 px-2 py-1 resize-none"
                    />
                    <button
                      onClick={() => removeFeature(index)}
                      className="text-red-500 hover:text-red-700 text-sm"
                    >
                      Remove Feature
                    </button>
                  </div>
                ) : (
                  <>
                    <dt className="text-base font-semibold leading-7 text-gray-900">
                      {feature.icon && (
                        <div className="absolute left-0 top-0 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white">
                          {feature.icon}
                        </div>
                      )}
                      <span className={feature.icon ? 'ml-12' : ''}>
                        {feature.title}
                      </span>
                    </dt>
                    <dd className={`mt-2 text-base leading-7 text-gray-600 ${feature.icon ? 'ml-12' : ''}`}>
                      {feature.description}
                    </dd>
                  </>
                )}
              </div>
            ))}
          </dl>

          {isEditing && (
            <button
              onClick={addFeature}
              className="mt-6 rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500"
            >
              Add Feature
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default FeaturesBlock;
