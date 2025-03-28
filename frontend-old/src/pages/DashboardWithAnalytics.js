// src/pages/Dashboard.js
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Flex,
  Grid,
  GridItem,
  Heading,
  Text,
  Button,
  Card,
  CardHeader,
  CardBody,
  HStack,
  VStack,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Badge,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  useToast,
  useColorModeValue,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Icon,
  Divider,
} from '@chakra-ui/react';
import {
  FiPlus,
  FiClock,
  FiCalendar,
  FiPhone,
  FiMessageSquare,
  FiBarChart2,
  FiMoreVertical,
  FiArrowRight,
} from 'react-icons/fi';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { format, parseISO, differenceInDays, formatDistance } from 'date-fns';

import { useAuth } from '../context/AuthContext';
import { getCallHistory, getScheduledCalls } from '../services/supabase';
import NextScheduledCall from '../../components/dashboard/NextScheduledCall';
import WelcomeMessage from '../../components/dashboard/WelcomeMessage';
import RecentCallsTable from '../../components/dashboard/RecentCallsTable';
import StatsOverview from '../../components/dashboard/StatsOverview';
import CallTrends from '../../components/dashboard/CallTrends';
import DashboardSkeleton from '../../components/dashboard/DashboardSkeleton';

// Chart colors
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const Dashboard = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [callStats, setCallStats] = useState({
    totalCalls: 0,
    totalDuration: 0,
    averageDuration: 0,
    callsThisWeek: 0,
    completionRate: 0,
    improvement: 0,
  });
  const [recentCalls, setRecentCalls] = useState([]);
  const [scheduledCalls, setScheduledCalls] = useState([]);
  const [nextCall, setNextCall] = useState(null);
  const [callTrends, setCallTrends] = useState([]);
  const [callDistribution, setCallDistribution] = useState([]);
  
  const { user, profile } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  
  const bgColor = useColorModeValue('white', 'gray.800');
  
  useEffect(() => {
    if (user) {
      fetchDashboardData();
    }
  }, [user]);
  
  const fetchDashboardData = async () => {
    setIsLoading(true);
    try {
      // Fetch call history
      const { data: callHistory, error: callHistoryError } = await getCallHistory(user.id, { limit: 10 });
      
      if (callHistoryError) throw callHistoryError;
      
      // Fetch scheduled calls
      const { data: schedules, error: schedulesError } = await getScheduledCalls(user.id);
      
      if (schedulesError) throw schedulesError;
      
      // Process data
      setRecentCalls(callHistory || []);
      setScheduledCalls(schedules || []);
      
      // Find the next scheduled call
      if (schedules && schedules.length > 0) {
        const enabledSchedules = schedules.filter(schedule => schedule.enabled);
        if (enabledSchedules.length > 0) {
          // In a real app, you would calculate the next occurrence time based on the schedule
          // For this example, we'll just use the first enabled schedule
          setNextCall(enabledSchedules[0]);
        }
      }
      
      // Calculate call statistics
      if (callHistory && callHistory.length > 0) {
        const totalCalls = callHistory.length;
        
        // Calculate total duration in minutes
        const totalDuration = callHistory.reduce((acc, call) => {
          return acc + (call.duration || 0);
        }, 0) / 60; // Convert seconds to minutes
        
        // Calculate average duration
        const averageDuration = totalDuration / totalCalls;
        
        // Count calls in the past week
        const now = new Date();
        const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        const callsThisWeek = callHistory.filter(call => {
          const callDate = new Date(call.started_at);
          return callDate >= oneWeekAgo;
        }).length;
        
        // Calculate completion rate
        const completedCalls = callHistory.filter(call => call.status === 'ended').length;
        const completionRate = (completedCalls / totalCalls) * 100;
        
        // Calculate improvement (mock data for example)
        const improvement = 5.2;
        
        setCallStats({
          totalCalls,
          totalDuration: Math.round(totalDuration * 10) / 10, // Round to 1 decimal
          averageDuration: Math.round(averageDuration * 10) / 10, // Round to 1 decimal
          callsThisWeek,
          completionRate: Math.round(completionRate),
          improvement,
        });
        
        // Generate call trends data (past 7 days)
        const trendData = [];
        for (let i = 6; i >= 0; i--) {
          const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
          const dateStr = format(date, 'MM/dd');
          
          // Count calls on this day
          const callsOnDay = callHistory.filter(call => {
            const callDate = new Date(call.started_at);
            return differenceInDays(callDate, date) === 0;
          }).length;
          
          trendData.push({
            date: dateStr,
            calls: callsOnDay,
          });
        }
        setCallTrends(trendData);
        
        // Generate call distribution data
        const distributionData = [
          { name: 'Morning', value: callHistory.filter(call => {
            const hour = new Date(call.started_at).getHours();
            return hour >= 5 && hour < 12;
          }).length },
          { name: 'Afternoon', value: callHistory.filter(call => {
            const hour = new Date(call.started_at).getHours();
            return hour >= 12 && hour < 17;
          }).length },
          { name: 'Evening', value: callHistory.filter(call => {
            const hour = new Date(call.started_at).getHours();
            return hour >= 17 && hour < 21;
          }).length },
          { name: 'Night', value: callHistory.filter(call => {
            const hour = new Date(call.started_at).getHours();
            return hour >= 21 || hour < 5;
          }).length },
        ];
        setCallDistribution(distributionData);
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      toast({
        title: 'Error loading dashboard',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleScheduleCall = () => {
    navigate('/schedule');
  };
  
  if (isLoading) {
    return <DashboardSkeleton />;
  }
  
  return (
    <Box p={4}>
      <Flex justify="space-between" align="center" mb={6}>
        <Box>
          <Heading size="lg" mb={1}>Dashboard</Heading>
          <Text color="gray.600">Welcome back, {profile?.first_name || 'User'}</Text>
        </Box>
        <Button
          leftIcon={<FiPlus />}
          colorScheme="blue"
          onClick={handleScheduleCall}
        >
          Schedule Call
        </Button>
      </Flex>
      
      <Grid templateColumns="repeat(12, 1fr)" gap={6}>
        {/* Welcome Card and Next Call */}
        <GridItem colSpan={{ base: 12, lg: 4 }}>
          <VStack spacing={6} align="stretch">
            <WelcomeMessage 
              name={profile?.first_name}
              callStats={callStats}
            />
            
            <NextScheduledCall 
              nextCall={nextCall}
              onSchedule={handleScheduleCall}
            />
          </VStack>
        </GridItem>
        
        {/* Statistics Overview */}
        <GridItem colSpan={{ base: 12, lg: 8 }}>
          <StatsOverview stats={callStats} />
        </GridItem>
        
        {/* Call Trends Chart */}
        <GridItem colSpan={{ base: 12, lg: 8 }}>
          <Card>
            <CardHeader>
              <Flex justify="space-between" align="center">
                <Heading size="md">Call Activity Trends</Heading>
                <Icon as={FiBarChart2} boxSize={5} color="gray.500" />
              </Flex>
            </CardHeader>
            <CardBody>
              {callTrends.length > 0 ? (
                <Box height="300px">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={callTrends}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="calls"
                        stroke="#3182CE"
                        strokeWidth={2}
                        activeDot={{ r: 8 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              ) : (
                <Box height="300px" display="flex" alignItems="center" justifyContent="center">
                  <Text color="gray.500">No call history available</Text>
                </Box>
              )}
            </CardBody>
          </Card>
        </GridItem>
        
        {/* Call Distribution Pie Chart */}
        <GridItem colSpan={{ base: 12, lg: 4 }}>
          <Card height="100%">
            <CardHeader>
              <Heading size="md">Call Distribution</Heading>
            </CardHeader>
            <CardBody>
              {callDistribution.length > 0 ? (
                <Box height="300px">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={callDistribution}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      >
                        {callDistribution.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              ) : (
                <Box height="300px" display="flex" alignItems="center" justifyContent="center">
                  <Text color="gray.500">No call history available</Text>
                </Box>
              )}
            </CardBody>
          </Card>
        </GridItem>
        
        {/* Recent Calls Table */}
        <GridItem colSpan={12}>
          <Card>
            <CardHeader>
              <Flex justify="space-between" align="center">
                <Heading size="md">Recent Calls</Heading>
                
                <Button
                  variant="ghost"
                  rightIcon={<FiArrowRight />}
                  onClick={() => navigate('/call-history')}
                  size="sm"
                >
                  View All
                </Button>
              </Flex>
            </CardHeader>
            <CardBody>
              <RecentCallsTable calls={recentCalls} />
              
              {recentCalls.length === 0 && (
                <Box textAlign="center" py={10}>
                  <Text color="gray.500">No recent calls</Text>
                  <Button
                    mt={4}
                    colorScheme="blue"
                    leftIcon={<FiPhone />}
                    onClick={handleScheduleCall}
                  >
                    Schedule Your First Call
                  </Button>
                </Box>
              )}
            </CardBody>
          </Card>
        </GridItem>
      </Grid>
    </Box>
  );
};

export default Dashboard;
