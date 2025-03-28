#!/bin/bash
# Startup script for the Morning Coffee application

# Exit on error
set -e

echo "Starting the application with direct REST API implementation..."
echo "Note: We're bypassing the AssemblyAI SDK entirely to avoid validation issues"

# Start the application
gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120 "app:create_app()" 