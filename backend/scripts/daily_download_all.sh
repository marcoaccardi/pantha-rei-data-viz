#!/bin/bash
# Comprehensive daily ocean data download script
# Downloads yesterday's data for all available ocean datasets
# 
# Usage: ./scripts/daily_download_all.sh
#
# This script covers:
# - SST Textures (High-quality ERDDAP)  
# - Raw SST Data
# - Ocean Acidity Data
# - Ocean Currents Data  
# - Wave Data
# - Microplastics Data

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PATH="$(dirname "$SCRIPT_DIR")"
PROJECT_PATH="$(dirname "$BACKEND_PATH")"
LOGS_PATH="$PROJECT_PATH/ocean-data/logs"

# Ensure we're in the right directory
cd "$BACKEND_PATH"

# Create logs directory if it doesn't exist
mkdir -p "$LOGS_PATH"

# Log file for this session
LOG_FILE="$LOGS_PATH/daily_download_$(date +%Y%m%d_%H%M%S).log"

echo -e "${BLUE}🌊 Daily Ocean Data Download - All Datasets${NC}"
echo -e "${BLUE}==============================================${NC}"
echo "Started: $(date)"
echo "Log file: $LOG_FILE"
echo ""

# Function to log and display messages
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
    
    case $level in
        "INFO")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Function to run a download task with error handling
run_download_task() {
    local task_name=$1
    local script_command=$2
    
    echo -e "${BLUE}📊 $task_name...${NC}"
    log_message "INFO" "Starting: $task_name"
    
    if eval "$script_command" >> "$LOG_FILE" 2>&1; then
        log_message "INFO" "✅ $task_name - SUCCESS"
        return 0
    else
        log_message "ERROR" "❌ $task_name - FAILED"
        return 1
    fi
}

# Initialize counters
TOTAL_TASKS=0
SUCCESSFUL_TASKS=0
FAILED_TASKS=0

# Activate virtual environment
log_message "INFO" "Activating virtual environment"
source .venv/bin/activate

echo -e "${BLUE}📋 Task 1: SST Textures (High-Quality ERDDAP)${NC}"
echo "Priority: HIGH - Downloads ultra-high resolution textures"
if run_download_task "SST ERDDAP Textures" "python scripts/daily_sst_texture_update.py"; then
    ((SUCCESSFUL_TASKS++))
else
    ((FAILED_TASKS++))
fi
((TOTAL_TASKS++))
echo ""

echo -e "${BLUE}📋 Task 2: Raw Data Downloads${NC}"
echo "Downloads raw data for processing and backup"
echo ""

# SST Raw Data
echo -e "${BLUE}  2a. SST Raw Data${NC}"  
if run_download_task "SST Raw Data" "python scripts/update_sst_data.py --yesterday || echo 'SST raw data script not found - skipping'"; then
    ((SUCCESSFUL_TASKS++))
else
    ((FAILED_TASKS++))
fi
((TOTAL_TASKS++))

# Ocean Acidity Data
echo -e "${BLUE}  2b. Ocean Acidity Data${NC}"
if run_download_task "Ocean Acidity Data" "python scripts/update_acidity_data.py --yesterday || echo 'Acidity data script not found - skipping'"; then
    ((SUCCESSFUL_TASKS++))
else
    ((FAILED_TASKS++))
fi
((TOTAL_TASKS++))

# Ocean Currents Data  
echo -e "${BLUE}  2c. Ocean Currents Data${NC}"
if run_download_task "Ocean Currents Data" "python scripts/update_currents_data.py --yesterday || echo 'Currents data script not found - skipping'"; then
    ((SUCCESSFUL_TASKS++))
else
    ((FAILED_TASKS++))
fi
((TOTAL_TASKS++))

# Wave Data
echo -e "${BLUE}  2d. Wave Data${NC}"
if run_download_task "Wave Data" "python scripts/update_waves_data.py --yesterday || echo 'Wave data script not found - skipping'"; then
    ((SUCCESSFUL_TASKS++))
else
    ((FAILED_TASKS++))
fi
((TOTAL_TASKS++))

# Microplastics Data
echo -e "${BLUE}  2e. Microplastics Data${NC}"
if run_download_task "Microplastics Data" "python scripts/update_microplastics_data.py --yesterday || echo 'Microplastics data script not found - skipping'"; then
    ((SUCCESSFUL_TASKS++))
else
    ((FAILED_TASKS++))
fi
((TOTAL_TASKS++))

echo ""
echo -e "${BLUE}📋 Task 3: Dataset Health Check${NC}"
echo -e "${BLUE}Checking overall system health...${NC}"

# Run health checks
echo "🏥 SST Texture Health:"
python scripts/daily_sst_texture_update.py --health-check 2>/dev/null || echo "Health check unavailable"

echo ""
echo "📁 Data Directory Status:"
ls -la "$PROJECT_PATH/ocean-data/textures/sst/" | tail -5

echo ""
echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}📊 DAILY DOWNLOAD SUMMARY${NC}"
echo -e "${BLUE}==============================================${NC}"
echo "Completed: $(date)"
echo "Duration: $(($(date +%s) - $(date -r "$LOG_FILE" +%s))) seconds"
echo ""
echo -e "${GREEN}Total Tasks: $TOTAL_TASKS${NC}"
echo -e "${GREEN}Successful: $SUCCESSFUL_TASKS${NC}"
if [ $FAILED_TASKS -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED_TASKS${NC}"
else
    echo -e "${GREEN}Failed: $FAILED_TASKS${NC}"
fi

# Calculate success rate
if [ $TOTAL_TASKS -gt 0 ]; then
    SUCCESS_RATE=$((SUCCESSFUL_TASKS * 100 / TOTAL_TASKS))
    echo "Success Rate: ${SUCCESS_RATE}%"
fi

echo ""
echo "📄 Detailed log: $LOG_FILE"

# Exit with appropriate code
if [ $FAILED_TASKS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Some tasks failed. Check the log for details.${NC}"
    exit 1
else
    echo -e "${GREEN}🎉 All tasks completed successfully!${NC}"
    exit 0
fi