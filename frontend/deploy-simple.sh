#!/bin/bash

set -e

# Display deployment banner
echo "------------------------------------"
echo "Morning Coffee Frontend Simple Deployment"
echo "------------------------------------"

# Navigate to the frontend directory
cd /home/adminrob/projects/affimations/frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Build the application with increased memory limit
echo "Building the application..."
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build

# Create the static directory in the standalone output if it doesn't exist
echo "Copying static files to standalone directory..."
mkdir -p .next/standalone/.next/static
cp -r .next/static .next/standalone/.next/

# Copy public folder if it exists
if [ -d "public" ]; then
  echo "Copying public folder..."
  mkdir -p .next/standalone/public
  cp -r public .next/standalone/
fi

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
  echo "PM2 is not installed. Please install it with: sudo npm install -g pm2"
  exit 1
fi

# Stop the existing process if it's running
echo "Stopping any existing PM2 processes..."
pm2 stop morning-coffee-frontend 2>/dev/null || true
pm2 delete morning-coffee-frontend 2>/dev/null || true

# Start the application with PM2
echo "Starting the application with PM2..."
cd .next/standalone
PORT=3000 pm2 start server.js --name morning-coffee-frontend --env production

# Save the PM2 configuration
echo "Saving PM2 configuration..."
pm2 save

# Display success message
echo "------------------------------------"
echo "Deployment successful!"
echo "Application is running at: http://152.53.84.219"
echo "------------------------------------"
echo "To view logs: pm2 logs morning-coffee-frontend"
echo "To stop: pm2 stop morning-coffee-frontend" 