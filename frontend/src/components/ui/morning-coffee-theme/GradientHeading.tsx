import React from 'react';

interface GradientHeadingProps {
  children: React.ReactNode;
  className?: string;
}

export function GradientHeading({ children, className = '' }: GradientHeadingProps) {
  return (
    <h1 className={`text-4xl font-bold bg-heading-gradient bg-clip-text text-transparent ${className}`.trim()}>
      {children}
    </h1>
  );
} 