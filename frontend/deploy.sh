#!/bin/bash

set -e

# Display deployment banner
echo "------------------------------------"
echo "Morning Coffee Frontend Deployment"
echo "------------------------------------"

# Source environment variables if available
if [ -f .env.production ]; then
  echo "Loading environment variables..."
  source .env.production
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  echo "Docker is not installed. Please install Docker before continuing."
  exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
  echo "Docker Compose is not installed. Please install Docker Compose before continuing."
  exit 1
fi

# Stop any existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.nextjs.yml down 2>/dev/null || true

# Build and start the Docker containers
echo "Building and starting containers..."
docker-compose -f docker-compose.nextjs.yml up -d --build

# Check if containers are running
echo "Checking container status..."
sleep 5
if docker ps | grep morning-coffee-frontend; then
  echo "------------------------------------"
  echo "Deployment successful!"
  echo "Application is running at: http://152.53.84.219:3000"
  echo "------------------------------------"
else
  echo "------------------------------------"
  echo "Deployment failed. Check docker logs for details:"
  echo "docker logs morning-coffee-frontend"
  echo "------------------------------------"
  exit 1
fi 