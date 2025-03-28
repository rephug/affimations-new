import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const { text, provider, voice } = await request.json();

    if (!text || !provider || !voice) {
      return NextResponse.json(
        { error: 'Missing required parameters' },
        { status: 400 }
      );
    }

    // Call the backend TTS API
    // In production, this would connect to the actual backend service
    const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:5000';
    
    const response = await fetch(`${backendUrl}/api/tts/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.API_KEY || 'test-key'}`,
      },
      body: JSON.stringify({
        text,
        provider,
        voice,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to generate speech');
    }

    const data = await response.json();
    
    return NextResponse.json({
      audioUrl: data.audioUrl,
      duration: data.duration,
      metadata: data.metadata,
    });
  } catch (error) {
    console.error('TTS generation error:', error);
    
    // For development, provide a mock response if backend is not available
    if (process.env.NODE_ENV === 'development') {
      return NextResponse.json({
        audioUrl: '/mock-audio.mp3', // This would be a real URL in production
        duration: 2.5,
        metadata: {
          provider: 'mock',
          voice: 'test-voice',
          characters: 50,
        }
      });
    }
    
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error occurred' },
      { status: 500 }
    );
  }
}

// Handle preflight requests
export async function OPTIONS() {
  return NextResponse.json({}, { status: 200 });
} 