#!/bin/bash

# Daily SST Texture Update Script
# Updates SST textures to the latest available date
# Can be run as a daily cron job: 0 6 * * * /path/to/update_sst_textures.sh

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🌊 Daily SST Texture Update${NC}"
echo -e "${CYAN}=========================${NC}"

# Change to backend directory and activate virtual environment
cd "$BACKEND_DIR"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating with uv...${NC}"
    uv venv
fi

echo -e "${GREEN}🐍 Activating virtual environment...${NC}"
source .venv/bin/activate

# Run the daily update script
echo -e "${GREEN}📥 Running daily SST texture update...${NC}"
python scripts/daily_sst_texture_update.py --verbose

# Check if update was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ SST texture update completed successfully!${NC}"
    echo -e "${GREEN}📍 Textures saved to: ocean-data/textures/sst/2025/${NC}"
else
    echo -e "${YELLOW}⚠️  SST texture update completed with some issues${NC}"
    echo -e "${YELLOW}📄 Check logs for details: ocean-data/logs/daily_sst_update.log${NC}"
fi

# Optional: Update frontend default dates automatically
echo -e "${GREEN}🔄 Checking for latest available date...${NC}"

# Find the latest texture file
LATEST_TEXTURE=$(find ../ocean-data/textures/sst/2025 -name "SST_*.png" | sort | tail -1)
if [ -n "$LATEST_TEXTURE" ]; then
    # Extract date from filename (SST_YYYYMMDD.png)
    LATEST_DATE=$(basename "$LATEST_TEXTURE" .png | sed 's/SST_//' | sed 's/\(.\{4\}\)\(.\{2\}\)\(.\{2\}\)/\1-\2-\3/')
    echo -e "${GREEN}📅 Latest available texture date: $LATEST_DATE${NC}"
    
    # Optionally update the frontend default date
    # sed -i "s/selectedDate] = useState<string | undefined>('.*'/selectedDate] = useState<string | undefined>('$LATEST_DATE'/g" ../frontend/src/hooks/useTextureLoader.ts
    echo -e "${YELLOW}💡 To update frontend default date to $LATEST_DATE, edit frontend/src/hooks/useTextureLoader.ts${NC}"
else
    echo -e "${YELLOW}⚠️  No textures found${NC}"
fi

echo -e "${CYAN}=========================${NC}"
echo -e "${GREEN}🎯 Update complete! Your SST textures are now up to date.${NC}"