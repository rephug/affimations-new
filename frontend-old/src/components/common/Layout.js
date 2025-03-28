import React, { useState } from 'react';
import { 
  Box, 
  Flex, 
  Text, 
  IconButton, 
  Avatar, 
  HStack, 
  VStack, 
  useDisclosure, 
  Drawer,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  DrawerHeader,
  DrawerBody,
  Badge,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  MenuDivider,
  useColorModeValue,
  Divider
} from '@chakra-ui/react';
import { 
  FiMenu, 
  FiHome, 
  FiCalendar, 
  FiPhone, 
  FiMessageSquare, 
  FiActivity, 
  FiSettings, 
  FiUser,
  FiLogOut,
  FiHelpCircle,
  FiChevronDown
} from 'react-icons/fi';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Logo from './Logo';

// Navigation items for the sidebar
const NAV_ITEMS = [
  { label: 'Dashboard', icon: FiHome, to: '/dashboard' },
  { label: 'Schedule Call', icon: FiCalendar, to: '/schedule' },
  { label: 'Call Tester', icon: FiPhone, to: '/call-tester' },
  { label: 'TTS Tester', icon: FiMessageSquare, to: '/tts-tester' },
  { label: 'Transcriptions', icon: FiActivity, to: '/transcription-monitor' },
];

const SidebarContent = ({ onClose, ...rest }) => {
  const location = useLocation();
  
  return (
    <Box
      bg={useColorModeValue('white', 'gray.900')}
      borderRight="1px"
      borderRightColor={useColorModeValue('gray.200', 'gray.700')}
      w={{ base: 'full', md: 60 }}
      pos="fixed"
      h="full"
      {...rest}
    >
      <Flex h="20" alignItems="center" mx="8" justifyContent="space-between">
        <Logo size="md" />
        <CloseButton display={{ base: 'flex', md: 'none' }} onClick={onClose} />
      </Flex>
      <VStack align="stretch" spacing={1} px={2}>
        {NAV_ITEMS.map((navItem) => (
          <NavItem 
            key={navItem.label} 
            icon={navItem.icon} 
            to={navItem.to}
            isActive={location.pathname === navItem.to}
          >
            {navItem.label}
          </NavItem>
        ))}
        
        <Divider my={4} />
        
        <NavItem 
          icon={FiSettings} 
          to="/profile"
          isActive={location.pathname === '/profile'}
        >
          Account Settings
        </NavItem>
      </VStack>
    </Box>
  );
};

const NavItem = ({ icon, to, children, isActive, ...rest }) => {
  return (
    <Link to={to} style={{ textDecoration: 'none' }}>
      <Flex
        align="center"
        p="4"
        mx="4"
        borderRadius="lg"
        role="group"
        cursor="pointer"
        bg={isActive ? 'blue.50' : 'transparent'}
        color={isActive ? 'blue.600' : 'gray.600'}
        fontWeight={isActive ? 'bold' : 'normal'}
        _hover={{
          bg: 'blue.50',
          color: 'blue.600',
        }}
        {...rest}
      >
        {icon && (
          <Box mr="4" color={isActive ? 'blue.500' : 'gray.500'}>
            {React.createElement(icon)}
          </Box>
        )}
        {children}
      </Flex>
    </Link>
  );
};

const CloseButton = ({ ...rest }) => {
  return (
    <IconButton
      variant="ghost"
      icon={<FiMenu />}
      {...rest}
    />
  );
};

const MobileNav = ({ onOpen, ...rest }) => {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  
  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
  };

  return (
    <Flex
      ml={{ base: 0, md: 60 }}
      px={{ base: 4, md: 4 }}
      height="20"
      alignItems="center"
      bg={useColorModeValue('white', 'gray.900')}
      borderBottomWidth="1px"
      borderBottomColor={useColorModeValue('gray.200', 'gray.700')}
      justifyContent={{ base: 'space-between', md: 'flex-end' }}
      {...rest}
    >
      <IconButton
        display={{ base: 'flex', md: 'none' }}
        onClick={onOpen}
        variant="outline"
        aria-label="open menu"
        icon={<FiMenu />}
      />

      <HStack spacing={{ base: '0', md: '6' }}>
        <Flex alignItems={'center'}>
          <Menu>
            <MenuButton
              py={2}
              transition="all 0.3s"
              _focus={{ boxShadow: 'none' }}
            >
              <HStack>
                <Avatar
                  size={'sm'}
                  name={user?.user_metadata?.full_name || user?.email}
                  src={user?.user_metadata?.avatar_url}
                />
                <VStack
                  display={{ base: 'none', md: 'flex' }}
                  alignItems="flex-start"
                  spacing="1px"
                  ml="2"
                >
                  <Text fontSize="sm" fontWeight="bold">
                    {user?.user_metadata?.full_name || 'User'}
                  </Text>
                  <Text fontSize="xs" color="gray.600">
                    {user?.email}
                  </Text>
                </VStack>
                <Box display={{ base: 'none', md: 'flex' }}>
                  <FiChevronDown />
                </Box>
              </HStack>
            </MenuButton>
            <MenuList
              bg={useColorModeValue('white', 'gray.900')}
              borderColor={useColorModeValue('gray.200', 'gray.700')}
            >
              <MenuItem as={Link} to="/profile" icon={<FiUser />}>
                Profile
              </MenuItem>
              <MenuItem as={Link} to="/dashboard" icon={<FiHome />}>
                Dashboard
              </MenuItem>
              <MenuItem as={Link} to="/schedule" icon={<FiCalendar />}>
                Schedule Call
              </MenuItem>
              <MenuDivider />
              <MenuItem as={Link} to="#" icon={<FiHelpCircle />}>
                Help & Support
              </MenuItem>
              <MenuItem onClick={handleSignOut} icon={<FiLogOut />}>
                Sign Out
              </MenuItem>
            </MenuList>
          </Menu>
        </Flex>
      </HStack>
    </Flex>
  );
};

const Layout = ({ children }) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  
  return (
    <Box minH="100vh" bg={useColorModeValue('gray.50', 'gray.900')}>
      <SidebarContent 
        onClose={onClose} 
        display={{ base: 'none', md: 'block' }} 
      />
      <Drawer
        isOpen={isOpen}
        placement="left"
        onClose={onClose}
        returnFocusOnClose={false}
        onOverlayClick={onClose}
      >
        <DrawerOverlay />
        <DrawerContent>
          <DrawerCloseButton />
          <DrawerHeader>Morning Coffee</DrawerHeader>
          <DrawerBody p={0}>
            <SidebarContent onClose={onClose} />
          </DrawerBody>
        </DrawerContent>
      </Drawer>
      <MobileNav onOpen={onOpen} />
      <Box ml={{ base: 0, md: 60 }} p="4">
        {children}
      </Box>
    </Box>
  );
};

export default Layout; 