# Main Application Dockerfile

FROM python:3.9-slim

WORKDIR /app

# Arguments
ARG INSTALL_REALTIMETTS=true

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg \
    libsndfile1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install RealtimeTTS and its dependencies if requested
RUN if [ "$INSTALL_REALTIMETTS" = "true" ] ; then \
    pip install --no-cache-dir RealtimeTTS pyaudio nltk ; \
    python -c "import nltk; nltk.download('punkt')" ; \
    fi

# Copy application code
COPY . .

# Create log directory and cache directory
RUN mkdir -p /app/logs /app/cache/tts

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Make scripts executable
RUN chmod +x /app/patch_assemblyai.py
RUN chmod +x /app/patch_assemblyai_validation.py
RUN chmod +x /app/start.sh

# Run the start script
CMD ["/app/start.sh"] 