#!/bin/bash

set -e

# Display banner
echo "------------------------------------"
echo "Morning Coffee Frontend Styling Fix"
echo "------------------------------------"

# Navigate to the frontend directory
cd /home/adminrob/projects/affimations/frontend

# Stop existing processes
echo "Stopping existing PM2 processes..."
pm2 stop morning-coffee-frontend 2>/dev/null || true
pm2 delete morning-coffee-frontend 2>/dev/null || true

# Ensure the static files are correctly copied
echo "Creating proper directory structure..."
mkdir -p .next/standalone/.next/static
mkdir -p .next/standalone/.next/server/edge-chunks

echo "Copying static files to the standalone directory..."
cp -r .next/static/* .next/standalone/.next/static/

# Copy edge-chunks (a common issue with Next.js standalone mode)
if [ -d ".next/server/edge-chunks" ]; then
  echo "Copying edge-chunks files..."
  cp -r .next/server/edge-chunks/* .next/standalone/.next/server/edge-chunks/
fi

# Copy public directory if it exists
if [ -d "public" ]; then
  echo "Copying public directory..."
  cp -r public .next/standalone/
fi

# Modify environment to ensure correct port
echo "PORT=3000" > .next/standalone/.env.local
echo "NODE_ENV=production" >> .next/standalone/.env.local

# Start the application with PM2
echo "Starting application with PM2..."
cd .next/standalone
PORT=3000 pm2 start server.js --name morning-coffee-frontend --env production

# Save PM2 config
echo "Saving PM2 configuration..."
pm2 save

echo "------------------------------------"
echo "Fix completed! The application should now have proper styling."
echo "If it still doesn't work, try clearing your browser cache."
echo "The site is available at: http://152.53.84.219"
echo "------------------------------------" 