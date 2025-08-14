#!/bin/bash
# Setup script for Linux/macOS - Install all dependencies and create virtual environments

echo "🔧 Pantha Rei Data Viz - Linux/macOS Setup"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python is available
echo -e "${BLUE}🐍 Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.8+ first${NC}"
    echo ""
    echo -e "${YELLOW}📥 Installation Options:${NC}"
    echo "  • Ubuntu/Debian: sudo apt-get install python3 python3-pip python3-venv"
    echo "  • macOS: brew install python3"
    echo "  • Fedora: sudo dnf install python3 python3-pip"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Python found${NC}"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  pip not found. Installing pip...${NC}"
    python3 -m ensurepip --upgrade
fi

# Check if uv is available (optional)
echo -e "${BLUE}📦 Checking uv package manager...${NC}"
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠️  uv not found. Installing uv...${NC}"
    pip3 install uv
fi

if command -v uv &> /dev/null; then
    echo -e "${GREEN}✅ uv available${NC}"
fi

# Check if Node.js is available
echo -e "${BLUE}🟢 Checking Node.js installation...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js first${NC}"
    echo ""
    echo -e "${YELLOW}📥 Installation Options:${NC}"
    echo "  • Ubuntu/Debian: curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs"
    echo "  • macOS: brew install node"
    echo "  • Via nvm: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Node.js found${NC}"

# Setup backend
echo ""
echo -e "${BLUE}🌊 Setting up backend environment...${NC}"
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}📦 Creating Python virtual environment...${NC}"
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to create virtual environment${NC}"
        exit 1
    fi
fi

# Activate virtual environment and install dependencies
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
source .venv/bin/activate

# Upgrade pip first
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Some packages failed to install, trying with uv...${NC}"
    if command -v uv &> /dev/null; then
        uv pip install -r requirements.txt
    fi
fi

echo -e "${GREEN}✅ Backend setup complete${NC}"
cd ..

# Setup frontend
echo ""
echo -e "${BLUE}⚛️  Setting up frontend environment...${NC}"
cd frontend

echo -e "${BLUE}📦 Installing Node.js dependencies...${NC}"
npm install
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to install frontend dependencies${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Frontend setup complete${NC}"
cd ..

echo ""
echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}🚀 Next steps:${NC}"
echo -e "  1. Run ${YELLOW}./start.sh${NC} to start both backend and frontend"
echo -e "  2. Open ${YELLOW}http://localhost:5173${NC} in your browser"
echo -e "  3. For Windows, use ${YELLOW}start.bat${NC} instead"
echo ""
echo -e "${BLUE}📝 Manual activation:${NC}"
echo -e "  • Backend: ${YELLOW}source backend/.venv/bin/activate${NC}"
echo -e "  • Frontend: ${YELLOW}cd frontend && npm run dev${NC}"
echo ""

# Make scripts executable
chmod +x start.sh update_ocean_data.sh

echo -e "${GREEN}✅ Scripts made executable${NC}"