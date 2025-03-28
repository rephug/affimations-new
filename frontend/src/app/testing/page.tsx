'use client';

// Add export to ensure Next.js generates this route correctly
export const dynamic = 'force-dynamic';

import React from 'react';
import Link from 'next/link';
import { GradientBackground, GradientHeading, CoffeeCard } from '@/components/ui/morning-coffee-theme';

const testingTools = [
  {
    title: 'Voice & Call Testing Lab',
    description: 'Test voice providers and make calls with selected voices',
    link: '/testing/voice-call-lab',
    icon: '🎙️📞',
  },
  {
    title: 'Voice Testing',
    description: 'Test different TTS providers and voices',
    link: '/testing/voice-test',
    icon: '🎙️',
  },
  {
    title: 'Call Testing',
    description: 'Test phone call functionality',
    link: '/testing/call-test',
    icon: '📞',
  },
  {
    title: 'API Health Check',
    description: 'Check the status of various API endpoints and services',
    link: '/api/health',
    icon: '🩺',
  },
];

export default function TestingPage() {
  return (
    <GradientBackground className="p-6">
      <div className="max-w-4xl mx-auto">
        <GradientHeading className="mb-8">Morning Coffee Testing Suite</GradientHeading>
        
        <CoffeeCard className="mb-8">
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">Testing Tools</h2>
          <p className="text-medium-brown mb-6">
            Select one of the testing tools below to help debug and test the Morning Coffee system.
            These tools are intended for development and testing purposes.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {testingTools.map((tool, index) => (
              <Link 
                key={index}
                href={tool.link}
                className="block hover:no-underline"
              >
                <div className="bg-cream hover:bg-caramel transition-all p-6 rounded-xl h-full flex flex-col">
                  <div className="text-4xl mb-3">{tool.icon}</div>
                  <h3 className="text-xl font-semibold mb-2 text-deep-brown">{tool.title}</h3>
                  <p className="text-medium-brown">{tool.description}</p>
                </div>
              </Link>
            ))}
          </div>
        </CoffeeCard>
        
        <CoffeeCard>
          <h2 className="text-2xl font-semibold mb-4 text-deep-brown">System Information</h2>
          
          <div className="space-y-4">
            <div className="bg-cream p-4 rounded-lg">
              <h3 className="font-medium text-deep-brown">Environment</h3>
              <p className="text-medium-brown">Production</p>
            </div>
            
            <div className="bg-cream p-4 rounded-lg">
              <h3 className="font-medium text-deep-brown">Build Information</h3>
              <p className="text-medium-brown">Version: {process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0'}</p>
              <p className="text-medium-brown">Build Date: {new Date().toLocaleDateString()}</p>
            </div>
            
            <div className="bg-cream p-4 rounded-lg">
              <h3 className="font-medium text-deep-brown">Connected Services</h3>
              <ul className="list-disc list-inside text-medium-brown">
                <li>TTS Service: OpenAI API</li>
                <li>Calling Service: Telnyx</li>
                <li>Voice Analysis: AssemblyAI</li>
                <li>Database: Supabase</li>
              </ul>
            </div>
          </div>
        </CoffeeCard>
      </div>
    </GradientBackground>
  );
} 