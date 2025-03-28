#!/bin/bash
# Diagnostic script for Morning Coffee API

# Display banner
echo "=================================================="
echo "    MORNING COFFEE API DIAGNOSTICS"
echo "=================================================="
echo

# Check Python version
echo "Checking Python version..."
python3 --version
echo

# Check virtual environment
if [ -d "venv" ]; then
  echo "Virtual environment found."
  source venv/bin/activate
  echo "Activated virtual environment."
else
  echo "Warning: No virtual environment found at 'venv/'."
fi

# Check for required packages
echo "Checking required packages..."
pip list | grep -E "flask|openai|telnyx|redis|pyaudio" || echo "Some packages may be missing."
echo

# Check .env file
echo "Checking .env file..."
if [ -f ".env" ]; then
  echo ".env file exists."
  
  # Check for syntax errors in .env
  source .env 2>/tmp/env_errors
  if [ -s /tmp/env_errors ]; then
    echo "Warning: Found syntax errors in .env file:"
    cat /tmp/env_errors
    echo "Consider fixing these errors before starting the server."
  else
    echo ".env file loaded successfully."
  fi
else
  echo "Error: .env file not found. Please create one based on .env.example."
fi
echo

# Check Redis connection
echo "Checking Redis connection..."
if command -v redis-cli &> /dev/null; then
  redis-cli ping 2>/dev/null || echo "Warning: Redis server not responding."
else
  echo "Warning: redis-cli not installed. Cannot check Redis connection."
fi
echo

# Check for common importable modules
echo "Testing imports of key modules..."
python3 -c "
try:
    from flask import Flask
    print('✓ Flask imported successfully')
except ImportError as e:
    print('✗ Flask import error:', e)

try:
    import openai
    print('✓ OpenAI imported successfully')
except ImportError as e:
    print('✗ OpenAI import error:', e)

try:
    import redis
    print('✓ Redis imported successfully')
except ImportError as e:
    print('✗ Redis import error:', e)

try:
    import telnyx
    print('✓ Telnyx imported successfully')
except ImportError as e:
    print('✗ Telnyx import error:', e)

try:
    import pyaudio
    print('✓ PyAudio imported successfully')
except ImportError as e:
    print('✗ PyAudio import error:', e)
"
echo

echo "Checking for network connectivity to key services..."
for domain in api.openai.com api.telnyx.com; do
  echo -n "Testing connection to $domain: "
  ping -c 1 -W 2 $domain >/dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "✓ Connected"
  else
    echo "✗ Failed"
  fi
done
echo

echo "=================================================="
echo "Diagnostic checks completed."
echo "To start the API server, run: ./start_api_server.sh"
echo "==================================================" 