# Analysis Scripts

Data analysis, quality assessment, and performance testing tools for ocean data research and system optimization.

## Scripts Overview

### Data Coverage & Availability
- **`analyze_data_availability.py`** - Comprehensive coverage analysis across all datasets
- **`analyze_netcdf_structure.py`** - Detailed NetCDF file structure examination
- **`complete_data_audit.py`** - Full system data audit and reporting

### API Performance & Testing
- **`test_api_data_access.py`** - Comprehensive API performance testing (348+ lines)
- **`simulate_api_extraction.py`** - Performance simulation and benchmarking

### Data Quality Validation
- **`verify_data_realism.py`** - Scientific data quality and realism checks
- **`verify_sst_data.py`** - SST-specific validation and quality assessment
- **`verify_csv_against_netcdf.py`** - Cross-format data consistency validation

### Data Extraction & Sampling
- **`extract_500_locations_real_data.py`** - Statistical sampling for testing
- **`extract_sample_reliable_data.py`** - Reliable data extraction for analysis
- **`extract_reliable_ocean_data.py`** - Ocean-specific data extraction
- **`generate_complete_reliable_dataset.py`** - Comprehensive dataset generation

## Common Usage Patterns

### Data Quality Assessment
```bash
# Check data availability across time ranges
python scripts/analysis/analyze_data_availability.py --start 2020-01-01 --end 2024-01-01

# Validate scientific data quality
python scripts/analysis/verify_data_realism.py --dataset sst

# Cross-format validation
python scripts/analysis/verify_csv_against_netcdf.py
```

### Performance Analysis
```bash
# API performance testing
python scripts/analysis/test_api_data_access.py --comprehensive

# Simulation testing
python scripts/analysis/simulate_api_extraction.py --locations 100
```

### Data Extraction
```bash
# Extract sample data for testing
python scripts/analysis/extract_500_locations_real_data.py

# Generate reliable dataset
python scripts/analysis/generate_complete_reliable_dataset.py
```

### Structure Analysis
```bash
# Analyze NetCDF file structures
python scripts/analysis/analyze_netcdf_structure.py --dataset currents

# Complete system audit
python scripts/analysis/complete_data_audit.py
```

## Key Insights

### `test_api_data_access.py` - Star Script
This 348-line comprehensive testing script provides:
- Detailed API performance metrics
- Error rate analysis
- Response time benchmarking
- Data quality assessment
- Concurrent access testing

### Data Quality Focus
These scripts emphasize scientific data validation:
- Temperature range validation for SST data
- Ocean current velocity bounds checking
- Temporal consistency validation
- Spatial coverage verification

### Research Applications
Analysis scripts support:
- Climate research data validation
- Oceanographic study preparation
- Data pipeline optimization
- System performance monitoring
- Scientific publication data verification

## Best Practices

1. **Regular Analysis**: Run availability analysis monthly
2. **Performance Monitoring**: Use API testing for system health
3. **Quality Assurance**: Validate data realism before research use
4. **Sampling**: Use extraction scripts for statistical analysis
5. **Documentation**: Keep analysis results for trend monitoring

These scripts provide the analytical foundation for maintaining high-quality ocean data and supporting scientific research.