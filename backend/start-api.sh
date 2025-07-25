#!/bin/bash
# Ocean Climate Data API Experimentation Script
# Runs coverage discovery and data access experiments for each category

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}OCEAN CLIMATE DATA API EXPERIMENTATION${NC}"
echo -e "${CYAN}================================================================${NC}"
echo ""
echo -e "${BLUE}Testing data access capabilities across multiple APIs${NC}"
echo -e "${BLUE}Coverage discovery → Data access testing → Integration analysis${NC}"
echo ""

# Create output directories
echo -e "${YELLOW}📁 Setting up output directories...${NC}"
mkdir -p output/coverage_maps
mkdir -p output/sample_data
mkdir -p output/availability_report

# Check Python environment
echo -e "${YELLOW}🐍 Checking Python environment...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found. Please install Python 3.7+${NC}"
    exit 1
fi

python3 --version
echo ""

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    pip3 install -r requirements.txt || {
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    }
    echo ""
fi

# Function to run a script and capture results
run_script() {
    local script_path="$1"
    local script_name="$2"
    local category="$3"
    
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}$category${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ -f "$script_path" ]; then
        echo -e "${BLUE}▶️  Running: $script_name${NC}"
        if python3 "$script_path"; then
            echo -e "${GREEN}✅ $script_name completed successfully${NC}"
        else
            echo -e "${RED}❌ $script_name failed${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Script not found: $script_path${NC}"
        return 1
    fi
    
    echo ""
    echo -e "${CYAN}Press Enter to continue to next test, or Ctrl+C to exit...${NC}"
    read -r
    echo ""
}

# Phase 1: API Coverage Discovery
echo -e "${GREEN}🔍 PHASE 1: API COVERAGE DISCOVERY${NC}"
echo -e "${GREEN}═════════════════════════════════════${NC}"
echo ""
echo "Discovering spatial and temporal coverage for each API..."
echo ""

# Copernicus Marine Service Coverage Discovery
run_script "discovery/discover_copernicus_coverage.py" "Copernicus Marine Service Coverage" "🌊 COPERNICUS MARINE SERVICE ANALYSIS"

# NOAA CO-OPS Coverage Discovery  
run_script "discovery/discover_noaa_coverage.py" "NOAA CO-OPS Coverage" "🇺🇸 NOAA CO-OPS COASTAL DATA ANALYSIS"

# PANGAEA Coverage Discovery
run_script "discovery/discover_pangaea_coverage.py" "PANGAEA Coverage" "🔬 PANGAEA RESEARCH DATA ANALYSIS"

# Phase 2: Data Access Experiments by Category
echo -e "${GREEN}🧪 PHASE 2: DATA ACCESS EXPERIMENTS${NC}"
echo -e "${GREEN}═════════════════════════════════════${NC}"
echo ""
echo "Testing actual data access for different climate data categories..."
echo ""

# Temperature & Heat Data
run_script "experiments/test_temperature.py" "Temperature & Heat Data Test" "🌡️  TEMPERATURE & HEAT DATA ACCESS"

# Microplastics Data (specialized focus)
run_script "experiments/test_microplastics.py" "Microplastics Data Test" "🔬 MICROPLASTICS POLLUTION DATA ACCESS"

# Check if other experiment files exist and run them
for experiment in experiments/test_*.py; do
    if [ -f "$experiment" ] && [ "$experiment" != "experiments/test_temperature.py" ] && [ "$experiment" != "experiments/test_microplastics.py" ]; then
        experiment_name=$(basename "$experiment" .py | sed 's/test_//' | tr '_' ' ' | sed 's/\b\w/\u&/g')
        category_name=$(echo "$experiment_name" | tr '[:lower:]' '[:upper:]')
        run_script "$experiment" "$experiment_name Test" "📊 $category_name DATA ACCESS"
    fi
done

# Phase 3: Results Summary
echo -e "${GREEN}📊 PHASE 3: RESULTS SUMMARY${NC}"
echo -e "${GREEN}═══════════════════════════════${NC}"
echo ""

echo -e "${CYAN}Generating comprehensive results summary...${NC}"

# Count result files
coverage_files=$(find output/coverage_maps -name "*.json" 2>/dev/null | wc -l)
sample_files=$(find output/sample_data -name "*.json" 2>/dev/null | wc -l)

echo ""
echo -e "${BLUE}📁 OUTPUT SUMMARY:${NC}"
echo -e "   Coverage Maps: $coverage_files files"
echo -e "   Sample Data Results: $sample_files files"
echo ""

# List key output files
echo -e "${BLUE}📋 KEY RESULT FILES:${NC}"

if [ -f "output/coverage_maps/copernicus_coverage_detailed.json" ]; then
    echo -e "${GREEN}   ✅ Copernicus coverage analysis${NC}"
else
    echo -e "${RED}   ❌ Copernicus coverage analysis${NC}"
fi

if [ -f "output/coverage_maps/noaa_cops_coverage_detailed.json" ]; then
    echo -e "${GREEN}   ✅ NOAA CO-OPS coverage analysis${NC}"
else
    echo -e "${RED}   ❌ NOAA CO-OPS coverage analysis${NC}"
fi

if [ -f "output/coverage_maps/pangaea_coverage_detailed.json" ]; then
    echo -e "${GREEN}   ✅ PANGAEA coverage analysis${NC}"
else
    echo -e "${RED}   ❌ PANGAEA coverage analysis${NC}"
fi

if [ -f "output/sample_data/temperature_data_test_results.json" ]; then
    echo -e "${GREEN}   ✅ Temperature data access test${NC}"
else
    echo -e "${RED}   ❌ Temperature data access test${NC}"
fi

if [ -f "output/sample_data/microplastics_data_test_results.json" ]; then
    echo -e "${GREEN}   ✅ Microplastics data access test${NC}"
else
    echo -e "${RED}   ❌ Microplastics data access test${NC}"
fi

echo ""

# Generate availability report
echo -e "${CYAN}📝 Generating availability report...${NC}"

report_file="output/availability_report/api_experimentation_summary.txt"
cat > "$report_file" << EOF
OCEAN CLIMATE DATA API EXPERIMENTATION SUMMARY
Generated: $(date)

APIS TESTED:
============
1. Copernicus Marine Service (#1 RECOMMENDED)
   - Global ocean data with subset API access
   - No downloads required
   - Comprehensive climate indicators

2. NOAA CO-OPS API (#2 RECOMMENDED) 
   - US coastal real-time data
   - Long historical records
   - Built-in trend analysis

3. PANGAEA API (#4 FOR RESEARCH DATA)
   - Peer-reviewed research datasets
   - Microplastics specialization
   - DOI-based citations

DATA CATEGORIES TESTED:
======================
• Temperature & Heat Data
  - Sea surface temperature
  - Marine heatwave indicators
  - Temperature anomalies

• Microplastics Pollution Data
  - Concentration measurements
  - Size distribution
  - Transport pathways

RESULTS LOCATION:
================
• Coverage Maps: output/coverage_maps/
• Sample Data Tests: output/sample_data/
• This Report: output/availability_report/

NEXT STEPS:
===========
1. Review individual API coverage reports
2. Analyze data access test results
3. Plan integration with web-globe frontend
4. Implement authentication for production API access

EOF

echo -e "${GREEN}✅ Availability report saved: $report_file${NC}"

# Final summary
echo ""
echo -e "${GREEN}🎉 API EXPERIMENTATION COMPLETED!${NC}"
echo -e "${GREEN}═══════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Summary:${NC}"
echo -e "• Tested $((coverage_files > 0 ? 1 : 0 + sample_files > 0 ? 1 : 0)) different API access approaches"
echo -e "• Generated $coverage_files coverage analysis files"
echo -e "• Created $sample_files data access test results"
echo -e "• Saved comprehensive availability report"
echo ""
echo -e "${CYAN}Check the output/ directory for detailed results and integration guidance.${NC}"
echo -e "${CYAN}Ready for web-globe frontend integration!${NC}"
echo ""

# Quick menu for specific tests
echo -e "${YELLOW}🔄 QUICK ACCESS MENU${NC}"
echo -e "${YELLOW}═══════════════════${NC}"
echo ""
echo "Run individual tests:"
echo "1. Copernicus Coverage: python3 discovery/discover_copernicus_coverage.py"
echo "2. NOAA Coverage: python3 discovery/discover_noaa_coverage.py"  
echo "3. PANGAEA Coverage: python3 discovery/discover_pangaea_coverage.py"
echo "4. Temperature Test: python3 experiments/test_temperature.py"
echo "5. Microplastics Test: python3 experiments/test_microplastics.py"
echo ""
echo -e "${GREEN}All experiments completed successfully! 🚀${NC}"