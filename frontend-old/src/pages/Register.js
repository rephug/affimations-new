import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
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
  Center,
} from '@chakra-ui/react';
import { FiEye, FiEyeOff, FiMail, FiLock, FiUser, FiGithub } from 'react-icons/fi';
import { useAuth } from '../context/AuthContext';
import Logo from '../components/common/Logo';
import { FaGoogle } from 'react-icons/fa';

const Register = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { signUp, signInWithProvider } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm();

  const password = watch('password', '');

  const onSubmit = async (data) => {
    try {
      setIsSubmitting(true);
      
      const { error } = await signUp(data.email, data.password, {
        data: {
          full_name: data.fullName,
        },
      });
      
      if (error) throw error;
      
      toast({
        title: 'Registration successful',
        description: 'Check your email to confirm your account',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      navigate('/login');
    } catch (error) {
      console.error('Registration error:', error);
      toast({
        title: 'Registration failed',
        description: error.message || 'An error occurred during registration',
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
              <Heading as="h1" size="xl">Create Account</Heading>
              <Text color="gray.600">Sign up for Morning Coffee</Text>
            </VStack>
            
            <VStack as="form" onSubmit={handleSubmit(onSubmit)} spacing={4}>
              <FormControl isInvalid={errors.fullName}>
                <FormLabel>Full Name</FormLabel>
                <InputGroup>
                  <Input
                    placeholder="John Doe"
                    {...register('fullName', {
                      required: 'Full name is required',
                    })}
                    leftElement={<Box pl={3}><FiUser color="gray.300" /></Box>}
                  />
                </InputGroup>
                <FormErrorMessage>{errors.fullName?.message}</FormErrorMessage>
              </FormControl>
            
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
                      minLength: {
                        value: 8,
                        message: 'Password must be at least 8 characters',
                      },
                      pattern: {
                        value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/,
                        message: 'Password must include uppercase, lowercase, number and special character',
                      },
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
              
              <FormControl isInvalid={errors.confirmPassword}>
                <FormLabel>Confirm Password</FormLabel>
                <InputGroup>
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    {...register('confirmPassword', {
                      required: 'Please confirm your password',
                      validate: value => value === password || 'Passwords do not match',
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
                <FormErrorMessage>{errors.confirmPassword?.message}</FormErrorMessage>
              </FormControl>
              
              <Button
                type="submit"
                colorScheme="blue"
                size="lg"
                width="full"
                isLoading={isSubmitting}
                loadingText="Creating account"
                mt={2}
              >
                Create Account
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
                Already have an account?{' '}
                <Link to="/login">
                  <Text as="span" color="blue.600" fontWeight="medium">
                    Sign in
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

export default Register; 