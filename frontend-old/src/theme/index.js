// src/theme/index.js
import { extendTheme } from '@chakra-ui/react';

// Theme configuration
const config = {
  initialColorMode: 'light',
  useSystemColorMode: false,
};

// Brand colors
const colors = {
  brand: {
    50: '#e6f7ff',
    100: '#b3e0ff',
    200: '#80c9ff',
    300: '#4db2ff',
    400: '#1a9bff',
    500: '#0084e6',
    600: '#006bb4',
    700: '#005282',
    800: '#003a50',
    900: '#00121e',
  },
};

// Font configuration
const fonts = {
  heading: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif',
  body: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif',
};

// Create the theme
const theme = extendTheme({
  config,
  colors,
  fonts,
  components: {
    Button: {
      baseStyle: {
        fontWeight: 'medium',
        borderRadius: 'md',
      },
    },
    Card: {
      baseStyle: {
        container: {
          borderRadius: 'md',
          boxShadow: 'md',
        },
      },
    },
  },
});

export default theme;