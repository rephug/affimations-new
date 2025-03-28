#!/bin/bash
# Script to start the Morning Coffee API server

# Display banner
echo "=================================================="
echo "    MORNING COFFEE API SERVER STARTER"
echo "=================================================="
echo

# Ensure .env file exists
if [ ! -f .env ]; then
  echo "Error: .env file not found!"
  echo "Please create a .env file with required configuration."
  exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
  echo "Activating virtual environment..."
  source venv/bin/activate
else
  echo "Warning: Virtual environment not found."
  echo "Creating new virtual environment..."
  python3 -m venv venv
  source venv/bin/activate
  
  echo "Installing requirements..."
  pip install -r app/requirements.txt
fi

# Check if Redis is running
redis_running=$(ps aux | grep redis-server | grep -v grep)
if [ -z "$redis_running" ]; then
  echo "Warning: Redis server does not appear to be running."
  echo "Starting Redis server..."
  redis-server --daemonize yes
fi

# Export environment variables
export FLASK_APP=app/app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# Load environment variables from .env
set -a
source .env
set +a

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Starting Morning Coffee API server..."
cd app && python -m flask run --host=0.0.0.0 --port=5000 