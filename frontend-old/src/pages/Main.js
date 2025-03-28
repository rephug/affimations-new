import React, { useState, useEffect } from 'react';
import { ChakraProvider, Box, Flex, Grid, VStack, HStack, Heading, Text, Tabs, TabList, TabPanels, Tab, TabPanel } from '@chakra-ui/react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// Import components
import Sidebar from ../../components/Sidebar';
import Header from ../../components/Header';
import Dashboard from './pages/Dashboard';
import SMSTester from './pages/SMSTester';
import CallTester from './pages/CallTester';
import TTSTester from './pages/TTSTester';
import TranscriptionMonitor from './pages/TranscriptionMonitor';
import Settings from './pages/Settings';
import CallStatus from './pages/CallStatus';

// Import theme
import theme from './theme';

function App() {
  const [systemStatus, setSystemStatus] = useState({
    app: 'unknown',
    tts: 'unknown',
    telnyx: 'unknown',
    assemblyai: 'unknown',
    llm: 'unknown',
    redis: 'unknown'
  });

  useEffect(() => {
    // Fetch system status on component mount
    const fetchSystemStatus = async () => {
      try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        setSystemStatus({
          app: data.status,
          tts: data.services?.tts || 'unknown',
          telnyx: data.services?.telnyx || 'unknown',
          assemblyai: data.services?.assemblyai || 'unknown',
          llm: data.services?.llm || 'unknown',
          redis: data.services?.redis || 'unknown'
        });
      } catch (error) {
        console.error('Error fetching system status:', error);
      }
    };

    fetchSystemStatus();
    // Refresh status every 30 seconds
    const intervalId = setInterval(fetchSystemStatus, 30000);
    
    return () => clearInterval(intervalId);
  }, []);

  return (
    <ChakraProvider theme={theme}>
      <Router>
        <Box minH="100vh" bg="gray.50">
          <Sidebar />
          <Box ml={{ base: 0, md: 60 }} transition=".3s ease">
            <Header systemStatus={systemStatus} />
            <Box p="4">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/sms-tester" element={<SMSTester />} />
                <Route path="/call-tester" element={<CallTester />} />
                <Route path="/tts-tester" element={<TTSTester />} />
                <Route path="/transcription-monitor" element={<TranscriptionMonitor />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/call-status/:id" element={<CallStatus />} />
              </Routes>
            </Box>
          </Box>
        </Box>
      </Router>
    </ChakraProvider>
  );
}

export default App;
