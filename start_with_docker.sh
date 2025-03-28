#!/bin/bash
# Script to start the Morning Coffee application with Docker Compose

# Display banner
echo "=================================================="
echo "    MORNING COFFEE DOCKER STARTER"
echo "=================================================="
echo

# Ensure .env file exists
if [ ! -f .env ]; then
  echo "Error: .env file not found!"
  echo "Please create a .env file with required configuration."
  echo "You can copy the example file with: cp .env.example .env"
  exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  echo "Error: Docker is not installed!"
  echo "Please install Docker and Docker Compose before running this script."
  exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
  echo "Error: Docker Compose is not installed!"
  echo "Please install Docker Compose before running this script."
  exit 1
fi

# Offer options for starting
echo "Please select a mode to start the application:"
echo "1. Production mode (all services, detached)"
echo "2. Development mode (with hot reloading)"
echo "3. Stop all containers"
echo "4. Restart specific service"
echo "5. View logs"
read -p "Enter your choice (1-5): " choice

case $choice in
  1)
    echo "Starting in production mode..."
    docker-compose up -d
    echo
    echo "Services started. Check status with: docker-compose ps"
    ;;
  2)
    echo "Starting in development mode..."
    docker-compose -f docker-compose.dev.yml up
    ;;
  3)
    echo "Stopping all containers..."
    docker-compose down
    echo "All containers stopped."
    ;;
  4)
    echo "Available services:"
    echo "- app (API server)"
    echo "- spark-tts (TTS service)"
    echo "- redis (Database)"
    echo "- frontend (Web UI)"
    read -p "Enter service name to restart: " service
    
    echo "Restarting $service..."
    docker-compose restart $service
    echo "$service restarted."
    ;;
  5)
    echo "Viewing logs..."
    echo "Press Ctrl+C to exit logs view."
    docker-compose logs -f
    ;;
  *)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac

echo
echo "=================================================="
echo "  MORNING COFFEE SERVICES"
echo "=================================================="
docker-compose ps 