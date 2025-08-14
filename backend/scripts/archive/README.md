# Archive - Obsolete & Historical Scripts

This archive contains scripts that are no longer in active use but are preserved for historical reference and potential future needs.

## Organization

### `obsolete_downloads/` - Redundant Download Scripts (13 files)
Scripts that have been superseded by the current production pipeline.

#### SST Download Scripts (5 files)
- `batch_download_sst_textures.py`
- `download_all_missing_sst.py`
- `download_high_quality_sst_textures.py` 
- `download_missing_sst.py`
- `download_sst_textures.sh`

#### Currents Download Scripts (8 files)
- `download_currents_daily_only.py`
- `download_missing_currents_comprehensive.py`
- `download_missing_cmems_currents.py`
- `download_cmems_currents_direct.py`
- `download_cmems_simple.py`
- `organize_oscar_currents.py`
- `organize_oscar_2003_2020.py`  
- `organize_oscar_2021_2023.py`

### `historical_fixes/` - One-Time Repair Scripts (6 files)
Scripts created for specific historical data issues and one-time operations.

- `download_1993_complete.sh` - Complete 1993 historical data download
- `download_acidity_historical_complete.sh` - Acidity historical data (1993-2022)
- `rename_currents_files.py` - File renaming utility
- `repair_known_corrupted_files.py` - Repair for specific corruption issues
- `add_microplastics_simple.py` - Initial microplastics integration
- `generate_microplastics_dataset.py` - Microplastics dataset creation

### `backups/` - Script Backups (2 files)
- `daily_download_all.sh.backup` - Backup of comprehensive daily script
- `daily_download_simple.sh.backup` - Backup of simple daily script

### `experimental/` - Development Experiments (empty)
Reserved for experimental development work that doesn't fit other categories.

## Why These Scripts Are Archived

### Obsolete Downloads
- **Redundancy**: Multiple scripts doing the same job
- **Superseded**: Replaced by unified production pipeline
- **Inconsistency**: Different approaches causing maintenance burden
- **Quality**: Varying levels of error handling and logging

### Historical Fixes
- **One-time Use**: Created for specific historical issues
- **Completed**: Tasks they were designed for are finished
- **Context-specific**: Solutions for problems that no longer exist
- **Maintenance**: Would require updates to work with current system

## Preservation Rationale

These scripts are preserved rather than deleted because they:
- **Document History**: Show evolution of the data pipeline
- **Provide Examples**: Demonstrate various approaches to ocean data handling
- **Enable Recovery**: Could be useful if specific functionality needs to be restored
- **Research Value**: May contain valuable logic for future development

## Usage Policy

### ❌ Not Recommended
- Don't use for new development
- Don't integrate into production workflows  
- Don't rely on for critical operations
- Don't expect maintenance or updates

### ✅ Potential Uses  
- Historical reference and documentation
- Code examples for specific techniques
- Understanding legacy system behavior
- Research into alternative approaches

## Migration Notes

If you were using any of these archived scripts:

1. **SST Downloads**: Use `./update_ocean_data.sh --datasets sst`
2. **Currents Downloads**: Use `./update_ocean_data.sh --datasets currents`  
3. **Historical Data**: Historical downloads are complete; use existing processed data
4. **File Repairs**: Use `scripts/maintenance/repair_corrupted_files.py`
5. **Organization**: Current pipeline handles file organization automatically

## Archive Maintenance

- **Preservation Only**: No active development or bug fixes
- **Documentation**: This README provides context
- **Access**: Files remain readable for reference
- **Cleanup**: May be compressed or further organized over time

These archived scripts represent the development history of the ocean data platform and demonstrate the iterative improvement process that led to the current, more organized and reliable system.