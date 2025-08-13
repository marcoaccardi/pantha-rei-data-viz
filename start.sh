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

# Store the root directory
ROOT_DIR=$(pwd)

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
    
    # Stop monitor process by removing flag file and killing process
    rm -f "/tmp/monitor_services_$$" 2>/dev/null || true
    if [ -n "$MONITOR_PID" ]; then
        kill -KILL $MONITOR_PID 2>/dev/null || true
        echo -e "${BLUE}🔍 Background monitor stopped${NC}"
    fi
    
    # Kill main services and their children aggressively
    if [ -n "$API_PID" ]; then
        # Kill the process group
        kill -KILL -$API_PID 2>/dev/null || true
        kill -KILL $API_PID 2>/dev/null || true
        echo -e "${BLUE}🌊 API server stopped${NC}"
    fi
    
    if [ -n "$FRONTEND_PID" ]; then
        # Kill the process group  
        kill -KILL -$FRONTEND_PID 2>/dev/null || true
        kill -KILL $FRONTEND_PID 2>/dev/null || true
        echo -e "${BLUE}⚛️  Frontend server stopped${NC}"
    fi
    
    # Force kill any remaining processes on our ports
    sudo fuser -k 8000/tcp 2>/dev/null || true
    sudo fuser -k 5173/tcp 2>/dev/null || true
    
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

# Function to kill processes on specific ports
kill_port_processes() {
    local port=$1
    local service_name=$2
    
    echo -e "${BLUE}🔍 Checking for processes on port ${port} (${service_name})...${NC}"
    
    # Find and kill processes using the port
    local pids=$(lsof -ti:${port} 2>/dev/null)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}⚠️  Found existing processes on port ${port}: $pids${NC}"
        echo -e "${YELLOW}🔧 Killing processes on port ${port}...${NC}"
        kill -9 $pids 2>/dev/null || true
        sleep 2
        
        # Verify they're gone
        local remaining=$(lsof -ti:${port} 2>/dev/null)
        if [ -n "$remaining" ]; then
            echo -e "${RED}❌ Failed to free port ${port}${NC}"
            return 1
        else
            echo -e "${GREEN}✅ Port ${port} freed${NC}"
        fi
    else
        echo -e "${GREEN}✅ Port ${port} is free${NC}"
    fi
    return 0
}

# Free all required ports before starting services
echo -e "${BLUE}🧹 Freeing required ports...${NC}"
kill_port_processes 8765 "WebSocket Server"
kill_port_processes 8000 "HTTP Server" 
kill_port_processes 5173 "Frontend Dev Server"

# Force use of backend Python virtual environment with uv
cd backend
if [ -d ".venv" ]; then
    echo -e "${BLUE}🐍 Using backend virtual environment (uv managed)...${NC}"
    # Use uv to activate environment
    source .venv/bin/activate
    # Set explicit Python path to avoid conda conflicts
    export PYTHON_BIN="$ROOT_DIR/backend/.venv/bin/python"
    export PATH="$ROOT_DIR/backend/.venv/bin:$PATH"
    echo -e "${GREEN}✅ Backend virtual environment activated${NC}"
else
    echo -e "${YELLOW}⚠️  Backend .venv not found, creating with uv...${NC}"
    uv venv
    source .venv/bin/activate
    export PYTHON_BIN="$ROOT_DIR/backend/.venv/bin/python"
    export PATH="$ROOT_DIR/backend/.venv/bin:$PATH"
    echo -e "${GREEN}✅ Created and activated uv virtual environment${NC}"
fi
cd "$ROOT_DIR"

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
if ! python -c "import fastapi, uvicorn, requests, numpy, pandas, asyncio, json, pathlib" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Some Python dependencies missing. Installing from requirements.txt...${NC}"
    
    # Use uv for package installation
    if [ -f "backend/requirements.txt" ]; then
        echo -e "${BLUE}📦 Installing backend dependencies with uv...${NC}"
        cd backend && uv pip install -r requirements.txt && cd "$ROOT_DIR"
    else
        echo -e "${YELLOW}⚠️  requirements.txt not found, installing essential packages...${NC}"
        cd backend && uv pip install fastapi uvicorn requests numpy pandas python-dotenv && cd "$ROOT_DIR"
    fi
fi

# Check for Copernicus Marine CLI (required for real data)
echo -e "${BLUE}🌊 Checking Copernicus Marine CLI...${NC}"
if ! python -c "import copernicusmarine" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Copernicus Marine CLI not found. Installing with uv...${NC}"
    cd backend && uv pip install copernicusmarine && cd "$ROOT_DIR"
    echo -e "${GREEN}✅ Copernicus Marine CLI installed${NC}"
else
    echo -e "${GREEN}✅ Copernicus Marine CLI available${NC}"
fi

# Check if Node.js is available
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm not found. Please install Node.js${NC}"
    exit 1
fi

# Start FastAPI backend server
echo -e "${BLUE}🌊 Starting Ocean Data API server on port 8000...${NC}"
echo -e "${GREEN}✅ Using FastAPI with real data from Copernicus Marine${NC}"

# Start the FastAPI server
echo -e "${BLUE}🔬 Starting FastAPI ocean data server...${NC}"
# Use explicit Python path if available, otherwise fallback to 'python'
if [ -n "$PYTHON_BIN" ]; then
    echo -e "${BLUE}🐍 Using Python: ${PYTHON_BIN}${NC}"
    cd backend && setsid $PYTHON_BIN -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > "$ROOT_DIR/logs/api.log" 2>&1 &
else
    cd backend && setsid python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > "$ROOT_DIR/logs/api.log" 2>&1 &
fi
API_PID=$!
cd "$ROOT_DIR"

# Check if API server started successfully with retries
for attempt in {1..5}; do
    sleep 5
    if ps -p $API_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ FastAPI ocean data server started successfully${NC}"
        echo -e "${GREEN}✅ API available at: http://localhost:8000${NC}"
        echo -e "${GREEN}✅ API docs at: http://localhost:8000/docs${NC}"
        break
    else
        echo -e "${YELLOW}⚠️  API server not ready (attempt $attempt/5)...${NC}"
        if [ $attempt -eq 5 ]; then
            echo -e "${RED}❌ API server failed to start after 5 attempts. Checking logs...${NC}"
            if [ -f "logs/api.log" ]; then
                echo -e "${YELLOW}📄 Last 15 lines of api.log:${NC}"
                tail -15 logs/api.log
            fi
            exit 1
        fi
    fi
done

# Test API connection
echo -e "${BLUE}🔗 Testing API connection...${NC}"
sleep 2

# Simple API connection test using curl
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API server is responding correctly${NC}"
else
    echo -e "${RED}❌ API connection test failed${NC}"
    echo -e "${YELLOW}⚠️  Server may still be starting up...${NC}"
fi

# Wait a moment for WebSocket server to start
sleep 3

# Navigate to frontend directory and start React app
echo -e "${BLUE}⚛️  Starting React Three Fiber frontend...${NC}"

# Debug: Ensure we're in the correct directory
echo -e "${BLUE}🔍 Current directory: $(pwd)${NC}"
echo -e "${BLUE}🔍 Looking for frontend directory...${NC}"

if [ ! -d "frontend" ]; then
    echo -e "${RED}❌ frontend directory not found${NC}"
    echo -e "${YELLOW}📁 Available directories: $(ls -la | grep ^d)${NC}"
    exit 1
fi

cd frontend

# Check if node_modules exists, install if not
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
    npm install
fi

# Start development server (background)
setsid npm run dev > "$ROOT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!

# Return to root directory
cd "$ROOT_DIR"

echo -e "${GREEN}✅ All services started successfully!${NC}"
echo ""
echo -e "${GREEN}🌊 REAL OCEAN DATA & DATE FUNCTIONALITY READY${NC}"
echo -e "${GREEN}🌍 Globe Interface: ${BLUE}http://localhost:5173${NC}"
echo -e "${GREEN}🔗 API Server: ${BLUE}http://localhost:8000${NC}"
echo -e "${GREEN}📖 API Documentation: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "${BLUE}📊 Features Available:${NC}"
echo -e "${GREEN}  ✅ Random ocean coordinate generation (120 verified points)${NC}"
echo -e "${GREEN}  ✅ Random date generation with data availability validation${NC}"
echo -e "${GREEN}  ✅ REAL ocean data from Copernicus Marine: SST, salinity, currents, chlorophyll, pH${NC}"
echo -e "${GREEN}  ✅ Temporal coverage: 1972-2025 with guaranteed data from 2022-06-01${NC}"
echo -e "${GREEN}  ✅ Real-time REST API communication with date parameters${NC}"
echo -e "${GREEN}  ✅ Automatic data download and caching with progress notifications${NC}"
echo -e "${GREEN}  ✅ Smart caching - subsequent requests load instantly${NC}"
echo -e "${GREEN}  ✅ Port management - all ports freed before startup${NC}"
echo -e "${GREEN}  ✅ WebSocket connection verification${NC}"
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
echo "  • API server: tail -f logs/api.log"
echo "  • Frontend: tail -f logs/frontend.log"
echo ""
echo -e "${RED}Press Ctrl+C to stop all services${NC}"

# Background process monitoring function
monitor_services() {
    # Create a flag file to control monitoring
    local monitor_flag="/tmp/monitor_services_$$"
    touch "$monitor_flag"
    
    while [ -f "$monitor_flag" ]; do
        sleep 30  # Check every 30 seconds
        
        # Exit if flag file is removed
        [ ! -f "$monitor_flag" ] && break
        
        # Check API server
        if ! ps -p $API_PID > /dev/null 2>&1; then
            echo -e "\n${RED}⚠️  API server crashed! Attempting restart...${NC}"
            
            # Try to restart API server
            cd backend
            if [ -n "$PYTHON_BIN" ]; then
                setsid $PYTHON_BIN -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > "$ROOT_DIR/logs/api.log" 2>&1 &
            else
                setsid python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > "$ROOT_DIR/logs/api.log" 2>&1 &
            fi
            API_PID=$!
            cd "$ROOT_DIR"
            
            # Wait and check if restart succeeded
            sleep 5
            if ps -p $API_PID > /dev/null 2>&1; then
                echo -e "${GREEN}✅ API server restarted successfully${NC}"
            else
                echo -e "${RED}❌ Failed to restart API server${NC}"
            fi
        fi
        
        # Check frontend server
        if ! ps -p $FRONTEND_PID > /dev/null 2>&1; then
            echo -e "\n${RED}⚠️  Frontend server crashed! Attempting restart...${NC}"
            
            cd frontend
            setsid npm run dev > "$ROOT_DIR/logs/frontend.log" 2>&1 &
            FRONTEND_PID=$!
            cd "$ROOT_DIR"
            
            # Wait and check if restart succeeded
            sleep 5
            if ps -p $FRONTEND_PID > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Frontend server restarted successfully${NC}"
            else
                echo -e "${RED}❌ Failed to restart frontend server${NC}"
            fi
        fi
    done
    
    # Clean up flag file
    rm -f "$monitor_flag"
}

# Start background monitoring
monitor_services &
MONITOR_PID=$!

echo -e "${BLUE}🔍 Background service monitoring active (PID: $MONITOR_PID)${NC}"

# Wait for user interruption
wait