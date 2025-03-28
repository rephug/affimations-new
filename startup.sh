#!/bin/bash
# Morning Coffee Project Startup Script

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}  Morning Coffee Project Startup Script      ${NC}"
echo -e "${BLUE}==============================================${NC}"

# Check if Docker and Docker Compose are installed
if ! [ -x "$(command -v docker)" ]; then
  echo -e "${RED}Error: Docker is not installed.${NC}" >&2
  echo -e "${YELLOW}Please install Docker first: https://docs.docker.com/get-docker/${NC}"
  exit 1
fi

if ! [ -x "$(command -v docker-compose)" ]; then
  echo -e "${RED}Error: Docker Compose is not installed.${NC}" >&2
  echo -e "${YELLOW}Please install Docker Compose: https://docs.docker.com/compose/install/${NC}"
  exit 1
fi

# Check if .env file exists, create from example if not
if [ ! -f ".env" ]; then
  echo -e "${YELLOW}No .env file found. Creating from .env.example...${NC}"
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo -e "${GREEN}Created .env file. Please edit it with your configuration.${NC}"
    echo -e "${YELLOW}Press any key to open the .env file for editing, or Ctrl+C to exit.${NC}"
    read -n 1 -s
    ${EDITOR:-vi} .env
  else
    echo -e "${RED}No .env.example file found. Please create a .env file manually.${NC}"
    exit 1
  fi
fi

# Create necessary directories
echo -e "${BLUE}Creating necessary directories...${NC}"
mkdir -p app/logs
mkdir -p spark-tts/models

# Check if the user wants to use Docker BuildKit
echo -e "${YELLOW}Would you like to enable Docker BuildKit for faster builds? (y/n)${NC}"
read -r use_buildkit

if [[ $use_buildkit =~ ^[Yy]$ ]]; then
  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1
  echo -e "${GREEN}Docker BuildKit enabled.${NC}"
fi

# Ask if the user wants to start in development or production mode
echo -e "${YELLOW}Do you want to start in development or production mode? (dev/prod)${NC}"
read -r mode

if [[ $mode =~ ^[Dd][Ee][Vv]$ ]]; then
  # Development mode
  echo -e "${BLUE}Starting in development mode...${NC}"
  
  # Build the development containers
  echo -e "${BLUE}Building containers...${NC}"
  docker-compose -f docker-compose.yml -f docker-compose.dev.yml build
  
  # Start the containers
  echo -e "${BLUE}Starting containers...${NC}"
  docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
  
  # Show the logs
  echo -e "${GREEN}Containers started in development mode.${NC}"
  echo -e "${YELLOW}Do you want to view the logs? (y/n)${NC}"
  read -r view_logs
  
  if [[ $view_logs =~ ^[Yy]$ ]]; then
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
  else
    echo -e "${GREEN}You can view the logs later with:${NC}"
    echo -e "${BLUE}docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f${NC}"
  fi
else
  # Production mode
  echo -e "${BLUE}Starting in production mode...${NC}"
  
  # Build the production containers
  echo -e "${BLUE}Building containers...${NC}"
  docker-compose build
  
  # Start the containers
  echo -e "${BLUE}Starting containers...${NC}"
  docker-compose up -d
  
  # Show the logs
  echo -e "${GREEN}Containers started in production mode.${NC}"
  echo -e "${YELLOW}Do you want to view the logs? (y/n)${NC}"
  read -r view_logs
  
  if [[ $view_logs =~ ^[Yy]$ ]]; then
    docker-compose logs -f
  else
    echo -e "${GREEN}You can view the logs later with:${NC}"
    echo -e "${BLUE}docker-compose logs -f${NC}"
  fi
fi

# Check services health
echo -e "${BLUE}Checking service health...${NC}"
sleep 10 # Wait for services to initialize

# Check app health
app_health=$(curl -s http://localhost:5000/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
if [[ $app_health == "healthy" ]]; then
  echo -e "${GREEN}App service: HEALTHY${NC}"
elif [[ $app_health == "degraded" ]]; then
  echo -e "${YELLOW}App service: DEGRADED${NC}"
else
  echo -e "${RED}App service: UNHEALTHY${NC}"
fi

# Check TTS health
tts_health=$(curl -s http://localhost:8020/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
if [[ $tts_health == "healthy" ]]; then
  echo -e "${GREEN}Spark TTS service: HEALTHY${NC}"
else
  echo -e "${RED}Spark TTS service: UNHEALTHY${NC}"
fi

echo -e "${BLUE}==============================================${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${BLUE}==============================================${NC}"
echo -e "Main application: ${GREEN}http://localhost:5000${NC}"
echo -e "Spark TTS service: ${GREEN}http://localhost:8020${NC}"
echo -e "${BLUE}==============================================${NC}" 