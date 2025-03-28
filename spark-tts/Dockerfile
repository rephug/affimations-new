# Spark TTS Service Dockerfile
# CPU-only configuration for Spark-TTS

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libsndfile1 \
    ffmpeg \
    git \
    git-lfs \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Initialize git-lfs
RUN git lfs install

# Clone the Spark TTS repository
RUN git clone https://github.com/SparkAudio/Spark-TTS.git /app/Spark-TTS

# Download the model files
WORKDIR /app/Spark-TTS
RUN mkdir -p pretrained_models/Spark-TTS-0.5B
RUN pip install huggingface_hub
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='SparkAudio/Spark-TTS-0.5B', local_dir='pretrained_models/Spark-TTS-0.5B')"

# Install dependencies from the repository's requirements file
RUN pip install -r requirements.txt

# Install flask and related requirements
RUN pip install flask==2.2.5 flask-cors==3.0.10 soundfile==0.12.1

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES="-1"
ENV PYTHONPATH="/app/Spark-TTS:${PYTHONPATH}"

# Copy server script to /app
WORKDIR /app
COPY server.py /app/

# Expose port
EXPOSE 8020

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8020/health || exit 1

# Start the server
CMD ["python", "server.py", "--device", "-1", "--model_dir", "/app/Spark-TTS/pretrained_models/Spark-TTS-0.5B"] 