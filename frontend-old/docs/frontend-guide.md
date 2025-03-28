# Full-Featured Frontend with Supabase Authentication

This document outlines the design and implementation of a comprehensive frontend for the Morning Coffee application with Supabase authentication.

## Architecture Overview

The full-featured frontend will be built using:

- **React** for the UI framework
- **Supabase** for authentication and database
- **Chakra UI** for component styling
- **React Router** for navigation
- **React Query** for data fetching and caching
- **React Hook Form** for form management
- **Zustand** for state management

## Supabase Integration

Supabase will provide:

1. **Authentication**: Email/password, social login, and MFA
2. **User Management**: User profiles, roles, and permissions
3. **Database**: Store configuration, scheduling, and user preferences
4. **Storage**: Store audio samples and call recordings

## Project Structure

```
frontend-app/
├── public/
├── src/
│   ├── assets/            # Static assets
│   ├── components/        # Reusable UI components
│   │   ├── auth/          # Authentication components
│   │   ├── layout/        # Layout components
│   │   ├── common/        # Common UI components
│   │   ├── dashboard/     # Dashboard components
│   │   ├── calls/         # Call-related components
│   │   ├── settings/      # Settings components
│   │   └── users/         # User management components
│   │
│   ├── hooks/             # Custom hooks
│   ├── pages/             # Page components
│   ├── services/          # API and service integrations
│   │   ├── api.js         # API client
│   │   ├── supabase.js    # Supabase client
│   │   └── tts.js         # TTS service client
│   │
│   ├── store/             # State management
│   ├── theme/             # Theme configuration
│   ├── utils/             # Utility functions
│   ├── App.js             # Main App component
│   ├── index.js           # Application entry point
│   └── routes.js          # Route definitions
│
├── .env                   # Environment variables
├── .env.development       # Development environment variables
├── package.json
└── README.md
```

## Supabase Database Schema

### Tables

1. **Users** (managed by Supabase Auth)
   - id: UUID (primary key)
   - email: String
   - created_at: Timestamp
   - updated_at: Timestamp

2. **Profiles**
   - id: UUID (references users.id)
   - first_name: String
   - last_name: String
   - phone_number: String
   - timezone: String
   - preferred_voice: String
   - notification_preferences: JSON

3. **Affirmations**
   - id: UUID
   - text: String
   - category: String
   - created_by: UUID (references users.id)
   - is_custom: Boolean
   - is_public: Boolean

4. **Scheduled_Calls**
   - id: UUID
   - user_id: UUID (references users.id)
   - schedule_type: String (daily, weekdays, custom)
   - schedule_config: JSON
   - time: Time
   - timezone: String
   - enabled: Boolean
   - affirmation_category: String
   - created_at: Timestamp
   - updated_at: Timestamp

5. **Call_History**
   - id: UUID
   - user_id: UUID (references users.id)
   - call_control_id: String
   - started_at: Timestamp
   - ended_at: Timestamp
   - duration: Integer
   - status: String
   - affirmation: String
   - transcription_count: Integer
   - recording_url: String (optional)

6. **Transcriptions**
   - id: UUID
   - call_id: UUID (references call_history.id)
   - transcription_job_id: String
   - text: String
   - status: String
   - created_at: Timestamp
   - completed_at: Timestamp

7. **Organizations** (for team features)
   - id: UUID
   - name: String
   - owner_id: UUID (references users.id)
   - created_at: Timestamp

8. **Organization_Members**
   - organization_id: UUID (references organizations.id)
   - user_id: UUID (references users.id)
   - role: String (owner, admin, member)
   - joined_at: Timestamp

## Authentication Flow

1. **User Registration**
   - Email/password registration
   - Social login options (Google, Microsoft)
   - Email verification

2. **User Login**
   - Email/password login
   - Social login
   - Optional MFA
   - Remember me functionality
   - Password reset

3. **Authorization**
   - Role-based access control
   - Permission checking
   - Protected routes

## Key Features

### User Dashboard

- Overview of upcoming scheduled calls
- Recent call history
- Quick actions (schedule call, test TTS)
- Call statistics

### Profile Management

- Personal information
- Phone number verification
- Timezone settings
- Voice preferences
- Notification preferences

### Affirmation Management

- Browse affirmation categories
- Create custom affirmations
- Share affirmations (for team accounts)
- Import/export affirmations

### Call Scheduling

- Set up recurring calls
- Choose affirmation categories for each schedule
- Enable/disable schedules
- One-time calls

### Call History and Analytics

- View past calls
- Listen to call recordings (if enabled)
- View transcriptions
- Analytics and trends

### Admin Features

- User management (for organization admins)
- System monitoring
- Usage statistics

### Team Features

- Create and manage organizations
- Invite team members
- Shared affirmations
- Team analytics

## Implementation Details

### Supabase Authentication Setup

1. Configure Supabase project and get API keys
2. Set up authentication providers (email, social)
3. Configure email templates
4. Set up row-level security policies

```javascript
// src/services/supabase.js
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Auth helpers
export const signUp = async (email, password) => {
  const { user, error } = await supabase.auth.signUp({ email, password });
  return { user, error };
};

export const signIn = async (email, password) => {
  const { user, error } = await supabase.auth.signInWithPassword({ email, password });
  return { user, error };
};

export const signOut = async () => {
  const { error } = await supabase.auth.signOut();
  return { error };
};

export const getCurrentUser = async () => {
  const { data: { user } } = await supabase.auth.getUser();
  return user;
};
```

### Authentication Components

**Sign Up Form**

```jsx
import React from 'react';
import { useForm } from 'react-hook-form';
import { 
  FormControl, 
  FormLabel, 
  Input, 
  Button, 
  FormErrorMessage,
  VStack,
  Heading,
  Text,
  useToast
} from '@chakra-ui/react';
import { signUp } from '../services/supabase';

const SignUpForm = () => {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm();
  const toast = useToast();
  
  const onSubmit = async (data) => {
    try {
      const { user, error } = await signUp(data.email, data.password);
      
      if (error) throw error;
      
      toast({
        title: 'Account created.',
        description: "We've sent you an email to verify your account.",
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Error creating account.',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };
  
  return (
    <VStack spacing={6} as="form" onSubmit={handleSubmit(onSubmit)}>
      <Heading size="lg">Create an account</Heading>
      
      <FormControl isInvalid={errors.email}>
        <FormLabel>Email</FormLabel>
        <Input
          type="email"
          {...register('email', {
            required: 'Email is required',
            pattern: {
              value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
              message: 'Invalid email address',
            },
          })}
        />
        <FormErrorMessage>{errors.email?.message}</FormErrorMessage>
      </FormControl>
      
      <FormControl isInvalid={errors.password}>
        <FormLabel>Password</FormLabel>
        <Input
          type="password"
          {...register('password', {
            required: 'Password is required',
            minLength: {
              value: 8,
              message: 'Password must be at least 8 characters',
            },
          })}
        />
        <FormErrorMessage>{errors.password?.message}</FormErrorMessage>
      </FormControl>
      
      <Button
        type="submit"
        colorScheme="blue"
        width="full"
        isLoading={isSubmitting}
      >
        Sign Up
      </Button>
      
      <Text>
        Already have an account? <Button variant="link" colorScheme="blue">Sign In</Button>
      </Text>
    </VStack>
  );
};

export default SignUpForm;
```

### Protected Routes

```jsx
// src/components/auth/ProtectedRoute.js
import { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spinner, Center } from '@chakra-ui/react';
import { supabase } from '../../services/supabase';

const ProtectedRoute = ({ children }) => {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const location = useLocation();
  
  useEffect(() => {
    const checkAuth = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user);
      setLoading(false);
    };
    
    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user || null);
      setLoading(false);
    });
    
    checkAuth();
    
    return () => {
      if (authListener?.subscription) {
        authListener.subscription.unsubscribe();
      }
    };
  }, []);
  
  if (loading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  return children;
};

export default ProtectedRoute;
```

### User Profile Management

```jsx
// src/pages/Profile.js
import { useEffect, useState } from 'react';
import { 
  Box, 
  VStack, 
  Heading, 
  FormControl, 
  FormLabel, 
  Input, 
  Button, 
  useToast,
  Select,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Card,
  CardBody
} from '@chakra-ui/react';
import { useForm } from 'react-hook-form';
import { supabase } from '../services/supabase';

const Profile = () => {
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm();
  const toast = useToast();
  
  useEffect(() => {
    const fetchProfile = async () => {
      setLoading(true);
      
      try {
        const { data: { user } } = await supabase.auth.getUser();
        
        if (!user) throw new Error('User not found');
        
        // Get the user's profile from the profiles table
        const { data, error } = await supabase
          .from('profiles')
          .select('*')
          .eq('id', user.id)
          .single();
          
        if (error) throw error;
        
        setProfile(data);
        reset(data); // Pre-fill the form
      } catch (error) {
        console.error('Error fetching profile:', error);
        toast({
          title: 'Error fetching profile',
          description: error.message,
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      } finally {
        setLoading(false);
      }
    };
    
    fetchProfile();
  }, [reset, toast]);
  
  const updateProfile = async (data) => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      
      if (!user) throw new Error('User not found');
      
      // Update the profile
      const { error } = await supabase
        .from('profiles')
        .update({
          first_name: data.first_name,
          last_name: data.last_name,
          phone_number: data.phone_number,
          timezone: data.timezone,
          preferred_voice: data.preferred_voice,
        })
        .eq('id', user.id);
        
      if (error) throw error;
      
      toast({
        title: 'Profile updated',
        description: 'Your profile has been updated successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Error updating profile:', error);
      toast({
        title: 'Error updating profile',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };
  
  return (
    <Box p={5}>
      <Heading mb={6}>Profile Settings</Heading>
      
      <Tabs>
        <TabList>
          <Tab>Personal Information</Tab>
          <Tab>Notification Preferences</Tab>
          <Tab>Voice Settings</Tab>
          <Tab>Security</Tab>
        </TabList>
        
        <TabPanels>
          <TabPanel>
            <Card>
              <CardBody>
                <VStack spacing={6} as="form" onSubmit={handleSubmit(updateProfile)}>
                  <FormControl isInvalid={errors.first_name}>
                    <FormLabel>First Name</FormLabel>
                    <Input
                      {...register('first_name', {
                        required: 'First name is required',
                      })}
                    />
                  </FormControl>
                  
                  <FormControl isInvalid={errors.last_name}>
                    <FormLabel>Last Name</FormLabel>
                    <Input
                      {...register('last_name', {
                        required: 'Last name is required',
                      })}
                    />
                  </FormControl>
                  
                  <FormControl isInvalid={errors.phone_number}>
                    <FormLabel>Phone Number</FormLabel>
                    <Input
                      {...register('phone_number', {
                        required: 'Phone number is required',
                        pattern: {
                          value: /^\+[1-9]\d{1,14}$/,
                          message: 'Invalid phone number format. Use E.164 format (e.g., +15551234567)',
                        },
                      })}
                      placeholder="+15551234567"
                    />
                  </FormControl>
                  
                  <FormControl isInvalid={errors.timezone}>
                    <FormLabel>Timezone</FormLabel>
                    <Select
                      {...register('timezone', {
                        required: 'Timezone is required',
                      })}
                    >
                      <option value="America/New_York">Eastern Time (ET)</option>
                      <option value="America/Chicago">Central Time (CT)</option>
                      <option value="America/Denver">Mountain Time (MT)</option>
                      <option value="America/Los_Angeles">Pacific Time (PT)</option>
                      <option value="Europe/London">London (GMT)</option>
                      <option value="Europe/Paris">Paris (CET)</option>
                      <option value="Asia/Tokyo">Tokyo (JST)</option>
                    </Select>
                  </FormControl>
                  
                  <Button
                    type="submit"
                    colorScheme="blue"
                    isLoading={isSubmitting}
                    width="200px"
                  >
                    Save Changes
                  </Button>
                </VStack>
              </CardBody>
            </Card>
          </TabPanel>
          
          {/* Additional tabs would be implemented here */}
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default Profile;
```

## Deployment

The full-featured frontend can be deployed alongside the existing backend using Docker. Here's how the updated docker-compose configuration would look:

```yaml
# Frontend with Supabase Auth
frontend-app:
  build:
    context: ./frontend-app
    dockerfile: Dockerfile
  container_name: morning-coffee-frontend-app
  restart: unless-stopped
  depends_on:
    - app
    - spark-tts
  ports:
    - "80:80"
  environment:
    - REACT_APP_API_URL=http://app:5000
    - REACT_APP_SUPABASE_URL=${SUPABASE_URL}
    - REACT_APP_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
  networks:
    - morning-coffee-network
```

## Responsive Design

The UI will be fully responsive, working well on:
- Desktop computers
- Tablets
- Mobile phones

This is achieved through:
- Chakra UI's responsive design system
- Custom responsive components
- Adaptive layouts

## Future Enhancements

1. **Advanced Analytics**: Detailed analytics on call performance, user engagement, and affirmation effectiveness.
2. **Integration with Productivity Tools**: Connect with calendar apps, task managers, and other productivity tools.
3. **Multi-language Support**: Expand the application to support multiple languages for both interface and voice.
4. **Voice Customization**: Allow users to clone their own voice or select from a wide variety of voice options.
5. **Mobile App**: Develop native mobile apps for iOS and Android.
