import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import {
  Box,
  Button,
  Flex,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Heading,
  Input,
  Text,
  VStack,
  Card,
  CardBody,
  useToast,
  InputGroup,
  Center,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from '@chakra-ui/react';
import { FiMail, FiArrowLeft } from 'react-icons/fi';
import { useAuth } from '../context/AuthContext';
import Logo from '../components/common/Logo';

const ForgotPassword = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const { resetPassword } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  const onSubmit = async (data) => {
    try {
      setIsSubmitting(true);
      
      const { error } = await resetPassword(data.email);
      
      if (error) throw error;
      
      setEmailSent(true);
      
      toast({
        title: 'Reset link sent',
        description: 'Check your email for a password reset link',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Password reset error:', error);
      toast({
        title: 'Reset failed',
        description: error.message || 'An error occurred during password reset',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Flex minH="100vh" align="center" justify="center" bg="gray.50">
      <Card maxW="md" w="full" boxShadow="lg">
        <CardBody p={8}>
          <VStack spacing={6} align="stretch">
            <Center mb={2}>
              <Logo size="lg" />
            </Center>
            
            <VStack spacing={2} align="center">
              <Heading as="h1" size="xl">Reset Password</Heading>
              <Text color="gray.600">Enter your email to receive a reset link</Text>
            </VStack>
            
            {emailSent ? (
              <Alert
                status="success"
                variant="subtle"
                flexDirection="column"
                alignItems="center"
                justifyContent="center"
                textAlign="center"
                borderRadius="md"
                py={6}
              >
                <AlertIcon boxSize="40px" mr={0} />
                <AlertTitle mt={4} mb={2} fontSize="lg">
                  Reset link sent!
                </AlertTitle>
                <AlertDescription maxWidth="sm">
                  We've sent a password reset link to your email address.
                  Please check your inbox and follow the instructions.
                </AlertDescription>
                <Button 
                  mt={6} 
                  colorScheme="blue" 
                  onClick={() => navigate('/login')}
                >
                  Return to Login
                </Button>
              </Alert>
            ) : (
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
                
                <Button
                  type="submit"
                  colorScheme="blue"
                  size="lg"
                  width="full"
                  isLoading={isSubmitting}
                  loadingText="Sending"
                  mt={2}
                >
                  Send Reset Link
                </Button>
              </VStack>
            )}
            
            <Box pt={4} textAlign="center">
              <Link to="/login">
                <Button variant="link" leftIcon={<FiArrowLeft />} colorScheme="blue">
                  Back to Login
                </Button>
              </Link>
            </Box>
          </VStack>
        </CardBody>
      </Card>
    </Flex>
  );
};

export default ForgotPassword; 