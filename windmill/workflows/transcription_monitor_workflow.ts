/**
 * Transcription Monitoring Workflow
 * 
 * This workflow periodically checks for pending AssemblyAI transcription jobs
 * and processes them when they are complete. This is an essential background
 * process for the Morning Coffee application.
 */

export interface TranscriptionMonitorParams {
  max_jobs?: number;          // Maximum number of jobs to process in one run (default: 10)
  timeout_seconds?: number;   // Maximum time in seconds to wait for a job to complete (default: 60)
}

/**
 * Step 1: Get pending transcription jobs
 */
export async function getPendingTranscriptions(params: TranscriptionMonitorParams) {
  const max_jobs = params.max_jobs || 10;
  
  try {
    // Fetch pending transcriptions from the application
    const response = await fetch('http://app:5000/api/check_transcriptions', {
      method: 'GET',
      headers: {
        'X-API-Key': process.env.MORNING_COFFEE_API_KEY || ''
      }
    });
    
    if (!response.ok) {
      throw new Error(`API call failed with status: ${response.status}`);
    }
    
    const result = await response.json();
    
    // Limit the number of jobs to process
    const pendingJobs = result.results || [];
    const jobsToProcess = pendingJobs.slice(0, max_jobs);
    
    return {
      total_pending: result.pending_count || 0,
      jobs_to_process: jobsToProcess.length,
      jobs: jobsToProcess,
      result
    };
  } catch (error) {
    console.error('Error fetching pending transcriptions:', error);
    return {
      total_pending: 0,
      jobs_to_process: 0,
      jobs: [],
      error: error.message
    };
  }
}

/**
 * Step 2: Process each pending transcription job
 */
export async function processJobs(params: {
  jobs: Array<{
    job_id: string;
    status: string;
    call_id: string;
  }>;
  timeout_seconds?: number;
}) {
  const { jobs } = params;
  const timeout_seconds = params.timeout_seconds || 60;
  
  // Skip if no jobs to process
  if (!jobs || jobs.length === 0) {
    return {
      jobs_processed: 0,
      message: 'No jobs to process'
    };
  }
  
  const results = [];
  
  // Process each job
  for (const job of jobs) {
    try {
      // Only process jobs that are still pending
      if (job.status === 'pending' || job.status === 'in_progress') {
        let processingResult;
        
        // Check if the job is already completed
        if (job.status === 'completed') {
          processingResult = {
            job_id: job.job_id,
            status: 'already_completed',
            message: 'Job was already completed'
          };
        } else {
          // For jobs still in progress, trigger a check
          processingResult = await checkTranscriptionStatus(job.job_id, timeout_seconds);
        }
        
        results.push(processingResult);
      } else {
        // Skip jobs that are not pending or in progress
        results.push({
          job_id: job.job_id,
          status: 'skipped',
          message: `Job is in status: ${job.status}`
        });
      }
    } catch (error) {
      console.error(`Error processing job ${job.job_id}:`, error);
      results.push({
        job_id: job.job_id,
        status: 'error',
        message: error.message
      });
    }
  }
  
  return {
    jobs_processed: jobs.length,
    successful: results.filter(r => r.status === 'completed').length,
    failed: results.filter(r => r.status === 'error').length,
    skipped: results.filter(r => r.status === 'skipped').length,
    results
  };
}

/**
 * Check the status of a transcription job with timeout
 */
async function checkTranscriptionStatus(jobId: string, timeoutSeconds: number) {
  // Calculate the deadline
  const deadline = Date.now() + (timeoutSeconds * 1000);
  
  // Function to check status
  const checkStatus = async () => {
    try {
      const response = await fetch(`http://app:5000/api/transcription/${jobId}/status`, {
        method: 'GET',
        headers: {
          'X-API-Key': process.env.MORNING_COFFEE_API_KEY || ''
        }
      });
      
      if (!response.ok) {
        throw new Error(`API call failed with status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error checking transcription status for job ${jobId}:`, error);
      throw error;
    }
  };
  
  // Initial check
  let status = await checkStatus();
  
  // If already completed, return
  if (status.status === 'completed') {
    return {
      job_id: jobId,
      status: 'completed',
      message: 'Job completed successfully',
      transcription: status.text
    };
  }
  
  // If error, return
  if (status.status === 'error') {
    return {
      job_id: jobId,
      status: 'error',
      message: `Job failed: ${status.error || 'Unknown error'}`
    };
  }
  
  // Poll until completed or deadline
  while (Date.now() < deadline) {
    // Wait for 5 seconds before checking again
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Check status again
    status = await checkStatus();
    
    // If completed or error, return
    if (status.status === 'completed') {
      return {
        job_id: jobId,
        status: 'completed',
        message: 'Job completed successfully',
        transcription: status.text
      };
    }
    
    if (status.status === 'error') {
      return {
        job_id: jobId,
        status: 'error',
        message: `Job failed: ${status.error || 'Unknown error'}`
      };
    }
  }
  
  // If we reach here, the job timed out
  return {
    job_id: jobId,
    status: 'timeout',
    message: `Job did not complete within ${timeoutSeconds} seconds`
  };
}

/**
 * Step 3: Log the results of the transcription monitoring
 */
export async function logResults(params: any) {
  console.log('Transcription monitoring workflow completed with result:', JSON.stringify(params, null, 2));
  
  // Return the final result
  return {
    workflow_completed: true,
    timestamp: new Date().toISOString(),
    summary: {
      jobs_processed: params.jobs_processed || 0,
      successful: params.successful || 0,
      failed: params.failed || 0,
      skipped: params.skipped || 0
    },
    results: params.results || []
  };
} 