import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Flex, 
  Heading, 
  Text, 
  Stat, 
  StatLabel, 
  StatNumber, 
  StatHelpText,
  SimpleGrid,
  Card, 
  CardHeader, 
  CardBody,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Button,
  useToast,
  Spinner,
  VStack,
  HStack,
  Icon
} from '@chakra-ui/react';
import { 
  FiPhone, 
  FiMessageSquare, 
  FiMic, 
  FiClock, 
  FiCheckCircle, 
  FiAlertCircle,
  FiActivity
} from 'react-icons/fi';
import { Link } from 'react-router-dom';

const Dashboard = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState({
    activeCalls: [],
    recentCalls: [],
    completedTranscriptions: 0,
    pendingTranscriptions: 0,
    failedTranscriptions: 0,
    sentMessages: 0
  });
  const toast = useToast();

  useEffect(() => {
    const fetchDashboardData = async () => {
      setIsLoading(true);
      try {
        // In a real implementation, these would be actual API calls
        // Simulating API calls for demonstration
        const activeCalls = await fetchActiveCalls();
        const recentCalls = await fetchRecentCalls();
        const transcriptionStats = await fetchTranscriptionStats();
        const messageStats = await fetchMessageStats();
        
        setDashboardData({
          activeCalls,
          recentCalls,
          completedTranscriptions: transcriptionStats.completed,
          pendingTranscriptions: transcriptionStats.pending,
          failedTranscriptions: transcriptionStats.failed,
          sentMessages: messageStats.sent
        });
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        toast({
          title: 'Error fetching data',
          description: error.message || 'Failed to load dashboard data',
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
    // Refresh data every 10 seconds
    const intervalId = setInterval(fetchDashboardData, 10000);
    
    return () => clearInterval(intervalId);
  }, [toast]);

  // Mocked API responses for demonstration
  const fetchActiveCalls = async () => {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 500));
    
    return [
      {
        id: 'call-1234',
        user_number: '+15551234567',
        stage: 'chat_intro',
        start_time: new Date(Date.now() - 120000).toISOString() // 2 minutes ago
      },
      {
        id: 'call-5678',
        user_number: '+15559876543',
        stage: 'recording_chat',
        start_time: new Date(Date.now() - 60000).toISOString() // 1 minute ago
      }
    ];
  };

  const fetchRecentCalls = async () => {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 700));
    
    return [
      {
        id: 'call-abcd',
        user_number: '+15551112222',
        stage: 'ended',
        start_time: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
        end_time: new Date(Date.now() - 3540000).toISOString(), // 59 minutes ago
        duration: 60, // seconds
        transcription_count: 3
      },
      {
        id: 'call-efgh',
        user_number: '+15553334444',
        stage: 'ended',
        start_time: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
        end_time: new Date(Date.now() - 7080000).toISOString(), // 1 hour 58 minutes ago
        duration: 120, // seconds
        transcription_count: 5
      },
      {
        id: 'call-ijkl',
        user_number: '+15555556666',
        stage: 'ended',
        start_time: new Date(Date.now() - 10800000).toISOString(), // 3 hours ago
        end_time: new Date(Date.now() - 10740000).toISOString(), // 2 hours 59 minutes ago
        duration: 60, // seconds
        transcription_count: 2
      }
    ];
  };

  const fetchTranscriptionStats = async () => {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 600));
    
    return {
      completed: 42,
      pending: 3,
      failed: 1
    };
  };

  const fetchMessageStats = async () => {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 400));
    
    return {
      sent: 51
    };
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

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatPhoneNumber = (phoneNumber) => {
    // Display only last 4 digits for privacy in this demo
    return phoneNumber.substring(0, phoneNumber.length - 4) + '****';
  };

  if (isLoading) {
    return (
      <Flex justify="center" align="center" height="600px">
        <VStack>
          <Spinner size="xl" color="blue.500" />
          <Text mt={4}>Loading dashboard data...</Text>
        </VStack>
      </Flex>
    );
  }

  return (
    <Box>
      <Heading mb={6}>Morning Coffee Dashboard</Heading>
      
      {/* Stats Overview */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} mb={8}>
        <Stat as={Card} p={4}>
          <StatLabel display="flex" alignItems="center">
            <Icon as={FiPhone} mr={2} /> Active Calls
          </StatLabel>
          <StatNumber>{dashboardData.activeCalls.length}</StatNumber>
          <StatHelpText>Real-time calls in progress</StatHelpText>
        </Stat>
        
        <Stat as={Card} p={4}>
          <StatLabel display="flex" alignItems="center">
            <Icon as={FiMessageSquare} mr={2} /> Messages Sent
          </StatLabel>
          <StatNumber>{dashboardData.sentMessages}</StatNumber>
          <StatHelpText>Total SMS affirmations</StatHelpText>
        </Stat>
        
        <Stat as={Card} p={4}>
          <StatLabel display="flex" alignItems="center">
            <Icon as={FiMic} mr={2} /> Transcriptions
          </StatLabel>
          <StatNumber>{dashboardData.completedTranscriptions}</StatNumber>
          <StatHelpText>
            <HStack spacing={2}>
              <Badge colorScheme="yellow">{dashboardData.pendingTranscriptions} pending</Badge>
              <Badge colorScheme="red">{dashboardData.failedTranscriptions} failed</Badge>
            </HStack>
          </StatHelpText>
        </Stat>
        
        <Stat as={Card} p={4}>
          <StatLabel display="flex" alignItems="center">
            <Icon as={FiActivity} mr={2} /> System Status
          </StatLabel>
          <StatNumber>
            <Badge colorScheme={dashboardData.pendingTranscriptions > 5 ? "yellow" : "green"}>
              {dashboardData.pendingTranscriptions > 5 ? "Busy" : "Normal"}
            </Badge>
          </StatNumber>
          <StatHelpText>System load indicator</StatHelpText>
        </Stat>
      </SimpleGrid>
      
      {/* Active Calls */}
      <Card mb={8}>
        <CardHeader>
          <Heading size="md" display="flex" alignItems="center">
            <Icon as={FiPhone} mr={2} color="green.500" /> Active Calls
          </Heading>
        </CardHeader>
        <CardBody>
          {dashboardData.activeCalls.length === 0 ? (
            <Text>No active calls at the moment</Text>
          ) : (
            <Table variant="simple">
              <Thead>
                <Tr>
                  <Th>Call ID</Th>
                  <Th>User</Th>
                  <Th>Status</Th>
                  <Th>Duration</Th>
                  <Th>Actions</Th>
                </Tr>
              </Thead>
              <Tbody>
                {dashboardData.activeCalls.map(call => (
                  <Tr key={call.id}>
                    <Td>{call.id}</Td>
                    <Td>{formatPhoneNumber(call.user_number)}</Td>
                    <Td>{getStatusBadge(call.stage)}</Td>
                    <Td>
                      {formatDuration(
                        Math.floor((new Date() - new Date(call.start_time)) / 1000)
                      )}
                    </Td>
                    <Td>
                      <Button 
                        as={Link} 
                        to={`/call-status/${call.id}`} 
                        size="sm" 
                        colorScheme="blue"
                      >
                        View
                      </Button>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </CardBody>
      </Card>
      
      {/* Recent Calls */}
      <Card>
        <CardHeader>
          <Heading size="md" display="flex" alignItems="center">
            <Icon as={FiClock} mr={2} color="blue.500" /> Recent Calls
          </Heading>
        </CardHeader>
        <CardBody>
          <Table variant="simple">
            <Thead>
              <Tr>
                <Th>Call ID</Th>
                <Th>User</Th>
                <Th>Status</Th>
                <Th>Start Time</Th>
                <Th>Duration</Th>
                <Th>Interactions</Th>
                <Th>Actions</Th>
              </Tr>
            </Thead>
            <Tbody>
              {dashboardData.recentCalls.map(call => (
                <Tr key={call.id}>
                  <Td>{call.id}</Td>
                  <Td>{formatPhoneNumber(call.user_number)}</Td>
                  <Td>{getStatusBadge(call.stage)}</Td>
                  <Td>{new Date(call.start_time).toLocaleTimeString()}</Td>
                  <Td>{formatDuration(call.duration)}</Td>
                  <Td>{call.transcription_count}</Td>
                  <Td>
                    <Button 
                      as={Link} 
                      to={`/call-status/${call.id}`} 
                      size="sm" 
                      colorScheme="blue"
                    >
                      Details
                    </Button>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </CardBody>
      </Card>
    </Box>
  );
};

export default Dashboard;
