'use client';

// Add export to ensure Next.js generates this route correctly
export const dynamic = 'force-dynamic';

import React, { useState } from 'react';
import { GradientBackground, GradientHeading, CoffeeButton, CoffeeCard } from '@/components/ui/morning-coffee-theme';

// Affirmation options for the call
const AFFIRMATIONS = [
  "I am capable, confident, and creative in everything I do.",
  "Today I embrace my potential and make positive choices.",
  "I am worthy of success and appreciate my unique qualities.",
  "My mind is clear, focused, and ready for today's challenges.",
  "I trust my abilities and know that I can achieve my goals.",
  "I choose to be happy and spread positivity to others.",
];

export default function CallTestPage() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [selectedAffirmation, setSelectedAffirmation] = useState(AFFIRMATIONS[0]);
  const [customAffirmation, setCustomAffirmation] = useState('');
  const [useCustomAffirmation, setUseCustomAffirmation] = useState(false);
  const [isCalling, setIsCalling] = useState(false);
  const [callStatus, setCallStatus] = useState<null | 'success' | 'error'>(null);
  const [callMessage, setCallMessage] = useState('');

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

    setIsCalling(true);
    setCallStatus(null);
    setCallMessage('');

    try {
      // Call the API endpoint to initiate the call
      const response = await fetch('/api/call/initiate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phoneNumber: phoneDigits,
          affirmation: affirmationText,
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
      setIsCalling(false);
    }
  };

  return (
    <GradientBackground className="p-6">
      <div className="max-w-4xl mx-auto">
        <GradientHeading className="mb-8">Call Testing Lab</GradientHeading>
        
        <CoffeeCard className="mb-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Phone Number</h2>
          <p className="text-medium-brown mb-4">Enter the phone number to call:</p>
          
          <input
            type="tel"
            value={phoneNumber}
            onChange={handlePhoneChange}
            placeholder="(123) 456-7890"
            className="w-full p-3 border border-caramel rounded-lg bg-cream"
          />
        </CoffeeCard>
        
        <CoffeeCard className="mb-6">
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
        </CoffeeCard>
        
        <CoffeeCard className="mb-6">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Call Controls</h2>
          
          <CoffeeButton 
            onClick={initiateCall}
            disabled={isCalling || !phoneNumber}
            className="w-full"
          >
            {isCalling ? 'Initiating Call...' : 'Call Now'}
          </CoffeeButton>
          
          {callStatus && (
            <div className={`mt-4 p-4 rounded-lg ${
              callStatus === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              {callMessage}
            </div>
          )}
        </CoffeeCard>
        
        <CoffeeCard>
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">How It Works</h2>
          <p className="text-medium-brown mb-2">
            This test page allows you to send a call to any phone number. The recipient will:
          </p>
          <ol className="list-decimal pl-5 space-y-2 text-medium-brown">
            <li>Receive a call from our service</li>
            <li>Hear the selected affirmation in the chosen voice</li>
            <li>Be prompted to repeat the affirmation</li>
            <li>Receive feedback and encouragement</li>
          </ol>
          <p className="mt-4 text-deep-brown font-medium">
            Note: This is a testing environment. In production, calls would be scheduled and managed through the main dashboard.
          </p>
        </CoffeeCard>
      </div>
    </GradientBackground>
  );
} 