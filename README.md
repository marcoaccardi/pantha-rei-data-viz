# NOAA Climate Data Globe Texture System

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://python.org)
[![React Three Fiber](https://img.shields.io/badge/React%20Three%20Fiber-Compatible-brightgreen.svg)](https://github.com/pmndrs/react-three-fiber)

A comprehensive, production-ready system for generating scientifically accurate Earth textures with real-time marine and climate data for 3D globe visualization.

## 🎯 Overview

This system generates high-quality Earth textures with comprehensive climate and marine data:

- **🌍 NASA Earth Base Textures**: High-resolution NASA Blue Marble imagery (7200x3600, 2:1 aspect ratio)
- **🌡️ ERDDAP SST Textures**: Pre-rendered sea surface temperature from NOAA Coral Reef Watch via PacIOOS ERDDAP
- **📊 Enhanced Climate Data**: Multi-API climate data collection with guaranteed availability
- **🪸 Marine Data Integration**: Coral bleaching, waves, currents, and biogeochemistry
- **🌊 Live API Queries**: Always requires date + coordinates for fresh data

## 🏗️ Architecture

```
noaa/
├── README.md                    # Documentation
├── requirements.txt             # Dependencies
├── config.py                    # Configuration
├── main.py                      # Main entry point
├── src/                         # Source code
│   ├── processors/              # Data processors
│   │   ├── earth_textures.py              # NASA Earth textures
│   │   ├── erddap_sst_processor.py        # ERDDAP SST textures
│   │   ├── enhanced_climate_data.py       # Climate data + marine integration
│   │   ├── coral_bleaching_processor.py   # NOAA Coral Reef Watch data
│   │   ├── wave_data_processor.py         # NOAA WaveWatch III data
│   │   ├── ocean_currents_processor.py    # OSCAR ocean currents
│   │   └── marine_bio_processor.py        # Marine biogeochemistry
│   └── utils/                   # Utilities
├── textures/                    # Output textures
│   ├── earth/                   # NASA Earth textures
│   └── sst/                     # SST textures
└── data/cache/                  # Cache and CSV exports
```

## 🚀 Quick Start

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd noaa
pip install -r requirements.txt
```

## 📊 Complete Usage Guide

### 🌍 Basic Climate Data Collection

```bash
# Default: Enhanced climate data for NYC coordinates
python main.py

# Specific coordinates (requires lat,lon format)
python main.py --coordinates="25.7617,-80.1918"  # Florida Keys
python main.py --coordinates="21.3,-157.8"       # Hawaii
python main.py --coordinates="-16.3,145.8"       # Great Barrier Reef

# Specific date (YYYY-MM-DD format)
python main.py --coordinates="34.0522,-118.2437" --date="2024-12-01"
```

### 🎲 Random Data Generation

```bash
# Generate random coordinates and date with detailed report
python main.py --generate

# Generate random coordinates + get marine data
python main.py --generate
```

### ⚡ Performance Options

```bash
# Quick mode: Skip climate data, only textures (2-3 seconds)
python main.py --quick

# Fast download with low resolution textures
python main.py --quick --resolution=low

# Ultra-fast with preview resolution (~329KB vs ~11MB)
python main.py --quick --resolution=preview

# Force re-download existing files
python main.py --force

# Quick mode with forced texture updates
python main.py --quick --force
```

### 🎯 Texture-Only Operations

```bash
# Generate only SST texture (medium resolution by default)
python main.py --sst-only

# Generate only Earth texture  
python main.py --earth-only

# Force re-download both textures
python main.py --sst-only --force
python main.py --earth-only --force
```

### 📐 SST Texture Resolution Options

```bash
# High resolution (7200x3600, ~11MB) - maximum quality
python main.py --sst-only --resolution=high

# Medium resolution (3600x1800, ~3.7MB) - DEFAULT, good balance
python main.py --sst-only --resolution=medium

# Low resolution (1800x900, ~1.1MB) - smaller file, still good quality
python main.py --sst-only --resolution=low

# Preview resolution (900x450, ~329KB) - tiny file for testing
python main.py --sst-only --resolution=preview
```

### 🔍 Validation and Diagnostics

```bash
# Validate existing output files
python main.py --validate

# Get help with all options
python main.py --help
```

## 🌊 Marine Data Integration

The system now includes comprehensive marine data from your coral reef monitoring system:

### Data Sources
- **🪸 Coral Bleaching**: NOAA Coral Reef Watch (DHW, BAA, SST Hotspot, Anomaly)
- **🌊 Wave Data**: NOAA WaveWatch III (9 wave parameters: height, period, direction)
- **🌊 Ocean Currents**: OSCAR currents (U/V components, speed, direction)
- **🧪 Marine Biogeochemistry**: Copernicus Marine Service (chlorophyll, pH, oxygen, nutrients)
- **🪸 Reef Proximity**: Distance to nearest major coral reef (from 217-reef database)

### Marine Data Examples

```bash
# Marine data for coral reef locations
python main.py --coordinates="25.7617,-80.1918"   # Florida Keys - coral reef zone
python main.py --coordinates="21.3,-157.8"        # Hawaii - major reef system
python main.py --coordinates="18.2,-67.1"         # Caribbean - reef ecosystem

# Marine data for open ocean
python main.py --coordinates="30.0,-60.0"         # Sargasso Sea
python main.py --coordinates="0.0,0.0"            # Equatorial Pacific

# Random marine data generation
python main.py --generate  # Includes marine data in detailed report
```

## 🚀 Performance & File Size Comparison

### SST Texture Download Performance

| Resolution | Dimensions | File Size | Download Time* | Use Case |
|------------|------------|-----------|----------------|----------|
| **High** | 7200x3600 | ~11MB | ~30-60s | Maximum quality, production |
| **Medium** | 3600x1800 | ~3.7MB | ~10-20s | **DEFAULT** - Best balance |
| **Low** | 1800x900 | ~1.1MB | ~3-8s | Fast development, mobile |
| **Preview** | 900x450 | ~329KB | ~1-3s | Testing, ultra-fast |

*Download times depend on internet connection and ERDDAP server load.

**Recommendation**: Use `medium` for most applications, `low` for development, `preview` for testing.

## 📈 Data Output Formats

### 🌊 Enhanced Climate Data CSV
**Location**: `data/cache/enhanced_climate_data_[lat]_[lon]_[date].csv`

**Columns**:
- `latitude`, `longitude`, `date` - Location and time
- `data_source` - Source API (NWS_Current, Gridded_Analysis, Historical_Estimate, etc.)
- `parameter` - Climate/marine parameter name
- `value` - Measured/estimated value
- `units` - Parameter units
- `description` - Human-readable parameter explanation
- `quality` - Data quality flag (V=Valid, Z=Missing, Fallback_Estimate, etc.)
- `confidence` - Confidence score (0.0-1.0)
- `climate_zone` - Köppen climate classification
- `weather_labels` - Descriptive condition labels
- `timestamp` - Data collection timestamp

**Sample Data Types**:
- **Atmospheric**: Temperature, pressure, wind, humidity (18 parameters)
- **Marine**: Coral bleaching stress, wave conditions, ocean currents (30+ parameters)
- **Biogeochemical**: Ocean pH, chlorophyll, nutrients, dissolved gases (12+ parameters)

### 🖼️ Textures

#### SST Textures
- **Format**: PNG with transparency
- **Resolution Options**: 
  - High: 7200x3600 (~11MB)
  - Medium: 3600x1800 (~3.7MB) - **DEFAULT**
  - Low: 1800x900 (~1.1MB)
  - Preview: 900x450 (~329KB)
- **Aspect Ratio**: 2:1 (perfect for sphere mapping)
- **Source**: NOAA Coral Reef Watch via PacIOOS ERDDAP
- **Location**: `textures/sst/erddap_sst_texture_[date]_[resolution].png`

#### Earth Textures  
- **Format**: JPEG
- **Dimensions**: 7200x3600 (2:1 aspect ratio)
- **Source**: NASA Blue Marble
- **Location**: `textures/earth/nasa_world_topo_bathy.jpg`

## 🔬 Data Quality & Reliability

### Confidence Scoring System
- **0.9**: Real-time observations from calibrated instruments (NWS stations)
- **0.8**: Historical data from validated climate datasets
- **0.7**: Gridded analysis with spatial interpolation
- **0.6**: Marine model analysis data
- **0.5**: Model-based fallback estimates
- **0.3-0.4**: Physics-based emergency fallbacks

### Quality Control Flags
- **V**: Verified/Valid data from instruments
- **C**: Calculated/Corrected data
- **Z**: Missing/Zero value  
- **Fallback_Estimate**: Generated from climate/marine models
- **Interpolated**: Spatially interpolated values

### Guaranteed Data Availability
The system **never returns empty datasets**. When live APIs fail:
- **Climate data**: Physics-based estimates using latitude, season, and climate zones
- **Marine data**: Oceanographic patterns based on geographic location
- **Quality transparency**: All fallback data clearly marked with confidence scores

## 🌐 Global Coverage Examples

### Coral Reef Ecosystems
```bash
python main.py --coordinates="25.7617,-80.1918"   # Florida Keys
python main.py --coordinates="-16.3,145.8"        # Great Barrier Reef  
python main.py --coordinates="3.2,73.2"           # Maldives
python main.py --coordinates="27.3,33.6"          # Red Sea
```

### Major Ocean Basins
```bash
python main.py --coordinates="30.0,-40.0"         # North Atlantic
python main.py --coordinates="-30.0,0.0"          # South Atlantic
python main.py --coordinates="0.0,-140.0"         # Equatorial Pacific
python main.py --coordinates="45.0,180.0"         # North Pacific
```

### Polar Regions
```bash
python main.py --coordinates="70.0,-150.0"        # Arctic Ocean
python main.py --coordinates="-65.0,0.0"          # Southern Ocean
```

## 🔧 System Components

### Core Climate Processors
- **EnhancedClimateDataProcessor**: Main coordinator with marine integration
- **EarthTextureProcessor**: NASA Earth imagery processing
- **ERDDAPSSTProcessor**: ERDDAP SST texture generation

### Marine Data Processors  
- **CoralBleachingProcessor**: NOAA Coral Reef Watch thermal stress data
- **WaveDataProcessor**: NOAA WaveWatch III wave conditions
- **OceanCurrentsProcessor**: OSCAR ocean surface currents
- **MarineBiogeochemistryProcessor**: Copernicus marine biogeochemistry

### Utilities
- **TextureValidator**: Validates texture quality and React Three Fiber compatibility
- **APIClient**: Handles API requests with retry logic and rate limiting
- **FileOperations**: Manages file operations and directory structure

## 🌐 React Three Fiber Integration

All textures are optimized for React Three Fiber:

```javascript
import { useLoader } from '@react-three/fiber'
import { TextureLoader } from 'three'

function Globe() {
  const earthTexture = useLoader(TextureLoader, '/textures/earth/nasa_world_topo_bathy.jpg')
  const sstTexture = useLoader(TextureLoader, '/textures/sst/erddap_sst_texture_20250618.png')
  
  return (
    <mesh>
      <sphereGeometry args={[1, 64, 64]} />
      <meshStandardMaterial map={earthTexture} />
      {/* Overlay SST texture with transparency */}
      <meshStandardMaterial map={sstTexture} transparent opacity={0.7} />
    </mesh>
  )
}
```

## ⚙️ Configuration

Key settings in `config.py`:

```python
# Texture specifications
TEXTURE_SPECS = {
    'target_width': 7200,
    'target_height': 3600,
    'aspect_ratio': 2.0
}

# Data sources
DATA_SOURCES = {
    'erddap_sst_base': 'https://pae-paha.pacioos.hawaii.edu/erddap/griddap',
    'nasa_earth_urls': {
        'world_topo_bathy': 'https://eoimages.gsfc.nasa.gov/...'
    }
}
```

## 🛠️ Dependencies

Core dependencies:
- `requests` - HTTP requests for API calls
- `numpy` - Numerical processing and marine calculations
- `pandas` - CSV data handling and export
- `Pillow` - Image processing for textures
- `xarray` - NetCDF data handling (future marine data)
- `matplotlib` - Visualization and color mapping

## 📊 Example Output Reports

### Climate Data Report (--generate mode)
```
📊 COMPREHENSIVE CLIMATE DATA REPORT
================================================================================
🌍 Location: 25.7617°, -80.1918° (Near: Florida Keys - 141.7 km)
📅 Date: 2025-06-25
🌡️ Climate Zone: Subtropical
🪸 Reef Context: Near major reef ecosystem

📡 CURRENT WEATHER CONDITIONS
  🌡️ Temperature: 28.3°C (Quality: V)
  💨 Wind Speed: 12.4 km/h (Quality: V)
  📊 Pressure: 101325 Pa (Quality: V)

🪸 CORAL REEF CONDITIONS (LIVE NOAA CRW DATA)
  🌡️ Sea Surface Temp: 29.1°C (CRW)
  🔥 Degree Heating Weeks: 1.2 DHW (Low bleaching risk)
  ⚠️ Bleaching Alert Level: Watch (BAA Level 1)

🌊 WAVE CONDITIONS (LIVE WAVEWATCH III DATA)  
  🌊 Significant Wave Height: 1.5 m
  ⏱️ Wave Period: 5.3 seconds
  🧭 Wave Direction: 095° (East)

🔗 DATA SOURCES & QUALITY
  ✅ Current Weather: 90.0%
  ✅ Coral Bleaching: 80.0%
  ⚠️ Wave Data: 70.0%
  ⚠️ Ocean Currents: 70.0%
```

## 🎯 Testing Commands

Test the complete system with these commands:

```bash
# Test basic functionality
python main.py --coordinates="40.7128,-74.0060"

# Test coral reef data
python main.py --coordinates="25.7617,-80.1918"

# Test with detailed reporting
python main.py --generate

# Test performance optimization
python main.py --quick

# Test global coverage
python main.py --coordinates="0.0,0.0"        # Equator
python main.py --coordinates="70.0,-150.0"    # Arctic
python main.py --coordinates="-65.0,0.0"      # Antarctic

# Test texture generation
python main.py --sst-only --force
python main.py --sst-only --resolution=low --force  # Fast download
python main.py --earth-only --force

# Test validation
python main.py --validate
```

Run these commands and report any issues or unexpected behavior. The system should provide comprehensive climate and marine data for any global coordinates with full quality transparency.

## 📝 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🌐 React Three Fiber Globe Integration

### NEW: Interactive 3D Globe Visualization

The NOAA system now includes a complete React Three Fiber web application for interactive 3D globe visualization with real-time climate data integration.

#### 🚀 Quick Start - Globe Visualization

```bash
# Start the integrated demo (recommended)
./demo.sh

# Or manually start components:

# 1. Start WebSocket server
python main.py --websocket-server

# 2. Start React Globe app (in another terminal)
cd web-globe
npm install
npm run dev
```

#### 🌍 Globe Features

- **🖱️ Interactive 3D Globe**: Click, drag, zoom with smooth animations
- **📡 Real-time Data**: WebSocket integration with Python NOAA system
- **🎯 Smart Camera**: Automatic zoom animations to selected coordinates  
- **🌊 Dynamic SST Textures**: Live sea surface temperature overlays
- **🌍 NASA Earth Base**: High-quality NASA Blue Marble imagery
- **📊 Climate Data Panel**: Real-time display of collected climate data
- **🎲 Random Exploration**: One-click random location generation

#### 🎮 How to Use

1. **Coordinate Selection**:
   - Click anywhere on the globe to select coordinates
   - Enter coordinates manually in the left panel
   - Use "Random Location" for exploration

2. **Real-time Integration**:
   - Camera smoothly zooms to selected location
   - Python backend processes climate data
   - SST texture updates with fresh NOAA data
   - Climate data panel shows comprehensive results

3. **Performance Options**:
   - Multiple SST resolution options (329KB to 11MB)
   - Responsive design for different screen sizes
   - Optimized loading and caching

#### 🏗️ Technical Architecture

```
┌─ React Three Fiber Globe (Frontend) ─┐    ┌─ Python NOAA System (Backend) ─┐
│                                       │    │                                  │
│  🌍 Globe Component                   │◄──►│  🐍 WebSocket Server            │
│  📹 Camera Controls                   │    │  🌊 NOAA Data Processors        │
│  🖼️ Texture Manager                   │    │  📊 Climate Data Collection     │
│  📡 WebSocket Client                  │    │  🎯 Coordinate Processing        │
│                                       │    │                                  │
└─ http://localhost:5173 ──────────────┘    └─ ws://localhost:8765 ────────────┘
```

#### 📁 Globe Project Structure

```
web-globe/                           # React Three Fiber application
├── src/
│   ├── components/
│   │   └── Globe.tsx               # Main 3D globe component
│   ├── hooks/
│   │   ├── useWebSocket.ts         # Real-time data communication
│   │   ├── useGlobeCamera.ts       # Camera animation control
│   │   └── useTextureLoader.ts     # Dynamic texture management
│   ├── utils/
│   │   ├── coordinates.ts          # Lat/lng ↔ 3D conversion
│   │   ├── animations.ts           # Smooth camera transitions
│   │   └── types.ts                # TypeScript interfaces
│   └── App.tsx                     # Main application
├── public/textures/                # Texture files (symlinked)
└── package.json                    # Dependencies
```

#### 🎯 Globe Testing Commands

```bash
# Test complete integration
./demo.sh

# Test specific locations
python main.py --coordinates="25.7617,-80.1918" --resolution=low  # Florida Keys
python main.py --coordinates="40.7128,-74.0060" --resolution=medium  # NYC  
python main.py --coordinates="-16.3,145.8" --resolution=high  # Great Barrier Reef

# Test WebSocket server only
python main.py --websocket-server

# Test React app only
cd web-globe && npm run dev
```

#### 🌐 Browser Compatibility

- **Chrome/Edge**: Full support (recommended)
- **Firefox**: Full support
- **Safari**: Full support (may require WebGL settings)
- **Mobile**: Responsive design with touch controls

#### 🔧 Development

```bash
# Install dependencies
cd web-globe
npm install @react-three/fiber @react-three/drei three @types/three

# Development server
npm run dev

# Production build
npm run build

# Type checking
npm run build  # Includes TypeScript compilation
```

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review the examples in the codebase
- Test with the demo script: `./demo.sh`