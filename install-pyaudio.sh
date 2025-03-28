#!/bin/bash
# Script to install PyAudio and its dependencies

# Display banner
echo "=================================================="
echo "    PYAUDIO INSTALLER FOR MORNING COFFEE"
echo "=================================================="
echo

# Install system dependencies
echo "Installing system dependencies for PyAudio..."
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pyaudio

# If we have a virtual environment, install PyAudio there
if [ -d "venv" ]; then
  echo "Installing PyAudio in virtual environment..."
  source venv/bin/activate
  pip install pyaudio
  deactivate
else
  echo "Installing PyAudio system-wide..."
  pip install pyaudio
fi

echo
echo "PyAudio installation completed. You can now start the API server."
echo "==================================================" 