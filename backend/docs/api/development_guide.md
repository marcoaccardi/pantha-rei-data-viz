# Ocean Data API Development Guide

**Last Updated**: 2025-07-25 13:30:00  
**API Version**: v1.0 (Development)  
**Status**: Ready for FastAPI Implementation

---

## 🎯 **API Overview**

### Design Principles
- **Performance First**: Sub-100ms response times
- **Auto-Optimized Data**: Direct access to harmonized files (178KB each)
- **Standardized Format**: Consistent JSON structure across datasets
- **Graceful Degradation**: Handle missing data elegantly
- **Real-time Sampling**: Live performance metrics with each download

### Current Readiness
- ✅ **SST**: Production ready (13-15ms response times)
- ⏳ **Waves**: Awaiting CMEMS implementation
- ⏳ **Currents**: Awaiting CMEMS implementation  
- ⏳ **Acidity**: Awaiting CMEMS implementation
- ⏳ **Microplastics**: Awaiting CSV processing implementation

---

## 📊 **Data Access Patterns**

### File Organization
```
/ocean-data/processed/unified_coords/
├── 2024/07/
│   ├── sst_harmonized_20240723.nc      (178KB, API-ready)
│   ├── sst_harmonized_20240724.nc      (178KB, API-ready)
│   ├── waves_harmonized_20240723.nc    (Future)
│   ├── currents_harmonized_20240723.nc (Future)
│   └── acidity_harmonized_20240723.nc  (Future)
└── microplastics/
    └── observations_20240723.csv       (Future)
```

### Data Characteristics
- **Coordinate System**: All data standardized to -180°/+180° longitude
- **Grid Resolution**: 1° for processed data (optimal for API performance)
- **File Format**: NetCDF4 for gridded data, CSV for point observations
- **Temporal Resolution**: Daily files with YYYYMMDD naming
- **Storage Efficiency**: 90%+ optimization applied

---

## 🚀 **API Response Specifications**

### Point Extraction Response
```json
{
  "coordinates": {
    "requested": {"lat": 25.0, "lon": -40.0},
    "actual": {"lat": 25.5, "lon": -39.5},
    "distance_km": 67.8
  },
  "date": "2024-07-23",
  "datasets": {
    "sst": {
      "value": 28.5,
      "units": "Celsius",
      "quality": "excellent",
      "anomaly": 1.2,
      "error_estimate": 0.12,
      "source": "NOAA_OISST_v2.1"
    },
    "waves": {
      "significant_height": {"value": 1.8, "units": "m"},
      "mean_direction": {"value": 225, "units": "degrees"},
      "peak_period": {"value": 8.2, "units": "s"},
      "source": "CMEMS_WAV_001_027"
    },
    "currents": {
      "u_velocity": {"value": 0.15, "units": "m/s"},
      "v_velocity": {"value": -0.08, "units": "m/s"}, 
      "speed": {"value": 0.17, "units": "m/s"},
      "direction": {"value": 208, "units": "degrees"},
      "source": "CMEMS_PHY_001_024"
    },
    "acidity": {
      "ph": {"value": 8.1, "units": "pH_units"},
      "fco2": {"value": 380, "units": "microatm"},
      "source": "CMEMS_BGC_001_028"
    },
    "microplastics": {
      "nearest_observation": {
        "distance_km": 45.2,
        "concentration": {"value": 0.15, "units": "particles_per_m3"},
        "observation_date": "2024-07-20",
        "confidence": "medium"
      },
      "source": "NOAA_NCEI_Microplastics"
    }
  },
  "metadata": {
    "extraction_time_ms": 24,
    "data_sources": ["NOAA", "CMEMS", "NCEI"],
    "coordinate_system": "WGS84",
    "processing_level": "L3_daily_1degree"
  }
}
```

### Performance Requirements
- **Point Extraction**: <100ms (target: <50ms)
- **Area Extraction**: <500ms for 10°×10° regions
- **Time Series**: <1s for 30-day periods
- **Concurrent Users**: Support 10+ simultaneous requests

---

## 🛠️ **Implementation Framework**

### Recommended FastAPI Structure
```python
# backend/api/main.py
from fastapi import FastAPI, HTTPException
from datetime import date
from .data_reader import OceanDataReader
from .models import PointRequest, PointResponse

app = FastAPI(title="Ocean Data API", version="1.0")
reader = OceanDataReader()

@app.get("/api/v1/point", response_model=PointResponse)
async def get_point_data(lat: float, lon: float, date: date, 
                        datasets: str = "all"):
    """Extract ocean data at specific coordinates and date."""
    return await reader.get_point_data(lat, lon, date, datasets)
```

### Data Reader Implementation
```python
# backend/api/data_reader.py
import xarray as xr
from pathlib import Path
from typing import Dict, List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

class OceanDataReader:
    """High-performance reader for harmonized ocean data."""
    
    def __init__(self, data_root: Path):
        self.data_root = data_root
        self.harmonized_path = data_root / "processed" / "unified_coords"
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def get_point_data(self, lat: float, lon: float, 
                           target_date: date, datasets: str = "all") -> Dict:
        """Extract data at coordinates with async processing."""
        
        # Validate coordinates
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError("Invalid coordinates")
        
        # Find available datasets for date
        available_files = self._find_files_for_date(target_date)
        
        # Parallel extraction from multiple datasets
        tasks = []
        for dataset, file_path in available_files.items():
            if datasets == "all" or dataset in datasets.split(","):
                task = asyncio.create_task(
                    self._extract_from_file(file_path, lat, lon, dataset)
                )
                tasks.append(task)
        
        # Collect results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Format response
        return self._format_response(lat, lon, target_date, results)
```

---

## 📈 **Performance Optimization**

### Current Performance (SST)
- **Average Response**: 13.77ms
- **Performance Grade**: Excellent (<20ms)
- **Success Rate**: 100%
- **Memory Usage**: <10MB per request

### Optimization Strategies

#### 1. File-Level Caching
```python
from functools import lru_cache
import weakref

class FileCache:
    """LRU cache for NetCDF datasets."""
    
    def __init__(self, max_size: int = 50):
        self.cache = {}
        self.max_size = max_size
        
    @lru_cache(maxsize=50)
    def get_dataset(self, file_path: str) -> xr.Dataset:
        """Cache recently accessed datasets."""
        return xr.open_dataset(file_path)
```

#### 2. Coordinate Indexing
```python
class SpatialIndex:
    """Pre-compute nearest grid points for common coordinates."""
    
    def __init__(self, grid_lats: np.ndarray, grid_lons: np.ndarray):
        self.grid_lats = grid_lats
        self.grid_lons = grid_lons
        self._build_kdtree()
    
    def find_nearest(self, lat: float, lon: float) -> tuple:
        """O(log n) coordinate lookup."""
        return self.kdtree.query([lat, lon])
```

#### 3. Response Caching
```python
from redis import Redis
import json

class ResponseCache:
    """Cache API responses for identical requests."""
    
    def __init__(self):
        self.redis = Redis(decode_responses=True)
        self.ttl = 3600  # 1 hour cache
    
    async def get_cached(self, lat: float, lon: float, date: str) -> Optional[Dict]:
        """Check for cached response."""
        key = f"ocean_data:{lat}:{lon}:{date}"
        cached = await self.redis.get(key)
        return json.loads(cached) if cached else None
```

---

## 🔧 **Error Handling**

### Standard Error Responses
```json
{
  "error": {
    "code": "INVALID_COORDINATES",
    "message": "Latitude must be between -90 and 90 degrees",
    "details": {
      "provided_lat": 95.0,
      "valid_range": {"min": -90, "max": 90}
    }
  },
  "request_id": "req_123456789",
  "timestamp": "2025-07-25T13:30:00Z"
}
```

### Error Categories
- **400 Bad Request**: Invalid coordinates, dates, or parameters
- **404 Not Found**: No data available for requested date/location
- **429 Too Many Requests**: Rate limiting exceeded
- **500 Internal Server Error**: Processing failures
- **503 Service Unavailable**: System maintenance

### Graceful Degradation
```python
async def get_point_data_with_fallback(lat: float, lon: float, date: date):
    """Attempt multiple data sources with graceful fallback."""
    
    try:
        # Primary: Harmonized processed data
        return await get_from_harmonized(lat, lon, date)
    except FileNotFoundError:
        try:
            # Fallback: Raw data with on-the-fly processing
            return await get_from_raw(lat, lon, date)
        except Exception:
            # Last resort: Nearest available date
            return await get_nearest_date(lat, lon, date)
```

---

## 📊 **Data Quality Indicators**

### Quality Scoring System
```python
def calculate_data_quality(value: float, dataset: str, metadata: Dict) -> str:
    """Assign quality grades based on data characteristics."""
    
    if dataset == "sst":
        if -5 <= value <= 40:  # Realistic ocean temperature
            return "excellent"
        elif -10 <= value <= 50:  # Extended range
            return "good"
        else:
            return "questionable"
    
    # Add quality logic for other datasets
    return "unknown"
```

### Missing Data Handling
```python
def handle_missing_data(dataset_name: str, coordinates: tuple) -> Dict:
    """Provide meaningful responses for missing data."""
    
    return {
        "value": None,
        "status": "no_data",
        "reason": "land_mask" if is_land(coordinates) else "data_gap",
        "nearest_valid": find_nearest_valid_point(coordinates),
        "alternative_dates": suggest_alternative_dates(coordinates)
    }
```

---

## 🌍 **Coordinate System Support**

### Input Validation
```python
def validate_coordinates(lat: float, lon: float) -> tuple:
    """Normalize and validate input coordinates."""
    
    # Latitude bounds
    if not -90 <= lat <= 90:
        raise ValueError(f"Invalid latitude: {lat}")
    
    # Normalize longitude to -180/+180
    lon = ((lon + 180) % 360) - 180
    
    return lat, lon
```

### Grid Resolution Handling
```python
def find_grid_point(lat: float, lon: float, resolution: float = 1.0) -> tuple:
    """Find nearest grid point for given resolution."""
    
    # Round to nearest grid point
    grid_lat = round(lat / resolution) * resolution
    grid_lon = round(lon / resolution) * resolution
    
    # Calculate distance from requested point
    distance_km = haversine_distance(lat, lon, grid_lat, grid_lon)
    
    return grid_lat, grid_lon, distance_km
```

---

## 🚀 **Deployment Configuration**

### FastAPI Server Setup
```python
# backend/api/main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import ocean_data, system_status

app = FastAPI(
    title="Ocean Data Management API",
    description="High-performance access to global ocean climate data",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"]
)

# Include routers
app.include_router(ocean_data.router, prefix="/api/v1")
app.include_router(system_status.router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=2)
```

### Production Considerations
```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ../ocean-data:/app/ocean-data:ro
    environment:
      - DATA_ROOT=/app/ocean-data
      - LOG_LEVEL=INFO
      - MAX_WORKERS=4
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

---

## 📋 **Testing Strategy**

### API Testing Framework
```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)

def test_point_extraction():
    """Test basic point data extraction."""
    response = client.get("/api/v1/point?lat=0&lon=180&date=2024-07-23")
    assert response.status_code == 200
    
    data = response.json()
    assert "datasets" in data
    assert "sst" in data["datasets"]
    assert data["metadata"]["extraction_time_ms"] < 100

def test_invalid_coordinates():
    """Test error handling for invalid coordinates."""
    response = client.get("/api/v1/point?lat=95&lon=180&date=2024-07-23")
    assert response.status_code == 400
    assert "error" in response.json()

def test_performance_benchmark():
    """Ensure response times meet requirements."""
    start_time = time.time()
    response = client.get("/api/v1/point?lat=25&lon=-40&date=2024-07-23")
    elapsed = (time.time() - start_time) * 1000
    
    assert response.status_code == 200
    assert elapsed < 100  # <100ms requirement
```

### Load Testing
```python
# tests/load_test.py
import asyncio
import aiohttp
import time

async def stress_test_api():
    """Test API under concurrent load."""
    
    async def single_request(session, lat, lon):
        url = f"http://localhost:8000/api/v1/point?lat={lat}&lon={lon}&date=2024-07-23"
        async with session.get(url) as response:
            return await response.json()
    
    async with aiohttp.ClientSession() as session:
        # 50 concurrent requests
        tasks = [
            single_request(session, lat, lon) 
            for lat in range(-50, 51, 10)
            for lon in range(-180, 181, 36)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        print(f"50 requests completed in {elapsed:.2f}s")
        print(f"Average: {(elapsed/50)*1000:.1f}ms per request")
```

---

## 📚 **Development Resources**

### Sample Implementation Files
- **Live API Samples**: `/ocean-data/logs/api_samples/sst_api_sample_*.json`
- **Performance Metrics**: Real extraction times logged with each download
- **Test Data**: Current SST files available for immediate API development

### Code Templates
- **Base Classes**: Auto-optimization and API sampling built into `base_downloader.py`
- **Response Format**: Standardized structure established in SST implementation
- **Error Patterns**: Consistent error handling across processing pipeline

### Monitoring Integration
```python
# backend/api/monitoring.py
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('api_requests_total', 'API requests', ['endpoint', 'status'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'Request duration')

@app.middleware("http")
async def monitor_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(request.url.path, response.status_code).inc()
    REQUEST_DURATION.observe(duration)
    
    return response
```

---

**🎯 Status**: Ready for FastAPI Implementation  
**⚡ Performance**: Sub-20ms proven  
**📊 Data**: Auto-optimized and API-ready  
**🔄 Next**: Implement remaining dataset downloaders