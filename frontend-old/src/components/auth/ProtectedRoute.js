import React, { useState, useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Center, Spinner } from '@chakra-ui/react';
import { useAuth } from '../../context/AuthContext';

const ProtectedRoute = ({ children }) => {
  const [isLoading, setIsLoading] = useState(true);
  const { user, isAuthenticated } = useAuth();
  const location = useLocation();

  useEffect(() => {
    // Check if authentication state is loaded
    const checkAuth = async () => {
      // Wait a short time to ensure auth state is loaded
      // This prevents flickering for quick auth checks
      setTimeout(() => {
        setIsLoading(false);
      }, 500);
    };

    checkAuth();
  }, [isAuthenticated]);

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner
          thickness="4px"
          speed="0.65s"
          emptyColor="gray.200"
          color="blue.500"
          size="xl"
        />
      </Center>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login page, but save the location they were trying to access
    // so we can redirect back after login
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

export default ProtectedRoute; 