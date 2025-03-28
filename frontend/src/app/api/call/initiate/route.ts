import { NextRequest, NextResponse } from 'next/server';

interface APIResponse {
  status: string;
  message?: string;
  error?: string;
}

export async function POST(req: NextRequest) {
  try {
    // Parse the request body
    const data = await req.json();
    const { phoneNumber, affirmation, voiceSettings } = data;
    
    console.log('Call initiation request received:', { 
      phoneNumber, 
      affirmation,
      voiceSettings 
    });

    // Validate required fields
    if (!phoneNumber || !affirmation) {
      return NextResponse.json(
        { status: 'error', error: 'Phone number and affirmation are required' }, 
        { status: 400 }
      );
    }
    
    // Format phone number for API call - ensure it has the + prefix for international format
    const formattedPhone = phoneNumber.startsWith('+') ? phoneNumber : `+${phoneNumber}`;
    
    // Extract voice settings or provide defaults
    const provider = voiceSettings?.provider || 'openai';
    const voice = voiceSettings?.voice || null;
    const speed = voiceSettings?.speed || 1.0;
    
    try {
      // Make API call to backend service
      const apiResponse = await fetch('http://localhost:5000/api/test/voice_call', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.MORNING_COFFEE_API_KEY || 'dev_api_key'
        },
        body: JSON.stringify({
          phone_number: formattedPhone,
          affirmation: affirmation,
          provider: provider,
          voice: voice,
          speed: speed
        })
      });
      
      // Check if the API call was successful
      if (!apiResponse.ok) {
        const errorData = await apiResponse.json();
        console.error('API call failed:', errorData);
        
        // If we couldn't reach the backend, return a simulated success response for development
        if (apiResponse.status === 404 || apiResponse.status === 502 || apiResponse.status === 503) {
          console.log('Backend unavailable, returning simulated response');
          return NextResponse.json({
            status: 'simulated',
            message: 'Call simulated (Backend API not available)',
            call_id: 'sim_' + Date.now()
          });
        }
        
        return NextResponse.json(
          { status: 'error', error: errorData.error || 'Failed to initiate call' }, 
          { status: apiResponse.status }
        );
      }
      
      // Return the success response
      const result = await apiResponse.json();
      return NextResponse.json({
        status: result.status,
        call_id: result.call_id,
        message: 'Call initiated successfully'
      });
      
    } catch (error) {
      console.error('Error connecting to backend:', error);
      
      // For development: return simulated success if can't connect to backend
      return NextResponse.json({
        status: 'simulated',
        message: 'Call simulated (Backend API not available)',
        call_id: 'sim_' + Date.now()
      });
    }
    
  } catch (error) {
    console.error('Error processing request:', error);
    return NextResponse.json(
      { status: 'error', error: 'Internal server error' }, 
      { status: 500 }
    );
  }
}

// Handle preflight requests
export async function OPTIONS() {
  return NextResponse.json({}, { status: 200 });
} 