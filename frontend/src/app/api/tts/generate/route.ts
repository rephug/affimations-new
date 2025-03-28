import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    console.log('TTS generate API called');
    
    // Get request body
    const body = await request.json();
    const { text, provider = 'openai', voice = 'alloy', speed = 1.0, pitch = 0 } = body;
    
    console.log('Request parameters:', { text, provider, voice, speed, pitch });

    if (!text) {
      console.error('Missing required parameter: text');
      return NextResponse.json(
        { message: 'Text is required' },
        { status: 400 }
      );
    }

    // Call the backend TTS service
    try {
      console.log('Calling backend TTS service');
      
      const response = await fetch('http://localhost:5000/api/tts/generate', {
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
        const errorText = await response.text().catch(() => 'Unknown error');
        console.error(`Backend TTS service error (${response.status}): ${errorText}`);
        
        return NextResponse.json(
          { message: `TTS service error: ${errorText}` },
          { status: response.status }
        );
      }
      
      const data = await response.json();
      console.log('TTS service response:', data);
      
      return NextResponse.json({
        success: true,
        audioUrl: data.audio_url,
        message: 'Speech generated successfully'
      });
    } catch (backendError) {
      console.error('Backend TTS service connection error:', backendError);
      
      // If backend service is unavailable, serve a sample audio file for testing
      console.log('Falling back to sample audio');
      const sampleAudioUrls = {
        openai: '/samples/openai-sample.mp3',
        elevenlabs: '/samples/elevenlabs-sample.mp3',
        kokoro: '/samples/kokoro-sample.mp3',
        google: '/samples/google-sample.mp3',
        murf: '/samples/murf-sample.mp3',
        azure: '/samples/azure-sample.mp3',
        telnyx: '/samples/telnyx-sample.mp3',
      };
      
      const audioUrl = sampleAudioUrls[provider as keyof typeof sampleAudioUrls] || '/samples/openai-sample.mp3';
      
      return NextResponse.json({
        success: true,
        audioUrl,
        message: 'Generated sample audio (TTS service unavailable)',
        isSample: true
      });
    }
  } catch (error) {
    console.error('TTS generate API error:', error);
    
    return NextResponse.json(
      { message: 'Internal server error', error: String(error) },
      { status: 500 }
    );
  }
}

// Add a health check endpoint
export async function GET() {
  return NextResponse.json({ 
    status: 'ok',
    supportedProviders: ['telnyx', 'openai', 'elevenlabs', 'kokoro', 'google', 'murf', 'azure']
  });
}

// Handle preflight requests
export async function OPTIONS() {
  return NextResponse.json({}, { status: 200 });
} 