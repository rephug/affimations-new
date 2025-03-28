# Morning Coffee Environment Configuration with OpenAI Audio Integration
# Add these settings to your .env file

# Basic application settings
FLASK_ENV=development
PORT=5000
LOG_LEVEL=INFO
MORNING_COFFEE_API_KEY=your_app_api_key

# Redis configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# TTS provider selection - set to "openai" to use OpenAI's TTS service
TTS_PROVIDER=openai
TTS_CACHE_ENABLED=true
TTS_CACHE_TTL=86400

# OpenAI configuration for TTS and transcription
OPENAI_API_KEY=your_openai_api_key
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TRANSCRIBE_MODEL=gpt-4o-mini-transcribe
OPENAI_DEFAULT_VOICE_STYLE="Speak in a natural, warm tone that is friendly and conversational"

# Telnyx settings (required for calling)
TELNYX_API_KEY=your_telnyx_api_key
TELNYX_APP_ID=your_telnyx_app_id
TELNYX_PHONE_NUMBER=your_telnyx_phone_number
TELNYX_MESSAGING_PROFILE_ID=your_telnyx_messaging_profile_id
TELNYX_STORAGE_BUCKET_ID=your_telnyx_storage_bucket_id

# AssemblyAI settings (fallback for transcription if OpenAI fails)
ASSEMBLYAI_API_KEY=your_assemblyai_api_key

# LLM settings
LLM_TYPE=openai
LLM_API_KEY=your_openai_api_key  # Can reuse OPENAI_API_KEY
LLM_MODEL=gpt-4o
LLM_ENDPOINT=https://api.openai.com/v1

# Webhook settings
WEBHOOK_BASE_URL=https://your-webhook-domain.com

# Custom voice mapping options (JSON format)
# Uncomment and modify if you need custom mapping beyond the defaults
# TTS_VOICE_MAPPING={"default_female":{"openai":"Speak in a natural female voice"},"default_male":{"openai":"Speak in a natural male voice"}}
