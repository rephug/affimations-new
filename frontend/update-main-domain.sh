#!/bin/bash

set -e

echo "------------------------------------"
echo "Morning Coffee Main Domain Update Script"
echo "------------------------------------"

# Navigate to the frontend directory
cd /home/adminrob/projects/affimations/frontend

# Create updated configuration for the main domain
cat > aireeaa.com.new.conf << 'EOL'
server {
    server_name aireeaa.com www.aireeaa.com;

    # Increase max body size for webhook payloads
    client_max_body_size 10M;

    # Serve static files directly from our static directory
    location /_next/static/ {
        alias /var/www/morning-coffee/static/;
        expires 365d;
        access_log off;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    # For the main application - Frontend (Next.js app)
    location / {
        proxy_pass http://127.0.0.1:3000;
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

    # Direct API access (bypass frontend)
    location /api/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Webhooks endpoints
    location /webhooks/ {
        proxy_pass http://127.0.0.1:5000/webhooks/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Specific settings for webhook endpoint
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Direct TTS access
    location /tts/ {
        proxy_pass http://127.0.0.1:8020/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/adminrob/projects/affimations/static;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/aireeaa.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/aireeaa.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    if ($host = www.aireeaa.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    if ($host = aireeaa.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name aireeaa.com www.aireeaa.com;
    return 404; # managed by Certbot
}
EOL

echo "------------------------------------"
echo "A new configuration file for aireeaa.com has been created."
echo "Backup the existing configuration and apply the new one with the following commands:"
echo ""
echo "sudo cp /etc/nginx/sites-available/aireeaa.com /etc/nginx/sites-available/aireeaa.com.backup"
echo "sudo cp $(pwd)/aireeaa.com.new.conf /etc/nginx/sites-available/aireeaa.com"
echo "sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "WARNING: This will replace the current application running on aireeaa.com"
echo "with the Morning Coffee frontend. Only proceed if you're sure this is what you want."
echo "------------------------------------" 