#!/bin/bash

# Test script to verify the complete ocean data system
echo "🌊 Testing NOAA Ocean Data System"
echo "=================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Kill any existing servers
echo "🔄 Stopping any existing servers..."
pkill -f simple_websocket_server.py 2>/dev/null
pkill -f real_data_websocket_server.py 2>/dev/null
sleep 2

# Start the real data WebSocket server
echo -e "${YELLOW}🚀 Starting Real Data WebSocket Server...${NC}"
python real_data_websocket_server.py > test_websocket.log 2>&1 &
WEBSOCKET_PID=$!

# Wait for server to start
sleep 5

echo -e "${YELLOW}📊 Running backend tests...${NC}"

# Run processor tests
echo "Testing processors..."
python tests/test_processors.py | grep -E "(✅|❌|SUMMARY|Status:|Action Required)"

echo ""
echo "Testing end-to-end communication..."

# Run end-to-end test
python tests/test_end_to_end.py | grep -E "(✅|❌|Response received|Ocean Data Response|Frontend Compatibility|END-TO-END)"

echo ""
echo -e "${YELLOW}📄 WebSocket Server Logs (last 20 lines):${NC}"
tail -20 test_websocket.log 2>/dev/null || echo "No log file found"

# Cleanup
echo -e "${YELLOW}🔄 Cleaning up...${NC}"
kill $WEBSOCKET_PID 2>/dev/null

echo ""  
echo -e "${GREEN}🏁 Test complete!${NC}"
echo "To run the full system, use: ./start.sh"