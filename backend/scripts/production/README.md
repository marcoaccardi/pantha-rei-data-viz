# Production Scripts

**🚨 CRITICAL PRODUCTION SCRIPTS - MODIFY WITH EXTREME CARE 🚨**

This folder contains the core scripts that run the production ocean data system. These scripts handle daily operations, data validation, and system recovery.

## Scripts Overview

### `update_ocean_data.sh` - Main Entry Point
The primary production script that orchestrates all data updates.
- Handles all datasets (SST, currents, acidity, microplastics)
- Includes comprehensive error handling and logging
- Supports dry-run mode for testing
- Provides detailed progress reporting

**Usage:**
```bash
./scripts/production/update_ocean_data.sh
./scripts/production/update_ocean_data.sh --datasets sst,currents
./scripts/production/update_ocean_data.sh --dry-run
```

### `update_ocean_data.py` - Python Orchestrator
Python backend that coordinates data downloads and processing.
- Manages temporal logic and date ranges
- Handles API communications
- Coordinates with file validator and recovery manager
- Provides detailed status reporting

### `file_validator.py` - Data Integrity Guardian
Validates downloaded files for corruption and completeness.
- Checks NetCDF file integrity
- Validates data structure and variables
- Generates validation reports
- Coordinates with recovery manager for repairs

### `recovery_manager.py` - Error Recovery System
Handles automatic recovery from download failures and corruption.
- Detects and repairs corrupted files
- Manages retry logic for failed downloads
- Coordinates with CMEMS and NOAA APIs
- Maintains recovery logs

### `daily_sst_texture_update.py` - SST Texture Pipeline
Specialized script for daily SST texture generation and validation.
- Downloads and processes ERDDAP SST data
- Generates texture files for 3D visualization
- Includes health checking and validation
- Still used in production workflow

### `validate_cmems_datasets.py` - CMEMS Validation
Critical validation script that prevents deployment of incorrect dataset configurations.
- Validates all CMEMS dataset IDs in sources.yaml
- Tests actual data access before deployment
- Prevents the currents P1M→P1D type of configuration errors
- Essential for system reliability

### `comprehensive_corruption_check.py` - Complete File Integrity
Thorough file integrity checking across all datasets.
- Deep validation of NetCDF file structure
- Variable and dimension checking
- Temporal coverage validation
- Generates detailed corruption reports

## Production Workflow

1. **Daily Updates**: Run `update_ocean_data.sh` daily
2. **Validation**: `file_validator.py` checks all downloads
3. **Recovery**: `recovery_manager.py` fixes any issues
4. **Monitoring**: `validate_cmems_datasets.py` ensures API health
5. **Integrity**: `comprehensive_corruption_check.py` validates file health

## Safety Guidelines

- **Test First**: Always use `--dry-run` when testing changes
- **Monitor Logs**: Check logs for any errors or warnings
- **Backup Data**: Ensure backups before major changes
- **Gradual Deployment**: Test individual datasets first
- **Validate Results**: Run integrity checks after changes

## Critical Dependencies

- Backend virtual environment must be active
- CMEMS credentials in `config/.env`
- NOAA API key configured
- Ocean-data directory structure in place
- Network access to data APIs

## Emergency Procedures

If production scripts fail:
1. Check system logs for errors
2. Verify API credentials and network access
3. Run individual components in isolation
4. Use recovery manager to repair corrupted files
5. Contact system administrators if issues persist

**Remember**: These scripts handle terabytes of scientific data. Changes should be thoroughly tested and documented.