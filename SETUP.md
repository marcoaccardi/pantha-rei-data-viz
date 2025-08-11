# Cross-Platform Setup Guide

## Prerequisites

### Required Software
- **Python 3.8+** ([Download](https://www.python.org/downloads/))
- **Node.js 16+** ([Download](https://nodejs.org/))
- **uv** (Python package manager) - will be installed automatically if missing

### Installation Notes
- **uv** (Python package manager) will be installed automatically via pip when needed
- Clear step-by-step instructions provided for missing dependencies

## Quick Start

### Option 1: Automated Setup (Recommended)

#### Linux/macOS
```bash
# Make setup script executable and run
chmod +x start.sh
./start.sh
```

#### Windows
```cmd
# Run setup script (provides clear installation instructions if needed)
setup.bat

# Then start the application
start.bat
```

### Option 2: Manual Setup

#### 1. Backend Setup

**Linux/macOS:**
```bash
cd backend
# Create virtual environment
uv venv --python python3
# Activate environment
source activate.sh
# Install dependencies
uv pip install -r requirements.txt
```

**Windows:**
```cmd
cd backend
# Create virtual environment
uv venv --python python
# Activate environment
activate.bat
# Install dependencies
uv pip install -r requirements.txt
```

#### 2. Frontend Setup

**Both platforms:**
```bash
cd frontend
npm install
```

#### 3. Start Services

**Backend (from backend/ directory):**
```bash
# Linux/macOS
source .venv/bin/activate
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Windows
.venv\Scripts\activate.bat
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend (from frontend/ directory):**
```bash
npm run dev
```

## Access Points

After setup, access the application at:
- **Frontend**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Environment Management

### Activation Scripts

Quick activation helpers are provided:

**Linux/macOS:**
```bash
source backend/activate.sh
```

**Windows:**
```cmd
backend\activate.bat
```

### Python Virtual Environment

The project uses `uv` for fast, reliable Python package management:
- Virtual environment location: `backend/.venv/`
- All dependencies are pinned in `backend/requirements.txt`
- Use `uv pip` instead of regular `pip` for consistency

## Troubleshooting

### Common Issues

**"uv not found":**
```bash
pip install uv
```

**"Port already in use":**
- Linux/macOS: The `start.sh` script automatically kills processes on required ports
- Windows: The `start.bat` script handles port conflicts

**Virtual environment activation fails:**
```bash
# Linux/macOS
cd backend && uv venv --python python3

# Windows
cd backend && uv venv --python python
```

**Dependencies install errors:**
Make sure you're in the activated virtual environment:
```bash
# Check if in venv (should show virtual env path)
echo $VIRTUAL_ENV  # Linux/macOS
echo %VIRTUAL_ENV%  # Windows
```

### Platform-Specific Notes

**Linux:**
- Uses Python from `/usr/bin/python3`
- Script permissions: `chmod +x start.sh`

**Windows:**
- Uses system Python or conda Python
- Batch scripts have `.bat` extension
- Limited color support in command prompt

**macOS:**
- Same as Linux, may use Homebrew Python
- Ensure Xcode Command Line Tools are installed

## Development Workflow

1. **First time setup:**
   - Run `setup.bat` (Windows) or `./start.sh` (Linux/macOS)

2. **Daily development:**
   - Run `start.bat` (Windows) or `./start.sh` (Linux/macOS)
   - Access http://localhost:5173 for the frontend

3. **Backend only:**
   - Activate: `source backend/activate.sh` or `backend\activate.bat`
   - Start: `python -m uvicorn api.main:app --reload`

4. **Frontend only:**
   - `cd frontend && npm run dev`

## Architecture

```
pantha-rei-data-viz/
├── backend/                 # Python FastAPI server
│   ├── .venv/              # Virtual environment (created by setup)
│   ├── activate.sh         # Linux/macOS activation
│   ├── activate.bat        # Windows activation
│   ├── requirements.txt    # Python dependencies
│   └── ...
├── frontend/               # React TypeScript app
│   ├── node_modules/      # NPM dependencies (created by setup)
│   ├── package.json       # Frontend dependencies
│   └── ...
├── start.sh               # Linux/macOS startup script
├── start.bat              # Windows startup script
├── setup.bat              # Windows setup script
└── SETUP.md              # This file
```

## Next Steps

After successful setup:
1. Open http://localhost:5173 in your browser
2. Explore the 3D globe interface
3. Check API documentation at http://localhost:8000/docs
4. Review project documentation in `backend/docs/`