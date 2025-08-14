# Processing Scripts

Data transformation and processing utilities that convert raw ocean data into unified, visualization-ready formats.

## Scripts Overview

### Core Processing Pipeline
- **`process_raw_to_unified.py`** - Main coordinate harmonization and data unification
- **`fix_ocean_coordinates.py`** - Coordinate system repairs and standardization
- **`generate_all_textures.py`** - Batch texture generation for 3D visualization

### Dataset-Specific Processing
- **`process_historical_data_comprehensive.py`** - Historical data processing with temporal alignment
- **`process_acidity_current.py`** - Ocean acidity data processing and validation
- **`process_microplastics_data.py`** - Microplastics data processing and standardization

## Processing Workflow

### Standard Processing Pipeline
1. **Raw Data Input** → Various coordinate systems, formats, temporal alignments
2. **Coordinate Unification** → Standardized lat/lon grid system
3. **Temporal Alignment** → Consistent time indexing across datasets
4. **Quality Validation** → Data range and consistency checks
5. **Output Generation** → Unified NetCDF files and visualization textures

### Key Transformations

#### Coordinate Harmonization
- **Input**: Various grid systems (CMEMS, NOAA ERDDAP, OSCAR)
- **Output**: Unified 180×360 global grid (-90° to 90°, -180° to 180°)
- **Process**: Bilinear interpolation, coordinate system translation

#### Temporal Standardization
- **Input**: Different time formats and frequencies
- **Output**: ISO 8601 datetime indexing
- **Process**: Temporal interpolation, gap filling, alignment

## Usage Patterns

### Complete Data Processing
```bash
# Process all raw data to unified format
python scripts/processing/process_raw_to_unified.py

# Generate visualization textures
python scripts/processing/generate_all_textures.py
```

### Dataset-Specific Processing
```bash
# Process historical data
python scripts/processing/process_historical_data_comprehensive.py --start 1993-01-01

# Process acidity data
python scripts/processing/process_acidity_current.py --validate

# Process microplastics
python scripts/processing/process_microplastics_data.py --quality-check
```

### Coordinate Repairs
```bash
# Fix coordinate system issues
python scripts/processing/fix_ocean_coordinates.py --dataset sst --repair-mode
```

## Data Flow

```
Raw Data Sources:
├── CMEMS (Sea Surface Temperature, Currents, Acidity)
├── NOAA ERDDAP (SST, Environmental Data)  
├── OSCAR (Ocean Currents)
└── Research Datasets (Microplastics)

↓ Processing Pipeline ↓

Unified Output:
├── ocean-data/processed/unified_coords/
│   ├── sst/           # Sea Surface Temperature
│   ├── currents/      # Ocean Currents (u,v components)
│   ├── acidity_current/    # Current Ocean Acidity
│   ├── acidity_historical/ # Historical Ocean Acidity  
│   └── microplastics/      # Microplastics Concentration

↓ Visualization Pipeline ↓

Texture Files:
└── Frontend-ready PNG textures for 3D globe visualization
```

## Technical Details

### Coordinate Systems Handled
- **CMEMS**: Various projections, non-uniform grids
- **ERDDAP**: Regular lat/lon grids, different resolutions
- **OSCAR**: 1/3° resolution global grid
- **Research**: Custom coordinate systems

### Output Specifications
- **Grid Resolution**: 180×360 (0.5° resolution)
- **Coordinate Range**: Lat [-90, 90], Lon [-180, 180]  
- **Time Format**: ISO 8601 UTC timestamps
- **File Format**: NetCDF4 with compression
- **Variable Standards**: CF-compliant metadata

### Processing Considerations
- **Memory Management**: Chunked processing for large datasets
- **Quality Control**: Automatic outlier detection and flagging
- **Gap Handling**: Interpolation and extrapolation strategies
- **Performance**: Optimized for multi-core processing

## Best Practices

1. **Sequential Processing**: Run coordinate fixes before main processing
2. **Validation**: Always validate output data quality
3. **Backup**: Preserve raw data during processing
4. **Monitoring**: Track processing performance and errors
5. **Testing**: Verify coordinate alignment after processing

These scripts form the core data transformation pipeline that enables unified ocean data visualization and analysis.