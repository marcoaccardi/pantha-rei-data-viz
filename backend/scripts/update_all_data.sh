#!/bin/bash

# Ocean Data Management System - Main Update Script
# Downloads and processes data for all ocean datasets to current date
# Usage: ./update_all_data.sh [options]

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$BACKEND_DIR/config"
OCEAN_DATA_DIR="$(dirname "$BACKEND_DIR")/ocean-data"
LOG_DIR="$OCEAN_DATA_DIR/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default options
DATASETS="sst,waves,currents,acidity,microplastics"
MAX_FILES=""
START_DATE=""
END_DATE=""
FORCE_UPDATE=false
DRY_RUN=false
VERBOSE=false

# Functions
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Ocean Data Management System - Update all datasets to current date

OPTIONS:
    -d, --datasets DATASETS     Comma-separated list of datasets to update
                               (default: sst,waves,currents,acidity,microplastics)
    -s, --start-date DATE      Start date in YYYY-MM-DD format (overrides status.json)
    -e, --end-date DATE        End date in YYYY-MM-DD format (default: yesterday)
    -m, --max-files NUM        Maximum number of files to download per dataset
    -f, --force                Force update even if data seems current
    -n, --dry-run              Show what would be downloaded without downloading
    -v, --verbose              Verbose output
    -h, --help                 Show this help message

EXAMPLES:
    $0                                      # Update all datasets to current date
    $0 -d sst                              # Update only SST data
    $0 -d sst,waves -m 10                  # Update SST and waves, max 10 files each
    $0 -s 2024-01-01 -e 2024-01-31        # Update specific date range
    $0 -n                                  # Dry run to see what would be downloaded

DATASETS:
    sst          Sea Surface Temperature (NOAA OISST v2.1)
    waves        Ocean Waves (CMEMS)
    currents     Ocean Currents (CMEMS)
    acidity      Ocean Acidity/pH (CMEMS BGC)
    microplastics Marine Microplastics (NOAA NCEI)

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

log_debug() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check required Python packages
    python3 -c "import yaml, requests, xarray, pandas, numpy" 2>/dev/null || {
        log_error "Required Python packages missing. Run: pip install -r $BACKEND_DIR/requirements.txt"
        exit 1
    }
    
    # Check for CMEMS credentials if needed
    if [[ "$DATASETS" =~ (waves|currents|acidity) ]]; then
        if [ ! -f "$CONFIG_DIR/credentials.env" ]; then
            log_warn "credentials.env not found. CMEMS datasets may fail without credentials."
            log_warn "Copy credentials.env.template and fill in your credentials."
        fi
    fi
    
    log_info "Dependencies check passed"
}

check_disk_space() {
    log_info "Checking available disk space..."
    
    # Get available space in GB
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        AVAILABLE_GB=$(df -g "$OCEAN_DATA_DIR" | tail -1 | awk '{print $4}')
    else
        # Linux
        AVAILABLE_GB=$(df -BG "$OCEAN_DATA_DIR" | tail -1 | awk '{print $4}' | sed 's/G//')
    fi
    
    log_info "Available disk space: ${AVAILABLE_GB} GB"
    
    if [ "$AVAILABLE_GB" -lt 10 ]; then
        log_error "Less than 10 GB available. Please free up disk space."
        exit 1
    elif [ "$AVAILABLE_GB" -lt 50 ]; then
        log_warn "Less than 50 GB available. Monitor disk usage during download."
    fi
}

load_status() {
    local dataset="$1"
    local status_file="$CONFIG_DIR/status.json"
    
    if [ ! -f "$status_file" ]; then
        echo "null"
        return
    fi
    
    python3 -c "
import json
try:
    with open('$status_file', 'r') as f:
        status = json.load(f)
    last_date = status.get('datasets', {}).get('$dataset', {}).get('last_date')
    print(last_date if last_date else 'null')
except:
    print('null')
"
}

get_date_range_info() {
    local dataset="$1"
    local last_date=$(load_status "$dataset")
    
    # Determine start date
    local start_date="$START_DATE"
    if [ -z "$start_date" ]; then
        if [ "$last_date" != "null" ] && [ ! -z "$last_date" ]; then
            # Continue from day after last download
            if [[ "$OSTYPE" == "darwin"* ]]; then
                start_date=$(date -j -v+1d -f "%Y-%m-%d" "$last_date" "+%Y-%m-%d")
            else
                start_date=$(date -d "$last_date + 1 day" "+%Y-%m-%d")
            fi
        else
            # First time - use test start date from config
            start_date="2024-01-01"  # Default test start
        fi
    fi
    
    # Determine end date
    local end_date="$END_DATE"
    if [ -z "$end_date" ]; then
        # Default to yesterday
        if [[ "$OSTYPE" == "darwin"* ]]; then
            end_date=$(date -j -v-1d "+%Y-%m-%d")
        else
            end_date=$(date -d "yesterday" "+%Y-%m-%d")
        fi
    fi
    
    echo "$start_date,$end_date,$last_date"
}

calculate_days_to_download() {
    local start_date="$1"
    local end_date="$2"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        local start_ts=$(date -j -f "%Y-%m-%d" "$start_date" "+%s")
        local end_ts=$(date -j -f "%Y-%m-%d" "$end_date" "+%s")
    else
        local start_ts=$(date -d "$start_date" "+%s")
        local end_ts=$(date -d "$end_date" "+%s")
    fi
    
    local days=$(( (end_ts - start_ts) / 86400 + 1 ))
    echo $days
}

download_dataset() {
    local dataset="$1"
    
    log_info "Processing dataset: $dataset"
    
    # Get date range information
    local date_info=$(get_date_range_info "$dataset")
    local start_date=$(echo "$date_info" | cut -d',' -f1)
    local end_date=$(echo "$date_info" | cut -d',' -f2)
    local last_date=$(echo "$date_info" | cut -d',' -f3)
    
    # Calculate days to download
    local days_to_download=$(calculate_days_to_download "$start_date" "$end_date")
    
    if [ $days_to_download -le 0 ]; then
        log_info "$dataset: No new data to download (last_date: $last_date)"
        return 0
    fi
    
    log_info "$dataset: Need to download $days_to_download days ($start_date to $end_date)"
    
    if [ "$last_date" != "null" ] && [ ! -z "$last_date" ]; then
        log_info "$dataset: Last successful download: $last_date"
    else
        log_info "$dataset: First time download"
    fi
    
    # Check if dry run
    if [ "$DRY_RUN" = true ]; then
        log_info "$dataset: [DRY RUN] Would download $days_to_download files"
        return 0
    fi
    
    # Prepare download command
    local cmd="python3 -c \"
import sys
sys.path.append('$BACKEND_DIR')
from downloaders.${dataset}_downloader import ${dataset^}Downloader

downloader = ${dataset^}Downloader()
result = downloader.download_date_range('$start_date', '$end_date'"
    
    if [ ! -z "$MAX_FILES" ]; then
        cmd="$cmd, max_files=$MAX_FILES"
    fi
    
    cmd="$cmd)
print(f'Downloaded: {result[\"downloaded\"]}')
print(f'Failed: {result[\"failed\"]}')
if result['errors']:
    print('Errors:')
    for error in result['errors']:
        print(f'  {error}')
\""
    
    # Create log file for this download
    local log_file="$LOG_DIR/$(date +%Y%m%d_%H%M%S)_${dataset}_download.log"
    mkdir -p "$LOG_DIR"
    
    log_info "$dataset: Starting download (logging to: $log_file)"
    
    # Execute download with logging
    if [ "$VERBOSE" = true ]; then
        eval "$cmd" 2>&1 | tee "$log_file"
        local exit_code=${PIPESTATUS[0]}
    else
        eval "$cmd" > "$log_file" 2>&1
        local exit_code=$?
    fi
    
    # Check result
    if [ $exit_code -eq 0 ]; then
        log_info "$dataset: Download completed successfully"
        
        # Show summary from log
        local downloaded=$(grep "Downloaded:" "$log_file" | cut -d' ' -f2 || echo "0")
        local failed=$(grep "Failed:" "$log_file" | cut -d' ' -f2 || echo "0")
        
        if [ "$downloaded" -gt 0 ]; then
            log_info "$dataset: Successfully downloaded $downloaded files"
        fi
        
        if [ "$failed" -gt 0 ]; then
            log_warn "$dataset: $failed files failed to download"
        fi
        
        return 0
    else
        log_error "$dataset: Download failed (see log: $log_file)"
        return 1
    fi
}

generate_summary_report() {
    log_info "Generating summary report..."
    
    python3 -c "
import sys
sys.path.append('$BACKEND_DIR')
from utils.status_manager import StatusManager
import json

status_manager = StatusManager()
summary = status_manager.get_download_summary()

print('\\n' + '='*60)
print('OCEAN DATA DOWNLOAD SUMMARY')
print('='*60)
print(f'Total datasets: {summary[\"total_datasets\"]}')
print(f'Active datasets: {summary[\"active_datasets\"]}')
print(f'Total files: {summary[\"total_files\"]}')
print(f'Total storage: {summary[\"total_storage_gb\"]:.2f} GB')

if summary.get('last_activity'):
    print(f'Last activity: {summary[\"last_activity\"]}')

print('\\nDataset Details:')
print('-' * 60)
for dataset, info in summary['datasets'].items():
    status = info['status']
    files = info['total_files']
    storage = info['storage_gb']
    last_date = info.get('last_date', 'None')
    
    print(f'{dataset:12s} | {status:12s} | {files:6d} files | {storage:8.2f} GB | {last_date}')

print('\\n' + '='*60)
"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--datasets)
            DATASETS="$2"
            shift 2
            ;;
        -s|--start-date)
            START_DATE="$2"
            shift 2
            ;;
        -e|--end-date)
            END_DATE="$2"
            shift 2
            ;;
        -m|--max-files)
            MAX_FILES="$2"
            shift 2
            ;;
        -f|--force)
            FORCE_UPDATE=true
            shift
            ;;
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
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

# Main execution
main() {
    echo -e "${CYAN}Ocean Data Management System - Update All Data${NC}"
    echo -e "${CYAN}=================================================${NC}"
    
    # Convert datasets string to array
    IFS=',' read -ra DATASET_ARRAY <<< "$DATASETS"
    
    log_info "Datasets to update: ${DATASETS}"
    
    if [ "$DRY_RUN" = true ]; then
        log_warn "DRY RUN MODE - No data will be downloaded"
    fi
    
    if [ ! -z "$MAX_FILES" ]; then
        log_info "Maximum files per dataset: $MAX_FILES"
    fi
    
    # Pre-flight checks
    check_dependencies
    check_disk_space
    
    # Create necessary directories
    mkdir -p "$LOG_DIR"
    
    # Track overall results
    local total_datasets=${#DATASET_ARRAY[@]}
    local successful_datasets=0
    local failed_datasets=0
    
    # Process each dataset
    for dataset in "${DATASET_ARRAY[@]}"; do
        echo ""  # Add spacing between datasets
        
        if download_dataset "$dataset"; then
            ((successful_datasets++))
        else
            ((failed_datasets++))
        fi
    done
    
    # Final summary
    echo ""
    echo -e "${CYAN}=================================================${NC}"
    log_info "Update completed!"
    log_info "Successful datasets: $successful_datasets/$total_datasets"
    
    if [ $failed_datasets -gt 0 ]; then
        log_warn "Failed datasets: $failed_datasets/$total_datasets"
        log_warn "Check logs in $LOG_DIR for details"
    fi
    
    # Generate detailed summary report
    if [ "$DRY_RUN" = false ]; then
        generate_summary_report
    fi
    
    # Exit with error code if any datasets failed
    if [ $failed_datasets -gt 0 ]; then
        exit 1
    fi
}

# Run main function
main "$@"