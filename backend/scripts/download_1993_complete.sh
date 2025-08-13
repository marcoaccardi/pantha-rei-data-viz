#!/bin/bash

# Complete Historical Data Download Script for 1993
# Downloads all available ocean data for the year 1993
# Note: Some datasets don't start until later years

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
YEAR="1993"
START_DATE="${YEAR}-01-01"
END_DATE="${YEAR}-12-31"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

echo -e "${CYAN}Historical Ocean Data Download for ${YEAR}${NC}"
echo -e "${CYAN}=============================================${NC}"

# Change to backend directory and activate virtual environment
cd "$BACKEND_DIR"
if [ ! -d ".venv" ]; then
    log_error "Virtual environment not found. Run 'uv venv' first."
    exit 1
fi

log_info "Activating virtual environment..."
source .venv/bin/activate

# Check credentials
if [ ! -f "config/.env" ]; then
    log_warn "No credentials file found. CMEMS downloads may fail."
    log_warn "Make sure config/.env exists with CMEMS_USERNAME and CMEMS_PASSWORD"
fi

log_info "Starting downloads for ${YEAR}..."
echo ""

# 1. SST Raw Data (Available from 1981-09-01) ✅
log_info "1/4 Downloading SST raw data for ${YEAR}..."
./scripts/update_all_data.sh -d sst -s "$START_DATE" -e "$END_DATE" --verbose
if [ $? -eq 0 ]; then
    log_info "✅ SST raw data download completed"
else
    log_error "❌ SST raw data download failed"
fi
echo ""


# 2. Acidity Historical Data (Available from 1993-01-01) ✅
log_info "2/3 Downloading acidity historical data for ${YEAR}..."
./scripts/update_all_data.sh -d acidity --acidity-source historical -s "$START_DATE" -e "$END_DATE" --verbose
if [ $? -eq 0 ]; then
    log_info "✅ Acidity historical data download completed"
else
    log_error "❌ Acidity historical data download failed"
fi
echo ""

# 3. Microplastics Data (Available from 1972-04-01, but sparse in early years) ⚠️
log_info "3/3 Downloading microplastics data for ${YEAR}..."
./scripts/update_all_data.sh -d microplastics -s "$START_DATE" -e "$END_DATE" --verbose
if [ $? -eq 0 ]; then
    log_info "✅ Microplastics data download completed"
else
    log_warn "⚠️ Microplastics data download failed (expected - sparse data in ${YEAR})"
fi
echo ""

# Summary of unavailable datasets
echo -e "${CYAN}=============================================${NC}"
log_warn "UNAVAILABLE DATASETS FOR ${YEAR}:"
log_warn "❌ SST Textures (available from 2003-01-01)"
log_warn "❌ Ocean Currents (available from 2003-01-01)"
echo ""

log_info "Historical data download for ${YEAR} completed!"
log_info "Available datasets: SST raw, Acidity (nutrients), Microplastics"
log_info "Data saved to: ../ocean-data/raw/"

echo -e "${CYAN}=============================================${NC}"