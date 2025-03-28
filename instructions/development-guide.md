# Development Guide: Morning Coffee with Spark TTS and Docker

This guide details the development process for setting up the Morning Coffee application with Spark TTS in a dockerized environment with Windmill orchestration.

## Prerequisites

Before beginning development, ensure you have the following installed:

- Docker and Docker Compose
- Git
- A code editor (VS Code recommended)
- Telnyx account and API credentials
- AssemblyAI API key
- LLM API key (OpenAI, Claude, or setup for local models)

## Project Structure

```
morning-coffee/
├── docker-compose.yml           # Main Docker Compose configuration
├── docker-compose.dev.yml       # Development overrides
├── .env.example                 # Example environment variables
├── .gitignore                   # Git ignore file
├── README.md                    # Project documentation
│
├── app/                         # Main Flask application
│   ├── Dockerfile               # Dockerfile for the main application
│   ├── requirements.txt         # Python dependencies
│   ├── app.py                   # Entry point
│   ├── config.py                # Configuration management
│   └── modules/                 # Application modules
│       ├── telnyx_handler.py    # Telnyx integration
│       ├── assemblyai_handler.py # AssemblyAI integration
│       ├── llm_handler.py       # LLM integration
│       ├── tts_client.py        # Client for TTS service
│       └── models.py            # Data models
│
├── spark-tts/                   # Spark TTS service
│   ├── Dockerfile               # Dockerfile for Spark TTS
│   ├── requirements.txt         # Python dependencies
│   ├── server.py                # API server for Spark TTS
│   ├── download_model.py        # Script to download models
│   └── models/                  # Directory for model files
│
├── llm/                         # Optional local LLM service
│   ├── Dockerfile               # Dockerfile for local LLM
│   ├── requirements.txt         # Python dependencies
│   ├── server.py                # API server for LLM
│   └── models/                  # Directory for model files
│
└── windmill/                    # Windmill workflows
    ├── workflows/               # Workflow definitions
    │   ├── morning_call.yaml    # Morning call workflow
    │   ├── call_handling.yaml   # Call handling workflow
    │   └── monitoring.yaml      # Monitoring workflow
    └── resources/               # Resource definitions
        ├── telnyx.yaml          # Telnyx resource
        ├── assemblyai.yaml      # AssemblyAI resource
        └── openai.yaml          # OpenAI resource
```

## Setting Up the Development Environment

### 1. Clone the Repository Template

```bash
git clone https://github.com/yourusername/morning-coffee.git
cd morning-coffee
```

### 2. Create Environment Variables

```bash
cp .env.example .env
# Edit .env file with your API keys and configuration
```

### 3. Build the Docker Images

```bash
# Build all services
docker-compose build

# Build a specific service
docker-compose build spark-tts
```

### 4. Start the Development Environment

```bash
# Start with development overrides
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs from all services
docker-compose logs -f

# View logs from a specific service
docker-compose logs -f app
```

## Working with Spark TTS

### Model Setup

Spark TTS requires model files to be downloaded before use. The `spark-tts/download_model.py` script handles this automatically, but you can also do it manually:

```bash
# Enter the spark-tts container
docker-compose exec spark-tts bash

# Download the model manually
python download_model.py
```

### Testing TTS Generation

You can test the Spark TTS service directly:

```bash
# Test with curl
curl -X POST http://localhost:8020/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"This is a test of Spark TTS.", "voice_id":"default"}' \
  --output test.wav
```

## Developing the Main Application

The main application in the `app/` directory follows a modular structure:

- `app.py`: Entry point and API routes
- `modules/`: Feature-specific modules
- `config.py`: Configuration management

### Local Development with Hot Reloading

The development Docker Compose configuration mounts your local code directory into the container and enables hot reloading:

```bash
# Start with development configuration
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d app
```

Any changes you make to the code will automatically reload the Flask application.

### Testing API Endpoints

```bash
# Test health check
curl http://localhost:5000/health

# Test schedule endpoint
curl -X POST http://localhost:5000/schedule_morning_coffee \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890"}'
```

## Setting Up Windmill

### 1. Install Windmill CLI

```bash
npm install -g windmill-cli
```

### 2. Login to Windmill

```bash
windmill login
```

### 3. Deploy Workflows

```bash
# Deploy a specific workflow
windmill deploy workflow ./windmill/workflows/morning_call.yaml

# Deploy all workflows
windmill deploy workflow ./windmill/workflows/
```

## Working with External Services

### Telnyx Configuration

1. Configure your Telnyx number, messaging profile, and call control application
2. Set webhook URLs to point to your application:
   - Call webhook: `https://your-domain.com/telnyx/call`
   - Message webhook: `https://your-domain.com/telnyx/message`

### AssemblyAI Configuration

1. Set up your AssemblyAI API key in the `.env` file
2. The application will handle the API calls and polling for results

### LLM Configuration

1. Choose your preferred LLM provider (OpenAI, Claude, local)
2. Set the appropriate API keys and configuration
3. If using a local model, ensure the LLM container has sufficient resources

## Testing End-to-End Functionality

### 1. Exposing Local Development with ngrok

For testing with Telnyx webhooks, you need to expose your local development environment:

```bash
# Install ngrok
npm install -g ngrok

# Expose port 5000
ngrok http 5000
```

Update your Telnyx webhook URLs to the ngrok URL.

### 2. Triggering a Test Call

```bash
# Trigger the morning coffee workflow
curl -X POST http://localhost:5000/schedule_morning_coffee \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890"}'
```

### 3. Monitoring the Workflow

1. Check Docker logs for real-time updates:
   ```bash
   docker-compose logs -f
   ```

2. Check Windmill execution logs in the Windmill dashboard

## Troubleshooting

### Common Issues and Solutions

1. **Spark TTS fails to start**:
   - Check if the model was downloaded correctly
   - Verify GPU availability and drivers if using GPU acceleration
   - Check memory allocation in Docker Compose

2. **Telnyx webhooks not being received**:
   - Verify ngrok is running and webhook URLs are correct
   - Check Telnyx portal for webhook delivery failures
   - Ensure ports are properly exposed in Docker Compose

3. **AssemblyAI transcriptions not completing**:
   - Check API key and request format
   - Verify background polling is working correctly
   - Check for timeout or rate limit issues

### Debugging Tools

1. **Docker Logs**:
   ```bash
   docker-compose logs -f app
   ```

2. **Container Shell**:
   ```bash
   docker-compose exec app bash
   ```

3. **Application Debugging**:
   The development environment includes Python debugging support. You can connect with VS Code's remote debugging.

## Deployment to Production

### Preparing for Production

1. Build optimized Docker images:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
   ```

2. Update environment variables for production:
   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with production settings
   ```

### Deployment Options

1. **Docker Compose**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

2. **Kubernetes**:
   ```bash
   # Apply Kubernetes configurations
   kubectl apply -f kubernetes/
   ```

3. **Cloud Platforms**:
   - AWS ECS
   - Google Cloud Run
   - Digital Ocean App Platform

### Setting Up Monitoring

1. Configure health checks
2. Set up alerting
3. Implement logging aggregation (e.g., ELK stack, Loki)

## Performance Optimization

### Spark TTS Optimization

1. Use CUDA acceleration when available
2. Implement caching for common phrases
3. Consider model quantization for faster inference

### Application Scaling

1. Horizontal scaling for the main application
2. Load balancing for distributed deployment
3. Cache optimization for Redis

## Security Best Practices

1. Use secrets management for API keys
2. Implement proper authentication and authorization
3. Regular security audits
4. Keep all dependencies up to date

## Contributing to the Project

1. Follow the established code style and structure
2. Add tests for new features
3. Document changes in the README
4. Create pull requests with clear descriptions
