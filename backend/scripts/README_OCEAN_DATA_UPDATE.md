# Ocean Data Update System

## New Unified Update System

The ocean data update system has been enhanced with a comprehensive, zero-error approach.

### Main Script: `update_ocean_data.sh` (Project Root)

**Location**: `./update_ocean_data.sh` (moved to project root for easier access)

This is the **primary script** you should use for all data updates. It provides:

- **Intelligent Gap Detection**: Scans actual files to find missing dates
- **Handles Any Gap Period**: Days, weeks, or months between updates
- **Comprehensive Validation**: Ensures all files are valid and uncorrupted
- **Automatic Error Recovery**: Fixes corrupted files and processing issues
- **Zero-Error Guarantee**: Never leaves system in broken state

### Usage Examples

```bash
# Update all datasets (recommended for routine use)
./update_ocean_data.sh

# Update specific datasets only
./update_ocean_data.sh --datasets sst_textures,sst

# Preview what would be updated (safe to run anytime)
./update_ocean_data.sh --dry-run

# Repair mode - fix any corrupted files
./update_ocean_data.sh --repair-mode

# Include cleanup of old files
./update_ocean_data.sh --cleanup

# Validation only (no downloads)
./update_ocean_data.sh --validate-only
```

### Dataset Types

1. **sst_textures** - High-quality PNG texture files (5km resolution)
2. **sst** - Raw SST NetCDF data (NOAA OISST v2.1) 
3. **currents** - Ocean currents NetCDF data (CMEMS)
4. **acidity** - Ocean biogeochemistry data (hybrid CMEMS sources)

**Note:** Microplastics data is a static dataset that doesn't require regular updates.

### System Components

The unified system consists of:

```
update_ocean_data.sh              # Main bash wrapper
├── update_ocean_data.py          # Python orchestrator with gap detection
├── file_validator.py             # Comprehensive file validation
├── recovery_manager.py           # Error recovery and repair
└── Uses existing reliable components:
    ├── All downloader classes
    ├── coordinate_harmonizer.py
    ├── status_manager.py
    └── Existing validation scripts
```

### Key Features

#### Gap Detection
- Scans actual files in `ocean-data/` directories
- Finds true latest date vs expected current date
- Handles irregular update schedules (perfect for weekly/monthly runs)

#### File Validation
- NetCDF integrity checking (structure, dimensions, data ranges)
- PNG texture validation (format, size, corruption)
- Coordinate system validation
- Data quality checks

#### Error Recovery
- Automatic redownload of corrupted files
- Reprocessing of failed coordinate harmonization
- Cleanup of partial downloads
- Retry logic with exponential backoff

#### Processing Pipeline
- Raw data → coordinate harmonization → unified coordinates
- SST textures require no processing (direct PNG download)
- Validates all processing steps

### Legacy Scripts

The following scripts are **deprecated** but kept for compatibility:

- `daily_download_all.sh.backup` - Old daily script (replaced by unified system)
- `daily_download_simple.sh.backup` - Old simple script (replaced by unified system)
- `update_sst_data.py` - Individual SST updater (use unified system instead)
- `update_currents_data.py` - Individual currents updater (use unified system instead)
- `update_acidity_data.py` - Individual acidity updater (use unified system instead)
- `update_microplastics_data.py` - Individual microplastics updater (use unified system instead)

### Migration Guide

**Old approach:**
```bash
# Had to run daily or files would be missed
./daily_download_all.sh
```

**New approach:**
```bash
# Can run anytime - automatically finds and fills gaps
./update_ocean_data.sh
```

### Scheduling

Unlike the old system, the new unified system **does not require daily execution**. You can run it:

- **Weekly**: `./update_ocean_data.sh` (handles 7-day gap automatically)
- **After vacation**: `./update_ocean_data.sh` (handles month-long gaps)
- **Irregularly**: No problem - it always detects gaps intelligently

### Monitoring

All operations are logged to `ocean-data/logs/` with timestamped files:

- `update_ocean_data_YYYYMMDD_HHMMSS.log` - Main update logs
- `validation_report_YYYYMMDD_HHMMSS.json` - Validation reports
- `recovery_report_YYYYMMDD_HHMMSS.json` - Recovery operation logs

### Error Handling

The system guarantees zero errors through:

1. **Pre-flight checks**: Disk space, network, permissions
2. **Download validation**: File integrity after download
3. **Processing validation**: Coordinate harmonization success
4. **Recovery loops**: Automatic retry until fixed
5. **Final validation**: Comprehensive health check

If any errors remain after recovery attempts, they are logged for manual review, but the system maintains consistency.

### Best Practices

1. **Use the unified script**: `./update_ocean_data.sh` for all updates
2. **Run dry-run first**: Use `--dry-run` to preview large updates
3. **Monitor logs**: Check log files for any warnings or issues
4. **Repair mode**: Use `--repair-mode` if you suspect corruption
5. **Cleanup regularly**: Use `--cleanup` periodically to maintain disk space

### Troubleshooting

If you encounter issues:

1. Check recent log files in `ocean-data/logs/`
2. Run `./update_ocean_data.sh --validate-only` to check file health
3. Use `./update_ocean_data.sh --repair-mode` to fix corruption
4. Ensure virtual environment is properly set up in `backend/.venv`
5. Check credentials in `backend/config/credentials.env`

### Support

For issues or questions about the ocean data update system, check:

1. This README file
2. Log files in `ocean-data/logs/`
3. The individual script help: `./update_ocean_data.sh --help`