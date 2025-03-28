# Windmill Workflows for Morning Coffee

This directory contains Windmill workflows for orchestrating various tasks in the Morning Coffee application.

## What is Windmill?

[Windmill](https://windmill.dev) is an open-source developer platform that enables you to build and run production-ready workflows. It provides a way to orchestrate tasks and integrations between different services.

## Workflows

### Morning Call Workflow (`morning_call_workflow.ts`)

This workflow handles the scheduling and execution of morning calls to users:

1. Validates input parameters (phone number, scheduled time)
2. Schedules the call for the specified time or executes immediately
3. Monitors the call progress
4. Records the outcome

**Triggering:**
- Can be triggered manually with a phone number
- Scheduled to run daily at 8:00 AM

### Transcription Monitor Workflow (`transcription_monitor_workflow.ts`)

This workflow monitors and processes pending AssemblyAI transcription jobs:

1. Retrieves a list of pending transcription jobs
2. Processes each job, checking its status
3. Logs the results

**Triggering:**
- Runs automatically every minute to check for pending transcriptions
- Can be triggered manually to process specific transcription jobs

## Environment Variables

The workflows expect the following environment variables:

- `MORNING_COFFEE_API_KEY`: API key for authenticating with the Morning Coffee API

## Development

When developing or modifying workflows:

1. Make changes to the TypeScript files
2. Test locally if possible
3. Deploy to Windmill
4. Test each step individually before running the entire workflow

## Deployment

To deploy these workflows to Windmill:

1. Set up a Windmill instance
2. Create a new workspace if needed
3. Import the workflow TypeScript files
4. Configure triggers and schedules
5. Set environment variables
6. Test workflows individually 