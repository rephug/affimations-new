#!/bin/bash

set -e

echo "===== Updating Color Scheme Across Morning Coffee Frontend ====="

# Update the globals.css file
echo "Updating globals.css with new color scheme..."
cat > /home/adminrob/projects/affimations/frontend/src/styles/globals.css << 'EOL'
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Morning Coffee Color Scheme */
    --deep-brown: 22 52% 16%;      /* #3B2416 - rich coffee beans */
    --medium-brown: 23 35% 38%;    /* #825B3F - warm and inviting */
    --coffee: 23 30% 48%;          /* #A27254 - medium coffee tone */
    --caramel: 24 33% 65%;         /* #C89F82 - lighter coffee with cream */
    --cream: 35 63% 91%;           /* #F4E4CF - soft background color */
    --sunrise-orange: 24 100% 63%; /* #FF8C42 - energetic accent color */
    --warm-yellow: 43 100% 70%;    /* #FFD166 - reminiscent of morning sun */
    --morning-blue: 200 63% 67%;   /* #7BBCDE - optional sky-like accent */

    /* Map to Tailwind CSS variables */
    --background: var(--cream);
    --foreground: var(--deep-brown);

    --card: 0 0% 100%;
    --card-foreground: var(--deep-brown);

    --popover: 0 0% 100%;
    --popover-foreground: var(--deep-brown);

    --primary: var(--sunrise-orange);
    --primary-foreground: 0 0% 100%;

    --secondary: var(--medium-brown);
    --secondary-foreground: 0 0% 100%;

    --accent: var(--warm-yellow);
    --accent-foreground: var(--deep-brown);

    --muted: var(--caramel);
    --muted-foreground: var(--medium-brown);

    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;

    --border: var(--caramel);
    --input: var(--cream);
    --ring: var(--sunrise-orange);

    --radius: 0.5rem;
  }

  .dark {
    --background: var(--deep-brown);
    --foreground: var(--cream);

    --card: var(--medium-brown);
    --card-foreground: var(--cream);

    --popover: var(--deep-brown);
    --popover-foreground: var(--cream);

    --primary: var(--sunrise-orange);
    --primary-foreground: var(--deep-brown);

    --secondary: var(--caramel);
    --secondary-foreground: var(--deep-brown);

    --accent: var(--warm-yellow);
    --accent-foreground: var(--deep-brown);

    --muted: var(--medium-brown);
    --muted-foreground: var(--caramel);

    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 100%;

    --border: var(--medium-brown);
    --input: var(--medium-brown);
    --ring: var(--sunrise-orange);
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
    font-feature-settings: "rlig" 1, "calt" 1;
  }
}

/* Custom Animation Classes */
.animate-fade-in {
  animation: fadeIn 0.5s ease-in-out forwards;
}

.animate-slide-up {
  animation: slideUp 0.5s ease-in-out forwards;
}

.animate-slide-in-right {
  animation: slideInRight 0.5s ease-in-out forwards;
}

.animate-pulse-subtle {
  animation: pulseSubtle 2s infinite;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes slideInRight {
  from {
    transform: translateX(20px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes pulseSubtle {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

/* Custom styles for Morning Coffee */
.morning-coffee-gradient {
  background: linear-gradient(135deg, #F4E4CF 0%, #C89F82 100%);
}

.morning-coffee-card {
  background: white;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(59, 36, 22, 0.1);
}

.morning-coffee-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 15px 35px rgba(59, 36, 22, 0.15);
  transition: all 0.3s ease;
}

.morning-coffee-button {
  background: #FF8C42;
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 30px;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 5px 15px rgba(255, 140, 66, 0.3);
}

.morning-coffee-button:hover {
  background: #3B2416;
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(59, 36, 22, 0.3);
}

.gradient-heading {
  background: linear-gradient(to right, #3B2416, #FF8C42);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
EOL

# Update the tailwind.config.js file
echo "Updating tailwind.config.js with new color scheme..."
cat > /home/adminrob/projects/affimations/frontend/tailwind.config.js << 'EOL'
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'deep-brown': '#3B2416',
        'medium-brown': '#825B3F',
        'coffee': '#A27254',
        'caramel': '#C89F82',
        'cream': '#F4E4CF',
        'sunrise-orange': '#FF8C42',
        'warm-yellow': '#FFD166',
        'morning-blue': '#7BBCDE',
        
        primary: {
          DEFAULT: '#FF8C42',
          50: '#fff8f2',
          100: '#fff0e5',
          200: '#ffddc2',
          300: '#ffc499',
          400: '#ff9e4d',
          500: '#FF8C42',
          600: '#ff6b17',
          700: '#e95300',
          800: '#bf4300',
          900: '#9c3800',
          950: '#571d00',
        },
        secondary: {
          DEFAULT: '#825B3F',
          50: '#f8f5f3',
          100: '#f0ebe6',
          200: '#e3d7cc',
          300: '#d2bda9',
          400: '#bc9c83',
          500: '#a58265',
          600: '#825B3F',
          700: '#6e4c34',
          800: '#5d402f',
          900: '#4f392a',
          950: '#2e1f16',
        },
        accent: {
          DEFAULT: '#FFD166',
          50: '#fffcf0',
          100: '#fff8dc',
          200: '#ffefb0',
          300: '#ffe57d',
          400: '#ffda47',
          500: '#FFD166',
          600: '#fcb705',
          700: '#d39502',
          800: '#a97509',
          900: '#8b5d0f',
          950: '#4b3100',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'coffee-sm': '0 5px 15px rgba(255, 140, 66, 0.3)',
        'coffee': '0 10px 30px rgba(59, 36, 22, 0.1)',
        'coffee-lg': '0 15px 35px rgba(59, 36, 22, 0.15)',
      },
      backgroundImage: {
        'coffee-gradient': 'linear-gradient(135deg, #F4E4CF 0%, #C89F82 100%)',
        'heading-gradient': 'linear-gradient(to right, #3B2416, #FF8C42)',
      },
    },
  },
  plugins: [],
};
EOL

# Create a customized theme component for easy use
echo "Creating theme component for consistent styling..."
mkdir -p /home/adminrob/projects/affimations/frontend/src/components/ui
cat > /home/adminrob/projects/affimations/frontend/src/components/ui/morning-coffee-theme.tsx << 'EOL'
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
EOL

# Rebuild the Next.js application with the new color scheme
echo "Rebuilding Next.js application with new color scheme..."
cd /home/adminrob/projects/affimations/frontend
npm run build

# Update static files
echo "Updating static files with new styles..."
cp -R .next/static/* /var/www/morning-coffee/static/
mkdir -p /var/www/morning-coffee/static/_next/static
cp -R .next/static/* /var/www/morning-coffee/static/_next/static/

# Restart the Next.js application
echo "Restarting Next.js application with new color scheme..."
pm2 restart morning-coffee-frontend || pm2 start npm --name "morning-coffee-frontend" -- start

echo "===== Color scheme update complete! ====="
echo "The Next.js application should now use the Morning Coffee color scheme"
echo "You may need to clear your browser cache to see the changes" 