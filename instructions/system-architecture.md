# Morning Coffee: System Architecture and Specifications

This document outlines the architecture, components, and deployment strategy for the Morning Coffee application with Spark TTS, Docker containerization, and Windmill orchestration.

## System Overview

The Morning Coffee system consists of the following key components:

1. **Main Application Service**: Flask application that handles the core logic, Telnyx webhooks, and coordinates the workflow
2. **Spark TTS Service**: Runs Spark TTS locally to generate high-quality speech from text
3. **Telnyx Integration**: Handles phone calls, SMS, and storage for audio files
4. **AssemblyAI Integration**: Provides speech-to-text capabilities
5. **LLM Service**: Generates conversational responses (OpenAI, Llama, or Claude)
6. **Windmill Orchestration**: Coordinates workflows and manages dependencies between services

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                         Docker Environment                         │
│  ┌──────────────┐       ┌───────────────┐       ┌──────────────┐   │
│  │ Main Service │       │  Spark TTS    │       │ Local LLM    │   │
│  │ (Flask App)  │◄─────►│   Service     │       │ (Optional)   │   │
│  └──────┬───────┘       └───────────────┘       └──────────────┘   │
│         │                                                          │
│         │            ┌───────────────┐                             │
│         └───────────►│   Redis       │◄────────────────────┐       │
│                      │   Cache       │                     │       │
│                      └───────────────┘                     │       │
└────────────────────────────────────────────────────────────┼───────┘
                                                             │
┌──────────────────────┐                 ┌──────────────────┐│┐
│   Windmill           │                 │   External       ││
│   Orchestration      │◄───────────────►│   Services       ││
└──────────────────────┘                 │                  ││
                                         │  - Telnyx        ││
                                         │  - AssemblyAI    ││
                                         │  - OpenAI/Claude ││
                                         └──────────────────┘│
                                                             │
┌────────────────────────────────────────────────────────────┘
│ User Interaction
│
└─► SMS/Call ◄─► Telnyx ◄─► Main Service ◄─► Workflow Execution
```

## Component Specifications

### 1. Main Application Container

**Responsibilities**:
- Handle Telnyx webhooks for calls and SMS
- Coordinate the workflow between services
- Manage user conversations and call state
- Interface with external APIs

**Technical Specs**:
- Base Image: Python 3.9-slim
- Exposed Ports: 5000
- Dependencies: Flask, Telnyx SDK, AssemblyAI SDK, LLM SDKs
- Storage: Mounts volume for persistent data
- Environment Variables: API keys, configuration settings

### 2. Spark TTS Container

**Responsibilities**:
- Run Spark TTS model locally
- Convert text to high-quality speech
- Expose API for the main application

**Technical Specs**:
- Base Image: Python 3.9 with CUDA support (for GPU acceleration)
- Exposed Ports: 8020
- Dependencies: PyTorch, Transformers, Spark TTS model
- GPU Support: Optional but recommended
- Memory Requirement: Minimum 4GB RAM, 8GB recommended
- Storage: Mounts volume for model storage

### 3. Redis Container (Optional)

**Responsibilities**:
- Store conversation state
- Cache generated audio for reuse
- Manage job queues for asynchronous tasks

**Technical Specs**:
- Base Image: Redis:alpine
- Exposed Ports: 6379
- Persistence: Configured for AOF persistence
- Memory: 512MB minimum

### 4. LLM Container (Optional, for local models)

**Responsibilities**:
- Run local LLM model (Llama, etc.)
- Generate conversational responses

**Technical Specs**:
- Base Image: Python 3.9 with CUDA support
- Exposed Ports: 8080
- Memory: Minimum 8GB RAM
- GPU Support: Strongly recommended
- Storage: Mounts volume for model storage

## Windmill Orchestration

Windmill will orchestrate the following workflows:

1. **Morning Call Workflow**:
   - Trigger: Schedule or API call
   - Steps:
     1. Send affirmation SMS
     2. Initiate phone call
     3. Execute call script with TTS and STT
     4. Record conversation outcomes

2. **Call Handling Workflow**:
   - Trigger: Telnyx webhook
   - Steps:
     1. Generate TTS audio
     2. Play audio and record user speech
     3. Transcribe speech with AssemblyAI
     4. Get LLM response
     5. Generate and play response audio

3. **Monitoring Workflow**:
   - Trigger: Scheduled (every 5 minutes)
   - Steps:
     1. Check service health
     2. Monitor pending transcriptions
     3. Notify on failures

## Docker Compose Configuration

The Docker Compose file will define:
- All service containers
- Network configuration
- Volume mounts
- Environment variables
- Health checks
- Restart policies

## Development Workflow

1. **Local Development**:
   - Docker Compose for local development
   - Hot reloading for the Flask application
   - Volume mounts for code changes

2. **Testing**:
   - Separate Docker Compose configuration for testing
   - Mock services for Telnyx and AssemblyAI
   - Automated tests with pytest

3. **Production Deployment**:
   - Kubernetes deployment option
   - Docker Compose for simpler deployments
   - Proper secrets management

## Security Considerations

1. **API Key Management**:
   - Use Docker secrets or environment variables
   - Never commit API keys to source control

2. **Network Security**:
   - Internal communication over a private Docker network
   - Only expose necessary ports
   - HTTPS for all external communication

3. **Data Privacy**:
   - Encryption for sensitive data
   - Compliance with privacy regulations
   - Proper data retention policies

## Performance Considerations

1. **Spark TTS Optimization**:
   - GPU acceleration when available
   - Model quantization for faster inference
   - Caching of commonly used phrases

2. **Scaling**:
   - Horizontal scaling for the main application
   - Load balancing for distributed deployment
   - Queue-based architecture for handling spikes

## Next Steps

1. Create Dockerfiles for each service
2. Set up Docker Compose configuration
3. Implement the Spark TTS integration
4. Configure Windmill workflows
5. Test the end-to-end system
6. Document deployment procedures
