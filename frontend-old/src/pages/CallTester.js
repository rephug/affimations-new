import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  FormControl,
  FormLabel,
  Heading,
  Input,
  VStack,
  HStack,
  Text,
  useToast,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Spinner,
  Alert,
  AlertIcon,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  FormHelperText,
  IconButton,
  Tooltip,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  useDisclosure
} from '@chakra-ui/react';
import { FiPhone, FiInfo, FiRefreshCw, FiEye, FiMessageSquare, FiClock } from 'react-icons/fi';
import { Link } from 'react-router-dom';

const CallTester = () => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeCalls, setActiveCalls] = useState([]);
  const [isLoadingCalls, setIsLoadingCalls] = useState(true);
  const [selectedCall, setSelectedCall] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  
  const toast = useToast();

  useEffect(() => {
    // Fetch active calls on component mount
    fetchActiveCalls();
    
    // Refresh active calls every 10 seconds
    const intervalId = setInterval(fetchActiveCalls, 10000);
    
    return () => clearInterval(intervalId);
  }, []);

  const fetchActiveCalls = async () => {
    setIsLoadingCalls(true);
    try {
      // In a real implementation, this would be an actual API call
      // Simulating API call for demonstration
      const response = await simulateFetchActiveCalls();
      setActiveCalls(response);
    } catch (error) {
      console.error('Error fetching active calls:', error);
      toast({
        title: 'Error fetching calls',
        description: error.message || 'Failed to load active calls',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoadingCalls(false);
    }
  };

  // Mocked API response for demonstration
  const simulateFetchActiveCalls = async () => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    return [
      {
        id: 'call-1234',
        user_number: '+15551234567',
        stage: 'chat_intro',
        start_time: new Date(Date.now() - 120000).toISOString(), // 2 minutes ago
        last_updated: new Date(Date.now() - 30000).toISOString(), // 30 seconds ago
        affirmation: "I am capable of achieving my goals and dreams."
      },
      {
        id: 'call-5678',
        user_number: '+15559876543',
        stage: 'recording_chat',
        start_time: new Date(Date.now() - 60000).toISOString(), // 1 minute ago
        last_updated: new Date(Date.now() - 15000).toISOString(), // 15 seconds ago
        affirmation: "I embrace the day with positivity and purpose."
      }
    ];
  };

  const initiateCall = async () => {
    // Validate phone number format
    const phoneRegex = /^\+[1-9]\d{1,14}$/;
    if (!phoneRegex.test(phoneNumber)) {
      toast({
        title: 'Invalid phone number',
        description: 'Please enter a valid phone number in E.164 format (e.g., +15551234567)',
        status: 'warning',
        duration: 5000,
        isClosable: true,
      });
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      // In a real implementation, this would be an actual API call
      // Here we're just simulating a successful call initiation
      
      const response = await fetch('/api/schedule_morning_coffee', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phone_number: phoneNumber
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to initiate call: ${response.status}`);
      }
      
      const result = await response.json();
      
      toast({
        title: 'Call initiated',
        description: `Affirmation SMS sent and call scheduled for ${phoneNumber}`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      // Refresh the active calls list
      setTimeout(fetchActiveCalls, 1000);
      
      // Clear the form
      setPhoneNumber('');
    } catch (error) {
      console.error('Error initiating call:', error);
      toast({
        title: 'Failed to initiate call',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleViewCallDetails = (call) => {
    setSelectedCall(call);
    onOpen();
  };

  const getStatusBadge = (status) => {
    const statusColors = {
      'greeting': 'blue',
      'recording_affirmation': 'purple',
      'chat_intro': 'teal',
      'recording_chat': 'orange',
      'ai_response': 'green',
      'ended': 'gray'
    };
    
    return (
      <Badge colorScheme={statusColors[status] || 'gray'}>
        {status.replace('_', ' ')}
      </Badge>
    );
  };

  const formatDuration = (startTime) => {
    const start = new Date(startTime);
    const now = new Date();
    const durationInSeconds = Math.floor((now - start) / 1000);
    
    const minutes = Math.floor(durationInSeconds / 60);
    const seconds = durationInSeconds % 60;
    
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <Box>
      <Heading mb={6}>Call Tester</Heading>
      
      <Tabs variant="enclosed" mb={8}>
        <TabList>
          <Tab>Initiate Call</Tab>
          <Tab>Active Calls</Tab>
        </TabList>
        
        <TabPanels>
          <TabPanel>
            <Card>
              <CardHeader>
                <Heading size="md">Schedule Morning Coffee</Heading>
              </CardHeader>
              <CardBody>
                <VStack spacing={5} align="stretch">
                  <Alert status="info">
                    <AlertIcon />
                    This will send an affirmation SMS and initiate a phone call to the specified number.
                  </Alert>
                  
                  <FormControl>
                    <FormLabel>Phone Number</FormLabel>
                    <Input
                      type="tel"
                      value={phoneNumber}
                      onChange={(e) => setPhoneNumber(e.target.value)}
                      placeholder="+15551234567"
                    />
                    <FormHelperText>
                      Enter phone number in E.164 format (e.g., +15551234567)
                    </FormHelperText>
                  </FormControl>
                  
                  <Button
                    colorScheme="blue"
                    onClick={initiateCall}
                    isLoading={isSubmitting}
                    loadingText="Initiating"
                    leftIcon={<FiPhone />}
                    width="200px"
                  >
                    Schedule Call
                  </Button>
                </VStack>
              </CardBody>
            </Card>
          </TabPanel>
          
          <TabPanel>
            <Card>
              <CardHeader>
                <HStack justifyContent="space-between">
                  <Heading size="md">Active Calls</Heading>
                  <Button
                    size="sm"
                    onClick={fetchActiveCalls}
                    leftIcon={<FiRefreshCw />}
                    isLoading={isLoadingCalls}
                  >
                    Refresh
                  </Button>
                </HStack>
              </CardHeader>
              <CardBody>
                {isLoadingCalls ? (
                  <Box textAlign="center" py={10}>
                    <Spinner size="xl" />
                    <Text mt={3}>Loading active calls...</Text>
                  </Box>
                ) : activeCalls.length === 0 ? (
                  <Alert status="info">
                    <AlertIcon />
                    No active calls at the moment.
                  </Alert>
                ) : (
                  <Table variant="simple">
                    <Thead>
                      <Tr>
                        <Th>Call ID</Th>
                        <Th>Phone Number</Th>
                        <Th>Status</Th>
                        <Th>Duration</Th>
                        <Th>Last Update</Th>
                        <Th>Actions</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {activeCalls.map(call => (
                        <Tr key={call.id}>
                          <Td>{call.id}</Td>
                          <Td>{call.user_number}</Td>
                          <Td>{getStatusBadge(call.stage)}</Td>
                          <Td>{formatDuration(call.start_time)}</Td>
                          <Td>{new Date(call.last_updated).toLocaleTimeString()}</Td>
                          <Td>
                            <HStack spacing={2}>
                              <IconButton
                                aria-label="View details"
                                icon={<FiEye />}
                                size="sm"
                                onClick={() => handleViewCallDetails(call)}
                              />
                              <IconButton
                                as={Link}
                                to={`/call-status/${call.id}`}
                                aria-label="Full details"
                                icon={<FiInfo />}
                                size="sm"
                              />
                            </HStack>
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                )}
              </CardBody>
            </Card>
          </TabPanel>
        </TabPanels>
      </Tabs>
      
      {/* Call Details Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="lg">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Call Details</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {selectedCall && (
              <VStack align="stretch" spacing={4}>
                <Box>
                  <Text fontWeight="bold">Call ID:</Text>
                  <Text>{selectedCall.id}</Text>
                </Box>
                
                <Box>
                  <Text fontWeight="bold">Phone Number:</Text>
                  <Text>{selectedCall.user_number}</Text>
                </Box>
                
                <Box>
                  <Text fontWeight="bold">Status:</Text>
                  {getStatusBadge(selectedCall.stage)}
                </Box>
                
                <Box>
                  <Text fontWeight="bold">Affirmation:</Text>
                  <Text fontStyle="italic">"{selectedCall.affirmation}"</Text>
                </Box>
                
                <Box>
                  <Text fontWeight="bold">Start Time:</Text>
                  <Text>{new Date(selectedCall.start_time).toLocaleString()}</Text>
                </Box>
                
                <Box>
                  <Text fontWeight="bold">Duration:</Text>
                  <Text>{formatDuration(selectedCall.start_time)}</Text>
                </Box>
                
                <Box>
                  <Text fontWeight="bold">Last Updated:</Text>
                  <Text>{new Date(selectedCall.last_updated).toLocaleString()}</Text>
                </Box>
                
                <Alert status="info">
                  <AlertIcon />
                  View the full call status page for more details including transcriptions and conversation history.
                </Alert>
              </VStack>
            )}
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Close
            </Button>
            {selectedCall && (
              <Button 
                as={Link} 
                to={`/call-status/${selectedCall.id}`}
                colorScheme="blue"
              >
                View Full Details
              </Button>
            )}
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default CallTester;
