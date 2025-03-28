#!/bin/bash

set -e

echo "===== DEEP RESET: Morning Coffee Frontend Fix ====="
echo "This will completely reset and rebuild the frontend"

# Stop all existing processes
echo "Stopping ALL existing Next.js processes..."
pm2 delete all || true
pkill -f "node" || true
pkill -f "npm" || true
sudo netstat -tlpn | grep ":3000" | awk '{print $7}' | cut -d'/' -f1 | xargs -r sudo kill -9 || true

echo "Cleaning up any previous builds..."
cd /home/adminrob/projects/affimations/frontend
rm -rf .next || true
rm -rf node_modules/.cache || true

echo "Reinstalling node modules to ensure clean state..."
npm ci

echo "Building the Next.js application..."
NODE_OPTIONS="--max-old-space-size=4096" npm run build

echo "Setting up Nginx configuration for Next.js..."
# Create proper static serving directory
sudo rm -rf /var/www/morning-coffee || true
sudo mkdir -p /var/www/morning-coffee
sudo chown -R adminrob:adminrob /var/www/morning-coffee

# Copy all static assets
echo "Copying all static assets..."
mkdir -p /var/www/morning-coffee/static
cp -R .next/static/* /var/www/morning-coffee/static/

# Extra directory for edge chunks
mkdir -p /var/www/morning-coffee/static/_next/static
cp -R .next/static/* /var/www/morning-coffee/static/_next/static/

# Create standalone directory structure if using standalone output
if [ -d ".next/standalone" ]; then
  echo "Copying standalone Next.js build..."
  mkdir -p /var/www/morning-coffee/app
  cp -R .next/standalone/* /var/www/morning-coffee/app/
  cp -R .next/static /var/www/morning-coffee/app/.next/
  cp -R public /var/www/morning-coffee/app/
fi

# Optimized Nginx configuration
echo "Creating optimized Nginx configuration..."
cat > /home/adminrob/projects/affimations/frontend/morningcoffee.aireeaa.com.conf << 'EOL'
server {
    listen 80;
    server_name morningcoffee.aireeaa.com;

    # Main location for static files
    location /_next/static/ {
        alias /var/www/morning-coffee/static/;
        expires 365d;
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri $uri/ =404;
    }

    # Handle public directory files
    location /static/ {
        alias /home/adminrob/projects/affimations/frontend/public/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    # All static assets with file extensions
    location ~ ^/_next/.+\.(jpg|jpeg|gif|png|svg|ico|css|js|woff|woff2)$ {
        root /var/www/morning-coffee;
        expires 365d;
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri $uri/ =404;
    }

    # Handle all other Next.js requests
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    # Custom error page
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}
EOL

# Apply the configuration
echo "Applying Nginx configuration..."
sudo cp /home/adminrob/projects/affimations/frontend/morningcoffee.aireeaa.com.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/morningcoffee.aireeaa.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Start the application with PM2
echo "Starting Next.js with PM2..."
cd /home/adminrob/projects/affimations/frontend
pm2 start npm --name "morning-coffee-frontend" -- start

echo "===== DEEP RESET COMPLETE ====="
echo "Please clear your browser cache and try accessing https://morningcoffee.aireeaa.com again"
echo "If you still have issues, check the browser's developer console for specific errors" 