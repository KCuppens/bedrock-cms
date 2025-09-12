import React, { useMemo } from 'react';
import { BlockProps } from '../BlockRenderer';
import { Button } from '@/components/ui/button';
import { useBlockTranslation } from '@/hooks/useBlockTranslation';

interface HeroBlockProps extends BlockProps {
  props: {
    title?: string;
    subtitle?: string;
    content?: string;
    backgroundImage?: string;
    backgroundColor?: string;
    textColor?: string;
    buttonText?: string;
    buttonUrl?: string;
    alignment?: 'left' | 'center' | 'right';
    className?: string;
  };
  isEditable?: boolean;
}

const HeroBlock: React.FC<HeroBlockProps> = React.memo(({ props, isEditable }) => {
  // Register and use translations
  const { t } = useBlockTranslation({
    blockType: 'hero',
    keys: {
      loading: 'Loading hero content...',
      error: 'Failed to load hero block',
      defaultTitle: 'Welcome',
      defaultSubtitle: 'Start your journey here',
      defaultButton: 'Get Started'
    }
  });
  const {
    title,
    subtitle,
    content,
    backgroundImage,
    backgroundColor = 'bg-gray-900',
    textColor = 'text-white',
    buttonText,
    buttonUrl,
    alignment = 'center',
    className = ''
  } = props;

  const alignmentClasses = useMemo(() => ({
    left: 'text-left',
    center: 'text-center',
    right: 'text-right'
  }), []);

  const containerStyle: React.CSSProperties = useMemo(() => ({
    ...(backgroundImage && {
      backgroundImage: `url(${backgroundImage})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat'
    })
  }), [backgroundImage]);

  // Show loading state in edit mode if no content
  if (isEditable && !title && !subtitle && !content) {
    return (
      <div className="hero-block-loading p-8 text-center bg-gray-100">
        <p className="text-gray-500">{t('loading')}</p>
      </div>
    );
  }

  return (
    <section
      className={`hero-block relative py-20 px-6 ${backgroundColor} ${textColor} ${alignmentClasses[alignment]} ${className}`.trim()}
      style={containerStyle}
      aria-label="Hero section"
    >
      {backgroundImage && (
        <div className="absolute inset-0 bg-black/50" aria-hidden="true" />
      )}

      <div className="relative max-w-4xl mx-auto">
        {(title || isEditable) && (
          <h1 className="text-4xl md:text-6xl font-bold mb-6">
            {title || (isEditable ? t('defaultTitle') : null)}
          </h1>
        )}

        {(subtitle || isEditable) && (
          <h2 className="text-xl md:text-2xl font-medium mb-6 opacity-90">
            {subtitle || (isEditable ? t('defaultSubtitle') : null)}
          </h2>
        )}

        {content && (
          <div
            className="text-lg mb-8 opacity-80 prose prose-invert max-w-none"
            dangerouslySetInnerHTML={{ __html: content }}
          />
        )}

        {(buttonText || isEditable) && buttonUrl && (
          <Button
            asChild
            size="lg"
            className="bg-white text-gray-900 hover:bg-gray-100"
          >
            <a href={buttonUrl}>
              {buttonText || t('defaultButton')}
            </a>
          </Button>
        )}
      </div>
    </section>
  );
});

HeroBlock.displayName = 'HeroBlock';

export default HeroBlock;
