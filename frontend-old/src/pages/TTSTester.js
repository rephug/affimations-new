import React, { useState, useEffect, useRef } from 'react';
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
  Select,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Stack,
  Text,
  Textarea,
  VStack,
  HStack,
  useToast,
  IconButton,
  Badge,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Spinner,
  Alert,
  AlertIcon,
  Tabs, 
  TabList, 
  TabPanels, 
  Tab, 
  TabPanel,
  Center,
  Divider
} from '@chakra-ui/react';
import { FiPlay, FiDownload, FiSave, FiCopy, FiList, FiRefreshCw } from 'react-icons/fi';

const TTSTester = () => {
  const [text, setText] = useState("Welcome to the Morning Coffee TTS tester. This text will be converted to speech when you press the Generate button.");
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState("default");
  const [speed, setSpeed] = useState(1.0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [ttsInfo, setTtsInfo] = useState(null);
  const [recentGenerations, setRecentGenerations] = useState([]);
  const [isLoadingVoices, setIsLoadingVoices] = useState(true);
  
  const audioRef = useRef(null);
  const toast = useToast();

  useEffect(() => {
    // Fetch available voices
    fetchVoices();
    fetchTtsInfo();
  }, []);

  const fetchVoices = async () => {
    setIsLoadingVoices(true);
    try {
      const response = await fetch('/tts/voices');
      if (!response.ok) {
        throw new Error(`Failed to fetch voices: ${response.status}`);
      }
      
      const data = await response.json();
      setVoices(data.voices || []);
    } catch (error) {
      console.error('Error fetching voices:', error);
      toast({
        title: 'Failed to fetch voices',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoadingVoices(false);
    }
  };

  const fetchTtsInfo = async () => {
    try {
      const response = await fetch('/tts/info');
      if (!response.ok) {
        throw new Error(`Failed to fetch TTS info: ${response.status}`);
      }
      
      const data = await response.json();
      setTtsInfo(data);
    } catch (error) {
      console.error('Error fetching TTS info:', error);
    }
  };

  const generateSpeech = async () => {
    if (!text.trim()) {
      toast({
        title: 'Text is required',
        description: 'Please enter some text to generate speech',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsGenerating(true);
    
    try {
      // Prepare the request payload
      const payload = {
        text,
        voice_id: selectedVoice,
        speed
      };

      // Generate the speech
      const response = await fetch('/tts/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Failed to generate speech: ${response.status}`);
      }

      // Get the audio data
      const audioBlob = await response.blob();
      const url = URL.createObjectURL(audioBlob);
      
      // Create a timestamp for the generation
      const timestamp = new Date().toISOString();
      
      // Save to recent generations
      const newGeneration = {
        id: `gen-${Date.now()}`,
        text: text.length > 50 ? `${text.substring(0, 50)}...` : text,
        fullText: text,
        voice: selectedVoice,
        speed,
        timestamp,
        audioUrl: url,
        blob: audioBlob
      };
      
      setRecentGenerations(prev => [newGeneration, ...prev].slice(0, 10));
      
      // Set the audio URL and play it
      setAudioUrl(url);
      
      // Play the audio
      if (audioRef.current) {
        audioRef.current.load();
        audioRef.current.play();
      }
      
      toast({
        title: 'Speech generated',
        description: 'Speech has been generated successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Error generating speech:', error);
      toast({
        title: 'Failed to generate speech',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadAudio = (url, filename = 'speech.wav') => {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const playAudio = (url) => {
    setAudioUrl(url);
    
    // Play the audio
    setTimeout(() => {
      if (audioRef.current) {
        audioRef.current.load();
        audioRef.current.play();
      }
    }, 100);
  };

  const copyToForm = (item) => {
    setText(item.fullText);
    setSelectedVoice(item.voice);
    setSpeed(item.speed);
    
    toast({
      title: 'Copied to form',
      description: 'The settings have been applied to the form',
      status: 'info',
      duration: 2000,
      isClosable: true,
    });
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  return (
    <Box>
      <Heading mb={6}>TTS Tester</Heading>
      
      <Tabs variant="enclosed" mb={8}>
        <TabList>
          <Tab>Generate Speech</Tab>
          <Tab>Recent Generations</Tab>
          <Tab>System Info</Tab>
        </TabList>
        
        <TabPanels>
          <TabPanel>
            <Card>
              <CardHeader>
                <Heading size="md">Text-to-Speech Generator</Heading>
              </CardHeader>
              <CardBody>
                <VStack spacing={5} align="stretch">
                  <FormControl>
                    <FormLabel>Text to Convert</FormLabel>
                    <Textarea
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                      placeholder="Enter text to convert to speech"
                      size="md"
                      rows={6}
                    />
                  </FormControl>
                  
                  <HStack>
                    <FormControl>
                      <FormLabel>Voice</FormLabel>
                      {isLoadingVoices ? (
                        <HStack>
                          <Spinner size="sm" />
                          <Text>Loading voices...</Text>
                        </HStack>
                      ) : (
                        <Select 
                          value={selectedVoice} 
                          onChange={(e) => setSelectedVoice(e.target.value)}
                        >
                          {voices.map(voice => (
                            <option key={voice.id} value={voice.id}>
                              {voice.name}
                            </option>
                          ))}
                        </Select>
                      )}
                    </FormControl>
                    
                    <FormControl>
                      <FormLabel>Speed: {speed.toFixed(1)}x</FormLabel>
                      <Slider
                        min={0.5}
                        max={1.5}
                        step={0.1}
                        value={speed}
                        onChange={(val) => setSpeed(val)}
                      >
                        <SliderTrack>
                          <SliderFilledTrack />
                        </SliderTrack>
                        <SliderThumb />
                      </Slider>
                    </FormControl>
                  </HStack>
                  
                  <HStack>
                    <Button
                      colorScheme="blue"
                      onClick={generateSpeech}
                      isLoading={isGenerating}
                      loadingText="Generating"
                      leftIcon={<FiPlay />}
                    >
                      Generate Speech
                    </Button>
                    
                    {audioUrl && (
                      <Button
                        colorScheme="green"
                        onClick={() => downloadAudio(audioUrl)}
                        leftIcon={<FiDownload />}
                      >
                        Download
                      </Button>
                    )}
                    
                    <Button
                      variant="outline"
                      onClick={fetchVoices}
                      leftIcon={<FiRefreshCw />}
                    >
                      Refresh Voices
                    </Button>
                  </HStack>
                  
                  {audioUrl && (
                    <Box border="1px" borderColor="gray.200" p={4} borderRadius="md">
                      <Text mb={2}>Generated Audio:</Text>
                      <audio ref={audioRef} controls style={{ width: '100%' }}>
                        <source src={audioUrl} type="audio/wav" />
                        Your browser does not support the audio element.
                      </audio>
                    </Box>
                  )}
                </VStack>
              </CardBody>
            </Card>
          </TabPanel>
          
          <TabPanel>
            <Card>
              <CardHeader>
                <Heading size="md">Recent Generations</Heading>
              </CardHeader>
              <CardBody>
                {recentGenerations.length === 0 ? (
                  <Text>No recent generations</Text>
                ) : (
                  <Table variant="simple">
                    <Thead>
                      <Tr>
                        <Th>Time</Th>
                        <Th>Text</Th>
                        <Th>Voice</Th>
                        <Th>Speed</Th>
                        <Th>Actions</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {recentGenerations.map((item) => (
                        <Tr key={item.id}>
                          <Td>{formatTimestamp(item.timestamp)}</Td>
                          <Td>{item.text}</Td>
                          <Td>{item.voice}</Td>
                          <Td>{item.speed}x</Td>
                          <Td>
                            <HStack spacing={2}>
                              <IconButton
                                aria-label="Play"
                                icon={<FiPlay />}
                                size="sm"
                                onClick={() => playAudio(item.audioUrl)}
                              />
                              <IconButton
                                aria-label="Download"
                                icon={<FiDownload />}
                                size="sm"
                                onClick={() => downloadAudio(item.audioUrl)}
                              />
                              <IconButton
                                aria-label="Copy to form"
                                icon={<FiCopy />}
                                size="sm"
                                onClick={() => copyToForm(item)}
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
          
          <TabPanel>
            <Card>
              <CardHeader>
                <Heading size="md">TTS System Information</Heading>
              </CardHeader>
              <CardBody>
                {!ttsInfo ? (
                  <Center>
                    <Spinner />
                  </Center>
                ) : (
                  <VStack align="start" spacing={4}>
                    <Box>
                      <Text fontWeight="bold">Service Name:</Text>
                      <Text>{ttsInfo.name}</Text>
                    </Box>
                    
                    <Box>
                      <Text fontWeight="bold">Model:</Text>
                      <Text>{ttsInfo.model}</Text>
                    </Box>
                    
                    <Box>
                      <Text fontWeight="bold">Sample Rate:</Text>
                      <Text>{ttsInfo.sample_rate} Hz</Text>
                    </Box>
                    
                    <Box>
                      <Text fontWeight="bold">Hardware:</Text>
                      <HStack>
                        <Text>{ttsInfo.device}</Text>
                        {ttsInfo.gpu_available && (
                          <Badge colorScheme="green">GPU Accelerated</Badge>
                        )}
                      </HStack>
                    </Box>
                    
                    <Divider />
                    
                    <Box>
                      <Text fontWeight="bold">Available Voices:</Text>
                      {isLoadingVoices ? (
                        <Spinner size="sm" ml={2} />
                      ) : (
                        <Table variant="simple" size="sm">
                          <Thead>
                            <Tr>
                              <Th>ID</Th>
                              <Th>Name</Th>
                              <Th>Description</Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {voices.map(voice => (
                              <Tr key={voice.id}>
                                <Td>{voice.id}</Td>
                                <Td>{voice.name}</Td>
                                <Td>{voice.description}</Td>
                              </Tr>
                            ))}
                          </Tbody>
                        </Table>
                      )}
                    </Box>
                    
                    <Button
                      leftIcon={<FiRefreshCw />}
                      onClick={() => {
                        fetchVoices();
                        fetchTtsInfo();
                      }}
                    >
                      Refresh Information
                    </Button>
                  </VStack>
                )}
              </CardBody>
            </Card>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default TTSTester;
