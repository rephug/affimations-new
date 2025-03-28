# Morning Coffee Application

A system that sends daily affirmations via SMS, calls users to have them repeat the affirmation, and enables AI conversation using Telnyx, OpenAI TTS, Spark TTS, AssemblyAI, and containerized with Docker.

## Overview

Morning Coffee is a service that helps users start their day with positive affirmations. The system:

1. Sends personalized affirmations via SMS
2. Makes phone calls to users and reads their daily affirmation
3. Records users repeating their affirmation
4. Engages in a supportive conversation using AI
5. Transcribes speech using OpenAI or AssemblyAI
6. Generates natural-sounding speech with OpenAI TTS or Spark TTS
7. Supports voice styling for more engaging conversations

## Architecture

The application is built using a microservices architecture:

- **Main Application**: Flask-based API that handles requests, manages call flow, and coordinates services
- **TTS Service**: Generates high-quality speech from text using multiple providers
  - OpenAI TTS: For realistic and expressive speech with voice styling
  - Spark TTS: For alternative high-quality speech generation
- **Redis**: Stores user data, call sessions, and conversation state
- **External Services**:
  - Telnyx: For SMS and voice calls (with HD audio support)
  - OpenAI: For speech-to-text transcription and TTS
  - AssemblyAI: For alternative speech-to-text transcription
  - LLM Provider (OpenAI, Claude, or Llama): For generating conversational responses

## Prerequisites

- Docker and Docker Compose
- Telnyx account with:
  - API key
  - Phone number
  - Messaging profile
  - Call Control application (Connection)
- AssemblyAI API key
- LLM API key (OpenAI, Claude, or Llama endpoint)
- Public URL for webhooks (can use ngrok for development)

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/morning-coffee.git
   cd morning-coffee
   ```

2. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file with your API keys and configuration.

4. Start the application:
   ```bash
   # For production
   ./startup.sh

   # For development
   docker-compose -f docker-compose.dev.yml up
   ```

## Development

For development, use the development Docker Compose file:

```bash
docker-compose -f docker-compose.dev.yml up
```

This will:
- Mount local directories for hot reloading
- Enable debug mode
- Provide Redis Commander at http://localhost:8081

## API Endpoints

### User Management

- `POST /api/users` - Create a new user
- `GET /api/users/{user_id}` - Get user by ID
- `GET /api/users/phone/{phone_number}` - Get user by phone number
- `PUT /api/users/{user_id}` - Update user data

### SMS and Calls

- `POST /api/send_affirmation` - Send an affirmation SMS to a user
- `POST /api/make_call` - Initiate a call to a user
- `GET /api/call_status/{call_id}` - Get the status of a call
- `GET /api/active_calls/{user_id}` - Get all active calls for a user

### Webhooks

- `/webhooks/telnyx/call` - Webhook for Telnyx call events
- `/webhooks/telnyx/message` - Webhook for Telnyx messaging events

### Utility

- `/health` - Health check endpoint
- `/dev/tts/test` - Test TTS generation (development only)
- `/dev/clear_test_data` - Clear test data (development only)

## Components

### Main Application

The main application is a Flask-based API that:
- Handles API requests
- Processes Telnyx webhooks
- Coordinates the call flow
- Manages user data and call sessions

### TTS Service

The TTS service supports multiple providers:

- **OpenAI TTS**: Using OpenAI's advanced text-to-speech models for realistic and expressive speech with voice styling capabilities
- **Spark TTS**: Alternative high-quality speech synthesis

The system automatically selects the appropriate provider based on configuration and fallback preferences.

### Redis Store

Handles data persistence for:
- User information
- Call sessions
- Conversation history

## Call Flow

1. User receives an SMS with their daily affirmation
2. System calls the user and reads their affirmation
3. User is asked to repeat the affirmation
4. System records and transcribes the user's speech
5. AI responds and engages in a supportive conversation
6. Call ends with a positive message

## Voice Styling

Morning Coffee supports voice styling with OpenAI TTS to create more engaging and personalized interactions:

- **Excited**: Enthusiastic and high-energy delivery
- **Calm**: Soothing and relaxed tone
- **Sad**: Empathetic and somber expression
- **Professional**: Clear, formal presentation
- **Custom**: Define custom voice instructions for special use cases

Voice styles can be configured per user or set for specific interaction contexts.

## Configuration

Configuration is managed through environment variables. See `.env.example` for all available options.

Key OpenAI configuration options:
- `OPENAI_API_KEY`: API key for OpenAI services
- `OPENAI_TTS_MODEL`: Model to use for TTS (default: gpt-4o-mini-tts)
- `OPENAI_VOICE_MAPPING`: JSON mapping of user voices to OpenAI voice IDs
- `OPENAI_VOICE_STYLE_MAPPING`: JSON mapping of style names to voice instructions
- `OPENAI_TRANSCRIPTION_MODEL`: Model to use for speech-to-text (default: whisper-1)

## Running the System

### Using Docker (Recommended)

For ease of deployment, use the provided Docker script:

```bash
chmod +x start_with_docker.sh
./start_with_docker.sh
```

This interactive script provides options to:
1. Start in production mode (all services, detached)
2. Start in development mode (with hot reloading)
3. Stop all containers
4. Restart specific services
5. View logs

### Running Backend API Directly

For development or testing, you can run the backend API directly:

```bash
chmod +x start_api_server.sh
./start_api_server.sh
```

This script:
- Sets up a Python virtual environment if needed
- Ensures Redis is running
- Configures environment variables
- Starts the Flask application

## Voice & Call Testing Lab

The system includes a dedicated testing interface for experimenting with voice and call features:

### Web Interface

Access the Voice & Call Testing Lab at:
```
https://morningcoffee.aireeaa.com/testing/voice-call-lab
```

This interface lets you:
- Select from multiple TTS providers (OpenAI, ElevenLabs, Google, Azure, etc.)
- Choose specific voices for each provider
- Adjust speech parameters (speed, pitch)
- Enter custom text
- Input a phone number for testing calls
- Generate and preview speech before making calls

### Testing API Endpoint

The system includes a dedicated API endpoint for testing voice calls with different settings:

```http
POST /api/test/voice_call
Content-Type: application/json
X-API-Key: your_api_key_here

{
  "phone_number": "+1234567890",
  "affirmation": "You are doing great today!",
  "provider": "openai",
  "voice": "friendly",
  "speed": 1.0
}
```

This endpoint:
- Accepts voice settings (provider, voice, speed)
- Generates speech using the specified settings
- Uploads the audio to Telnyx
- Initiates a call to the provided phone number
- Returns call status and tracking information

### Supported TTS Providers

The system supports multiple TTS providers, each offering different voices and capabilities:

1. **OpenAI** (default): High-quality AI voice with styling capabilities
2. **ElevenLabs**: Premium voice cloning and emotional expression
3. **Google Cloud TTS**: Wide range of natural-sounding voices
4. **Azure**: Microsoft's neural voices with natural prosody
5. **Kokoro**: Local TTS option using RealtimeTTS
6. **Murf**: Commercial TTS provider with voice customization

Configure provider settings in the `.env` file.

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Testing

The Morning Coffee application includes a comprehensive test suite using pytest. The tests are organized into:

- **Unit Tests** - Testing individual components in isolation
- **Functional Tests** - Testing API endpoints and integrations

### Running Tests

To run the tests:

```bash
# Run all tests
python -m pytest

# Run unit tests only
python -m pytest tests/unit/

# Run functional tests only
python -m pytest tests/functional/

# Generate coverage report
python -m pytest --cov=app tests/
```

See the [tests/README.md](tests/README.md) file for more detailed information about testing.

## Workflows

The Morning Coffee application uses Windmill for orchestrating background tasks and scheduled jobs:

1. **Morning Call Workflow** - Schedules and executes daily morning calls with affirmations
2. **Transcription Monitor Workflow** - Monitors pending AssemblyAI transcription jobs

For more information about the workflows, see the [windmill/README.md](windmill/README.md) file. # morningcf
