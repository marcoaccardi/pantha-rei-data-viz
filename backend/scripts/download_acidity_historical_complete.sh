#!/bin/bash

# Complete Acidity Historical Dataset Download
# Downloads CMEMS historical biogeochemistry data (1993-2022)
# Current status: Only has 1993-01-01 to 1993-01-27
# Missing: 1993-01-28 to 2022-12-31 (29+ years)

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${CYAN}Acidity Historical Dataset - Complete Download${NC}"
echo -e "${CYAN}==============================================${NC}"

# Change to backend directory and activate virtual environment
cd "$BACKEND_DIR"
if [ ! -d ".venv" ]; then
    log_error "Virtual environment not found. Run 'uv venv' first."
    exit 1
fi

log_info "Activating virtual environment..."
source .venv/bin/activate

# Check CMEMS credentials
if [ ! -f "config/.env" ]; then
    log_error "CMEMS credentials not found. Create config/.env with CMEMS_USERNAME and CMEMS_PASSWORD"
    exit 1
fi

log_info "Current status: acidity_historical has data through 1993-01-27"
log_info "Missing data: 1993-01-28 to 2022-12-31 (29+ years)"
echo ""

# Option 1: Complete 1993 first
log_info "Step 1: Completing 1993 data (Jan 28 - Dec 31)..."
./scripts/update_all_data.sh -d acidity --acidity-source historical -s 1993-01-28 -e 1993-12-31 --force --verbose

if [ $? -eq 0 ]; then
    log_info "✅ 1993 acidity historical data completed"
else
    log_error "❌ 1993 acidity historical data failed"
    log_error "Check CMEMS credentials and network connection"
    exit 1
fi

echo ""

# Option 2: Download all remaining years (1994-2022)
log_info "Step 2: Downloading remaining historical years (1994-2022)..."
log_warn "This will download ~29 years of data - will take several hours"
read -p "Continue with full historical download? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Starting full historical download..."
    ./scripts/update_all_data.sh -d acidity --acidity-source historical -s 1994-01-01 -e 2022-12-31 --force --verbose
    
    if [ $? -eq 0 ]; then
        log_info "✅ Complete acidity historical dataset downloaded!"
        log_info "Coverage: 1993-01-01 to 2022-12-31"
        log_info "Variables: chl, no3, po4, si, o2, nppv"
    else
        log_error "❌ Historical download failed"
        exit 1
    fi
else
    log_info "Partial download completed. Run this script again to continue."
    log_info "Or use: ./scripts/update_all_data.sh -d acidity --acidity-source historical -s 1994-01-01 -e 2022-12-31 --force --verbose"
fi

echo -e "${CYAN}==============================================${NC}"