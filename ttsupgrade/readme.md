# OpenAI Audio Models Integration Guide

This guide explains how to integrate OpenAI's new audio models into the Morning Coffee application to provide enhanced text-to-speech and speech-to-text capabilities.

## Overview

OpenAI recently released several new audio models that bring significant improvements to both text-to-speech and speech-to-text capabilities:

1. **gpt-4o-mini-tts**: A text-to-speech model that can generate natural-sounding speech with customizable voice styles
2. **gpt-4o-transcribe**: A high-quality speech-to-text model for transcribing audio
3. **gpt-4o-mini-transcribe**: A faster, more cost-efficient speech-to-text model

This integration adds support for these models to the Morning Coffee application, enhancing the voice experience for users with more natural and expressive speech.

## Key Features

- **Voice Style Instructions**: Use natural language to customize how voices sound (excited, calm, professional, etc.)
- **Higher Quality Audio**: More natural and expressive voice compared to previous TTS systems
- **Improved Transcription**: Better speech recognition accuracy compared to Whisper
- **Seamless Integration**: Works with existing Morning Coffee call flows
- **Fallback Mechanism**: Falls back to existing providers if OpenAI services are unavailable

## Setup Instructions

### 1. Update Environment Variables

Add the following settings to your `.env` file:

```bash
# TTS provider selection - set to "openai" to use OpenAI's TTS service
TTS_PROVIDER=openai
TTS_CACHE_ENABLED=true
TTS_CACHE_TTL=86400

# OpenAI configuration for TTS and transcription
OPENAI_API_KEY=your_openai_api_key
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TRANSCRIBE_MODEL=gpt-4o-mini-transcribe
OPENAI_DEFAULT_VOICE_STYLE="Speak in a natural, warm tone that is friendly and conversational"
```

### 2. Update Dependencies

Ensure you have the latest OpenAI Python package installed:

```bash
pip install --upgrade openai
```

### 3. Restart the Application

After updating your environment variables, restart the Morning Coffee application to apply the changes:

```bash
docker-compose down
docker-compose up -d
```

## Voice Styling

One of the most powerful features of OpenAI's new TTS model is the ability to customize voice characteristics using natural language instructions. Here are some examples:

### Voice Style Examples

- **Friendly**: "Speak in a very friendly and warm tone, like talking to an old friend"
- **Professional**: "Speak in a clear, professional tone like a news anchor"
- **Calm**: "Speak in a calm, soothing voice like a mindfulness guide"
- **Excited**: "Speak with enthusiasm and excitement, like you're sharing great news"
- **Sad**: "Speak with a sad and melancholic tone"
- **Customer Service**: "Speak like a helpful customer service representative who is ready to assist"
- **Teacher**: "Speak like a kind, patient teacher explaining a concept to students"

### Using Voice Styles in Code

```python
# Example: Generate speech with a specific voice style
audio_data = tts_service.generate_with_style(
    text="Hello, how are you feeling today?",
    style="Speak in a caring, empathetic voice like a therapist"
)
```

## Cost Considerations

The OpenAI audio models have the following pricing:

- **gpt-4o-mini-tts**: $0.015 per minute of generated audio
- **gpt-4o-mini-transcribe**: $0.003 per minute of processed audio
- **gpt-4o-transcribe**: $0.006 per minute of processed audio

The Morning Coffee application includes caching for TTS responses to minimize costs. The caching system stores generated audio and reuses it for identical text, voice style, and speed combinations.

## Testing

To test the OpenAI TTS integration, you can use the included example scripts:

### Voice Style Testing

```bash
python examples/openai-voice-style-example.py --api-key your_openai_api_key --style excited --text "Hello! It's great to meet you!"
```

### TTS Development Endpoint

You can also test the TTS functionality through the development API endpoint:

```bash
curl -X POST http://localhost:5000/dev/tts/test \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test of the OpenAI TTS system.", "style": "Speak like a friendly robot with a bit of electronic distortion in the voice"}'
```

## Troubleshooting

### Common Issues

1. **API Key Issues**: Ensure your OpenAI API key is valid and has access to the audio models
2. **Model Availability**: Make sure the specified models are available in your OpenAI account
3. **Rate Limiting**: If you encounter rate limits, implement exponential backoff in your requests

### Error Handling

The implementation includes robust error handling with fallbacks to other providers if OpenAI services are unavailable:

1. If OpenAI TTS fails, it will fall back to the next available provider
2. If OpenAI transcription fails, it will fall back to AssemblyAI if configured

## Advanced Configuration

### Voice Mapping

You can customize the voice mapping to use specific voice style instructions for different voice IDs:

```json
{
  "default_female": {
    "openai": "Speak in a natural, warm female voice with a friendly tone"
  },
  "default_male": {
    "openai": "Speak in a natural, warm male voice with a friendly tone"
  },
  "professional": {
    "openai": "Speak in a clear, professional tone. Be concise and articulate."
  }
}
```

Set this mapping in your `.env` file:

```bash
TTS_VOICE_MAPPING='{"default_female":{"openai":"Speak in a natural, warm female voice with a friendly tone"},"default_male":{"openai":"Speak in a natural, warm male voice with a friendly tone"}}'
```

## Conclusion

By integrating OpenAI's new audio models, Morning Coffee can provide a more natural and engaging voice experience for users. The ability to customize voice styles using natural language instructions opens up new possibilities for creating more personal and context-appropriate interactions.
