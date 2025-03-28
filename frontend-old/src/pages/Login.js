// src/pages/Login.js
import React, { useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import {
  Box,
  Button,
  Divider,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Heading,
  Input,
  Text,
  VStack,
  HStack,
  Flex,
  useToast,
  InputGroup,
  InputRightElement,
  IconButton,
  Card,
  CardBody,
  Checkbox,
  Center,
} from '@chakra-ui/react';
import { FiEye, FiEyeOff, FiMail, FiLock, FiGithub } from 'react-icons/fi';
import { useAuth } from '../context/AuthContext';
import Logo from '../components/common/Logo';
import { FaGoogle } from 'react-icons/fa';
const Login = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { signIn, signInWithProvider } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  
  // Get the return URL from location state or default to dashboard
  const from = location.state?.from?.pathname || '/dashboard';

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  const onSubmit = async (data) => {
    try {
      setIsSubmitting(true);
      
      const { data: authData, error } = await signIn(data.email, data.password);
      
      if (error) throw error;
      
      // If login successful, store token if remember me is checked
      if (data.rememberMe) {
        localStorage.setItem('supabase.auth.token', authData.session.access_token);
      }
      
      toast({
        title: 'Login successful',
        description: 'Welcome back!',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      // Redirect to original destination or dashboard
      navigate(from, { replace: true });
    } catch (error) {
      console.error('Login error:', error);
      toast({
        title: 'Login failed',
        description: error.message || 'An error occurred during login',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSocialLogin = async (provider) => {
    try {
      const { error } = await signInWithProvider(provider);
      
      if (error) throw error;
      
      // The redirect will happen automatically, but we'll show a toast just in case
      toast({
        title: 'Redirecting...',
        description: `Signing in with ${provider}`,
        status: 'info',
        duration: 2000,
        isClosable: true,
      });
    } catch (error) {
      console.error(`${provider} login error:`, error);
      toast({
        title: 'Login failed',
        description: error.message || `An error occurred during ${provider} login`,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const togglePasswordVisibility = () => setShowPassword(!showPassword);

  return (
    <Flex minH="100vh" align="center" justify="center" bg="gray.50">
      <Card maxW="md" w="full" boxShadow="lg">
        <CardBody p={8}>
          <VStack spacing={6} align="stretch">
            <Center mb={2}>
              <Logo size="lg" />
            </Center>
            
            <VStack spacing={2} align="center">
              <Heading as="h1" size="xl">Morning Coffee</Heading>
              <Text color="gray.600">Sign in to your account</Text>
            </VStack>
            
            <VStack as="form" onSubmit={handleSubmit(onSubmit)} spacing={4}>
              <FormControl isInvalid={errors.email}>
                <FormLabel>Email</FormLabel>
                <InputGroup>
                  <Input
                    type="email"
                    placeholder="you@example.com"
                    {...register('email', {
                      required: 'Email is required',
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: 'Invalid email address',
                      },
                    })}
                    leftElement={<Box pl={3}><FiMail color="gray.300" /></Box>}
                  />
                </InputGroup>
                <FormErrorMessage>{errors.email?.message}</FormErrorMessage>
              </FormControl>
              
              <FormControl isInvalid={errors.password}>
                <FormLabel>Password</FormLabel>
                <InputGroup>
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    {...register('password', {
                      required: 'Password is required',
                    })}
                    leftElement={<Box pl={3}><FiLock color="gray.300" /></Box>}
                  />
                  <InputRightElement>
                    <IconButton
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      icon={showPassword ? <FiEyeOff /> : <FiEye />}
                      variant="ghost"
                      onClick={togglePasswordVisibility}
                      tabIndex="-1"
                    />
                  </InputRightElement>
                </InputGroup>
                <FormErrorMessage>{errors.password?.message}</FormErrorMessage>
              </FormControl>
              
              <HStack justify="space-between" w="full">
                <Checkbox
                  {...register('rememberMe')}
                  colorScheme="blue"
                >
                  Remember me
                </Checkbox>
                <Link to="/forgot-password">
                  <Text color="blue.600" fontSize="sm" fontWeight="medium">
                    Forgot password?
                  </Text>
                </Link>
              </HStack>
              
              <Button
                type="submit"
                colorScheme="blue"
                size="lg"
                width="full"
                isLoading={isSubmitting}
                loadingText="Signing in"
                mt={2}
              >
                Sign in
              </Button>
            </VStack>
            
            <Divider my={4} />
            
            <VStack spacing={3}>
              <Text align="center" fontSize="sm" color="gray.600">
                Or continue with
              </Text>
              
              <HStack spacing={3} w="full">
                <Button
                  w="full"
                  variant="outline"
                  leftIcon={<FaGoogle />}
                  onClick={() => handleSocialLogin('google')}
                >
                  Google
                </Button>
                <Button
                  w="full"
                  variant="outline"
                  leftIcon={<FiGithub />}
                  onClick={() => handleSocialLogin('github')}
                >
                  GitHub
                </Button>
              </HStack>
            </VStack>
            
            <Box pt={4} textAlign="center">
              <Text color="gray.600">
                Don't have an account?{' '}
                <Link to="/register">
                  <Text as="span" color="blue.600" fontWeight="medium">
                    Sign up
                  </Text>
                </Link>
              </Text>
            </Box>
          </VStack>
        </CardBody>
      </Card>
    </Flex>
  );
};

export default Login;
