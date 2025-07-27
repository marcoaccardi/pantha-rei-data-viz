# Panta Rhei Data Map Project

## Project Structure
This is an ocean data visualization project with the following structure:

```
panta-rhei-data-map/
├── backend/                    # Python backend (uv environment)
│   ├── api/                   # API layer
│   │   ├── endpoints/         # API endpoint definitions
│   │   ├── middleware/        # Request/response middleware
│   │   └── models/           # Data models
│   ├── config/               # Configuration files
│   ├── docs/                 # Backend documentation
│   │   ├── api/             # API documentation
│   │   ├── datasets/        # Dataset documentation
│   │   └── status/          # Project status docs
│   ├── downloaders/         # Data download modules
│   ├── processors/          # Data processing modules
│   ├── scripts/            # Utility scripts
│   ├── tests/              # Test files
│   └── utils/              # Utility functions
├── frontend/                  # React/TypeScript frontend
│   ├── public/              # Static assets
│   │   └── textures/        # 3D texture assets
│   │       ├── earth/       # Earth texture files
│   │       └── sst/         # Sea surface temperature textures
│   └── src/                 # Source code
│       ├── components/      # React components
│       ├── hooks/          # Custom React hooks
│       ├── tests/          # Frontend tests
│       └── utils/          # Frontend utilities
├── ocean-data/               # Data storage (/Volumes/Backup/panta-rhei-data-map/ocean-data)
│   ├── cache/              # Cached data files
│   ├── logs/               # Processing logs
│   │   ├── api_samples/    # API response samples
│   │   ├── api_simulation/ # API simulation logs
│   │   ├── optimization/   # Performance optimization logs
│   │   └── verification/   # Data verification logs
│   ├── processed/          # Processed data files
│   │   ├── microplastics_filtered/
│   │   ├── sst_downsampled/
│   │   └── unified_coords/ # Unified coordinate system data
│   │       ├── acidity/
│   │       ├── currents/
│   │       ├── microplastics/
│   │       ├── sst/
│   │       └── waves/
│   └── raw/               # Raw downloaded data
│       ├── acidity/
│       ├── currents/
│       ├── microplastics/
│       ├── sst/
│       └── waves/
└── docs/                   # Project-level documentation
```

## Backend Development Rules
- **Always use `uv` for virtual environment management**
- **Always use `uv pip` for package installations** (never use regular pip)
- **Always ensure the virtual environment is active when running Python**
  - Use `uv run` or activate the venv with `source .venv/bin/activate` in `backend/` folder
  - **NEVER use system Python or conda environments** (e.g., /opt/miniconda3)
  - Always check dependencies exist in the backend virtual environment
  - **Before running any Python script or installing libraries, activate environment with `source .venv/bin/activate`**
- **Never use conda** - only use uv for Python environment management
- **All test code must be in `backend/tests/` folder**
- Data downloads should be saved to `/Volumes/Backup/panta-rhei-data-map/ocean-data`
- **Credentials are stored in `backend/config/.env`**
  - Copernicus Marine Service: `CMEMS_USERNAME` and `CMEMS_PASSWORD`
  - NOAA API: `NOAA_API_KEY`


## Key Guidelines
- Follow existing code conventions and patterns
- Use the TodoWrite tool for planning multi-step tasks
- Run lint/typecheck commands after making changes
- Never commit changes unless explicitly requested
- **Always refer to `backend/docs/` for current project state and future tasks**
  - Check PRD file for project requirements and progress
  - Review existing documentation before starting work
- **Systematically test any new feature of the backend and review code for each code request in the `backend/tests/` folder**
- **Always update documentation when implementation differs from docs**
  - If bugs are found or implementation proves incorrect, update docs immediately
  - Keep documentation consistent with actual working code
  - Never leave contradictions between docs and implementation
  - Never try making code with synthetic data when the resource is not available. Ask instead what to do or find an alternative resource.

## Data Processing Workflow
The system now has a complete data processing pipeline:

### Processing Pipeline
1. **Download**: Raw data saved to `/ocean-data/raw/{dataset}/`
2. **Preserve**: Raw files preserved (no longer auto-deleted)
3. **Process**: Dataset-specific processors convert to unified coordinates
4. **Output**: Harmonized data in `/ocean-data/processed/unified_coords/{dataset}/`

### Available Processors
- **SST**: `sst_downsampler.py` - 0.25° → 1° spatial downsampling
- **Acidity**: `acidity_processor.py` - biogeochemistry data processing
- **Currents**: `currents_processor.py` - ocean currents with derived variables
- **Waves**: `coordinate_harmonizer.py` - coordinate system harmonization
- **Coordinate Harmonizer**: Base processor for longitude conversion (0-360° ↔ -180-180°)

### Processing Commands
```bash
# Test processors with synthetic data
python scripts/test_processors.py

# Process existing raw data to unified coordinates
python scripts/process_raw_to_unified.py

# Test raw data preservation
python scripts/test_raw_preservation.py
```

## Validation Tools
- **CMEMS Dataset Validation**: Use `python scripts/validate_cmems_datasets.py` to verify dataset IDs before deployment
  - Validates all CMEMS dataset configurations in sources.yaml
  - Prevents deployment of incorrect dataset IDs (like the currents P1M→P1D fix)
  - Use `--test-download` flag to test actual data access
- **Texture Validation**: Use `python scripts/validate_texture_alignment.py` to verify texture alignment after texture generation

## Code Organization Rules
- **NEVER create test files outside of `backend/tests/` folder**
- **NEVER create ad-hoc Python scripts in the backend root directory**
- **Always use existing bash scripts in `scripts/` for data operations**
  - Use `scripts/update_all_data.sh` for downloading data
  - Create new scripts in `scripts/` folder if needed, not in root
- **Test files must follow naming convention**: `test_<module_name>.py`
- **Keep the backend root directory clean** - only config files and folders belong there
- **Always handle both string and date object inputs in downloaders**
- **Test bash script integration for all new downloaders**
