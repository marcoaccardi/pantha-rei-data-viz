# Backend-API Implementation Guide

**Complete integration guide for production deployment and web-globe connectivity**

---

## 🚀 Quick Start Implementation

### Prerequisites Verification ✅
Your system already has:
- ✅ Working backend-api codebase with verified functionality
- ✅ Existing web-globe visualization infrastructure  
- ✅ WebSocket server architecture in place
- ✅ Ocean coordinate validation system
- ✅ Texture generation and caching pipeline

### Immediate Implementation Steps

#### 1. **Production API Authentication Setup** (Priority 1)

**Copernicus Marine Service** (Essential for global data):
```bash
# Register for Copernicus Marine Service
# 1. Visit: https://data.marine.copernicus.eu
# 2. Create account and request access
# 3. Install production toolbox
pip install copernicusmarine

# 4. Configure authentication
export COPERNICUS_MARINE_USERNAME="your_username"
export COPERNICUS_MARINE_PASSWORD="your_password"

# 5. Test authentication
copernicusmarine login
```

**Update client for production:**
```python
# backend-api/clients/copernicus_client.py
import copernicusmarine

# Replace simulated queries with real API calls:
def query_data(self, lat, lon, start_date, end_date, parameters=None):
    # Real implementation using copernicusmarine.subset()
    return copernicusmarine.subset(
        dataset_id=self.dataset_id,
        variables=parameters,
        minimum_longitude=lon-0.1, maximum_longitude=lon+0.1,
        minimum_latitude=lat-0.1, maximum_latitude=lat+0.1,
        start_datetime=start_date, end_datetime=end_date
    )
```

#### 2. **WebSocket Integration Layer** (Priority 1)

**Create new WebSocket handler:**
```python
# backend/servers/climate_data_websocket_server.py
import asyncio
import websockets
import json
import sys
sys.path.append('../backend-api/clients')

from copernicus_client import CopernicusMarineClient
from pangaea_client import PANGAEAClient

class ClimateDataWebSocketServer:
    def __init__(self):
        self.copernicus_client = CopernicusMarineClient()
        self.pangaea_client = PANGAEAClient()
    
    async def handle_temperature_request(self, websocket, message):
        """Handle real-time temperature data requests"""
        try:
            lat = message['coordinates']['lat']
            lon = message['coordinates']['lon']
            date_range = message.get('dateRange', {})
            
            # Query Copernicus for temperature data
            result = self.copernicus_client.query_data(
                lat=lat, lon=lon,
                start_date=date_range.get('start', '2024-01-01'),
                end_date=date_range.get('end', '2024-01-31'),
                dataset_key='sst_global_l4'
            )
            
            # Format for web-globe
            response = {
                'type': 'temperature_data',
                'coordinates': {'lat': lat, 'lon': lon},
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(response, default=str))
            
        except Exception as e:
            error_response = {
                'type': 'error',
                'message': f'Temperature data query failed: {str(e)}'
            }
            await websocket.send(json.dumps(error_response))
    
    async def handle_microplastics_request(self, websocket, message):
        """Handle microplastics research data requests"""
        try:
            coordinates = message['coordinates']
            research_area = message.get('researchArea', 'microplastics')
            
            # Query PANGAEA for research data
            result = self.pangaea_client.query_data(
                lat=coordinates['lat'], 
                lon=coordinates['lon'],
                research_area=research_area,
                start_date='2010-01-01',
                end_date='2024-12-31'
            )
            
            response = {
                'type': 'microplastics_data',
                'coordinates': coordinates,
                'data': result,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(response, default=str))
            
        except Exception as e:
            error_response = {
                'type': 'error', 
                'message': f'Microplastics query failed: {str(e)}'
            }
            await websocket.send(json.dumps(error_response))

# Integration with existing WebSocket server
async def enhanced_websocket_handler(websocket, path):
    """Enhanced handler with climate data capabilities"""
    server = ClimateDataWebSocketServer()
    
    async for message in websocket:
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'temperature_request':
                await server.handle_temperature_request(websocket, data)
            elif message_type == 'microplastics_request':
                await server.handle_microplastics_request(websocket, data)
            # ... existing message handlers
            
        except Exception as e:
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Message processing failed: {str(e)}'
            }))
```

#### 3. **Web-Globe Frontend Integration** (Priority 1)

**Add climate data controls to web-globe:**
```typescript
// web-globe/src/components/ClimateDataControls.tsx
import React, { useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

interface ClimateDataControlsProps {
  onDataReceived: (data: any) => void;
}

export const ClimateDataControls: React.FC<ClimateDataControlsProps> = ({ onDataReceived }) => {
  const { sendMessage } = useWebSocket();
  const [selectedCoordinates, setSelectedCoordinates] = useState<{lat: number, lon: number} | null>(null);
  
  const requestTemperatureData = () => {
    if (!selectedCoordinates) return;
    
    sendMessage({
      type: 'temperature_request',
      coordinates: selectedCoordinates,
      dateRange: {
        start: '2024-01-01',
        end: '2024-01-31'
      }
    });
  };
  
  const requestMicroplasticsData = () => {
    if (!selectedCoordinates) return;
    
    sendMessage({
      type: 'microplastics_request',
      coordinates: selectedCoordinates,
      researchArea: 'microplastics'
    });
  };
  
  return (
    <div className="climate-data-controls">
      <h3>Ocean Climate Data</h3>
      
      <div className="coordinate-display">
        {selectedCoordinates ? (
          <p>Selected: {selectedCoordinates.lat.toFixed(4)}°, {selectedCoordinates.lon.toFixed(4)}°</p>
        ) : (
          <p>Click on globe to select coordinates</p>
        )}
      </div>
      
      <div className="data-request-buttons">
        <button onClick={requestTemperatureData} disabled={!selectedCoordinates}>
          Get Temperature Data
        </button>
        <button onClick={requestMicroplasticsData} disabled={!selectedCoordinates}>
          Get Microplastics Data
        </button>
      </div>
    </div>
  );
};
```

**Update Globe component for coordinate selection:**
```typescript
// web-globe/src/components/Globe.tsx
const handleGlobeClick = (event: any) => {
  const coords = convertScreenToLatLon(event.point);
  
  // Validate coordinates using backend-api
  if (validateOceanCoordinates(coords)) {
    setSelectedCoordinates(coords);
    onCoordinateSelected(coords);
  }
};
```

#### 4. **Cache System Configuration** (Priority 2)

**Extend existing cache for API data:**
```python
# backend-api/utils/enhanced_cache_manager.py
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

class APIResponseCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_db = cache_dir / 'api_response_cache.sqlite'
        self._init_database()
    
    def _init_database(self):
        """Initialize cache database tables"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name TEXT NOT NULL,
                query_hash TEXT NOT NULL,
                response_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                UNIQUE(api_name, query_hash)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_cached_response(self, api_name: str, query_hash: str):
        """Retrieve cached API response if valid"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT response_data FROM api_responses 
            WHERE api_name = ? AND query_hash = ? AND expires_at > ?
        ''', (api_name, query_hash, datetime.now()))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def cache_response(self, api_name: str, query_hash: str, response_data: any, ttl_hours: int = 24):
        """Cache API response with TTL"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        
        cursor.execute('''
            INSERT OR REPLACE INTO api_responses 
            (api_name, query_hash, response_data, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (api_name, query_hash, json.dumps(response_data, default=str), expires_at))
        
        conn.commit()
        conn.close()
```

---

## 📊 Production Configuration

### Environment Configuration
```bash
# production.env
COPERNICUS_MARINE_USERNAME=your_username
COPERNICUS_MARINE_PASSWORD=your_password
NOAA_API_KEY=your_key_if_needed
CACHE_TTL_HOURS=24
WEBSOCKET_PORT=8765
API_REQUEST_TIMEOUT=30
MAX_CONCURRENT_REQUESTS=10
```

### Logging Configuration  
```python
# backend-api/config/logging_config.py
import logging
import sys
from pathlib import Path

def setup_production_logging():
    """Configure logging for production deployment"""
    
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Configure formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler for API requests
    api_handler = logging.FileHandler(log_dir / 'api_requests.log')
    api_handler.setFormatter(formatter)
    api_handler.setLevel(logging.INFO)
    
    # File handler for errors
    error_handler = logging.FileHandler(log_dir / 'errors.log')
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Console handler for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure loggers
    api_logger = logging.getLogger('backend_api')
    api_logger.addHandler(api_handler)
    api_logger.addHandler(error_handler)
    api_logger.addHandler(console_handler)
    api_logger.setLevel(logging.INFO)
    
    return api_logger
```

### Performance Monitoring
```python
# backend-api/utils/performance_monitor.py
import time
import psutil
from typing import Dict, Any

class PerformanceMonitor:
    def __init__(self):
        self.request_times = []
        self.api_response_times = {}
        self.error_counts = {}
    
    def track_request(self, api_name: str, start_time: float, end_time: float, success: bool):
        """Track API request performance"""
        response_time = end_time - start_time
        
        if api_name not in self.api_response_times:
            self.api_response_times[api_name] = []
        
        self.api_response_times[api_name].append(response_time)
        
        if not success:
            self.error_counts[api_name] = self.error_counts.get(api_name, 0) + 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        stats = {
            'system_memory_usage': psutil.virtual_memory().percent,
            'system_cpu_usage': psutil.cpu_percent(),
            'api_performance': {}
        }
        
        for api_name, response_times in self.api_response_times.items():
            if response_times:
                stats['api_performance'][api_name] = {
                    'avg_response_time': sum(response_times) / len(response_times),
                    'max_response_time': max(response_times),
                    'min_response_time': min(response_times),
                    'total_requests': len(response_times),
                    'error_count': self.error_counts.get(api_name, 0),
                    'success_rate': ((len(response_times) - self.error_counts.get(api_name, 0)) / len(response_times)) * 100
                }
        
        return stats
```

---

## 🎯 Feature Implementation Priorities

### Phase 1: Core Functionality (Week 1-2)
1. **Global Temperature Monitoring Dashboard**
   ```python
   # Implement real-time SST data display
   # Add temperature anomaly detection
   # Create marine heatwave alerting
   ```

2. **WebSocket Real-time Data Streaming**
   ```python
   # Connect backend-api to existing WebSocket infrastructure
   # Implement coordinate-based data queries
   # Add real-time data update capabilities
   ```

### Phase 2: Enhanced Analytics (Week 3-4)
1. **Multi-API Data Fusion**
   ```python
   # Combine Copernicus + NOAA data for validation
   # Implement data quality scoring
   # Add cross-API comparison capabilities
   ```

2. **Advanced Visualization Features**
   ```python
   # SST texture generation from API data
   # Interactive data exploration tools
   # Historical trend analysis displays
   ```

### Phase 3: Research Integration (Month 2)
1. **Microplastics Research Portal**
   ```python
   # PANGAEA dataset browser interface
   # DOI-based citation management
   # Research data download capabilities
   ```

2. **Climate Analytics Platform**
   ```python
   # Multi-parameter correlation analysis
   # Trend detection and forecasting
   # Custom report generation
   ```

---

## 📋 Testing & Validation

### Pre-Production Testing Checklist
- [ ] **API Authentication** - Verify production credentials work
- [ ] **WebSocket Integration** - Test real-time data streaming
- [ ] **Coordinate Validation** - Verify ocean point accuracy
- [ ] **Cache Performance** - Test response caching effectiveness
- [ ] **Error Handling** - Verify graceful failure scenarios
- [ ] **Load Testing** - Test concurrent request handling
- [ ] **Data Quality** - Validate API response accuracy

### Production Monitoring Checklist
- [ ] **API Response Times** - Monitor < 2 second response times
- [ ] **Error Rates** - Keep < 5% error rate
- [ ] **Cache Hit Rates** - Target > 70% cache effectiveness
- [ ] **Memory Usage** - Monitor server resource consumption
- [ ] **WebSocket Connections** - Track concurrent user capacity

---

## 🚨 Troubleshooting Guide

### Common Issues & Solutions

**1. Copernicus Authentication Failures**
```bash
# Check credentials
copernicusmarine login --check

# Refresh authentication token
copernicusmarine login --force-refresh

# Verify API access permissions
copernicusmarine describe --dataset-id cmems_obs-sst_glo_phy_nrt_l4_0.083deg_P1D
```

**2. WebSocket Connection Issues**
```python
# Check WebSocket server status
netstat -an | grep :8765

# Test WebSocket connectivity
import websockets
async def test_connection():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        await websocket.send('{"type": "test"}')
        response = await websocket.recv()
        print(response)
```

**3. Cache Performance Issues**
```sql
-- Check cache database size
SELECT COUNT(*) FROM api_responses;

-- Clean expired cache entries
DELETE FROM api_responses WHERE expires_at < datetime('now');

-- Monitor cache hit rates
SELECT api_name, COUNT(*) as cached_requests 
FROM api_responses 
WHERE created_at > datetime('now', '-1 day')
GROUP BY api_name;
```

---

## 🎉 Deployment Success Verification

### Post-Deployment Tests
1. **Access Global Temperature Data**
   - Select coordinates on web-globe
   - Request temperature data via WebSocket
   - Verify real-time data display

2. **Microplastics Research Query** 
   - Search for microplastics datasets
   - Verify DOI resolution and citation display
   - Test research data access workflow

3. **Performance Validation**
   - Monitor API response times < 2 seconds
   - Verify cache effectiveness > 70%
   - Confirm WebSocket real-time updates

### Success Metrics
- ✅ **Global ocean temperature data accessible**
- ✅ **Real-time data streaming functional**
- ✅ **Microplastics research data discoverable**
- ✅ **Web-globe integration operational**
- ✅ **System performance within targets**

---

**🚀 Ready for Production Deployment!**

This implementation guide provides the complete pathway from current experimental system to full production deployment with web-globe integration. Follow the priority order for fastest time-to-value with global ocean climate monitoring capabilities.

*For technical support during implementation, refer to the comprehensive test reports and API documentation in the accompanying files.*