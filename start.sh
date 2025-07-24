#!/bin/bash

# NOAA Climate Data Globe - Integrated Demo Script
# Starts both WebSocket server and React Three Fiber frontend

echo "🌍 Starting NOAA Climate Data Globe System"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to handle cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $WEBSOCKET_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    kill $HTTP_SERVER_PID 2>/dev/null
    
    # Deactivate virtual environment if it was activated
    if [ -n "$VIRTUAL_ENV" ]; then
        echo -e "${BLUE}🐍 Deactivating virtual environment...${NC}"
        deactivate 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGINT SIGTERM

# Activate Python virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${BLUE}🐍 Activating Python virtual environment...${NC}"
    source .venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${YELLOW}⚠️  No .venv directory found, using system Python${NC}"
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not found. Please install Python 3.7+${NC}"
    exit 1
fi

# Verify we're using the correct Python
PYTHON_PATH=$(which python)
echo -e "${BLUE}🐍 Using Python: ${PYTHON_PATH}${NC}"

# Check if required Python packages are installed
echo -e "${BLUE}📦 Checking Python dependencies...${NC}"
if ! python -c "import websockets, requests, numpy, pandas" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Some Python dependencies missing. Installing from requirements.txt...${NC}"
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        echo -e "${YELLOW}⚠️  requirements.txt not found, installing essential packages...${NC}"
        pip install websockets requests numpy pandas
    fi
fi

# Check if Node.js is available
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm not found. Please install Node.js${NC}"
    exit 1
fi

# Start HTTP server for textures (background)
echo -e "${BLUE}🔗 Starting texture server on port 8000...${NC}"
python -m http.server 8000 --directory . > /dev/null 2>&1 &
HTTP_SERVER_PID=$!

# Wait a moment for server to start
sleep 2

# Start WebSocket server (background) - USE FIXED LAND VALIDATION SERVER
echo -e "${BLUE}🌊 Starting Fixed Land Validation WebSocket server on port 8765...${NC}"
echo -e "${YELLOW}🚨 Using NEW server with proper land/ocean validation${NC}"
python fixed_land_validation_server.py > websocket.log 2>&1 &
WEBSOCKET_PID=$!

# Wait a moment for WebSocket server to start
sleep 3

# Navigate to web-globe directory and start React app
echo -e "${BLUE}⚛️  Starting React Three Fiber frontend...${NC}"
cd web-globe

# Check if node_modules exists, install if not
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
    npm install
fi

# Start development server (background)
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!

# Return to root directory
cd ..

echo -e "${GREEN}✅ All services started successfully!${NC}"
echo ""
echo -e "${GREEN}🌍 Globe Interface: ${BLUE}http://localhost:5173${NC}"
echo -e "${GREEN}🔗 Texture Server: ${BLUE}http://localhost:8000${NC}"
echo -e "${GREEN}🌐 WebSocket Server: ${BLUE}ws://localhost:8765${NC}"
echo ""
echo -e "${YELLOW}📊 Usage:${NC}"
echo "  • Click anywhere on the 3D globe to select coordinates"
echo "  • Toggle SST overlay with the button in the data panel"
echo "  • Rotate, zoom, and pan the globe with mouse controls"
echo "  • Climate data will be fetched automatically for selected locations"
echo ""
echo -e "${YELLOW}📄 Logs:${NC}"
echo "  • WebSocket server: tail -f websocket.log"
echo "  • Frontend: tail -f frontend.log"
echo ""
echo -e "${RED}Press Ctrl+C to stop all services${NC}"

# Wait for user interruption
while true; do
    sleep 1
done