import React from 'react';
import { BlockProps } from '../BlockRenderer';
import BlockRenderer from '../BlockRenderer';

interface ContainerBlockProps extends BlockProps {
  props: {
    children?: BlockProps[];
    maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
    padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
    backgroundColor?: string;
    className?: string;
  };
}

const ContainerBlock: React.FC<ContainerBlockProps> = ({ props }) => {
  const {
    children = [],
    maxWidth = 'xl',
    padding = 'md',
    backgroundColor,
    className = ''
  } = props;

  const maxWidthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    full: 'max-w-full'
  };

  const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
    xl: 'p-12'
  };

  const containerStyles: React.CSSProperties = {
    ...(backgroundColor && { backgroundColor })
  };

  return (
    <div
      className={`container-block mx-auto ${maxWidthClasses[maxWidth]} ${paddingClasses[padding]} ${className}`.trim()}
      style={containerStyles}
    >
      <BlockRenderer blocks={children} />
    </div>
  );
};

export default ContainerBlock;
