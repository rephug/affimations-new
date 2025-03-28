#!/bin/bash
set -e

# Load environment variables from .env.production if it exists
if [ -f ".env.production" ]; then
  export $(grep -v '^#' .env.production | xargs)
fi

# Make sure npm install completed successfully
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Build and run Docker containers
echo "Building and starting Docker containers..."
docker-compose -f docker-compose.nextjs.yml up -d --build

echo "Containers are now running!"
echo "You can view the application at http://152.53.84.219"
echo ""
echo "To view logs: docker-compose -f docker-compose.nextjs.yml logs -f"
echo "To stop: docker-compose -f docker-compose.nextjs.yml down" 