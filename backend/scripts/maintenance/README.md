# Maintenance Scripts

System maintenance and health monitoring utilities for the ocean data platform.

## Scripts Overview

### Storage Management
- **`optimize_storage.py`** - Manages disk space, removes duplicate files, optimizes data organization
- **`quick_corruption_check.py`** - Fast integrity scan across all datasets

### Data Validation & Repair
- **`repair_corrupted_files.py`** - Manual repair utilities for corrupted NetCDF files
- **`validate_processed_data.py`** - Validates data processing pipeline outputs
- **`validate_texture_alignment.py`** - Ensures texture coordinate consistency
- **`deep_dataset_validation.py`** - Comprehensive data structure and quality validation

### System Monitoring
- **`monitor_dataset_validity.py`** - Continuous health monitoring and alerting
- **`validate_complete_integration.py`** - End-to-end integration testing

## Usage Patterns

### Daily Maintenance
```bash
# Quick health check
python scripts/maintenance/quick_corruption_check.py

# Monitor system health
python scripts/maintenance/monitor_dataset_validity.py
```

### Weekly Maintenance
```bash
# Deep validation
python scripts/maintenance/deep_dataset_validation.py

# Storage optimization
python scripts/maintenance/optimize_storage.py
```

### Problem Resolution
```bash
# Repair corrupted files
python scripts/maintenance/repair_corrupted_files.py --test
python scripts/maintenance/repair_corrupted_files.py --all

# Validate specific dataset
python scripts/maintenance/validate_processed_data.py --dataset sst
```

### Integration Testing
```bash
# Full system integration check
python scripts/maintenance/validate_complete_integration.py

# Texture alignment validation
python scripts/maintenance/validate_texture_alignment.py
```

## Monitoring Setup

The `monitor_dataset_validity.py` script can be configured for continuous monitoring:
- Run via cron for regular health checks
- Integrates with alerting systems
- Provides early warning for data issues
- Tracks system performance metrics

## Best Practices

1. **Regular Checks**: Run quick corruption checks daily
2. **Deep Validation**: Perform comprehensive validation weekly
3. **Storage Management**: Monitor disk usage and optimize monthly
4. **Repair Testing**: Always test repairs before applying to all files
5. **Integration Testing**: Run complete integration tests before major releases

These scripts help maintain system reliability and data quality without interfering with production operations.