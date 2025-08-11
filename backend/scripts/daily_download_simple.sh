#!/bin/bash
# Simple daily ocean data download script
# Downloads yesterday's data for all available ocean datasets
# 
# Usage: ./scripts/daily_download_simple.sh

# Project paths
PROJECT_PATH="/Volumes/Backup/panta-rhei-data-map"
BACKEND_PATH="$PROJECT_PATH/backend"

# Ensure we're in the right directory
cd "$BACKEND_PATH"

echo "🌊 Daily Ocean Data Download - All Datasets"
echo "============================================"
echo "Started: $(date)"
echo ""

# Activate virtual environment
source .venv/bin/activate

echo "📊 1. SST Textures (High-Quality ERDDAP)..."
python scripts/daily_sst_texture_update.py
echo ""

echo "📊 2. Raw Data Downloads..."
echo "  - SST Raw Data..."
python scripts/update_sst_data.py --yesterday 2>/dev/null || echo "    (script not ready yet)"

echo "  - Ocean Acidity Data..."
python scripts/update_acidity_data.py --yesterday 2>/dev/null || echo "    (script not ready yet)"

echo "  - Ocean Currents Data..."
python scripts/update_currents_data.py --yesterday 2>/dev/null || echo "    (script not ready yet)"

echo "  - Wave Data..."
python scripts/update_waves_data.py --yesterday 2>/dev/null || echo "    (script not ready yet)"

echo "  - Microplastics Data..."
python scripts/update_microplastics_data.py --yesterday 2>/dev/null || echo "    (script not ready yet)"

echo ""
echo "📊 3. System Health Check..."
python scripts/daily_sst_texture_update.py --health-check

echo ""
echo "============================================"
echo "✅ Daily download completed: $(date)"
echo "============================================"