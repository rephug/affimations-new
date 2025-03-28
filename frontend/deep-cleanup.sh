#!/bin/bash

set -e

# Display banner
echo "---------------------------------------"
echo "Morning Coffee Deep Cleanup & Fix Script"
echo "---------------------------------------"

# Navigate to the frontend directory
cd /home/adminrob/projects/affimations/frontend

# Stop existing PM2 processes
echo "Stopping existing PM2 processes..."
pm2 stop morning-coffee-frontend 2>/dev/null || true
pm2 delete morning-coffee-frontend 2>/dev/null || true

# Kill any processes on port 3000
echo "Killing any processes running on port 3000..."
sudo lsof -t -i:3000 | xargs -r sudo kill -9

# Clear existing static directories
echo "Clearing existing static directories..."
sudo rm -rf /var/www/morning-coffee/static
sudo mkdir -p /var/www/morning-coffee/static/_next/static

# Clear Next.js cache
echo "Clearing Next.js cache..."
rm -rf .next/cache
rm -rf .next/standalone

# Rebuild the application
echo "Rebuilding the application..."
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build

# Setup static files
echo "Setting up static files..."
sudo cp -r .next/static/* /var/www/morning-coffee/static/_next/static/
sudo chown -R www-data:www-data /var/www/morning-coffee

# Ensure proper permissions
echo "Ensuring proper permissions..."
sudo chmod -R 755 /var/www/morning-coffee

# Start new PM2 process
echo "Starting new PM2 process..."
NODE_ENV=production PORT=3000 pm2 start npm --name morning-coffee-frontend -- start

# Save PM2 configuration
echo "Saving PM2 configuration..."
pm2 save

# Fix Nginx configuration
echo "Updating Nginx configuration to ensure it points to the correct directory..."
cat > nginx-fixed.conf << EOL
server {
    server_name morningcoffee.aireeaa.com;

    # Root directory for static HTML
    root /var/www/morning-coffee/html;
    index index.html;

    # Main location for the root path to serve static HTML
    location = / {
        try_files \$uri /index.html;
    }

    # Specific location for the testing path to serve the static HTML
    location = /testing {
        try_files /testing/index.html =404;
    }

    # Testing pages are proxied to Next.js app
    location ~ ^/testing/ {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        
        # Add cache-busting header
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    # For API routes
    location /api {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
    }

    # Other app paths are proxied to Next.js
    location ~ ^/(dashboard|login|signup|_next) {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
    }

    # Enhanced static file handling
    location /_next/static {
        alias /var/www/morning-coffee/static/_next/static;
        expires 1d; # Shorter expiry for testing
        access_log off;
        add_header Cache-Control "public, max-age=86400";
    }
    
    # Serve CSS files with proper content type
    location ~* \.css$ {
        add_header Content-Type text/css;
        expires 1d; # Shorter expiry for testing
        add_header Cache-Control "public, max-age=86400";
    }

    # Serve JavaScript files with proper content type
    location ~* \.js$ {
        add_header Content-Type application/javascript;
        expires 1d; # Shorter expiry for testing
        add_header Cache-Control "public, max-age=86400";
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/morningcoffee.aireeaa.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/morningcoffee.aireeaa.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    if (\$host = morningcoffee.aireeaa.com) {
        return 301 https://\$host\$request_uri;
    } # managed by Certbot

    listen 80;
    server_name morningcoffee.aireeaa.com;
    return 404; # managed by Certbot
}
EOL

# Apply the fixed Nginx configuration
echo "Applying Nginx configuration..."
sudo cp nginx-fixed.conf /etc/nginx/sites-available/morningcoffee.aireeaa.com.conf
sudo systemctl reload nginx

# Force clear Nginx cache
echo "Clearing Nginx cache..."
sudo rm -rf /var/cache/nginx/*

# Restart Nginx service
echo "Restarting Nginx service..."
sudo systemctl restart nginx

echo "---------------------------------------"
echo "Deep cleanup and fix completed!"
echo "Please test the site at: https://morningcoffee.aireeaa.com/testing/voice-test"
echo "---------------------------------------"
echo "To verify the page is updated, check for the Provider Selection section at the top of the Voice Testing Lab."
echo
echo "If still not working, try:"
echo "1. Clear your browser cache: Ctrl+Shift+Delete"
echo "2. Access in an incognito/private window"
echo "3. Add a random query parameter: ?refresh=$(date +%s)"
echo "4. Check the browser developer console for errors" 