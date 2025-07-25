#!/bin/bash
# Setup monitoring alerts for CMEMS dataset validity
# This script sets up cron jobs to regularly check dataset validity

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_ENV="$BACKEND_DIR/.venv/bin/python"
MONITOR_SCRIPT="$SCRIPT_DIR/monitor_dataset_validity.py"
LOG_DIR="$BACKEND_DIR/../ocean-data/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up CMEMS Dataset Monitoring Alerts${NC}"
echo "=========================================="

# Create log directory
mkdir -p "$LOG_DIR"

# Create monitoring log file
MONITOR_LOG="$LOG_DIR/dataset_monitoring.log"
touch "$MONITOR_LOG"

echo "Backend directory: $BACKEND_DIR"
echo "Monitor script: $MONITOR_SCRIPT"
echo "Log file: $MONITOR_LOG"
echo ""

# Function to add cron job safely
add_cron_job() {
    local schedule="$1"
    local command="$2"
    local description="$3"
    
    # Check if job already exists
    if crontab -l 2>/dev/null | grep -q "$command"; then
        echo -e "${YELLOW}⚠️  Cron job already exists: $description${NC}"
        return 0
    fi
    
    # Add the job
    (crontab -l 2>/dev/null; echo "$schedule $command") | crontab -
    echo -e "${GREEN}✅ Added cron job: $description${NC}"
}

# Daily monitoring check (9 AM)
add_cron_job \
    "0 9 * * *" \
    "cd $BACKEND_DIR && $PYTHON_ENV $MONITOR_SCRIPT >> $MONITOR_LOG 2>&1" \
    "Daily dataset validity check"

# Weekly detailed report (Monday 8 AM)
add_cron_job \
    "0 8 * * 1" \
    "cd $BACKEND_DIR && $PYTHON_ENV $MONITOR_SCRIPT --json >> $MONITOR_LOG 2>&1 && echo '--- Weekly Report $(date) ---' >> $MONITOR_LOG" \
    "Weekly detailed monitoring report"

# Critical alert check (every 6 hours when critical)
add_cron_job \
    "0 */6 * * *" \
    "cd $BACKEND_DIR && if $PYTHON_ENV $MONITOR_SCRIPT --json | grep -q '\"critical\": true'; then echo 'CRITICAL DATASET ALERT: $(date)' >> $MONITOR_LOG; $PYTHON_ENV $MONITOR_SCRIPT >> $MONITOR_LOG 2>&1; fi" \
    "Critical dataset expiry alerts"

echo ""
echo -e "${GREEN}📋 Current cron jobs related to monitoring:${NC}"
crontab -l 2>/dev/null | grep -E "(monitor_dataset_validity|dataset.*validity)" || echo "No existing monitoring jobs found"

echo ""
echo -e "${GREEN}🎯 Monitoring Setup Complete!${NC}"
echo ""
echo "The following alerts are now active:"
echo "• Daily validity checks at 9 AM"
echo "• Weekly reports on Mondays at 8 AM" 
echo "• Critical alerts every 6 hours when datasets are expiring"
echo ""
echo "Logs will be written to: $MONITOR_LOG"
echo ""
echo -e "${YELLOW}Manual Testing:${NC}"
echo "Test the monitoring script manually:"
echo "  cd $BACKEND_DIR && source .venv/bin/activate && python scripts/monitor_dataset_validity.py"
echo ""
echo "View monitoring logs:"
echo "  tail -f $MONITOR_LOG"
echo ""
echo -e "${YELLOW}To remove monitoring alerts:${NC}"
echo "  crontab -e  # Remove lines containing 'monitor_dataset_validity'"