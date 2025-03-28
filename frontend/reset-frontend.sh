#!/bin/bash

set -e

# Display banner
echo "------------------------------------"
echo "Morning Coffee Frontend Reset Script"
echo "------------------------------------"

# Navigate to the frontend directory
cd /home/adminrob/projects/affimations/frontend

# Terminate all processes using port 3000
echo "Terminating any processes using port 3000..."
lsof -t -i:3000 | xargs -r kill -9

# Stop existing PM2 processes
echo "Stopping existing PM2 processes..."
pm2 stop morning-coffee-frontend 2>/dev/null || true
pm2 delete morning-coffee-frontend 2>/dev/null || true

# Rebuild the application with increased memory
echo "Rebuilding the application..."
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build

# Setup static files for direct serving
echo "Setting up static files..."
sudo mkdir -p /var/www/morning-coffee/static
sudo cp -r .next/static/* /var/www/morning-coffee/static/
sudo chown -R www-data:www-data /var/www/morning-coffee

# Create proper directory structure for standalone mode
echo "Creating proper standalone directory structure..."
mkdir -p .next/standalone/.next/static
mkdir -p .next/standalone/.next/server/edge-chunks
cp -r .next/static/* .next/standalone/.next/static/

# Copy edge-chunks if they exist
if [ -d ".next/server/edge-chunks" ]; then
  echo "Copying edge-chunks files..."
  cp -r .next/server/edge-chunks/* .next/standalone/.next/server/edge-chunks/
fi

# Copy public directory if it exists
if [ -d "public" ]; then
  echo "Copying public directory..."
  cp -r public .next/standalone/
fi

# Set environment variables for standalone mode
echo "Setting environment variables..."
echo "PORT=3000" > .next/standalone/.env.local
echo "NODE_ENV=production" >> .next/standalone/.env.local

# Restart the application with PM2
echo "Starting application with PM2..."
cd .next/standalone
PORT=3000 pm2 start server.js --name morning-coffee-frontend --env production

# Save PM2 configuration
echo "Saving PM2 configuration..."
pm2 save

# Apply nginx configuration
echo "Applying Nginx configuration..."
sudo cp /home/adminrob/projects/affimations/frontend/nginx-direct.conf /etc/nginx/sites-available/morning-coffee
sudo systemctl reload nginx

echo "------------------------------------"
echo "Frontend reset completed successfully!"
echo "The application is available at: http://152.53.84.219"
echo "------------------------------------"
echo "If styling still doesn't appear correctly, try:"
echo "1. Clearing your browser cache completely"
echo "2. Try accessing the site in an incognito window"
echo "3. Check console errors in your browser's developer tools"
echo "------------------------------------" 