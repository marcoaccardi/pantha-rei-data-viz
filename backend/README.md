# Ocean Climate Data API Experimentation

Backend API experimentation folder for testing ocean climate data retrieval from multiple sources. This system focuses on **data range discovery** and **access verification** before frontend integration.

## 🎯 Purpose

Test and validate data access capabilities from the top ocean climate APIs:

1. **Copernicus Marine Service** (#1 Recommended) - Global ocean data with subset API access
2. **NOAA CO-OPS API** (#2 Recommended) - US coastal real-time data and trends  
3. **PANGAEA API** (#4 Research Focus) - Peer-reviewed datasets, microplastics specialization

## 🚀 Quick Start

```bash
# Run all experiments
./start-api.sh

# Or run individual tests
python3 discovery/discover_copernicus_coverage.py
python3 experiments/test_temperature.py
python3 experiments/test_microplastics.py
```

## 📁 Project Structure

```
backend-api/
├── discovery/              # API coverage discovery scripts
│   ├── discover_copernicus_coverage.py
│   ├── discover_noaa_coverage.py
│   └── discover_pangaea_coverage.py
├── clients/                # API client implementations
│   ├── base_client.py      # Common client functionality
│   ├── copernicus_client.py
│   ├── noaa_cops_client.py
│   └── pangaea_client.py
├── experiments/            # Data access testing
│   ├── test_temperature.py
│   └── test_microplastics.py
├── utils/                  # Coverage mapping utilities
│   └── coverage_mapper.py
├── config/                 # Configuration and test data
│   ├── api_endpoints.py
│   └── test_coordinates.py
├── output/                 # Results and analysis
│   ├── coverage_maps/      # API coverage analysis
│   ├── sample_data/        # Data access test results
│   └── availability_report/
└── start-api.sh           # Main experimentation script
```

## 🌡️ Climate Data Categories Tested

### Temperature & Heat
- Sea Surface Temperature (SST) anomalies
- Ocean Heat Content (OHC)
- Marine heatwave indicators
- Temperature stratification

### Microplastics & Pollution  
- Microplastics concentration
- Particle size distribution
- Transport pathways
- Pollution hotspot mapping

### Sea Level & Dynamics (Future)
- Sea level rise rates
- Ocean circulation changes
- Atlantic Meridional Overturning Circulation (AMOC)

### Ocean Chemistry (Future)
- pH levels and ocean acidification
- Dissolved CO2 concentrations
- Nutrient distribution changes

## 🔍 Coverage Discovery Process

Each API is analyzed for:

### Spatial Coverage
- Global vs regional availability
- Coordinate bounds and resolution
- Ocean basin coverage

### Temporal Coverage  
- Historical data availability
- Real-time data streams
- Update frequencies and latency

### Parameter Coverage
- Available climate variables
- Data quality indicators
- Resolution and accuracy

## 🧪 Data Access Testing

### Coordinate-Based Testing
Using validated ocean points from the existing coordinate system:
- North Atlantic (Gulf Stream)
- Pacific Gyre regions  
- Coral reef areas
- Polar regions
- Coastal monitoring stations

### API Integration Analysis
- Cross-validation opportunities
- Complementary data coverage
- Integration challenges and solutions

## 📊 Results Format

### Coverage Maps (JSON)
```json
{
  "api_name": "Copernicus Marine Service",
  "spatial_bounds": {"lat_min": -90, "lat_max": 90, ...},
  "temporal_bounds": {"start": "1993-01-01", "end": "2024-12-31"},
  "available_parameters": ["sea_surface_temperature", "sla", ...],
  "datasets": {...},
  "access_methods": [...]
}
```

### Data Access Results (JSON)
```json
{
  "test_timestamp": "2024-01-15T10:30:00Z",
  "apis_tested": ["Copernicus", "NOAA CO-OPS"],
  "results_by_location": {...},
  "api_comparison": {...},
  "recommendations": {...}
}
```

## 🔗 Frontend Integration Ready

### Web-Globe Compatibility
- Results formatted for existing coordinate system
- JSON output compatible with WebSocket servers
- Coordinate validation using ocean validation system

### Data Output Format
- Compatible with texture generation pipeline
- Ready for WebSocket real-time streaming
- Integrated with existing cache system

## 🏆 API Recommendations

### For Global Ocean Analysis
**Primary:** Copernicus Marine Service
- Comprehensive global coverage
- Multiple data products
- Direct API subset access (no downloads)

### For US Coastal Monitoring  
**Primary:** NOAA CO-OPS
- Real-time coastal data
- Long historical records
- Built-in trend analysis

### For Research & Microplastics
**Primary:** PANGAEA
- Peer-reviewed research quality
- Comprehensive microplastics datasets
- DOI-based citations

## 🔧 Technical Implementation Notes

### Authentication Requirements
- **Copernicus:** Registration required for production access
- **NOAA CO-OPS:** No authentication needed
- **PANGAEA:** Open access, citations required

### Rate Limits
- **Copernicus:** No quotas on volume/bandwidth
- **NOAA CO-OPS:** Reasonable limits for typical use
- **PANGAEA:** Academic use encouraged

### Data Formats
- **JSON:** Primary format for API responses
- **NetCDF:** Available for gridded datasets  
- **CSV:** Available for time series data

## 🚀 Next Steps

1. **Review Coverage Results**
   - Analyze spatial/temporal bounds
   - Identify data gaps and overlaps
   - Plan integration strategies

2. **Implement Authentication**
   - Set up Copernicus Marine credentials
   - Configure production API access
   - Implement secure credential management

3. **Frontend Integration**
   - Connect to existing WebSocket servers
   - Integrate with texture generation
   - Add real-time data streaming

4. **Scale Testing**
   - Test with full coordinate datasets
   - Validate performance at scale
   - Optimize caching strategies

## 📚 API Documentation

- **Copernicus Marine:** https://help.marine.copernicus.eu/
- **NOAA CO-OPS:** https://api.tidesandcurrents.noaa.gov/api/prod/
- **PANGAEA:** https://pangaea.de/submit/documentation/api

## 🤝 Contributing

This experimentation framework is designed to be extended:
- Add new API clients in `clients/`
- Create new experiment scripts in `experiments/`
- Extend coverage mapping in `utils/coverage_mapper.py`

Ready for comprehensive ocean climate data integration! 🌊