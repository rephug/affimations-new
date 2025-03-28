// src/pages/TranscriptionMonitor.js
import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Heading,
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
  Flex,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatGroup,
  Progress,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  Code,
  Tag,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  IconButton,
  Divider
} from '@chakra-ui/react';
import { 
  FiRefreshCw, 
  FiClock, 
  FiCheckCircle, 
  FiAlertCircle, 
  FiPlayCircle,
  FiCpu,
  FiEye,
  FiDownload
} from 'react-icons/fi';

const TranscriptionMonitor = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [pendingTranscriptions, setPendingTranscriptions] = useState([]);
  const [completedTranscriptions, setCompletedTranscriptions] = useState([]);
  const [stats, setStats] = useState({
    pending: 0,
    inProgress: 0,
    completed: 0,
    failed: 0
  });
  const [selectedTranscription, setSelectedTranscription] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  
  const toast = useToast();

  useEffect(() => {
    // Fetch transcriptions on component mount
    fetchTranscriptions();
    
    // Refresh data every 10 seconds
    const intervalId = setInterval(fetchTranscriptions, 10000);
    
    return () => clearInterval(intervalId);
  }, []);

  const fetchTranscriptions = async () => {
    setIsLoading(true);
    try {
      // In a real implementation, these would be actual API calls
      // Simulating API calls for demonstration
      const pendingData = await simulateFetchPendingTranscriptions();
      const completedData = await simulateFetchCompletedTranscriptions();
      
      setPendingTranscriptions(pendingData);
      setCompletedTranscriptions(completedData);
      
      // Calculate stats
      const stats = {
        pending: pendingData.filter(t => t.status === 'pending').length,
        inProgress: pendingData.filter(t => t.status === 'in_progress').length,
        completed: completedData.length,
        failed: completedData.filter(t => t.status === 'error').length
      };
      
      setStats(stats);
    } catch (error) {
      console.error('Error fetching transcriptions:', error);
      toast({
        title: 'Error fetching transcriptions',
        description: error.message || 'Failed to load transcription data',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const checkTranscriptions = async () => {
    try {
      // In a real implementation, this would be an actual API call
      const response = await fetch('/api/check_transcriptions');
      
      if (!response.ok) {
        throw new Error(`Failed to check transcriptions: ${response.status}`);
      }
      
      const result = await response.json();
      
      toast({
        title: 'Transcriptions checked',
        description: `${result.pending_count} pending transcriptions found`,
        status: 'info',
        duration: 3000,
        isClosable: true,
      });
      
      // Refresh the transcription list
      fetchTranscriptions();
    } catch (error) {
      console.error('Error checking transcriptions:', error);
      toast({
        title: 'Failed to check transcriptions',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  // Mocked API responses for demonstration
  const simulateFetchPendingTranscriptions = async () => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    return [
      {
        id: 'job-1234',
        call_control_id: 'call-abcd',
        client_state: 'record_chat',
        status: 'pending',
        start_time: new Date(Date.now() - 30000).toISOString() // 30 seconds ago
      },
      {
        id: 'job-5678',
        call_control_id: 'call-efgh',
        client_state: 'record_affirmation',
        status: 'in_progress',
        start_time: new Date(Date.now() - 15000).toISOString() // 15 seconds ago
      }
    ];
  };

  const simulateFetchCompletedTranscriptions = async () => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 700));
    
    return [
      {
        id: 'job-abcd',
        call_control_id: 'call-1234',
        client_state: 'record_chat',
        status: 'completed',
        start_time: new Date(Date.now() - 60000).toISOString(), // 1 minute ago
        completed_at: new Date(Date.now() - 45000).toISOString(), // 45 seconds ago
        text: "I'm feeling great today, ready to tackle the challenges ahead.",
        duration: 15 // seconds
      },
      {
        id: 'job-efgh',
        call_control_id: 'call-5678',
        client_state: 'record_affirmation',
        status: 'completed',
        start_time: new Date(Date.now() - 90000).toISOString(), // 1.5 minutes ago
        completed_at: new Date(Date.now() - 80000).toISOString(), // 80 seconds ago
        text: "I am capable of achieving my goals and dreams.",
        duration: 10 // seconds
      },
      {
        id: 'job-ijkl',
        call_control_id: 'call-9012',
        client_state: 'record_chat',
        status: 'error',
        start_time: new Date(Date.now() - 120000).toISOString(), // 2 minutes ago
        completed_at: new Date(Date.now() - 110000).toISOString(), // 110 seconds ago
        error: "Unable to transcribe audio: poor audio quality",
        duration: 10 // seconds
      }
    ];
  };

  const handleViewTranscription = (transcription) => {
    setSelectedTranscription(transcription);
    onOpen();
  };

  const getStatusBadge = (status) => {
    const statusColors = {
      'pending': 'blue',
      'in_progress': 'orange',
      'completed': 'green',
      'error': 'red'
    };
    
    return (
      <Badge colorScheme={statusColors[status] || 'gray'}>
        {status.replace('_', ' ')}
      </Badge>
    );
  };

  const formatDuration = (startTime, endTime) => {
    if (!endTime) {
      // For pending jobs, calculate time since start
      const start = new Date(startTime);
      const now = new Date();
      const durationInSeconds = Math.floor((now - start) / 1000);
      
      return `${durationInSeconds}s ago`;
    }
    
    // For completed jobs, calculate duration
    const start = new Date(startTime);
    const end = new Date(endTime);
    const durationInSeconds = Math.floor((end - start) / 1000);
    
    return `${durationInSeconds}s`;
  };

  return (
    <Box>
      <Heading mb={6}>Transcription Monitor</Heading>
      
      <StatGroup mb={6}>
        <Stat>
          <StatLabel>Total Pending</StatLabel>
          <StatNumber>{stats.pending + stats.inProgress}</StatNumber>
          <StatHelpText>
            {stats.pending} pending + {stats.inProgress} in progress
          </StatHelpText>
        </Stat>
        
        <Stat>
          <StatLabel>Completed</StatLabel>
          <StatNumber>{stats.completed}</StatNumber>
          <StatHelpText>
            {stats.completed - stats.failed} successful, {stats.failed} failed
          </StatHelpText>
        </Stat>
        
        <Stat>
          <StatLabel>Success Rate</StatLabel>
          <StatNumber>
            {stats.completed ? 
              `${Math.round(((stats.completed - stats.failed) / stats.completed) * 100)}%` : 
              'N/A'}
          </StatNumber>
          <StatHelpText>
            Overall transcription success
          </StatHelpText>
        </Stat>
      </StatGroup>
      
      <HStack mb={6} spacing={4}>
        <Button
          colorScheme="blue"
          onClick={checkTranscriptions}
          leftIcon={<FiCpu />}
        >
          Process Pending Transcriptions
        </Button>
        
        <Button
          onClick={fetchTranscriptions}
          leftIcon={<FiRefreshCw />}
          isLoading={isLoading}
        >
          Refresh Data
        </Button>
      </HStack>
      
      <Tabs variant="enclosed" mb={8}>
        <TabList>
          <Tab>Pending Transcriptions</Tab>
          <Tab>Completed Transcriptions</Tab>
        </TabList>
        
        <TabPanels>
          <TabPanel>
            <Card>
              <CardHeader>
                <HStack justifyContent="space-between">
                  <Heading size="md">Pending Transcriptions</Heading>
                  <Badge colorScheme={pendingTranscriptions.length > 0 ? "orange" : "green"}>
                    {pendingTranscriptions.length} pending
                  </Badge>
                </HStack>
              </CardHeader>
              <CardBody>
                {isLoading ? (
                  <Box textAlign="center" py={10}>
                    <Spinner size="xl" />
                    <Text mt={3}>Loading transcription data...</Text>
                  </Box>
                ) : pendingTranscriptions.length === 0 ? (
                  <Alert status="success">
                    <AlertIcon />
                    No pending transcriptions!
                  </Alert>
                ) : (
                  <Table variant="simple">
                    <Thead>
                      <Tr>
                        <Th>Job ID</Th>
                        <Th>Call ID</Th>
                        <Th>Type</Th>
                        <Th>Status</Th>
                        <Th>Started</Th>
                        <Th>Actions</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {pendingTranscriptions.map(job => (
                        <Tr key={job.id}>
                          <Td>{job.id}</Td>
                          <Td>{job.call_control_id}</Td>
                          <Td>
                            <Tag>
                              {job.client_state.replace('record_', '')}
                            </Tag>
                          </Td>
                          <Td>{getStatusBadge(job.status)}</Td>
                          <Td>{formatDuration(job.start_time)}</Td>
                          <Td>
                            <IconButton
                              aria-label="View details"
                              icon={<FiEye />}
                              size="sm"
                              onClick={() => handleViewTranscription(job)}
                            />
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                )}
              </CardBody>
            </Card>
          </TabPanel>
          
          <TabPanel>
            <Card>
              <CardHeader>
                <HStack justifyContent="space-between">
                  <Heading size="md">Completed Transcriptions</Heading>
                  <Badge colorScheme="green">
                    {completedTranscriptions.length} completed
                  </Badge>
                </HStack>
              </CardHeader>
              <CardBody>
                {isLoading ? (
                  <Box textAlign="center" py={10}>
                    <Spinner size="xl" />
                    <Text mt={3}>Loading transcription data...</Text>
                  </Box>
                ) : completedTranscriptions.length === 0 ? (
                  <Alert status="info">
                    <AlertIcon />
                    No completed transcriptions yet.
                  </Alert>
                ) : (
                  <Table variant="simple">
                    <Thead>
                      <Tr>
                        <Th>Job ID</Th>
                        <Th>Call ID</Th>
                        <Th>Type</Th>
                        <Th>Status</Th>
                        <Th>Duration</Th>
                        <Th>Text</Th>
                        <Th>Actions</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {completedTranscriptions.map(job => (
                        <Tr key={job.id}>
                          <Td>{job.id}</Td>
                          <Td>{job.call_control_id}</Td>
                          <Td>
                            <Tag>
                              {job.client_state.replace('record_', '')}
                            </Tag>
                          </Td>
                          <Td>{getStatusBadge(job.status)}</Td>
                          <Td>{formatDuration(job.start_time, job.completed_at)}</Td>
                          <Td>
                            {job.status === 'error' ? (
                              <Text color="red.500">{job.error}</Text>
                            ) : (
                              <Text>
                                {job.text.length > 30 ? 
                                  `${job.text.substring(0, 30)}...` : 
                                  job.text}
                              </Text>
                            )}
                          </Td>
                          <Td>
                            <IconButton
                              aria-label="View details"
                              icon={<FiEye />}
                              size="sm"
                              onClick={() => handleViewTranscription(job)}
                            />
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
      
      {/* Modal for transcription details */}
      <Modal isOpen={isOpen} onClose={onClose} size="lg">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Transcription Details</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {selectedTranscription && (
              <VStack align="stretch" spacing={4}>
                <Box>
                  <Text fontWeight="bold">Job ID:</Text>
                  <Text>{selectedTranscription.id}</Text>
                </Box>
                
                <Box>
                  <Text fontWeight="bold">Call ID:</Text>
                  <Text>{selectedTranscription.call_control_id}</Text>
                </Box>
                
                <Box>
                  <Text fontWeight="bold">Type:</Text>
                  <Tag>{selectedTranscription.client_state.replace('record_', '')}</Tag>
                </Box>
                
                <Box>
                  <Text fontWeight="bold">Status:</Text>
                  {getStatusBadge(selectedTranscription.status)}
                </Box>
                
                <Box>
                  <Text fontWeight="bold">Started:</Text>
                  <Text>{new Date(selectedTranscription.start_time).toLocaleString()}</Text>
                </Box>
                
                {selectedTranscription.completed_at && (
                  <Box>
                    <Text fontWeight="bold">Completed:</Text>
                    <Text>{new Date(selectedTranscription.completed_at).toLocaleString()}</Text>
                  </Box>
                )}
                
                {selectedTranscription.text && (
                  <Box>
                    <Text fontWeight="bold">Transcribed Text:</Text>
                    <Code p={3} borderRadius="md" mt={2}>
                      {selectedTranscription.text}
                    </Code>
                  </Box>
                )}
                
                {selectedTranscription.error && (
                  <Box>
                    <Text fontWeight="bold">Error:</Text>
                    <Alert status="error" mt={2}>
                      <AlertIcon />
                      {selectedTranscription.error}
                    </Alert>
                  </Box>
                )}
                
                {selectedTranscription.status === 'pending' || selectedTranscription.status === 'in_progress' ? (
                  <Box>
                    <Text fontWeight="bold">Elapsed Time:</Text>
                    <HStack mt={2} spacing={4}>
                      <Progress 
                        value={Math.min(100, (new Date() - new Date(selectedTranscription.start_time)) / 300)} 
                        size="sm" 
                        width="100%" 
                        colorScheme="blue" 
                        hasStripe 
                        isAnimated
                      />
                      <Text>
                        {formatDuration(selectedTranscription.start_time)}
                      </Text>
                    </HStack>
                  </Box>
                ) : null}
              </VStack>
            )}
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Close
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default TranscriptionMonitor;