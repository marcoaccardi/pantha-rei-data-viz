#!/bin/bash
# 
# Comprehensive On-Demand Ocean Data Update Script
# 
# This script intelligently detects gaps in ocean data and downloads missing files
# from the last available date to the current date. It includes comprehensive
# file validation, error recovery, and data processing to ensure zero errors.
#
# Features:
# - Intelligent gap detection based on actual files
# - Downloads from last file date to current date (handles days to months of gaps)
# - Comprehensive file validation and corruption detection
# - Automatic error recovery with retry logic
# - Coordinate harmonization for raw data
# - Health checks and cleanup operations
# 
# Usage:
#   ./update_ocean_data.sh                                    # Update all datasets
#   ./update_ocean_data.sh --datasets sst,currents           # Update specific datasets
#   ./update_ocean_data.sh --dry-run                         # Preview what would be updated
#   ./update_ocean_data.sh --repair-mode                     # Aggressive repair mode
#   ./update_ocean_data.sh --cleanup                         # Include cleanup operations
#   ./update_ocean_data.sh --validate-only                   # Only run validation
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration (now at project root level)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_DIR/backend"
OCEAN_DATA_DIR="$PROJECT_DIR/ocean-data"
LOGS_DIR="$OCEAN_DATA_DIR/logs"

# Default options
DATASETS=""
DRY_RUN=false
REPAIR_MODE=false
CLEANUP=false
VALIDATE_ONLY=false
VERBOSE=false
FORCE=false

# Function definitions
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Comprehensive On-Demand Ocean Data Update Script

OPTIONS:
    -d, --datasets DATASETS     Comma-separated list of datasets to update
                                (sst_textures,sst,currents,acidity)
    -n, --dry-run              Show what would be updated without downloading
    -r, --repair-mode          Run aggressive repair mode (revalidate all files)
    -c, --cleanup              Include cleanup of obsolete/partial files
    -v, --validate-only        Only run validation checks, no updates
    --verbose                  Verbose output and logging
    --force                    Force update even if pre-flight checks fail
    -h, --help                 Show this help message

EXAMPLES:
    $0                                      # Update all datasets to current date
    $0 -d sst_textures,sst                 # Update only SST data and textures
    $0 -n                                  # Dry run to see what would be updated
    $0 -r                                  # Repair mode - fix any corrupted files
    $0 -c                                  # Include cleanup operations
    $0 -v                                  # Only validate existing files
    $0 -d currents --verbose              # Update currents with verbose logging

DATASETS:
    sst_textures    High-quality SST texture PNG files (5km resolution)
    sst             Raw SST NetCDF data (NOAA OISST v2.1)
    currents        Ocean currents NetCDF data (CMEMS)
    acidity         Ocean biogeochemistry data (hybrid CMEMS sources)

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
    
    # Check if we're in the right directory
    if [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
        log_error "Cannot find backend directory with requirements.txt"
        log_error "Please run this script from the backend/scripts directory"
        exit 1
    fi
    
    # Check for virtual environment
    if [ ! -d "$BACKEND_DIR/.venv" ]; then
        log_error "Virtual environment not found at $BACKEND_DIR/.venv"
        log_error "Please run: cd $BACKEND_DIR && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
    
    log_info "Dependencies check passed"
}

check_disk_space() {
    log_info "Checking available disk space..."
    
    # Create ocean-data directory if it doesn't exist
    mkdir -p "$OCEAN_DATA_DIR"
    
    # Get available space in GB
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        AVAILABLE_GB=$(df -g "$OCEAN_DATA_DIR" | tail -1 | awk '{print $4}')
    else
        # Linux
        AVAILABLE_GB=$(df -BG "$OCEAN_DATA_DIR" | tail -1 | awk '{print $4}' | sed 's/G//')
    fi
    
    log_info "Available disk space: ${AVAILABLE_GB} GB"
    
    if [ "$AVAILABLE_GB" -lt 5 ]; then
        log_error "Less than 5 GB available. Please free up disk space."
        if [ "$FORCE" != true ]; then
            exit 1
        else
            log_warn "Continuing due to --force flag"
        fi
    elif [ "$AVAILABLE_GB" -lt 20 ]; then
        log_warn "Less than 20 GB available. Monitor disk usage during update."
    fi
}

check_network_connectivity() {
    log_info "Checking network connectivity..."
    
    # Test connectivity to key data sources
    local test_urls=(
        "https://www.ncei.noaa.gov"
        "https://pae-paha.pacioos.hawaii.edu"
    )
    
    for url in "${test_urls[@]}"; do
        if curl --connect-timeout 10 --max-time 30 -s "$url" > /dev/null; then
            log_debug "Connectivity to $url: OK"
        else
            log_warn "Cannot reach $url - some downloads may fail"
        fi
    done
}

activate_virtual_environment() {
    log_info "Activating virtual environment..."
    
    # Change to backend directory
    cd "$BACKEND_DIR"
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Verify activation
    if [ "$VIRTUAL_ENV" != "$BACKEND_DIR/.venv" ]; then
        log_error "Failed to activate virtual environment"
        exit 1
    fi
    
    log_info "Virtual environment activated: $VIRTUAL_ENV"
}

run_pre_flight_checks() {
    log_info "Running pre-flight checks..."
    
    check_dependencies
    check_disk_space
    check_network_connectivity
    activate_virtual_environment
    
    # Create necessary directories
    mkdir -p "$LOGS_DIR"
    mkdir -p "$OCEAN_DATA_DIR/raw"
    mkdir -p "$OCEAN_DATA_DIR/processed/unified_coords"
    mkdir -p "$OCEAN_DATA_DIR/textures"
    
    log_info "Pre-flight checks completed successfully"
}

run_update() {
    log_info "Starting ocean data update..."
    
    # Build Python command
    local python_cmd="python backend/scripts/production/update_ocean_data.py"
    
    if [ ! -z "$DATASETS" ]; then
        python_cmd="$python_cmd --datasets $DATASETS"
    fi
    
    if [ "$DRY_RUN" = true ]; then
        python_cmd="$python_cmd --dry-run"
    fi
    
    if [ "$REPAIR_MODE" = true ]; then
        python_cmd="$python_cmd --repair-mode"
    fi
    
    if [ "$VERBOSE" = true ]; then
        python_cmd="$python_cmd --verbose"
    fi
    
    # Run the update
    log_info "Executing: $python_cmd"
    
    if $python_cmd; then
        log_info "Update completed successfully"
        return 0
    else
        local exit_code=$?
        log_error "Update failed with exit code: $exit_code"
        return $exit_code
    fi
}

run_validation() {
    log_info "Running file validation..."
    
    local python_cmd="python backend/scripts/production/file_validator.py --generate-report"
    
    if [ ! -z "$DATASETS" ]; then
        # Run validation for each dataset separately
        IFS=',' read -ra DATASET_ARRAY <<< "$DATASETS"
        for dataset in "${DATASET_ARRAY[@]}"; do
            log_info "Validating dataset: $dataset"
            python backend/scripts/production/file_validator.py --dataset "$dataset"
        done
    else
        # Generate comprehensive report
        log_info "Generating comprehensive validation report..."
        $python_cmd
    fi
}

run_recovery() {
    log_info "Running error recovery..."
    
    local python_cmd="python backend/scripts/production/recovery_manager.py"
    
    if [ ! -z "$DATASETS" ]; then
        python_cmd="$python_cmd --datasets $DATASETS"
    fi
    
    if [ "$REPAIR_MODE" = true ]; then
        python_cmd="$python_cmd --repair-mode"
    fi
    
    if [ "$VERBOSE" = true ]; then
        python_cmd="$python_cmd --verbose"
    fi
    
    log_info "Executing: $python_cmd"
    
    if $python_cmd; then
        log_info "Recovery completed successfully"
        return 0
    else
        local exit_code=$?
        log_error "Recovery failed with exit code: $exit_code"
        return $exit_code
    fi
}

cleanup_operations() {
    if [ "$CLEANUP" != true ]; then
        return 0
    fi
    
    log_info "Running cleanup operations..."
    
    # Clean up old log files (keep last 30 days)
    log_info "Cleaning up old log files..."
    find "$LOGS_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true
    find "$LOGS_DIR" -name "*.json" -mtime +30 -delete 2>/dev/null || true
    
    # Clean up temporary files
    log_info "Cleaning up temporary files..."
    find "$OCEAN_DATA_DIR" -name "*.tmp" -delete 2>/dev/null || true
    find "$OCEAN_DATA_DIR" -name "*.temp" -delete 2>/dev/null || true
    find "$OCEAN_DATA_DIR" -name "*~" -delete 2>/dev/null || true
    
    log_info "Cleanup operations completed"
}

generate_summary_report() {
    log_info "Generating summary report..."
    
    # Get basic statistics
    local total_files=$(find "$OCEAN_DATA_DIR" -name "*.nc" -o -name "*.png" | wc -l)
    local total_size=$(du -sh "$OCEAN_DATA_DIR" 2>/dev/null | cut -f1 || echo "Unknown")
    
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    OCEAN DATA UPDATE SUMMARY                    ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Update completed: $(date)"
    echo "Total files: $total_files"
    echo "Total storage: $total_size"
    echo ""
    
    # Show recent log files
    echo "Recent log files:"
    ls -lt "$LOGS_DIR"/*.log 2>/dev/null | head -5 | while read -r line; do
        echo "  $line"
    done || echo "  No log files found"
    
    echo ""
    echo "Data directory structure:"
    ls -la "$OCEAN_DATA_DIR" 2>/dev/null | head -10
    
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--datasets)
                DATASETS="$2"
                shift 2
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -r|--repair-mode)
                REPAIR_MODE=true
                shift
                ;;
            -c|--cleanup)
                CLEANUP=true
                shift
                ;;
            -v|--validate-only)
                VALIDATE_ONLY=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --force)
                FORCE=true
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
    
    # Display header
    echo -e "${CYAN}Ocean Data Management System - Comprehensive Update${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ ! -z "$DATASETS" ]; then
        log_info "Datasets to process: $DATASETS"
    else
        log_info "Processing all datasets: sst_textures,sst,currents,acidity"
    fi
    
    if [ "$DRY_RUN" = true ]; then
        log_warn "DRY RUN MODE - No data will be downloaded"
    fi
    
    if [ "$REPAIR_MODE" = true ]; then
        log_warn "REPAIR MODE - Will revalidate and fix all files"
    fi
    
    if [ "$VALIDATE_ONLY" = true ]; then
        log_info "VALIDATION ONLY - No updates will be performed"
    fi
    
    echo ""
    
    # Track execution time
    local start_time=$(date +%s)
    
    # Execute operations
    local exit_code=0
    
    # Pre-flight checks
    if ! run_pre_flight_checks; then
        log_error "Pre-flight checks failed"
        exit 1
    fi
    
    if [ "$VALIDATE_ONLY" = true ]; then
        # Only run validation
        if ! run_validation; then
            exit_code=1
        fi
    else
        # Full update process
        
        # 1. Run initial validation and recovery
        log_info "Phase 1: Initial validation and recovery"
        if ! run_recovery; then
            log_warn "Recovery phase had issues, but continuing..."
        fi
        
        # 2. Run main update
        log_info "Phase 2: Data update"
        if ! run_update; then
            exit_code=1
        fi
        
        # 3. Run post-update recovery (fix any issues from new downloads)
        log_info "Phase 3: Post-update validation and recovery"
        if ! run_recovery; then
            log_warn "Post-update recovery had issues"
            exit_code=1
        fi
        
        # 4. Final validation
        log_info "Phase 4: Final validation"
        if ! run_validation; then
            log_warn "Final validation found issues"
        fi
        
        # 5. Cleanup
        cleanup_operations
    fi
    
    # Calculate execution time
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local duration_formatted=$(printf "%02d:%02d:%02d" $((duration/3600)) $((duration%3600/60)) $((duration%60)))
    
    # Generate summary
    generate_summary_report
    
    echo ""
    echo "Execution time: $duration_formatted"
    echo ""
    
    if [ $exit_code -eq 0 ]; then
        log_info "Ocean data update completed successfully!"
    else
        log_error "Ocean data update completed with errors (exit code: $exit_code)"
        log_error "Check the logs in $LOGS_DIR for details"
    fi
    
    exit $exit_code
}

# Handle interrupts gracefully
trap 'echo -e "\n${YELLOW}Update interrupted by user${NC}"; exit 130' INT TERM

# Run main function
main "$@"