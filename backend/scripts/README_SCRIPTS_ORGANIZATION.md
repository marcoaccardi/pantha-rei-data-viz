# Backend Scripts Organization Guide

This document describes the new organization of all backend scripts, implemented to improve maintainability and reduce confusion.

## Folder Structure Overview

### 🟢 `production/` - Critical Production Scripts (7 files)
**Active production scripts that are essential for daily operations.**

- `update_ocean_data.sh` - Main update script and entry point
- `update_ocean_data.py` - Python orchestrator for data updates
- `file_validator.py` - File validation and integrity checking
- `recovery_manager.py` - Error recovery and repair coordination
- `daily_sst_texture_update.py` - Daily SST texture generation
- `validate_cmems_datasets.py` - CMEMS dataset validation
- `comprehensive_corruption_check.py` - Complete file integrity checking

**These scripts are mission-critical and should be modified with extreme care.**

### 🟡 `maintenance/` - System Maintenance Scripts (8 files)
**Important utilities for system health and data validation.**

- `optimize_storage.py` - Storage management and cleanup
- `repair_corrupted_files.py` - Manual file repair utilities
- `monitor_dataset_validity.py` - Health monitoring and alerting
- `quick_corruption_check.py` - Fast integrity checking
- `validate_processed_data.py` - Processing validation
- `validate_texture_alignment.py` - Texture coordinate validation
- `validate_complete_integration.py` - Integration testing
- `deep_dataset_validation.py` - Comprehensive data validation

### 🔵 `analysis/` - Data Analysis & Testing Scripts (12 files)
**Scripts for data analysis, quality checks, and performance testing.**

- `analyze_data_availability.py` - Coverage and availability analysis
- `analyze_netcdf_structure.py` - File structure analysis
- `test_api_data_access.py` - API performance testing (348 lines, comprehensive)
- `simulate_api_extraction.py` - Performance simulation
- `verify_data_realism.py` - Quality validation
- `verify_sst_data.py` - SST-specific validation
- `verify_csv_against_netcdf.py` - Cross-format validation
- `extract_500_locations_real_data.py` - Data sampling
- `extract_sample_reliable_data.py` - Reliable data extraction
- `extract_reliable_ocean_data.py` - Ocean data extraction
- `generate_complete_reliable_dataset.py` - Dataset generation
- `complete_data_audit.py` - Full system audit

### 🟠 `processing/` - Data Processing Utilities (6 files)
**Scripts for transforming and processing raw data.**

- `process_raw_to_unified.py` - Main coordinate harmonization
- `process_historical_data_comprehensive.py` - Historical data processing
- `process_acidity_current.py` - Acidity data processing
- `process_microplastics_data.py` - Microplastics processing
- `fix_ocean_coordinates.py` - Coordinate system repairs
- `generate_all_textures.py` - Batch texture generation

### 🟤 `legacy_individual_updaters/` - Legacy Scripts (5 files)
**Individual dataset updaters kept for backward compatibility.**

- `update_sst_data.py` - Individual SST updater
- `update_currents_data.py` - Individual currents updater
- `update_acidity_data.py` - Individual acidity updater
- `update_microplastics_data.py` - Individual microplastics updater
- `update_all_data.sh` - Legacy comprehensive script (520 lines)

**These are superseded by the production scripts but kept for compatibility.**

### 🔴 `archive/` - Obsolete & Historical Scripts
**Scripts that are no longer in active use, organized by category.**

#### `archive/obsolete_downloads/` (13 files)
- Multiple redundant SST download scripts
- Multiple redundant currents download scripts
- Obsolete OSCAR current organizers

#### `archive/historical_fixes/` (6 files)
- One-time historical data downloads (1993, acidity historical)
- File renaming and repair scripts
- Microplastics dataset generation scripts

#### `archive/backups/` (2 files)
- Backup copies of old daily download scripts

#### `archive/experimental/` (empty)
- Reserved for experimental development scripts

### 📚 `documentation/` - Educational & Demo Scripts (3 files)
- `demonstrate_temporal_logic.py` - Logic demonstration
- `temporal_strategy_explanation.py` - Strategy explanations
- `setup_monitoring_alerts.sh` - Monitoring setup example
- `examples/` - Usage examples (folder)

## Migration Benefits

1. **Clear Purpose**: Each folder has a specific, well-defined role
2. **Easy Maintenance**: Production scripts are isolated and protected
3. **Reduced Clutter**: 25+ obsolete files moved out of the way
4. **Better Discovery**: Users can quickly find relevant scripts
5. **Safe Cleanup**: Nothing deleted, just organized for clarity
6. **Improved Documentation**: Clear guides for each category

## Usage Guidelines

### For Production Operations
- Always use scripts in `production/` for daily operations
- Use `production/update_ocean_data.sh` as the main entry point

### For Maintenance
- Use `maintenance/` scripts for system health checks
- Run `maintenance/monitor_dataset_validity.py` for monitoring

### For Analysis
- Use `analysis/` scripts to investigate data issues
- `analysis/test_api_data_access.py` is comprehensive for API testing

### For Processing
- Use `processing/` scripts to transform raw data
- Start with `processing/process_raw_to_unified.py` for coordinate work

### For Compatibility
- Individual dataset scripts in `legacy_individual_updaters/` still work
- Use only if the main production scripts don't meet specific needs

## Path Updates

All active scripts have been updated with correct import paths. If you encounter path issues:

1. Check if the script has been moved to a new folder
2. Update any external references to use the new folder structure
3. Production scripts now reference `scripts/production/...`
4. Maintenance scripts reference `scripts/maintenance/...`

## Next Steps

This organization provides a solid foundation for:
- Easier onboarding of new developers
- Clearer separation of concerns
- Safer production operations
- Better maintenance workflows
- More focused development efforts

The archive folder preserves all historical work while keeping active directories clean and purposeful.