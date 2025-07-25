# Missing Downloaders Analysis

## Current Implementation Status

### ✅ Implemented Datasets
- **SST (Sea Surface Temperature)**: FULLY IMPLEMENTED
  - Source: NOAA OISST v2.1
  - Status: Complete with downsampling and coordinate harmonization
  - Test Coverage: Comprehensive test suite with 15 tests passing
  - Processing Pipeline: Raw → Downsampled (1°) → Harmonized coordinates

### ❌ Missing Dataset Downloaders

#### 1. Waves Data Downloader
- **Source**: CMEMS Global Waves (GLOBAL_ANALYSISFORECAST_WAV_001_027)
- **Configuration**: Complete in `sources.yaml`
- **Variables**: VHM0 (significant height), MWD (direction), PP1D (period)
- **Authentication**: Requires CMEMS credentials
- **Implementation Needed**: 
  - `backend/downloaders/waves_downloader.py`
  - CMEMS API authentication
  - NetCDF processing for wave parameters
- **Priority**: HIGH (wave data is critical for ocean dynamics)

#### 2. Currents Data Downloader  
- **Source**: CMEMS Global Ocean Currents (GLOBAL_ANALYSISFORECAST_PHY_001_024)
- **Configuration**: Complete in `sources.yaml`
- **Variables**: uo (zonal velocity), vo (meridional velocity)
- **Resolution**: 0.083° (1/12 degree)
- **Authentication**: Requires CMEMS credentials
- **Implementation Needed**:
  - `backend/downloaders/currents_downloader.py`
  - High-resolution processing (finer than SST)
  - Vector field validation
- **Priority**: HIGH (ocean currents fundamental for modeling)

#### 3. Acidity Data Downloader
- **Source**: CMEMS Global Ocean Biogeochemistry (GLOBAL_ANALYSISFORECAST_BGC_001_028)
- **Configuration**: Complete in `sources.yaml`  
- **Variables**: ph, fco2 (fugacity CO2), DIC, TA
- **Authentication**: Requires CMEMS credentials
- **Implementation Needed**:
  - `backend/downloaders/acidity_downloader.py`
  - Biogeochemical data validation
  - pH range validation (typical 7.8-8.2)
- **Priority**: MEDIUM (important for climate studies)

#### 4. Microplastics Data Downloader
- **Source**: NOAA NCEI Marine Microplastics Database
- **Configuration**: Complete in `sources.yaml`
- **Format**: CSV (not NetCDF)
- **Variables**: concentration, particle_count, polymer_type, size_class, depth
- **Authentication**: None required
- **Implementation Needed**:
  - `backend/downloaders/microplastics_downloader.py`
  - CSV processing instead of NetCDF
  - Sparse/irregular data handling
  - Data filtering by date range
- **Priority**: LOW (research interest, not operational)

## Authentication Requirements

### CMEMS (Copernicus Marine Service) Credentials
- **Required for**: Waves, Currents, Acidity datasets
- **Credentials needed**: Username and password
- **Environment variables**: `CMEMS_USERNAME`, `CMEMS_PASSWORD`
- **Status**: Not currently configured

### NOAA API Access
- **Required for**: Microplastics (optional enhancement)
- **Credential needed**: API key
- **Environment variable**: `NOAA_API_KEY`
- **Status**: Not currently needed for basic access

## Implementation Roadmap

### Phase 1: CMEMS Integration (Immediate Priority)
1. **Set up CMEMS authentication**
   - Create credentials management
   - Test CMEMS API access
   - Implement authentication flow

2. **Implement Waves Downloader**
   - Highest priority due to data importance
   - Similar structure to SST but with CMEMS API
   - Wave-specific validation logic

3. **Implement Currents Downloader**
   - High-resolution data handling
   - Vector field processing
   - Performance optimization for large files

### Phase 2: Extended Datasets (Future)
4. **Implement Acidity Downloader**
   - Biogeochemical data processing
   - pH-specific validation
   - Integration with existing pipeline

5. **Implement Microplastics Downloader**  
   - CSV processing pipeline
   - Irregular data handling
   - Research-grade data quality checks

## Technical Considerations

### Base Class Compatibility
- All new downloaders should inherit from `BaseDataDownloader`
- Consistent interface for `download_date()` method
- Standard status tracking and error handling

### Processing Pipeline Integration
- Extend coordinate harmonization for different projections
- Handle varying temporal resolutions (daily, weekly, monthly)
- Implement dataset-specific validation rules

### Storage Requirements
- Waves: ~25 MB per day
- Currents: ~15 MB per day  
- Acidity: ~20 MB per day
- Microplastics: ~50 MB total (historical dataset)

### Testing Strategy
- Follow SST test suite pattern
- Mock CMEMS API for testing
- Validation tests for each data type
- Integration tests with existing pipeline

## Next Steps

1. **Immediate**: Set up CMEMS account and credentials
2. **Week 1**: Implement waves downloader
3. **Week 2**: Implement currents downloader
4. **Week 3**: Implement acidity downloader
5. **Week 4**: Implement microplastics downloader and integration testing

All implementations should follow the established patterns from the SST downloader and maintain compatibility with the existing infrastructure.