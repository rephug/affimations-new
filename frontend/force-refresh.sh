#!/bin/bash

set -e

# Display banner
echo "-------------------------------------------"
echo "Morning Coffee Frontend Force Refresh Script"
echo "-------------------------------------------"

# Navigate to the frontend directory
cd /home/adminrob/projects/affimations/frontend

# Stop existing PM2 processes
echo "Stopping existing PM2 processes..."
pm2 stop morning-coffee-frontend 2>/dev/null || true
pm2 delete morning-coffee-frontend 2>/dev/null || true

# Clear Next.js cache
echo "Clearing Next.js cache..."
rm -rf .next/cache

# Rebuild the application with increased memory
echo "Rebuilding the application..."
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build

# Setup static files for direct serving
echo "Setting up static files..."
sudo rm -rf /var/www/morning-coffee/static/_next
sudo mkdir -p /var/www/morning-coffee/static/_next
sudo cp -r .next/static/* /var/www/morning-coffee/static/_next/static/
sudo chown -R www-data:www-data /var/www/morning-coffee

# Restart the application with PM2
echo "Starting application with PM2..."
NODE_ENV=production PORT=3000 pm2 start npm --name morning-coffee-frontend -- start

# Save PM2 configuration
echo "Saving PM2 configuration..."
pm2 save

# Apply Nginx configuration changes
echo "Applying Nginx configuration changes..."
sudo systemctl reload nginx

# Clear Nginx cache if any
echo "Clearing Nginx cache..."
sudo rm -rf /var/cache/nginx/*

# Restart Nginx
echo "Restarting Nginx..."
sudo systemctl restart nginx

echo "-------------------------------------------"
echo "Frontend force refresh completed successfully!"
echo "The application should now be updated at: https://morningcoffee.aireeaa.com"
echo "-------------------------------------------"
echo "If the page still doesn't show changes, try:"
echo "1. Clearing your browser cache completely (Ctrl+Shift+Delete)"
echo "2. Try accessing the site in an incognito window"
echo "3. Check console errors in your browser's developer tools"
echo "4. Add a cache-busting query parameter, e.g., ?v=$(date +%s)" 