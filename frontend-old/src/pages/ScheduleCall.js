// src/pages/ScheduleCall.js
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  Divider,
  Flex,
  FormControl,
  FormLabel,
  FormErrorMessage,
  FormHelperText,
  Grid,
  GridItem,
  Heading,
  Input,
  Select,
  Stack,
  Switch,
  Text,
  VStack,
  HStack,
  useToast,
  Radio,
  RadioGroup,
  Checkbox,
  CheckboxGroup,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Tooltip,
  Icon,
  Badge,
  useColorModeValue,
} from '@chakra-ui/react';
import { useForm, Controller } from 'react-hook-form';
import { FiInfo, FiClock, FiCalendar, FiRepeat, FiCheck, FiX } from 'react-icons/fi';

import { useAuth } from '../context/AuthContext';
import { createScheduledCall, getAffirmations } from '../services/supabase';
import TimezoneSelect from '../components/common/TimezoneSelect';
import SchedulePreview from '../components/scheduler/SchedulePreview';

const weekdays = [
  { id: 0, name: 'Sunday', short: 'Sun' },
  { id: 1, name: 'Monday', short: 'Mon' },
  { id: 2, name: 'Tuesday', short: 'Tue' },
  { id: 3, name: 'Wednesday', short: 'Wed' },
  { id: 4, name: 'Thursday', short: 'Thu' },
  { id: 5, name: 'Friday', short: 'Fri' },
  { id: 6, name: 'Saturday', short: 'Sat' },
];

const scheduleTypes = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekdays', label: 'Weekdays' },
  { value: 'weekends', label: 'Weekends' },
  { value: 'custom', label: 'Custom' },
];

const affirmationCategories = [
  { value: 'all', label: 'All Categories' },
  { value: 'confidence', label: 'Confidence' },
  { value: 'morning', label: 'Morning' },
  { value: 'gratitude', label: 'Gratitude' },
  { value: 'growth', label: 'Growth' },
  { value: 'mindfulness', label: 'Mindfulness' },
  { value: 'custom', label: 'My Custom Affirmations' },
];

const ScheduleCall = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [affirmations, setAffirmations] = useState([]);
  const { user, profile } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  
  const cardBg = useColorModeValue('white', 'gray.800');
  
  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors },
  } = useForm({
    defaultValues: {
      schedule_type: 'daily',
      time: '08:00',
      timezone: profile?.timezone || 'America/New_York',
      affirmation_category: 'all',
      custom_days: ['1', '2', '3', '4', '5'], // Monday to Friday
      enabled: true,
    }
  });
  
  // Watch values for conditional rendering
  const scheduleType = watch('schedule_type');
  
  useEffect(() => {
    fetchAffirmations();
    
    // Set timezone from profile if available
    if (profile?.timezone) {
      setValue('timezone', profile.timezone);
    }
  }, [profile]);
  
  const fetchAffirmations = async () => {
    try {
      const { data, error } = await getAffirmations({
        isPublic: true,
        limit: 10,
      });
      
      if (error) throw error;
      
      setAffirmations(data || []);
    } catch (error) {
      console.error('Error fetching affirmations:', error);
      toast({
        title: 'Error',
        description: 'Failed to load affirmations',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };
  
  const onSubmit = async (data) => {
    try {
      setIsSubmitting(true);
      
      // Build schedule config based on schedule type
      let scheduleConfig = {};
      
      if (data.schedule_type === 'custom') {
        scheduleConfig = {
          days: data.custom_days.map(day => parseInt(day)),
        };
      }
      
      // Create the scheduled call
      const scheduledCall = {
        user_id: user.id,
        schedule_type: data.schedule_type,
        schedule_config: scheduleConfig,
        time: data.time,
        timezone: data.timezone,
        affirmation_category: data.affirmation_category,
        enabled: data.enabled,
      };
      
      const { error } = await createScheduledCall(scheduledCall);
      
      if (error) throw error;
      
      toast({
        title: 'Schedule created',
        description: 'Your call has been scheduled successfully',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      navigate('/schedules');
    } catch (error) {
      console.error('Error creating schedule:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to create schedule',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const getScheduleDescription = (type, days) => {
    switch (type) {
      case 'daily':
        return 'Every day';
      case 'weekdays':
        return 'Monday to Friday';
      case 'weekends':
        return 'Saturday and Sunday';
      case 'custom':
        if (!days || days.length === 0) return 'No days selected';
        
        const dayNames = days.map(day => {
          const weekday = weekdays.find(wd => wd.id === parseInt(day));
          return weekday ? weekday.short : '';
        });
        
        return dayNames.join(', ');
      default:
        return '';
    }
  };
  
  // Preview the next few occurrences based on the schedule
  const getNextOccurrences = (scheduleType, customDays, time, timezone) => {
    // Convert to user's timezone
    const now = new Date();
    const occurrences = [];
    
    // Get days of week to include
    let daysToInclude = [];
    
    switch (scheduleType) {
      case 'daily':
        daysToInclude = [0, 1, 2, 3, 4, 5, 6]; // All days
        break;
      case 'weekdays':
        daysToInclude = [1, 2, 3, 4, 5]; // Monday to Friday
        break;
      case 'weekends':
        daysToInclude = [0, 6]; // Sunday and Saturday
        break;
      case 'custom':
        daysToInclude = customDays.map(day => parseInt(day));
        break;
      default:
        daysToInclude = [];
    }
    
    // Generate the next 5 occurrences
    const currentDate = new Date(now);
    let count = 0;
    
    while (occurrences.length < 5 && count < 14) { // Look up to 14 days ahead
      const dayOfWeek = currentDate.getDay();
      
      if (daysToInclude.includes(dayOfWeek)) {
        // Parse the time
        const [hours, minutes] = time.split(':').map(Number);
        
        const occurrence = new Date(currentDate);
        occurrence.setHours(hours, minutes, 0, 0);
        
        // Only include future occurrences
        if (occurrence > now) {
          occurrences.push(occurrence);
        }
      }
      
      // Move to next day
      currentDate.setDate(currentDate.getDate() + 1);
      count++;
    }
    
    return occurrences;
  };
  
  // Get form values for preview
  const formValues = watch();
  const previewOccurrences = getNextOccurrences(
    formValues.schedule_type,
    formValues.custom_days,
    formValues.time,
    formValues.timezone
  );
  
  return (
    <Box p={4}>
      <Heading mb={6}>Schedule Morning Call</Heading>
      
      <form onSubmit={handleSubmit(onSubmit)}>
        <Grid templateColumns="repeat(12, 1fr)" gap={6}>
          {/* Main Form */}
          <GridItem colSpan={{ base: 12, lg: 8 }}>
            <Card bg={cardBg}>
              <CardHeader pb={0}>
                <Heading size="md">Call Schedule</Heading>
              </CardHeader>
              
              <CardBody>
                <VStack spacing={6} align="stretch">
                  {/* Schedule Pattern */}
                  <FormControl isInvalid={errors.schedule_type}>
                    <FormLabel>
                      <HStack>
                        <Icon as={FiRepeat} />
                        <Text>Repeat Pattern</Text>
                      </HStack>
                    </FormLabel>
                    
                    <Controller
                      name="schedule_type"
                      control={control}
                      rules={{ required: 'Please select a schedule type' }}
                      render={({ field }) => (
                        <RadioGroup {...field}>
                          <HStack spacing={4} wrap="wrap">
                            {scheduleTypes.map(type => (
                              <Radio key={type.value} value={type.value}>
                                {type.label}
                              </Radio>
                            ))}
                          </HStack>
                        </RadioGroup>
                      )}
                    />
                    <FormErrorMessage>{errors.schedule_type?.message}</FormErrorMessage>
                  </FormControl>
                  
                  {/* Custom Days Selection (if custom schedule type) */}
                  {scheduleType === 'custom' && (
                    <FormControl isInvalid={errors.custom_days}>
                      <FormLabel>Select Days</FormLabel>
                      
                      <Controller
                        name="custom_days"
                        control={control}
                        rules={{ 
                          required: 'Please select at least one day',
                          validate: value => value.length > 0 || 'Please select at least one day'
                        }}
                        render={({ field }) => (
                          <CheckboxGroup {...field}>
                            <HStack spacing={4} wrap="wrap">
                              {weekdays.map(day => (
                                <Checkbox key={day.id} value={day.id.toString()}>
                                  {day.name}
                                </Checkbox>
                              ))}
                            </HStack>
                          </CheckboxGroup>
                        )}
                      />
                      <FormErrorMessage>{errors.custom_days?.message}</FormErrorMessage>
                    </FormControl>
                  )}
                  
                  {/* Time Selection */}
                  <FormControl isInvalid={errors.time}>
                    <FormLabel>
                      <HStack>
                        <Icon as={FiClock} />
                        <Text>Time</Text>
                      </HStack>
                    </FormLabel>
                    
                    <Input
                      type="time"
                      {...register('time', {
                        required: 'Please select a time',
                      })}
                    />
                    <FormErrorMessage>{errors.time?.message}</FormErrorMessage>
                  </FormControl>
                  
                  {/* Timezone Selection */}
                  <FormControl isInvalid={errors.timezone}>
                    <FormLabel>
                      <HStack>
                        <Icon as={FiCalendar} />
                        <Text>Timezone</Text>
                      </HStack>
                    </FormLabel>
                    
                    <Controller
                      name="timezone"
                      control={control}
                      rules={{ required: 'Please select a timezone' }}
                      render={({ field }) => (
                        <TimezoneSelect
                          value={field.value}
                          onChange={field.onChange}
                        />
                      )}
                    />
                    <FormErrorMessage>{errors.timezone?.message}</FormErrorMessage>
                  </FormControl>
                  
                  <Divider />
                  
                  {/* Affirmation Category */}
                  <FormControl>
                    <FormLabel>Affirmation Category</FormLabel>
                    
                    <Select
                      {...register('affirmation_category')}
                    >
                      {affirmationCategories.map(category => (
                        <option key={category.value} value={category.value}>
                          {category.label}
                        </option>
                      ))}
                    </Select>
                    <FormHelperText>
                      Select a category for your daily affirmations
                    </FormHelperText>
                  </FormControl>
                  
                  {/* Enable/Disable Switch */}
                  <FormControl display="flex" alignItems="center">
                    <FormLabel htmlFor="enabled" mb="0">
                      Enable schedule
                    </FormLabel>
                    <Switch
                      id="enabled"
                      colorScheme="blue"
                      size="lg"
                      {...register('enabled')}
                    />
                  </FormControl>
                </VStack>
              </CardBody>
              
              <CardFooter>
                <Flex width="100%" justify="space-between">
                  <Button
                    variant="outline"
                    onClick={() => navigate('/schedules')}
                  >
                    Cancel
                  </Button>
                  
                  <Button
                    type="submit"
                    colorScheme="blue"
                    isLoading={isSubmitting}
                    loadingText="Saving"
                  >
                    Save Schedule
                  </Button>
                </Flex>
              </CardFooter>
            </Card>
          </GridItem>
          
          {/* Schedule Preview */}
          <GridItem colSpan={{ base: 12, lg: 4 }}>
            <SchedulePreview
              scheduleType={formValues.schedule_type}
              description={getScheduleDescription(formValues.schedule_type, formValues.custom_days)}
              occurrences={previewOccurrences}
              timezone={formValues.timezone}
              enabled={formValues.enabled}
            />
            
            {/* Sample Affirmations Card */}
            <Card bg={cardBg} mt={6}>
              <CardHeader>
                <Heading size="sm">Sample Affirmations</Heading>
              </CardHeader>
              <CardBody>
                <VStack align="start" spacing={3}>
                  {affirmations.slice(0, 3).map((affirmation, index) => (
                    <Box key={index}>
                      <Text fontSize="sm" fontStyle="italic">"{affirmation.text}"</Text>
                      <Badge colorScheme="blue" mt={1}>{affirmation.category}</Badge>
                    </Box>
                  ))}
                  
                  {affirmations.length === 0 && (
                    <Text color="gray.500">No sample affirmations available</Text>
                  )}
                </VStack>
              </CardBody>
            </Card>
          </GridItem>
        </Grid>
      </form>
    </Box>
  );
};

export default ScheduleCall;
