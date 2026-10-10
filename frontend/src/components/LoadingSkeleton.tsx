import React from 'react';

interface LoadingSkeletonProps {
  height?: string;
  count?: number;
  borderRadius?: string;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  height = '40px',
  count = 1,
  borderRadius = 'var(--radius-md)',
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="skeleton" style={{ height, width: '100%', borderRadius }} />
      ))}
    </div>
  );
};
