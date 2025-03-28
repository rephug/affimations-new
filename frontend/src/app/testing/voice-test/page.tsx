'use client';

// Add export to ensure Next.js generates this route correctly
export const dynamic = 'force-dynamic';

import React, { useState, useRef } from 'react';
import { GradientBackground, GradientHeading, CoffeeButton } from '@/components/ui/morning-coffee-theme';

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

// Define provider type based on the keys of VOICE_OPTIONS
type ProviderType = keyof typeof VOICE_OPTIONS;

export default function VoiceTestPage() {
  const [provider, setProvider] = useState<ProviderType>('openai');
  const [voice, setVoice] = useState('alloy');
  const [text, setText] = useState('Good morning! Welcome to your day. You are capable, creative, and ready to succeed.');
  const [speed, setSpeed] = useState(1.0);
  const [pitch, setPitch] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState('');
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handleProviderChange = (newProvider: ProviderType) => {
    console.log("Switching TTS provider to:", newProvider);
    setProvider(newProvider);
    // Set default voice for the new provider
    setVoice(VOICE_OPTIONS[newProvider][0].id);
  };

  const generateSpeech = async () => {
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

  return (
    <GradientBackground className="min-h-screen p-6">
      <div className="max-w-4xl mx-auto">
        <GradientHeading className="mb-8">Voice Testing Lab</GradientHeading>
        
        {/* Provider Selection */}
        <div className="morning-coffee-card p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Provider Selection</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {TTS_PROVIDERS.map((ttsProvider) => (
              <button
                type="button"
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
              </button>
            ))}
          </div>
        </div>
        
        {/* Voice Selection */}
        <div className="morning-coffee-card p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Voice Selection</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {VOICE_OPTIONS[provider].map((voiceOption) => (
              <button
                type="button"
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
              </button>
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
        
        {/* Text Input */}
        <div className="morning-coffee-card p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Text Input</h2>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter text to convert to speech..."
            className="w-full p-3 border border-caramel rounded-lg bg-cream min-h-[120px]"
          />
          
          <div className="mt-4">
            <button
              onClick={generateSpeech}
              disabled={isLoading || !text}
              className={`morning-coffee-button w-full ${isLoading ? 'opacity-70 cursor-not-allowed' : ''}`}
            >
              {isLoading ? 'Generating...' : 'Generate Speech'}
            </button>
          </div>
        </div>
        
        {/* Audio Player */}
        {audioUrl && (
          <div className="morning-coffee-card p-6">
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
      </div>
    </GradientBackground>
  );
} 