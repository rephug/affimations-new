/**
 * Morning Call Workflow
 * 
 * This workflow sends a morning affirmation via SMS and initiates a
 * phone call to have the user repeat the affirmation and engage in
 * a brief conversation.
 */

export interface MorningCallParams {
  phone_number: string;  // User's phone number in E.164 format
  time?: string;         // Optional time to schedule the call (HH:MM)
}

/**
 * Step 1: Validate input parameters
 */
export async function validateInputs(params: MorningCallParams) {
  const { phone_number, time } = params;
  
  // Validate phone number format (E.164)
  const phoneRegex = /^\+[1-9]\d{1,14}$/;
  if (!phoneRegex.test(phone_number)) {
    throw new Error(`Invalid phone number format: ${phone_number}. Must be in E.164 format (e.g., +15551234567)`);
  }
  
  // Validate time format if provided
  if (time) {
    const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;
    if (!timeRegex.test(time)) {
      throw new Error(`Invalid time format: ${time}. Must be in HH:MM format (e.g., 08:00)`);
    }
  }
  
  return {
    phone_number,
    time,
    valid: true
  };
}

/**
 * Step 2: Schedule the morning coffee routine
 */
export async function scheduleCall(params: MorningCallParams) {
  const { phone_number, time } = params;
  
  // Check if we need to schedule for later or execute now
  if (time) {
    const now = new Date();
    const [hours, minutes] = time.split(':').map(Number);
    
    const scheduledTime = new Date();
    scheduledTime.setHours(hours, minutes, 0, 0);
    
    // If scheduled time is in the past for today, add delay
    if (scheduledTime < now) {
      return {
        scheduled: true,
        message: `Call for ${phone_number} will be scheduled for tomorrow at ${time}`,
        execute: false
      };
    }
    
    // Calculate delay in milliseconds
    const delayMs = scheduledTime.getTime() - now.getTime();
    
    if (delayMs > 0) {
      // Schedule for later
      setTimeout(() => {
        executeCall(phone_number);
      }, delayMs);
      
      return {
        scheduled: true,
        message: `Call for ${phone_number} scheduled for ${time} (in ${Math.round(delayMs / 60000)} minutes)`,
        execute: false
      };
    }
  }
  
  // Execute immediately
  return executeCall(phone_number);
}

/**
 * Execute the call to the user
 */
async function executeCall(phoneNumber: string) {
  try {
    // Make the API call to schedule the morning coffee
    const response = await fetch('http://app:5000/api/make_call', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.MORNING_COFFEE_API_KEY || ''
      },
      body: JSON.stringify({
        phone_number: phoneNumber
      })
    });
    
    if (!response.ok) {
      throw new Error(`API call failed with status: ${response.status}`);
    }
    
    const result = await response.json();
    
    return {
      scheduled: true,
      message: `Morning coffee routine initiated for ${phoneNumber}`,
      execute: true,
      result
    };
  } catch (error) {
    console.error('Error scheduling call:', error);
    return {
      scheduled: false,
      message: `Failed to schedule call for ${phoneNumber}: ${error.message}`,
      execute: false,
      error: error.message
    };
  }
}

/**
 * Step 3: Monitor call progress
 */
export async function monitorCall(params: {
  result: {
    scheduled: boolean;
    message: string;
    execute: boolean;
    result?: any;
    error?: string;
  }
}) {
  const { result } = params;
  
  // If the call was not executed, just return the result
  if (!result.execute) {
    return result;
  }
  
  // If the call was executed, monitor its progress
  const callId = result.result?.call_id;
  
  if (!callId) {
    return {
      ...result,
      monitoring: false,
      status: 'No call ID available to monitor'
    };
  }
  
  try {
    // Check call status after 30 seconds
    await new Promise(resolve => setTimeout(resolve, 30000));
    
    // Make API call to check call status
    const response = await fetch(`http://app:5000/api/call_status/${callId}`, {
      method: 'GET',
      headers: {
        'X-API-Key': process.env.MORNING_COFFEE_API_KEY || ''
      }
    });
    
    if (!response.ok) {
      throw new Error(`API call failed with status: ${response.status}`);
    }
    
    const callStatus = await response.json();
    
    return {
      ...result,
      monitoring: true,
      status: callStatus
    };
  } catch (error) {
    console.error('Error monitoring call:', error);
    return {
      ...result,
      monitoring: false,
      status: `Failed to monitor call: ${error.message}`
    };
  }
}

/**
 * Step 4: Record the outcome of the call
 */
export async function recordOutcome(params: any) {
  // Simply log the complete workflow outcome
  console.log('Morning call workflow completed with result:', JSON.stringify(params, null, 2));
  
  // Here you would typically store the outcome in a database
  // This is a placeholder for that functionality
  
  return {
    workflow_completed: true,
    timestamp: new Date().toISOString(),
    outcome: params
  };
} 