import React from 'react';

export const GradientHeading = ({ children, className = '', ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h1 
    className={`text-4xl font-bold gradient-heading ${className}`}
    {...props}
  >
    {children}
  </h1>
);

export const CoffeeCard = ({ children, className = '', ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div 
    className={`morning-coffee-card p-6 ${className}`}
    {...props}
  >
    {children}
  </div>
);

export const CoffeeButton = ({ 
  children, 
  className = '', 
  ...props 
}: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
  <button 
    className={`morning-coffee-button ${className}`}
    {...props}
  >
    {children}
  </button>
);

export const CoffeeLink = ({ 
  children, 
  className = '', 
  ...props 
}: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
  <a 
    className={`morning-coffee-button inline-block ${className}`}
    {...props}
  >
    {children}
  </a>
);

export const FeatureCard = ({ 
  icon, 
  title, 
  description, 
  className = '', 
  ...props 
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
} & React.HTMLAttributes<HTMLDivElement>) => (
  <div 
    className={`bg-white rounded-xl p-6 text-center transition-all morning-coffee-card ${className}`}
    {...props}
  >
    <div className="text-4xl mb-4 text-sunrise-orange">{icon}</div>
    <h3 className="text-xl font-semibold mb-3 text-deep-brown">{title}</h3>
    <p className="text-medium-brown">{description}</p>
  </div>
);

export const GradientBackground = ({ 
  children, 
  className = '', 
  ...props 
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div 
    className={`morning-coffee-gradient min-h-screen ${className}`}
    {...props}
  >
    {children}
  </div>
);
