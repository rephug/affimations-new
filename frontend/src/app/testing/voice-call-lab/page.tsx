'use client';

// Add export to ensure Next.js generates this route correctly
export const dynamic = 'force-dynamic';

import React, { useState, useRef } from 'react';
import { GradientBackground, GradientHeading, CoffeeButton, CoffeeCard } from '@/components/ui/morning-coffee-theme';

// TTS Provider options
const TTS_PROVIDERS = [
  { id: 'openai', name: 'OpenAI', description: 'OpenAI TTS voices' },
  { id: 'elevenlabs', name: 'ElevenLabs', description: 'ElevenLabs voices' },
  { id: 'kokoro', name: 'Kokoro', description: 'Kokoro voices' },
  { id: 'google', name: 'Google', description: 'Google voices' },
  { id: 'murf', name: 'Murf', description: 'Murf voices' },
  { id: 'azure', name: 'Azure', description: 'Azure voices' },
  { id: 'telnyx', name: 'Telnyx', description: 'Telnyx voices' },
];

// Voice options for each provider
const VOICE_OPTIONS = {
  openai: [
    { id: 'alloy', name: 'Alloy', description: 'Versatile, general purpose voice' },
    { id: 'echo', name: 'Echo', description: 'Focused, clear voice' },
    { id: 'fable', name: 'Fable', description: 'Narrative, warm voice' },
    { id: 'onyx', name: 'Onyx', description: 'Deep, authoritative voice' },
    { id: 'nova', name: 'Nova', description: 'Energetic, optimistic voice' },
    { id: 'shimmer', name: 'Shimmer', description: 'Confident, friendly, professional voice' }
  ],
  elevenlabs: [
    { id: 'rachel', name: 'Rachel', description: 'Clear feminine voice' },
    { id: 'domi', name: 'Domi', description: 'Neutral voice' },
    { id: 'bella', name: 'Bella', description: 'Soft feminine voice' },
    { id: 'antoni', name: 'Antoni', description: 'Deep masculine voice' }
  ],
  kokoro: [
    { id: 'female', name: 'Female', description: 'Standard female voice' },
    { id: 'male', name: 'Male', description: 'Standard male voice' }
  ],
  google: [
    { id: 'en-US-Standard-C', name: 'Female', description: 'Standard female voice' },
    { id: 'en-US-Standard-D', name: 'Male', description: 'Standard male voice' }
  ],
  murf: [
    { id: 'en-US-jenny', name: 'Jenny', description: 'Female voice' },
    { id: 'en-US-mike', name: 'Mike', description: 'Male voice' }
  ],
  azure: [
    { id: 'en-US-JennyNeural', name: 'Jenny', description: 'Female neural voice' },
    { id: 'en-US-GuyNeural', name: 'Guy', description: 'Male neural voice' }
  ],
  telnyx: [
    { id: 'female', name: 'Female', description: 'Female voice' },
    { id: 'male', name: 'Male', description: 'Male voice' }
  ]
} as const;

// Affirmation options for the call
const AFFIRMATIONS = [
  "I am capable, confident, and creative in everything I do.",
  "Today I embrace my potential and make positive choices.",
  "I am worthy of success and appreciate my unique qualities.",
  "My mind is clear, focused, and ready for today's challenges.",
  "I trust my abilities and know that I can achieve my goals.",
  "I choose to be happy and spread positivity to others.",
];

// Define provider type based on the keys of VOICE_OPTIONS
type ProviderType = keyof typeof VOICE_OPTIONS;

export default function VoiceCallLabPage() {
  // Voice selection states
  const [provider, setProvider] = useState<ProviderType>('openai');
  const [voice, setVoice] = useState('alloy');
  const [speed, setSpeed] = useState(1.0);
  const [pitch, setPitch] = useState(0);
  
  // Call states
  const [phoneNumber, setPhoneNumber] = useState('');
  const [selectedAffirmation, setSelectedAffirmation] = useState(AFFIRMATIONS[0]);
  const [customAffirmation, setCustomAffirmation] = useState('');
  const [useCustomAffirmation, setUseCustomAffirmation] = useState(false);
  
  // Shared states
  const [isLoading, setIsLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState('');
  const [callStatus, setCallStatus] = useState<null | 'success' | 'error'>(null);
  const [callMessage, setCallMessage] = useState('');
  const audioRef = useRef<HTMLAudioElement | null>(null);
  
  // Format phone number input
  const formatPhoneNumber = (value: string) => {
    // Strip all non-numeric characters
    const phoneDigits = value.replace(/\D/g, '');
    
    // Format with proper US pattern
    if (phoneDigits.length <= 3) {
      return phoneDigits;
    } else if (phoneDigits.length <= 6) {
      return `(${phoneDigits.slice(0, 3)}) ${phoneDigits.slice(3)}`;
    } else {
      return `(${phoneDigits.slice(0, 3)}) ${phoneDigits.slice(3, 6)}-${phoneDigits.slice(6, 10)}`;
    }
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPhoneNumber(formatPhoneNumber(e.target.value));
  };

  const handleProviderChange = (newProvider: ProviderType) => {
    setProvider(newProvider);
    // Set default voice for the new provider
    setVoice(VOICE_OPTIONS[newProvider][0].id);
  };

  const generateSpeech = async () => {
    // Get the affirmation text to use
    const text = useCustomAffirmation ? customAffirmation : selectedAffirmation;
    if (!text) return;
    
    setIsLoading(true);
    console.log(`Generating speech using provider: ${provider}, voice: ${voice}`);
    
    try {
      const response = await fetch('/api/tts/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text,
          provider,
          voice,
          speed,
          pitch,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate speech');
      }
      
      const data = await response.json();
      console.log('Generated audio:', data);
      setAudioUrl(data.audioUrl);
      
      // Play audio
      if (audioRef.current) {
        audioRef.current.load();
        audioRef.current.play().catch(err => console.error('Error playing audio:', err));
      }
    } catch (error) {
      console.error('Error generating speech:', error);
      alert('Failed to generate speech. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const initiateCall = async () => {
    // Validate phone number 
    const phoneDigits = phoneNumber.replace(/\D/g, '');
    if (phoneDigits.length !== 10) {
      setCallStatus('error');
      setCallMessage('Please enter a valid 10-digit phone number');
      return;
    }

    // Get the affirmation text to use
    const affirmationText = useCustomAffirmation ? customAffirmation : selectedAffirmation;
    if (!affirmationText) {
      setCallStatus('error');
      setCallMessage('Please select or enter an affirmation');
      return;
    }

    setIsLoading(true);
    setCallStatus(null);
    setCallMessage('');

    try {
      // Call the API endpoint to initiate the call with the selected voice
      const response = await fetch('/api/call/initiate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phoneNumber: phoneDigits,
          affirmation: affirmationText,
          voiceSettings: {
            provider,
            voice,
            speed,
            pitch
          }
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
        throw new Error(errorData.message || 'Failed to initiate call');
      }
      
      const data = await response.json();
      setCallStatus('success');
      
      // Check if it's a mock response
      if (data.isMock) {
        setCallMessage(`${data.message} (Note: This is a simulated call since the backend service is not available)`);
      } else {
        setCallMessage(data.message);
      }
    } catch (error) {
      console.error('Error initiating call:', error);
      setCallStatus('error');
      setCallMessage(`Failed to initiate call: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="morning-coffee-gradient min-h-screen p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold gradient-heading mb-8">Voice & Call Testing Lab</h1>
        
        {/* Provider Selection */}
        <div className="morning-coffee-card p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Provider Selection</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {TTS_PROVIDERS.map((ttsProvider) => (
              <div
                key={ttsProvider.id}
                className={`p-4 rounded-xl cursor-pointer transition-all ${
                  provider === ttsProvider.id
                    ? 'bg-sunrise-orange text-white'
                    : 'bg-cream hover:bg-caramel'
                }`}
                onClick={() => handleProviderChange(ttsProvider.id as ProviderType)}
              >
                <h3 className="font-bold">{ttsProvider.name}</h3>
                <p className="text-sm">{ttsProvider.description}</p>
              </div>
            ))}
          </div>
        </div>
        
        {/* Voice Selection */}
        <div className="morning-coffee-card p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Voice Selection</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {VOICE_OPTIONS[provider].map((voiceOption) => (
              <div
                key={voiceOption.id}
                className={`p-4 rounded-xl cursor-pointer transition-all ${
                  voice === voiceOption.id
                    ? 'bg-sunrise-orange text-white'
                    : 'bg-cream hover:bg-caramel'
                }`}
                onClick={() => setVoice(voiceOption.id)}
              >
                <h3 className="font-bold">{voiceOption.name}</h3>
                <p className="text-sm">{voiceOption.description}</p>
              </div>
            ))}
          </div>
        </div>
        
        {/* Voice Styling */}
        <div className="morning-coffee-card p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Voice Styling</h2>
          
          <div className="mb-4">
            <label className="block text-medium-brown mb-2">Speed: {speed}</label>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={speed}
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>
          
          <div className="mb-4">
            <label className="block text-medium-brown mb-2">Pitch: {pitch}</label>
            <input
              type="range"
              min="-10"
              max="10"
              step="1"
              value={pitch}
              onChange={(e) => setPitch(parseInt(e.target.value))}
              className="w-full"
            />
          </div>
        </div>
        
        {/* Phone Number */}
        <div className="morning-coffee-card p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Phone Number</h2>
          <p className="text-medium-brown mb-4">Enter the phone number to call:</p>
          
          <input
            type="tel"
            value={phoneNumber}
            onChange={handlePhoneChange}
            placeholder="(123) 456-7890"
            className="w-full p-3 border border-caramel rounded-lg bg-cream"
          />
        </div>
        
        {/* Affirmation Selection */}
        <div className="morning-coffee-card p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Affirmation Selection</h2>
          
          <div className="flex items-center mb-4">
            <input
              type="checkbox"
              id="useCustom"
              checked={useCustomAffirmation}
              onChange={() => setUseCustomAffirmation(!useCustomAffirmation)}
              className="mr-2"
            />
            <label htmlFor="useCustom" className="text-medium-brown">Use custom affirmation</label>
          </div>
          
          {useCustomAffirmation ? (
            <textarea
              value={customAffirmation}
              onChange={(e) => setCustomAffirmation(e.target.value)}
              placeholder="Enter your custom affirmation..."
              className="w-full p-3 border border-caramel rounded-lg bg-cream min-h-[120px]"
            />
          ) : (
            <div className="space-y-2">
              {AFFIRMATIONS.map((affirmation, index) => (
                <div 
                  key={index}
                  className={`p-3 rounded-lg cursor-pointer ${
                    selectedAffirmation === affirmation 
                      ? 'bg-sunrise-orange text-white' 
                      : 'bg-cream hover:bg-caramel'
                  }`}
                  onClick={() => setSelectedAffirmation(affirmation)}
                >
                  {affirmation}
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Action Buttons */}
        <div className="morning-coffee-card p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Test Options</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <CoffeeButton 
                onClick={generateSpeech}
                disabled={isLoading || (!useCustomAffirmation && !selectedAffirmation) || (useCustomAffirmation && !customAffirmation)}
                className="w-full"
              >
                {isLoading ? 'Generating...' : 'Generate Speech (Test)'}
              </CoffeeButton>
              
              <p className="mt-2 text-sm text-medium-brown">
                Generate and play the affirmation with the selected voice settings.
              </p>
            </div>
            
            <div>
              <CoffeeButton 
                onClick={initiateCall}
                disabled={isLoading || !phoneNumber || (!useCustomAffirmation && !selectedAffirmation) || (useCustomAffirmation && !customAffirmation)}
                className="w-full"
              >
                {isLoading ? 'Initiating...' : 'Make Call'}
              </CoffeeButton>
              
              <p className="mt-2 text-sm text-medium-brown">
                Call the phone number and deliver the affirmation with the selected voice.
              </p>
            </div>
          </div>
          
          {/* Status messages */}
          {callStatus && (
            <div className={`mt-4 p-4 rounded-lg ${
              callStatus === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              {callMessage}
            </div>
          )}
        </div>
        
        {/* Audio Player */}
        {audioUrl && (
          <div className="morning-coffee-card p-6 mb-6">
            <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Generated Audio</h2>
            <div className="mb-2 text-gray-700">
              Provider: <span className="font-semibold">{provider}</span> | 
              Voice: <span className="font-semibold">{voice}</span>
            </div>
            <audio ref={audioRef} controls className="w-full">
              <source src={audioUrl} type="audio/mpeg" />
              Your browser does not support the audio element.
            </audio>
          </div>
        )}
        
        {/* How It Works */}
        <div className="morning-coffee-card p-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">How It Works</h2>
          <p className="text-medium-brown mb-2">
            This testing lab allows you to:
          </p>
          <ol className="list-decimal pl-5 space-y-2 text-medium-brown">
            <li>Select a TTS provider and voice</li>
            <li>Adjust voice settings like speed and pitch</li>
            <li>Test the voice by generating sample audio</li>
            <li>Make a real call with your selected voice and affirmation</li>
          </ol>
          <p className="mt-4 text-deep-brown font-medium">
            Note: This is a testing environment. In production, calls would be scheduled and managed through the main dashboard.
          </p>
        </div>
      </div>
    </div>
  );
} 