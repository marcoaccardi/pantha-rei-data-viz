#!/bin/bash

# SST Textures Download Script
# Downloads high-quality SST textures from PacIOOS ERDDAP
# Available from 2003-01-01 to present

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

# Default parameters
START_DATE="2003-01-01"
END_DATE="2024-12-31"
BATCH_SIZE="100"
RECENT_DAYS=""

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Download high-quality SST textures from PacIOOS ERDDAP (5km resolution)

OPTIONS:
    -s, --start-date DATE    Start date (default: 2003-01-01)
    -e, --end-date DATE      End date (default: 2024-12-31)
    -r, --recent DAYS        Download recent N days instead of date range
    -b, --batch-size SIZE    Batch size for downloads (default: 100)
    -h, --help              Show this help

EXAMPLES:
    $0                                    # Download all available textures
    $0 -s 2024-01-01 -e 2024-12-31      # Download 2024 textures
    $0 -r 30                             # Download last 30 days
    $0 -s 2003-01-01 -e 2003-12-31 -b 50 # Download 2003 with smaller batches

NOTE: SST textures are only available from 2003-01-01 onwards
EOF
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--start-date)
            START_DATE="$2"
            shift 2
            ;;
        -e|--end-date)
            END_DATE="$2"
            shift 2
            ;;
        -r|--recent)
            RECENT_DAYS="$2"
            shift 2
            ;;
        -b|--batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

echo -e "${CYAN}SST Textures Download${NC}"
echo -e "${CYAN}====================${NC}"

# Change to backend directory and activate virtual environment
cd "$BACKEND_DIR"
if [ ! -d ".venv" ]; then
    log_error "Virtual environment not found. Run 'uv venv' first."
    exit 1
fi

log_info "Activating virtual environment..."
source .venv/bin/activate

# Build command based on parameters
if [ ! -z "$RECENT_DAYS" ]; then
    log_info "Downloading recent $RECENT_DAYS days of SST textures..."
    python scripts/download_high_quality_sst_textures.py --recent "$RECENT_DAYS" --verbose
else
    log_info "Downloading SST textures from $START_DATE to $END_DATE..."
    python scripts/batch_download_sst_textures.py \
        --start "$START_DATE" \
        --end "$END_DATE" \
        --batch-size "$BATCH_SIZE" \
        --verbose
fi

if [ $? -eq 0 ]; then
    log_info "✅ SST texture download completed successfully!"
    log_info "Textures saved to: frontend/public/textures/sst/"
else
    log_error "❌ SST texture download failed"
    exit 1
fi

echo -e "${CYAN}====================${NC}"