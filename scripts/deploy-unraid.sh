#!/bin/bash

# HD HomeRun XMLTV Converter - Unraid Deployment Script
# This script helps deploy the application to Unraid using Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.unraid.yml"
ENV_FILE=".env.unraid"
APP_DIR="/mnt/user/appdata/hdhr-xmltv"

echo -e "${BLUE}HD HomeRun XMLTV Converter - Unraid Deployment${NC}"
echo "================================================="

# Function to create directories
create_directories() {
    echo -e "${YELLOW}Creating application directories...${NC}"
    
    # Create app config directory
    if [ ! -d "$APP_DIR" ]; then
        mkdir -p "$APP_DIR"
        echo "Created: $APP_DIR"
    fi
    
    # Create output directory
    if [ ! -d "$APP_DIR/output" ]; then
        mkdir -p "$APP_DIR/output"
        echo "Created: $APP_DIR/output"
    fi
    
    # Set permissions
    chmod -R 755 "$APP_DIR"
    echo -e "${GREEN}Directories created successfully${NC}"
}

# Function to copy configuration files
copy_configs() {
    echo -e "${YELLOW}Copying configuration files...${NC}"
    
    # Copy environment file
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$APP_DIR/.env"
        echo "Copied: $ENV_FILE -> $APP_DIR/.env"
    else
        echo -e "${RED}Error: $ENV_FILE not found${NC}"
        exit 1
    fi
    
    # Copy docker compose file
    if [ -f "$COMPOSE_FILE" ]; then
        cp "$COMPOSE_FILE" "$APP_DIR/docker-compose.yml"
        echo "Copied: $COMPOSE_FILE -> $APP_DIR/docker-compose.yml"
    else
        echo -e "${RED}Error: $COMPOSE_FILE not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Configuration files copied successfully${NC}"
}

# Function to deploy with docker compose
deploy() {
    echo -e "${YELLOW}Deploying HD HomeRun XMLTV Converter...${NC}"
    
    cd "$APP_DIR"
    
    # Pull latest image
    echo "Pulling latest image..."
    docker-compose pull
    
    # Start the service
    echo "Starting service..."
    docker-compose up -d
    
    echo -e "${GREEN}Deployment completed successfully!${NC}"
}

# Function to show status
show_status() {
    echo -e "${YELLOW}Service Status:${NC}"
    cd "$APP_DIR"
    docker-compose ps
    
    echo -e "\n${YELLOW}Recent Logs:${NC}"
    docker-compose logs --tail=20
}

# Function to show configuration info
show_info() {
    echo -e "\n${BLUE}Deployment Information:${NC}"
    echo "App Directory: $APP_DIR"
    echo "Output Directory: $APP_DIR/output"
    echo "XMLTV File: $APP_DIR/output/xmltv.xml"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "View logs: cd $APP_DIR && docker-compose logs -f"
    echo "Restart: cd $APP_DIR && docker-compose restart"
    echo "Stop: cd $APP_DIR && docker-compose down"
    echo "Test run: cd $APP_DIR && docker-compose run --rm hdhr-xmltv-converter once"
    echo ""
    echo -e "${YELLOW}Integration with Plex:${NC}"
    echo "Point Plex DVR XMLTV to: $APP_DIR/output/xmltv.xml"
    echo "Or mount directly to Plex config by updating OUTPUT_VOLUME in .env"
}

# Main execution
main() {
    echo -e "${BLUE}Starting deployment process...${NC}"
    
    # Check if running on Unraid
    if [ ! -d "/mnt/user" ]; then
        echo -e "${RED}Warning: This script is designed for Unraid servers${NC}"
        echo "Continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check for required files
    if [ ! -f "$COMPOSE_FILE" ] || [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: Required files not found in current directory${NC}"
        echo "Make sure you're running this from the docker/ directory"
        echo "Required files: $COMPOSE_FILE, $ENV_FILE"
        exit 1
    fi
    
    create_directories
    copy_configs
    deploy
    show_status
    show_info
    
    echo -e "\n${GREEN}HD HomeRun XMLTV Converter deployed successfully!${NC}"
}

# Handle command line arguments
case "${1:-}" in
    "deploy")
        main
        ;;
    "status")
        cd "$APP_DIR" 2>/dev/null || { echo "App not deployed yet"; exit 1; }
        show_status
        ;;
    "logs")
        cd "$APP_DIR" 2>/dev/null || { echo "App not deployed yet"; exit 1; }
        docker-compose logs -f
        ;;
    "restart")
        cd "$APP_DIR" 2>/dev/null || { echo "App not deployed yet"; exit 1; }
        docker-compose restart
        ;;
    "stop")
        cd "$APP_DIR" 2>/dev/null || { echo "App not deployed yet"; exit 1; }
        docker-compose down
        ;;
    "update")
        cd "$APP_DIR" 2>/dev/null || { echo "App not deployed yet"; exit 1; }
        docker-compose pull && docker-compose up -d
        ;;
    *)
        echo "HD HomeRun XMLTV Converter - Unraid Deployment Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  deploy  - Deploy the application (default)"
        echo "  status  - Show service status and logs"
        echo "  logs    - Follow service logs"
        echo "  restart - Restart the service"
        echo "  stop    - Stop the service"
        echo "  update  - Update to latest image"
        echo ""
        echo "First time setup: $0 deploy"
        echo ""
        exit 1
        ;;
esac