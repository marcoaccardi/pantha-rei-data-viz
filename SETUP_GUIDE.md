# 🚀 Pantha Rei Data Viz - Setup Guide

This guide will help you set up the project from scratch on both Windows and Linux/macOS.

## 📋 Prerequisites

### Required Software
- **Python 3.8+** (3.12 recommended)
- **Node.js 18+** (LTS version recommended)
- **Git** (for cloning the repository)

### Optional but Recommended
- **uv** (fast Python package manager)
- **Conda/Miniconda** (for isolated Python environments)

## 🪟 Windows Setup

### Quick Setup (Recommended)
```batch
# 1. Clone the repository
git clone <repository-url>
cd pantha-rei-data-viz

# 2. Run the setup script
setup.bat

# 3. Start the application
start.bat
```

### Manual Setup
```batch
# 1. Install Python (if not installed)
# Download from https://www.python.org/downloads/
# OR use Chocolatey: choco install python
# OR use Winget: winget install Python.Python.3.12

# 2. Install Node.js (if not installed)
# Download from https://nodejs.org/
# OR use Chocolatey: choco install nodejs
# OR use Winget: winget install OpenJS.NodeJS

# 3. Setup backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd ..

# 4. Setup frontend
cd frontend
npm install
cd ..

# 5. Start the application
start.bat
```

## 🐧 Linux/Ubuntu Setup

### Quick Setup (Recommended)
```bash
# 1. Clone the repository
git clone <repository-url>
cd pantha-rei-data-viz

# 2. Run the setup script
chmod +x setup.sh
./setup.sh

# 3. Start the application
./start.sh
```

### Manual Setup
```bash
# 1. Install Python and Node.js (if not installed)
# Ubuntu/Debian:
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv nodejs npm

# macOS (using Homebrew):
brew install python3 node

# 2. Setup backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# 3. Setup frontend
cd frontend
npm install
cd ..

# 4. Start the application
./start.sh
```

## 🔄 Cross-Platform Compatibility

The project is designed to work on both Windows and Linux/macOS:

### Virtual Environment Issues
If you encounter issues with virtual environments created on different platforms:

**Windows → Linux Migration:**
```bash
cd backend
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Linux → Windows Migration:**
```batch
cd backend
rmdir /s /q .venv
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 📊 Data Management

### Update Ocean Data
```batch
# Windows
update_ocean_data.bat

# Linux/macOS
./update_ocean_data.sh
```

### Command Options
- `--help` - Show help message
- `--validate-only` - Only validate existing files
- `--dry-run` - Preview what would be updated
- `--datasets sst,currents` - Update specific datasets
- `--repair-mode` - Fix corrupted files
- `--cleanup` - Clean old files
- `--force` - Force update even if checks fail

## 🐳 Docker Setup (Alternative)

For a fully isolated environment:

```bash
# Build and run with Docker Compose
docker-compose up --build

# Access the application
# Frontend: http://localhost:5173
# API: http://localhost:8000
```

## 🔧 Troubleshooting

### Common Issues

1. **"Virtual environment not found"**
   - Run `setup.bat` (Windows) or `./setup.sh` (Linux/macOS)

2. **"numpy C-extensions failed"**
   - This happens when mixing Linux and Windows environments
   - Solution: Recreate the virtual environment for your platform

3. **"Port already in use"**
   - Kill existing processes:
     - Windows: `taskkill /f /im python.exe` and `taskkill /f /im node.exe`
     - Linux: `killall python3` and `killall node`

4. **"Module not found" errors**
   - Ensure virtual environment is activated
   - Reinstall dependencies: `pip install -r requirements.txt`

### Environment Variables

Create a `.env` file in the `backend/config/` directory:

```env
# Copernicus Marine Service (optional for ocean data)
CMEMS_USERNAME=your_username
CMEMS_PASSWORD=your_password

# NOAA API (optional for ocean data)
NOAA_API_KEY=your_api_key
```

## 📝 Development Workflow

1. **Activate virtual environment:**
   - Windows: `backend\.venv\Scripts\activate`
   - Linux: `source backend/.venv/bin/activate`

2. **Run backend only:**
   - `cd backend && python -m uvicorn api.main:app --reload`

3. **Run frontend only:**
   - `cd frontend && npm run dev`

4. **Run tests:**
   - Backend: `cd backend && pytest`
   - Frontend: `cd frontend && npm test`

## 🆘 Support

If you encounter issues:
1. Check the logs in `ocean-data/logs/`
2. Ensure all prerequisites are installed
3. Try running the setup script again
4. Create an issue on GitHub with:
   - Your operating system
   - Python version (`python --version`)
   - Node.js version (`node --version`)
   - Error messages from logs

## ✅ Verification

After setup, verify everything works:

```bash
# Check Python
python --version  # Should show 3.8+

# Check Node.js
node --version    # Should show 18+

# Check virtual environment
# Windows: backend\.venv\Scripts\python --version
# Linux: backend/.venv/bin/python --version

# Test API
curl http://localhost:8000/health

# Test Frontend
curl http://localhost:5173
```

## 🎯 Ready to Go!

Once setup is complete:
1. Open http://localhost:5173 in your browser
2. The globe interface should load
3. Click on the globe to select ocean locations
4. View real-time ocean data

Enjoy exploring ocean data! 🌊