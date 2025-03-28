import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { 
  ChakraProvider,
  Box, 
  Flex, 
  Grid, 
  VStack, 
  HStack, 
  Heading, 
  Text, 
  TabsRoot, 
  TabsList, 
  TabsContent, 
  TabsTrigger
} from '@chakra-ui/react';

// Import theme
import theme from './theme';

// Auth Context
import { AuthProvider } from './context/AuthContext';

// Import pages
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import Profile from './pages/Profile';
import TTSTester from './pages/TTSTester';
import CallTester from './pages/CallTester';
import TranscriptionMonitor from './pages/TranscriptionMonitor';
import ScheduleCall from './pages/ScheduleCall';

// Import components
import ProtectedRoute from './components/auth/ProtectedRoute';

function App() {
  return (
    <ChakraProvider theme={theme}>
      <AuthProvider>
        <Router>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            
            {/* Protected routes */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            <Route path="/profile" element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            } />
            <Route path="/tts-tester" element={
              <ProtectedRoute>
                <TTSTester />
              </ProtectedRoute>
            } />
            <Route path="/call-tester" element={
              <ProtectedRoute>
                <CallTester />
              </ProtectedRoute>
            } />
            <Route path="/transcription-monitor" element={
              <ProtectedRoute>
                <TranscriptionMonitor />
              </ProtectedRoute>
            } />
            <Route path="/schedule" element={
              <ProtectedRoute>
                <ScheduleCall />
              </ProtectedRoute>
            } />
            
            {/* Redirect to dashboard by default */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ChakraProvider>
  );
}

export default App;
