# Ocean Data Management Backend

A Python-based system for downloading, processing, and serving ocean climate data from multiple sources including NOAA, CMEMS, and NCEI.

## Features

- **Automated Downloads**: Manual shell scripts that check latest dates and update to current
- **Multiple Data Sources**: SST, ocean waves, currents, acidity, and microplastics
- **Smart Processing**: Downsampling (SST: 0.25° → 1°) and coordinate harmonization
- **Status Tracking**: JSON-based tracking of download progress and system health
- **Data Validation**: Built-in validation for downloaded NetCDF and CSV files
- **Storage Management**: Organized directory structure with ~40-80 GB for 2024-2025 data

## Quick Start

### 1. Installation

```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Set up credentials (for CMEMS data)
cp config/credentials.env.template config/credentials.env
# Edit credentials.env with your CMEMS username/password
```

### 2. Test Single Download

```bash
# Test SST download for a single date
python scripts/test_single_date.py --dataset sst --date 2024-01-15

# Test all systems
python scripts/test_single_date.py --test-all
```

### 3. Update All Data

```bash
# Update all datasets to current date
./scripts/update_all_data.sh

# Update specific datasets
./scripts/update_all_data.sh -d sst,waves

# Dry run to see what would be downloaded
./scripts/update_all_data.sh -n
```

## Supported Datasets

| Dataset | Source | Resolution | Update Freq | Storage (2024-2025) |
|---------|--------|------------|-------------|-------------------|
| **SST** | NOAA OISST v2.1 | 0.25°→1° | Daily | ~1 GB |
| **Waves** | CMEMS Global | 0.2° | Daily | ~10 GB |
| **Currents** | CMEMS Global | 1/12° | Daily | ~6 GB |
| **Acidity** | CMEMS BGC | 0.25° | Daily | ~8 GB |
| **Microplastics** | NOAA NCEI | Point data | Weekly | <100 MB |

## Architecture

### Directory Structure

```
backend/
├── config/                    # Configuration files
│   ├── sources.yaml          # Data source definitions
│   ├── credentials.env       # API credentials (create from template)
│   └── status.json           # Download status tracking
├── downloaders/              # Dataset-specific downloaders
│   ├── base_downloader.py    # Base class with common functionality
│   ├── sst_downloader.py     # NOAA OISST downloader
│   └── ...                   # Other dataset downloaders
├── processors/               # Data processing utilities
│   ├── coordinate_harmonizer.py  # Longitude conversion (0-360° ↔ -180-180°)
│   └── sst_downsampler.py    # Spatial downsampling (0.25° → 1°)
├── utils/                    # Utility modules
│   └── status_manager.py     # Status tracking and health checks
├── scripts/                  # Shell scripts and utilities
│   ├── update_all_data.sh    # Main update script
│   └── test_single_date.py   # Testing utility
└── api/                      # FastAPI server (planned)
```

### Data Storage

```
ocean-data/
├── raw/                      # Original downloaded files
│   ├── sst/2024/01/         # oisst-avhrr-v02r01.20240115.nc
│   ├── waves/2024/01/       # waves_global_20240115.nc
│   └── ...
├── processed/               # Processed data
│   ├── sst_downsampled/    # 1° resolution SST files
│   └── unified_coords/     # -180-180° longitude files
└── logs/                   # Download logs
```

### Key Components

1. **Base Downloader**: Common functionality for all datasets including:
   - Date gap detection (downloads only missing dates)
   - Error handling and retry logic
   - Status tracking and progress reporting
   - File validation

2. **SST Downloader**: NOAA OISST-specific implementation with:
   - NetCDF file downloading and validation
   - Automatic downsampling from 0.25° to 1° resolution
   - Coordinate conversion from 0-360° to -180-180°
   - Processing pipeline integration

3. **Status Manager**: Centralized tracking system:
   - JSON-based status persistence
   - Health checks and disk usage monitoring
   - Download progress and error reporting
   - System-wide statistics

## Usage Examples

### Manual Download Control

```bash
# Update all datasets
./scripts/update_all_data.sh

# Update specific datasets only
./scripts/update_all_data.sh -d sst,waves

# Update specific date range
./scripts/update_all_data.sh -s 2024-01-01 -e 2024-01-31

# Limit number of files per dataset
./scripts/update_all_data.sh -m 10

# Dry run to preview downloads
./scripts/update_all_data.sh -n -v
```

### Python API Usage

```python
from downloaders.sst_downloader import SSTDownloader
from utils.status_manager import StatusManager

# Download SST data
sst = SSTDownloader()
result = sst.download_date_range('2024-01-01', '2024-01-31')
print(f"Downloaded {result['downloaded']} files")

# Check system status
status = StatusManager()
summary = status.get_download_summary()
print(f"Total storage: {summary['total_storage_gb']} GB")
```

### Status Monitoring

```python
from utils.status_manager import StatusManager

status_manager = StatusManager()

# Get overall summary
summary = status_manager.get_download_summary()
print(f"Active datasets: {summary['active_datasets']}")
print(f"Total files: {summary['total_files']}")
print(f"Storage usage: {summary['total_storage_gb']:.1f} GB")

# Perform health check
health = status_manager.perform_health_check(Path("../ocean-data"))
print(f"System health: {health['overall_status']}")
if health['issues']:
    print("Issues:", health['issues'])
```

## Configuration

### Data Sources (sources.yaml)

Each dataset is configured with:
- Source URLs and access patterns
- Temporal coverage and resolution
- Processing requirements (downsampling, coordinate conversion)
- File naming conventions

### Credentials (credentials.env)

Required for CMEMS datasets:
```bash
CMEMS_USERNAME=your_username
CMEMS_PASSWORD=your_password
NOAA_API_KEY=optional_api_key
```

### Status Tracking (status.json)

Automatically maintained JSON file tracking:
- Last successful download date per dataset
- File counts and storage usage
- Error history and health status
- System-wide statistics

## Data Processing

### SST Downsampling

- **Input**: NOAA OISST v2.1 at 0.25° resolution (~1.6 MB/day)
- **Process**: Spatial averaging using xarray.coarsen()
- **Output**: 1° resolution data (~100 KB/day)
- **Benefit**: 16x reduction in file size while maintaining scientific validity

### Coordinate Harmonization

- **Problem**: Different datasets use different longitude conventions
- **Solution**: Standardize to -180° to +180° longitude
- **Datasets**: NOAA uses 0-360°, CMEMS uses -180-180°
- **Process**: Automatic detection and conversion

## Monitoring and Maintenance

### Health Checks

The system provides comprehensive health monitoring:

```bash
python scripts/test_single_date.py --test-status
```

Monitors:
- Disk space usage and availability
- Dataset download status and freshness
- Error frequency and recent failures
- Storage usage per dataset

### Log Analysis

Download logs are stored in `ocean-data/logs/`:
- Daily download logs with timestamps
- Error details and retry attempts
- Processing statistics and validation results
- System health check reports

### Storage Management

Expected storage usage for 2024-2025 data (~1.5 years):
- **SST (downsampled)**: ~1 GB
- **Waves**: ~10 GB
- **Currents**: ~6 GB
- **Acidity**: ~8 GB
- **Microplastics**: <100 MB
- **Total**: ~25-40 GB

## Development

### Adding New Datasets

1. Create new downloader class inheriting from `BaseDataDownloader`
2. Implement required methods: `_get_filename_for_date()` and `download_date()`
3. Add dataset configuration to `sources.yaml`
4. Update `update_all_data.sh` to include new dataset

### Testing

```bash
# Test specific functionality
python scripts/test_single_date.py --test-config
python scripts/test_single_date.py --test-status
python scripts/test_single_date.py --dataset sst --date 2024-01-15

# Full system test
python scripts/test_single_date.py --test-all
```

### Contributing

1. Follow existing code patterns and error handling
2. Add appropriate logging and status updates
3. Test with single dates before implementing batch downloads
4. Update documentation for new features

## Troubleshooting

### Common Issues

1. **CMEMS Authentication Errors**
   - Verify credentials in `config/credentials.env`
   - Check if CMEMS account is active
   - Try manual login at data.marine.copernicus.eu

2. **Disk Space Issues**
   - Monitor usage with `df -h`
   - Clean up old log files if needed
   - Consider using lower resolution or shorter time ranges

3. **Network Timeout Errors**
   - Check internet connection stability
   - Increase timeout in configuration
   - Try downloading smaller date ranges

4. **Missing Dependencies**
   - Run `pip install -r requirements.txt`
   - Check Python version compatibility (3.8+)
   - Verify NetCDF4 library installation

### Getting Help

- Check logs in `ocean-data/logs/` for detailed error messages
- Run test scripts to isolate issues
- Review configuration files for typos or missing values
- Monitor system health with status manager tools