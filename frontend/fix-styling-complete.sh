#!/bin/bash

set -e

echo "===== Morning Coffee Frontend Style Fix Script ====="
echo "This script will fix CSS and JS loading issues"

# Stop any existing processes
echo "Stopping any existing PM2 processes..."
pm2 stop morning-coffee-frontend || true

# Create proper structure for static files
echo "Setting up static file directories..."
sudo mkdir -p /var/www/morning-coffee/static
sudo chown -R adminrob:adminrob /var/www/morning-coffee

# Copy all static files from the .next directory
echo "Copying static files to the correct location..."
cd /home/adminrob/projects/affimations/frontend
cp -R .next/static/* /var/www/morning-coffee/static/

# Create a specific directory for edge chunks
echo "Setting up edge chunks directory..."
mkdir -p /var/www/morning-coffee/static/_next/static
cp -R .next/static/* /var/www/morning-coffee/static/_next/static/

# Update Nginx configuration with improved static file handling
echo "Creating optimized Nginx configuration..."
cat > /home/adminrob/projects/affimations/frontend/morningcoffee.aireeaa.com.conf << 'EOL'
server {
    listen 80;
    server_name morningcoffee.aireeaa.com;

    # Improved static file handling for Next.js
    location /_next/static/ {
        root /var/www/morning-coffee;
        expires 365d;
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri $uri/ =404;
    }

    # Handle static files from public directory
    location /static/ {
        alias /home/adminrob/projects/affimations/frontend/public/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    # Fallback for all other static assets
    location ~ ^/_next/.+\.(jpg|jpeg|gif|png|svg|ico|css|js|woff|woff2)$ {
        root /var/www/morning-coffee;
        expires 365d;
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri $uri/ =404;
    }

    # For all other requests, proxy to Next.js
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

    # Error pages
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}
EOL

# Apply the new Nginx configuration
echo "Applying new Nginx configuration..."
sudo cp /home/adminrob/projects/affimations/frontend/morningcoffee.aireeaa.com.conf /etc/nginx/sites-available/
sudo nginx -t && sudo systemctl reload nginx

# Restart the Next.js application
echo "Starting Next.js application with PM2..."
cd /home/adminrob/projects/affimations/frontend
pm2 start npm --name "morning-coffee-frontend" -- start

echo "===== Style fix complete! ====="
echo "Please clear your browser cache and reload the site."
echo "The site should now display correctly at https://morningcoffee.aireeaa.com" 