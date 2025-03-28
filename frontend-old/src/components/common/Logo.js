// src/components/common/Logo.js
import React from 'react';
import { Box, Text, Flex, Image } from '@chakra-ui/react';
import { Link } from 'react-router-dom';

const Logo = ({ size = 'md', ...rest }) => {
  // Size mappings
  const sizeMap = {
    sm: {
      iconSize: "24px",
      fontSize: "lg",
      spacing: 2
    },
    md: {
      iconSize: "32px",
      fontSize: "xl",
      spacing: 2
    },
    lg: {
      iconSize: "40px",
      fontSize: "2xl",
      spacing: 3
    }
  };

  const { iconSize, fontSize, spacing } = sizeMap[size] || sizeMap.md;

  return (
    <Link to="/">
      <Flex align="center" gap={spacing} {...rest}>
        <Box 
          position="relative"
          w={iconSize} 
          h={iconSize}
          bg="blue.500"
          borderRadius="full"
          overflow="hidden"
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          {/* Coffee cup icon - SVG version */}
          <Box as="svg" width="60%" height="60%" viewBox="0 0 24 24" fill="white">
            <path d="M18.5 8h-1.5v-1.5c0-0.276-0.224-0.5-0.5-0.5h-13c-0.276 0-0.5 0.224-0.5 0.5v10c0 2.481 2.019 4.5 4.5 4.5h5c2.481 0 4.5-2.019 4.5-4.5v-2h1.5c1.93 0 3.5-1.57 3.5-3.5s-1.57-3.5-3.5-3.5zm-3.5 8.5c0 1.93-1.57 3.5-3.5 3.5h-5c-1.93 0-3.5-1.57-3.5-3.5v-9.5h12v9.5zm3.5-5h-1.5v-2.5h1.5c0.827 0 1.5 0.673 1.5 1.5s-0.673 1-1.5 1z" />
          </Box>
        </Box>
        <Text 
          fontWeight="bold" 
          fontSize={fontSize}
          letterSpacing="tight"
          color="blue.600"
        >
          Morning Coffee
        </Text>
      </Flex>
    </Link>
  );
};

export default Logo;