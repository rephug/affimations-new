#!/bin/bash

set -e

echo "===== Setting up static HTML page for Morning Coffee Frontend ====="

# Create directory for static files
echo "Creating static HTML directory..."
sudo mkdir -p /var/www/morning-coffee/html
sudo chown -R adminrob:adminrob /var/www/morning-coffee

# Create the index.html file
echo "Creating static HTML page..."
cat > /var/www/morning-coffee/html/index.html << 'EOL'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>morningCallfee | Start Your Day Right</title>
    <style>
        :root {
            /* Color palette inspired by sunrise and coffee */
            --deep-brown: #3B2416;
            --medium-brown: #825B3F;
            --coffee: #A27254;
            --caramel: #C89F82;
            --cream: #F4E4CF;
            --sunrise-orange: #FF8C42;
            --warm-yellow: #FFD166;
            --morning-blue: #7BBCDE;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, var(--cream) 0%, var(--caramel) 100%);
            color: var(--deep-brown);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }
        
        header {
            padding: 20px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 28px;
            font-weight: 700;
            color: var(--deep-brown);
        }
        
        .logo span {
            color: var(--sunrise-orange);
        }
        
        nav a {
            color: var(--deep-brown);
            text-decoration: none;
            margin-left: 25px;
            font-weight: 500;
            transition: color 0.3s ease;
        }
        
        nav a:hover {
            color: var(--sunrise-orange);
        }
        
        .hero {
            display: flex;
            align-items: center;
            padding: 80px 0 60px;
            position: relative;
            overflow: hidden;
        }
        
        .hero-content {
            width: 50%;
            z-index: 1;
        }
        
        .hero-image {
            width: 50%;
            position: relative;
            z-index: 1;
            display: flex;
            justify-content: center;
        }
        
        .hero-image img {
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 15px 30px rgba(59, 36, 22, 0.2);
        }
        
        h1 {
            font-size: 48px;
            font-weight: 800;
            margin-bottom: 20px;
            line-height: 1.2;
            background: linear-gradient(to right, var(--deep-brown), var(--sunrise-orange));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .subtitle {
            font-size: 20px;
            color: var(--medium-brown);
            margin-bottom: 30px;
        }
        
        .btn {
            display: inline-block;
            background: var(--sunrise-orange);
            color: white;
            padding: 12px 30px;
            border-radius: 30px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(255, 140, 66, 0.3);
        }
        
        .btn:hover {
            background: var(--deep-brown);
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(59, 36, 22, 0.3);
        }
        
        .features {
            padding: 60px 0;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(59, 36, 22, 0.1);
            margin-bottom: 60px;
        }
        
        .section-title {
            text-align: center;
            margin-bottom: 50px;
            color: var(--deep-brown);
            font-size: 32px;
            font-weight: 700;
        }
        
        .features-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 30px;
            padding: 0 30px;
        }
        
        .feature-card {
            background: linear-gradient(135deg, white 0%, var(--cream) 100%);
            border-radius: 10px;
            padding: 25px;
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .feature-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 10px 25px rgba(59, 36, 22, 0.1);
        }
        
        .feature-icon {
            font-size: 40px;
            margin-bottom: 15px;
            color: var(--sunrise-orange);
        }
        
        .feature-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 15px;
            color: var(--deep-brown);
        }
        
        .feature-desc {
            color: var(--medium-brown);
            font-size: 16px;
        }
        
        .gradient-circle {
            position: absolute;
            border-radius: 50%;
            opacity: 0.8;
            filter: blur(80px);
            z-index: 0;
        }
        
        .circle-1 {
            width: 400px;
            height: 400px;
            background: var(--warm-yellow);
            top: -100px;
            right: -100px;
        }
        
        .circle-2 {
            width: 300px;
            height: 300px;
            background: var(--coffee);
            bottom: -50px;
            left: -100px;
        }
        
        @media (max-width: 768px) {
            .hero {
                flex-direction: column;
                text-align: center;
                padding: 60px 0 40px;
            }
            
            .hero-content, .hero-image {
                width: 100%;
            }
            
            .hero-content {
                margin-bottom: 40px;
            }
            
            h1 {
                font-size: 36px;
            }
            
            .features-grid {
                grid-template-columns: repeat(1, 1fr);
            }
            
            nav {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">morning<span>Callfee</span></div>
            <nav>
                <a href="#">Home</a>
                <a href="#">Features</a>
                <a href="#">Pricing</a>
                <a href="#">About</a>
                <a href="#" class="btn">Sign Up</a>
            </nav>
        </header>
        
        <section class="hero">
            <div class="gradient-circle circle-1"></div>
            <div class="gradient-circle circle-2"></div>
            
            <div class="hero-content">
                <h1>Start Your Day with Purpose & Energy</h1>
                <p class="subtitle">Your morning call that delivers affirmations, organizes your day, and energizes your mind—all before your first sip of coffee.</p>
                <a href="#" class="btn">Get Started Today</a>
            </div>
            
            <div class="hero-image">
                <img src="https://placehold.co/400x320" alt="Morning call and productivity visualization" />
            </div>
        </section>
        
        <section class="features">
            <h2 class="section-title">Transform Your Mornings</h2>
            
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon">🗣️</div>
                    <h3 class="feature-title">Daily Affirmations</h3>
                    <p class="feature-desc">Start each day with personalized affirmations that boost confidence and set positive intentions.</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">📊</div>
                    <h3 class="feature-title">Smart Briefings</h3>
                    <p class="feature-desc">Get your email summarized, weather updates, and news on topics you care about—all in one call.</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">✅</div>
                    <h3 class="feature-title">Task Management</h3>
                    <p class="feature-desc">Organize your day with voice-controlled task lists and timely reminders.</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">🔍</div>
                    <h3 class="feature-title">Voice Analysis</h3>
                    <p class="feature-desc">Our AI analyzes your voice to adapt conversations and track wellbeing over time.</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">💬</div>
                    <h3 class="feature-title">Intelligent Conversation</h3>
                    <p class="feature-desc">Have meaningful discussions with an AI that remembers your context and preferences.</p>
                </div>
                
                <div class="feature-card">
                    <div class="feature-icon">⏰</div>
                    <h3 class="feature-title">Time-Saving</h3>
                    <p class="feature-desc">Save up to 30 minutes each morning by condensing information and planning efficiently.</p>
                </div>
            </div>
        </section>
    </div>
</body>
</html>
EOL

# Update the Nginx configuration to serve the static HTML
echo "Updating Nginx configuration to serve static HTML..."
cat > /home/adminrob/projects/affimations/frontend/morningcoffee.aireeaa.com.conf << 'EOL'
server {
    listen 80;
    server_name morningcoffee.aireeaa.com;

    # Root directory for static HTML
    root /var/www/morning-coffee/html;
    index index.html;

    # Main location for the root path to serve static HTML
    location = / {
        try_files $uri /index.html;
    }

    # Optional: If you want to keep the Next.js app for other routes
    location ~ ^/(?!api|_next).* {
        try_files $uri $uri/ /index.html;
    }

    # For Next.js API routes and any dynamic functionality
    location ~ ^/(api|_next) {
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

# Apply the Nginx configuration
echo "Applying Nginx configuration..."
sudo cp /home/adminrob/projects/affimations/frontend/morningcoffee.aireeaa.com.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/morningcoffee.aireeaa.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

echo "===== Static HTML page setup complete! ====="
echo "Your landing page should now be visible at https://morningcoffee.aireeaa.com"
echo "This is a static HTML page that does not rely on Next.js for rendering" 