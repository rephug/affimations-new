import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Container,
  Divider,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Heading,
  Input,
  Text,
  VStack,
  HStack,
  Grid,
  GridItem,
  useToast,
  InputGroup,
  InputRightElement,
  IconButton,
  Card,
  CardBody,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Flex,
  Badge,
  Avatar,
} from '@chakra-ui/react';
import { FiEye, FiEyeOff, FiMail, FiLock, FiUser } from 'react-icons/fi';
import { useForm } from 'react-hook-form';
import { useAuth } from '../context/AuthContext';
import Layout from '../components/common/Layout';

const Profile = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [isProfileSubmitting, setIsProfileSubmitting] = useState(false);
  const [isPasswordSubmitting, setIsPasswordSubmitting] = useState(false);
  const { user, updateUserProfile, updateUserPassword } = useAuth();
  const toast = useToast();

  // Profile form
  const {
    register: registerProfile,
    handleSubmit: handleProfileSubmit,
    formState: { errors: profileErrors },
    reset: resetProfile,
  } = useForm();

  // Password form
  const {
    register: registerPassword,
    handleSubmit: handlePasswordSubmit,
    formState: { errors: passwordErrors },
    watch,
    reset: resetPassword,
  } = useForm();

  const password = watch('newPassword', '');

  // Set initial form values when user data is available
  useEffect(() => {
    if (user) {
      resetProfile({
        fullName: user.user_metadata?.full_name || '',
        email: user.email,
      });
    }
  }, [user, resetProfile]);

  const onProfileSubmit = async (data) => {
    try {
      setIsProfileSubmitting(true);
      
      const { error } = await updateUserProfile({
        email: data.email,
        data: { full_name: data.fullName },
      });
      
      if (error) throw error;
      
      toast({
        title: 'Profile updated',
        description: 'Your profile has been successfully updated',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Profile update error:', error);
      toast({
        title: 'Update failed',
        description: error.message || 'An error occurred while updating your profile',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsProfileSubmitting(false);
    }
  };

  const onPasswordSubmit = async (data) => {
    try {
      setIsPasswordSubmitting(true);
      
      const { error } = await updateUserPassword(data.newPassword);
      
      if (error) throw error;
      
      toast({
        title: 'Password updated',
        description: 'Your password has been successfully changed',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      // Reset password form
      resetPassword();
    } catch (error) {
      console.error('Password change error:', error);
      toast({
        title: 'Password change failed',
        description: error.message || 'An error occurred while changing your password',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsPasswordSubmitting(false);
    }
  };

  const togglePasswordVisibility = () => setShowPassword(!showPassword);

  if (!user) {
    return (
      <Layout>
        <Container maxW="container.lg" py={8}>
          <Text>Loading user profile...</Text>
        </Container>
      </Layout>
    );
  }

  return (
    <Layout>
      <Container maxW="container.lg" py={8}>
        <Grid templateColumns={{ base: "1fr", md: "1fr 3fr" }} gap={8}>
          {/* Profile summary sidebar */}
          <GridItem>
            <Card>
              <CardBody>
                <VStack spacing={4} align="center">
                  <Avatar 
                    size="2xl" 
                    name={user.user_metadata?.full_name || user.email} 
                    src={user.user_metadata?.avatar_url}
                  />
                  
                  <Heading size="md">{user.user_metadata?.full_name || 'User'}</Heading>
                  <Text color="gray.600">{user.email}</Text>
                  
                  <Badge colorScheme="green" px={2} py={1} borderRadius="md">
                    Active Account
                  </Badge>
                  
                  <Text fontSize="sm" color="gray.500">
                    Member since {new Date(user.created_at).toLocaleDateString()}
                  </Text>
                </VStack>
              </CardBody>
            </Card>
          </GridItem>
          
          {/* Main content area */}
          <GridItem>
            <Card>
              <CardBody>
                <Tabs variant="soft-rounded" colorScheme="blue">
                  <TabList mb={4}>
                    <Tab>Profile</Tab>
                    <Tab>Security</Tab>
                    <Tab>Subscription</Tab>
                  </TabList>
                  
                  <TabPanels>
                    {/* Profile Tab */}
                    <TabPanel px={0}>
                      <VStack spacing={6} align="start" as="form" onSubmit={handleProfileSubmit(onProfileSubmit)}>
                        <Heading size="md">Personal Information</Heading>
                        
                        <FormControl isInvalid={profileErrors.fullName}>
                          <FormLabel>Full Name</FormLabel>
                          <InputGroup>
                            <Input
                              placeholder="John Doe"
                              {...registerProfile('fullName', {
                                required: 'Full name is required',
                              })}
                              leftElement={<Box pl={3}><FiUser color="gray.300" /></Box>}
                            />
                          </InputGroup>
                          <FormErrorMessage>{profileErrors.fullName?.message}</FormErrorMessage>
                        </FormControl>
                      
                        <FormControl isInvalid={profileErrors.email}>
                          <FormLabel>Email</FormLabel>
                          <InputGroup>
                            <Input
                              type="email"
                              placeholder="you@example.com"
                              {...registerProfile('email', {
                                required: 'Email is required',
                                pattern: {
                                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                                  message: 'Invalid email address',
                                },
                              })}
                              leftElement={<Box pl={3}><FiMail color="gray.300" /></Box>}
                            />
                          </InputGroup>
                          <FormErrorMessage>{profileErrors.email?.message}</FormErrorMessage>
                        </FormControl>
                        
                        <Button
                          type="submit"
                          colorScheme="blue"
                          isLoading={isProfileSubmitting}
                          loadingText="Saving"
                        >
                          Save Changes
                        </Button>
                      </VStack>
                    </TabPanel>
                    
                    {/* Security Tab */}
                    <TabPanel px={0}>
                      <VStack spacing={6} align="start" as="form" onSubmit={handlePasswordSubmit(onPasswordSubmit)}>
                        <Heading size="md">Change Password</Heading>
                        
                        <FormControl isInvalid={passwordErrors.currentPassword}>
                          <FormLabel>Current Password</FormLabel>
                          <InputGroup>
                            <Input
                              type={showPassword ? 'text' : 'password'}
                              placeholder="••••••••"
                              {...registerPassword('currentPassword', {
                                required: 'Current password is required',
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
                          <FormErrorMessage>{passwordErrors.currentPassword?.message}</FormErrorMessage>
                        </FormControl>
                        
                        <FormControl isInvalid={passwordErrors.newPassword}>
                          <FormLabel>New Password</FormLabel>
                          <InputGroup>
                            <Input
                              type={showPassword ? 'text' : 'password'}
                              placeholder="••••••••"
                              {...registerPassword('newPassword', {
                                required: 'New password is required',
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
                          <FormErrorMessage>{passwordErrors.newPassword?.message}</FormErrorMessage>
                        </FormControl>
                        
                        <FormControl isInvalid={passwordErrors.confirmPassword}>
                          <FormLabel>Confirm New Password</FormLabel>
                          <InputGroup>
                            <Input
                              type={showPassword ? 'text' : 'password'}
                              placeholder="••••••••"
                              {...registerPassword('confirmPassword', {
                                required: 'Please confirm your new password',
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
                          <FormErrorMessage>{passwordErrors.confirmPassword?.message}</FormErrorMessage>
                        </FormControl>
                        
                        <Button
                          type="submit"
                          colorScheme="blue"
                          isLoading={isPasswordSubmitting}
                          loadingText="Updating"
                        >
                          Change Password
                        </Button>
                      </VStack>
                    </TabPanel>
                    
                    {/* Subscription Tab */}
                    <TabPanel px={0}>
                      <VStack spacing={6} align="start">
                        <Heading size="md">Subscription Details</Heading>
                        
                        <Card w="full" variant="outline">
                          <CardBody>
                            <VStack spacing={4} align="start">
                              <HStack justify="space-between" w="full">
                                <Text fontWeight="bold">Current Plan</Text>
                                <Badge colorScheme="blue" fontSize="md" px={2} py={1}>
                                  Free Trial
                                </Badge>
                              </HStack>
                              
                              <Divider />
                              
                              <HStack justify="space-between" w="full">
                                <Text>Status</Text>
                                <Text>Active</Text>
                              </HStack>
                              
                              <HStack justify="space-between" w="full">
                                <Text>Trial Ends</Text>
                                <Text>In 14 days</Text>
                              </HStack>
                              
                              <HStack justify="space-between" w="full">
                                <Text>Daily SMS</Text>
                                <Text>1 message/day</Text>
                              </HStack>
                              
                              <HStack justify="space-between" w="full">
                                <Text>Daily Calls</Text>
                                <Text>1 call/day</Text>
                              </HStack>
                              
                              <Button colorScheme="blue" size="md" alignSelf="center" w="full">
                                Upgrade to Premium
                              </Button>
                            </VStack>
                          </CardBody>
                        </Card>
                      </VStack>
                    </TabPanel>
                  </TabPanels>
                </Tabs>
              </CardBody>
            </Card>
          </GridItem>
        </Grid>
      </Container>
    </Layout>
  );
};

export default Profile; 