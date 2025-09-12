import React from 'react';

export const BlockSkeleton: React.FC = () => {
  return (
    <div className="animate-pulse p-6 bg-gray-50 rounded-lg">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
      <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
      <div className="h-3 bg-gray-200 rounded w-2/3"></div>
    </div>
  );
};
