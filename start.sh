#!/bin/bash

# NOAA Climate Data Globe - Integrated Demo Script
# Starts both WebSocket server and React Three Fiber frontend

echo "🌍 Starting NOAA Climate Data Globe System"
echo "=========================================="

# Check if required directories exist
if [ ! -d "backend" ]; then
    echo -e "${RED}❌ backend directory not found${NC}"
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo -e "${RED}❌ frontend directory not found${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    echo -e "${BLUE}📁 Creating logs directory...${NC}"
    mkdir -p logs
fi

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

# Activate backend Python virtual environment
if [ -d "backend/.venv" ]; then
    echo -e "${BLUE}🐍 Activating backend virtual environment...${NC}"
    source backend/.venv/bin/activate
    echo -e "${GREEN}✅ Backend virtual environment activated${NC}"
elif [ -d ".venv" ]; then
    echo -e "${BLUE}🐍 Activating root virtual environment...${NC}"
    source .venv/bin/activate
    echo -e "${GREEN}✅ Root virtual environment activated${NC}"
else
    echo -e "${YELLOW}⚠️  No virtual environment found, using system Python${NC}"
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
if ! python -c "import websockets, requests, numpy, pandas, asyncio, json, pathlib" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Some Python dependencies missing. Installing from requirements.txt...${NC}"
    
    # Check backend requirements first
    if [ -f "backend/requirements.txt" ]; then
        echo -e "${BLUE}📦 Installing backend dependencies...${NC}"
        pip install -r backend/requirements.txt
    elif [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        echo -e "${YELLOW}⚠️  requirements.txt not found, installing essential packages...${NC}"
        pip install websockets requests numpy pandas python-dotenv
    fi
fi

# Check for Copernicus Marine CLI (required for real data)
echo -e "${BLUE}🌊 Checking Copernicus Marine CLI...${NC}"
if ! python -c "import copernicusmarine" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Copernicus Marine CLI not found. Installing...${NC}"
    pip install copernicusmarine
    echo -e "${GREEN}✅ Copernicus Marine CLI installed${NC}"
else
    echo -e "${GREEN}✅ Copernicus Marine CLI available${NC}"
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

# Start WebSocket server (background) - USE SIMPLE RELIABLE SERVER
echo -e "${BLUE}🌊 Starting Ocean Data WebSocket server on port 8765...${NC}"
echo -e "${GREEN}✅ Auto-detects real data availability (Copernicus Marine)${NC}"
echo -e "${YELLOW}ℹ️  Falls back to synthetic data if real data unavailable${NC}"
python backend/servers/simple_websocket_server.py > logs/websocket.log 2>&1 &
WEBSOCKET_PID=$!

# Check if server started successfully
sleep 3
if ! ps -p $WEBSOCKET_PID > /dev/null 2>&1; then
    echo -e "${RED}❌ WebSocket server failed to start. Checking logs...${NC}"
    if [ -f "logs/websocket.log" ]; then
        tail -10 logs/websocket.log
    fi
    echo -e "${YELLOW}🔧 Trying fallback server...${NC}"
    python backend/servers/fallback_websocket_server.py > logs/websocket.log 2>&1 &
    WEBSOCKET_PID=$!
    sleep 2
    if ! ps -p $WEBSOCKET_PID > /dev/null 2>&1; then
        echo -e "${RED}❌ All servers failed to start. Check logs/websocket.log${NC}"
        exit 1
    fi
fi

# Wait a moment for WebSocket server to start
sleep 3

# Navigate to frontend directory and start React app
echo -e "${BLUE}⚛️  Starting React Three Fiber frontend...${NC}"
cd frontend

# Check if node_modules exists, install if not
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
    npm install
fi

# Start development server (background)
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

# Return to root directory
cd ..

echo -e "${GREEN}✅ All services started successfully!${NC}"
echo ""
echo -e "${GREEN}🌊 OCEAN DATA & DATE FUNCTIONALITY READY${NC}"
echo -e "${GREEN}🌍 Globe Interface: ${BLUE}http://localhost:5175${NC}"
echo -e "${GREEN}🔗 Texture Server: ${BLUE}http://localhost:8000${NC}"
echo -e "${GREEN}🌐 WebSocket Server: ${BLUE}ws://localhost:8765${NC}"
echo ""
echo -e "${BLUE}📊 Features Available:${NC}"
echo -e "${GREEN}  ✅ Random ocean coordinate generation (120 verified points)${NC}"
echo -e "${GREEN}  ✅ Random date generation with data availability validation${NC}"
echo -e "${GREEN}  ✅ Real ocean data: SST, salinity, waves, currents, chlorophyll, pH${NC}"
echo -e "${GREEN}  ✅ Temporal coverage: 1972-2025 with guaranteed data from 2022-06-01${NC}"
echo -e "${GREEN}  ✅ Real-time WebSocket communication with date parameters${NC}"
echo -e "${GREEN}  ✅ Automatic data download and caching with progress notifications${NC}"
echo -e "${GREEN}  ✅ Smart caching - subsequent requests load instantly${NC}"
echo ""
echo -e "${YELLOW}📊 Usage:${NC}"
echo "  • Click anywhere on the 3D globe to select coordinates"
echo "  • Use date picker to select specific dates or generate random dates"
echo "  • Click 'Random Location' for verified ocean coordinates"
echo "  • Click 'Random Both' for random date + location combinations"
echo "  • Toggle SST overlay with the button in the data panel"
echo "  • Rotate, zoom, and pan the globe with mouse controls"
echo "  • Ocean data will be fetched automatically for selected locations and dates"
echo ""
echo -e "${YELLOW}📄 Logs:${NC}"
echo "  • WebSocket server: tail -f logs/websocket.log"
echo "  • Frontend: tail -f logs/frontend.log"
echo ""
echo -e "${RED}Press Ctrl+C to stop all services${NC}"

# Wait for user interruption
while true; do
    sleep 1
done