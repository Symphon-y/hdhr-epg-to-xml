#!/bin/bash

# Helper script for HD HomeRun XMLTV Converter development and testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
HDHR_HOST="${HDHR_HOST:-hdhomerun.local}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/output}"
LOGS_DIR="${LOGS_DIR:-$PROJECT_ROOT/logs}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build           Build the Docker image"
    echo "  build-dev       Build the development Docker image"
    echo "  run             Run the container in production mode"
    echo "  run-dev         Run the container in development mode"
    echo "  run-once        Run the conversion once and exit"
    echo "  test            Run the application locally (requires Python env)"
    echo "  clean           Clean up containers and images"
    echo "  logs            Show container logs"
    echo "  health          Check application health"
    echo ""
    echo "Environment variables:"
    echo "  HDHR_HOST       HD HomeRun device hostname/IP (default: hdhomerun.local)"
    echo "  OUTPUT_DIR      Output directory (default: ./output)"
    echo "  LOGS_DIR        Logs directory (default: ./logs)"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 run-once"
    echo "  HDHR_HOST=192.168.1.100 $0 test"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

ensure_dirs() {
    mkdir -p "$OUTPUT_DIR" "$LOGS_DIR"
    log_info "Created directories: $OUTPUT_DIR, $LOGS_DIR"
}

build_image() {
    log_info "Building production Docker image..."
    cd "$PROJECT_ROOT"
    docker build -f docker/Dockerfile -t hdhr-xmltv-converter:latest .
    log_success "Production image built successfully"
}

build_dev_image() {
    log_info "Building development Docker image..."
    cd "$PROJECT_ROOT"
    docker build -f docker/Dockerfile --target development -t hdhr-xmltv-converter:dev .
    log_success "Development image built successfully"
}

run_container() {
    ensure_dirs

    log_info "Starting container in production mode..."
    cd "$PROJECT_ROOT/docker"

    export HDHR_HOST="$HDHR_HOST"
    export OUTPUT_VOLUME="$OUTPUT_DIR"

    docker-compose up -d
    log_success "Container started successfully"
    log_info "Use '$0 logs' to view logs"
}

run_dev_container() {
    ensure_dirs

    log_info "Starting container in development mode..."
    cd "$PROJECT_ROOT/docker"

    export HDHR_HOST="$HDHR_HOST"
    export OUTPUT_VOLUME="$OUTPUT_DIR"

    docker-compose -f docker-compose.dev.yml up --build
}

run_once() {
    ensure_dirs

    log_info "Running conversion once..."
    cd "$PROJECT_ROOT/docker"

    export HDHR_HOST="$HDHR_HOST"
    export OUTPUT_VOLUME="$OUTPUT_DIR"

    docker-compose -f docker-compose.dev.yml run --rm hdhr-xmltv-converter-dev
    log_success "Single run completed"
}

test_local() {
    log_info "Running application locally..."
    cd "$PROJECT_ROOT"

    # Set environment variables for local testing
    export HDHR_HOST="$HDHR_HOST"
    export HDHR_OUTPUT_FILE_PATH="$OUTPUT_DIR/xmltv.xml"
    export HDHR_LOG_LEVEL="DEBUG"
    export HDHR_EPG_DAYS="1"
    export PYTHONPATH="$PROJECT_ROOT/src"

    ensure_dirs

    python -m hdhr_xmltv.main --run-once
}

clean_containers() {
    log_info "Cleaning up containers and images..."

    # Stop and remove containers
    docker-compose -f "$PROJECT_ROOT/docker/docker-compose.yml" down 2>/dev/null || true
    docker-compose -f "$PROJECT_ROOT/docker/docker-compose.dev.yml" down 2>/dev/null || true

    # Remove containers
    docker rm -f hdhr-xmltv-converter hdhr-xmltv-converter-dev 2>/dev/null || true

    # Remove images
    docker rmi hdhr-xmltv-converter:latest hdhr-xmltv-converter:dev 2>/dev/null || true

    log_success "Cleanup completed"
}

show_logs() {
    log_info "Showing container logs..."
    cd "$PROJECT_ROOT/docker"
    docker-compose logs -f
}

health_check() {
    log_info "Checking application health..."
    cd "$PROJECT_ROOT/docker"

    export HDHR_HOST="$HDHR_HOST"
    export OUTPUT_VOLUME="$OUTPUT_DIR"

    docker-compose exec hdhr-xmltv-converter python -m hdhr_xmltv.main --health-check
}

# Main script logic
case "${1:-}" in
    build)
        build_image
        ;;
    build-dev)
        build_dev_image
        ;;
    run)
        run_container
        ;;
    run-dev)
        run_dev_container
        ;;
    run-once)
        run_once
        ;;
    test)
        test_local
        ;;
    clean)
        clean_containers
        ;;
    logs)
        show_logs
        ;;
    health)
        health_check
        ;;
    help|--help|-h)
        print_usage
        ;;
    "")
        log_error "No command specified"
        print_usage
        exit 1
        ;;
    *)
        log_error "Unknown command: $1"
        print_usage
        exit 1
        ;;
esac