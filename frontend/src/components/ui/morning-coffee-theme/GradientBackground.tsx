import React from 'react';

interface GradientBackgroundProps {
  children: React.ReactNode;
  className?: string;
}

export function GradientBackground({ children, className = '' }: GradientBackgroundProps) {
  return (
    <div className={`bg-coffee-gradient ${className}`.trim()}>
      {children}
    </div>
  );
} 