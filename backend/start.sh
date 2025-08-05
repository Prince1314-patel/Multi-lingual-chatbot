#!/bin/bash

# WebSocket Chat Backend Startup Script
# Usage: ./start.sh [dev|prod] [options]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
MODE="dev"
VENV_PATH="venv"
REQUIREMENTS_FILE="requirements.txt"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [dev|prod] [options]"
    echo ""
    echo "Modes:"
    echo "  dev   - Start in development mode (default)"
    echo "  prod  - Start in production mode"
    echo ""
    echo "Options:"
    echo "  --no-venv     - Skip virtual environment activation"
    echo "  --install     - Install/update dependencies before starting"
    echo "  --help        - Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  HOST                    - Server host (default: 0.0.0.0)"
    echo "  PORT                    - Server port (default: 8000)"
    echo "  LOG_LEVEL              - Logging level (default: info)"
    echo "  CORS_ORIGINS           - Comma-separated CORS origins"
    echo "  WEBSOCKET_TIMEOUT      - WebSocket timeout in seconds"
    echo "  MAX_CONNECTIONS_PER_ROOM - Max connections per room"
}

# Parse command line arguments
USE_VENV=true
INSTALL_DEPS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        dev|development)
            MODE="dev"
            shift
            ;;
        prod|production)
            MODE="prod"
            shift
            ;;
        --no-venv)
            USE_VENV=false
            shift
            ;;
        --install)
            INSTALL_DEPS=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Print startup header
print_header "🚀 WebSocket Chat Backend Startup Script"
print_header "=========================================="

# Check if we're in the backend directory
if [[ ! -f "main.py" ]]; then
    print_error "main.py not found. Please run this script from the backend directory."
    exit 1
fi

# Activate virtual environment if requested and available
if [[ "$USE_VENV" == true ]]; then
    if [[ -d "$VENV_PATH" ]]; then
        print_status "Activating virtual environment..."
        source "$VENV_PATH/bin/activate"
        print_status "Virtual environment activated: $(which python)"
    else
        print_warning "Virtual environment not found at $VENV_PATH"
        print_warning "Creating virtual environment..."
        python3 -m venv "$VENV_PATH"
        source "$VENV_PATH/bin/activate"
        print_status "Virtual environment created and activated"
        INSTALL_DEPS=true  # Force dependency installation for new venv
    fi
fi

# Install/update dependencies if requested
if [[ "$INSTALL_DEPS" == true ]]; then
    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        print_status "Installing/updating dependencies..."
        pip install -r "$REQUIREMENTS_FILE"
        print_status "Dependencies installed successfully"
    else
        print_warning "Requirements file not found: $REQUIREMENTS_FILE"
    fi
fi

# Check if required dependencies are available
print_status "Checking dependencies..."
python -c "import fastapi, uvicorn, websockets, pydantic" 2>/dev/null || {
    print_error "Required dependencies not found. Run with --install to install them."
    exit 1
}

# Set environment variables for the mode
export ENVIRONMENT="$MODE"
if [[ "$MODE" == "dev" ]]; then
    export DEBUG="true"
    export RELOAD="true"
    export LOG_LEVEL="${LOG_LEVEL:-debug}"
else
    export DEBUG="false"
    export RELOAD="false"
    export LOG_LEVEL="${LOG_LEVEL:-info}"
fi

# Start the appropriate server
print_status "Starting server in $MODE mode..."
if [[ "$MODE" == "dev" ]]; then
    python start_dev.py
else
    python start_prod.py
fi