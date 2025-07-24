# Panta Rhei Data Visualization

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://python.org)
[![React Three Fiber](https://img.shields.io/badge/React%20Three%20Fiber-Compatible-brightgreen.svg)](https://github.com/pmndrs/react-three-fiber)
[![TypeScript](https://img.shields.io/badge/TypeScript-4.9+-blue.svg)](https://www.typescriptlang.org/)

An interactive 3D globe visualization system that displays real-time marine and climate data from NOAA and other scientific sources. Features a React Three Fiber web application with WebSocket integration for live data updates.

## 🎯 Overview

This system provides:

- **🌍 Interactive 3D Globe**: React Three Fiber visualization with smooth camera animations
- **🌡️ Real-time Climate Data**: Live data from NOAA and multiple climate APIs
- **🌊 Sea Surface Temperature**: Dynamic SST overlay textures from ERDDAP
- **📊 Marine Parameters**: Comprehensive ocean data including salinity, pH, depth, and more
- **📡 WebSocket Integration**: Real-time data streaming between Python backend and React frontend
- **🎲 Global Exploration**: Click anywhere on the globe or use random location generation

## 🏗️ Architecture

```
panta-rhei-data-map/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── config.py                    # Configuration settings
├── main.py                      # Main Python entry point
├── websocket_server.py          # WebSocket server for real-time data
├── demo.sh                      # Demo launcher script
├── src/                         # Python source code
│   ├── processors/              # Data processors
│   │   ├── earth_textures.py    # NASA Earth texture processor
│   │   ├── erddap_sst_processor.py  # ERDDAP SST data
│   │   ├── enhanced_climate_data.py  # Climate data aggregator
│   │   ├── fast_climate_processor.py # Optimized climate data
│   │   └── ...                  # Other marine data processors
│   └── utils/                   # Utility modules
├── web-globe/                   # React Three Fiber application
│   ├── src/
│   │   ├── App.tsx             # Main React application
│   │   ├── components/
│   │   │   ├── Globe.tsx       # 3D globe component
│   │   │   └── Scene.tsx       # Three.js scene setup
│   │   ├── hooks/              # Custom React hooks
│   │   │   ├── useWebSocket.ts # WebSocket connection
│   │   │   ├── useGlobeCamera.ts # Camera controls
│   │   │   └── useTextureLoader.ts # Texture management
│   │   └── utils/              # Utility functions
│   ├── public/textures/        # Earth and SST textures
│   └── package.json            # Node.js dependencies
└── data/                       # Data storage (created at runtime)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- Node.js 16+
- npm or yarn

### Installation

```bash
# Clone the repository
git clone git@github.com:marcoaccardi/pantha-rei-data-viz.git
cd pantha-rei-data-viz

# Install Python dependencies
pip install -r requirements.txt

# Install React dependencies
cd web-globe
npm install
cd ..
```

### Running the Application

#### Option 1: Use the Demo Script (Recommended)

```bash
./demo.sh
```

This will:
1. Download required textures
2. Start the WebSocket server
3. Launch the React development server
4. Open your browser to http://localhost:5173

#### Option 2: Manual Start

```bash
# Terminal 1: Start the WebSocket server
python websocket_server.py

# Terminal 2: Start the React app
cd web-globe
npm run dev
```

## 🎮 How to Use

### Interactive Globe Controls

1. **Click on Globe**: Select any location to fetch climate data
2. **Drag to Rotate**: Click and drag to rotate the globe
3. **Scroll to Zoom**: Use mouse wheel or trackpad to zoom in/out
4. **Keyboard Controls**: 
   - Arrow keys to rotate
   - +/- to zoom

### UI Controls

- **🌡️ Hide/Show SST Overlay**: Toggle sea surface temperature visualization
- **🎲 Random Ocean Location**: Jump to a random ocean coordinate
- **Coordinate Display**: Shows current latitude/longitude
- **Connection Status**: WebSocket connection indicator

### Data Panel

The right panel displays real-time marine and climate data:
- Sea Surface Temperature
- Ocean Depth
- Ocean Salinity
- Ocean pH Level
- Wind Speed
- And more parameters...

## 📊 Data Sources

### Climate Data APIs
- **NOAA National Weather Service**: Current weather observations
- **Open-Meteo**: Historical climate data and forecasts
- **NOAA Coral Reef Watch**: Sea surface temperature and coral bleaching metrics

### Texture Sources
- **NASA Blue Marble**: High-resolution Earth imagery
- **ERDDAP PacIOOS**: Sea surface temperature data via Hawaii ERDDAP server

## 🌐 WebSocket API

The WebSocket server (ws://localhost:8765) accepts JSON messages:

```javascript
// Request climate data
{
  "action": "get_climate_data",
  "lat": 25.7617,
  "lon": -80.1918
}

// Response
{
  "status": "success",
  "data": [
    {
      "parameter": "Sea Surface Temperature",
      "value": 29.1,
      "units": "°C",
      "data_source": "NOAA_CRW",
      "quality": "V",
      "confidence": 0.9
    },
    // ... more parameters
  ]
}
```

## ⚡ Performance Optimization

### Texture Resolution Options

```bash
# High resolution (7200x3600, ~11MB)
python main.py --sst-only --resolution=high

# Medium resolution (3600x1800, ~3.7MB) - DEFAULT
python main.py --sst-only --resolution=medium

# Low resolution (1800x900, ~1.1MB)
python main.py --sst-only --resolution=low

# Preview resolution (900x450, ~329KB)
python main.py --sst-only --resolution=preview
```

### Quick Mode

```bash
# Skip climate data, only download textures
python main.py --quick

# Ultra-fast with preview resolution
python main.py --quick --resolution=preview
```

## 🔧 Configuration

Key settings in `config.py`:

```python
# WebSocket settings
WEBSOCKET_HOST = 'localhost'
WEBSOCKET_PORT = 8765

# Texture specifications
TEXTURE_SPECS = {
    'target_width': 7200,
    'target_height': 3600,
    'aspect_ratio': 2.0
}

# API endpoints
DATA_SOURCES = {
    'nws_base': 'https://api.weather.gov',
    'open_meteo_base': 'https://archive-api.open-meteo.com/v1/archive',
    # ... more sources
}
```

## 🛠️ Development

### Project Structure

#### Python Backend (`/src`)
- **processors/**: Data processing modules for different sources
- **utils/**: Shared utilities for API calls, file operations, validation

#### React Frontend (`/web-globe`)
- **components/**: React components (Globe, Scene)
- **hooks/**: Custom React hooks for WebSocket, camera, textures
- **utils/**: Helper functions for coordinates, types

### Adding New Data Sources

1. Create a new processor in `src/processors/`
2. Implement the data fetching logic
3. Add to `enhanced_climate_data.py` for integration
4. Update WebSocket server to handle new data

### Customizing the Globe

Edit `web-globe/src/components/Globe.tsx` to:
- Change globe appearance
- Add new overlays
- Modify interaction behavior

## 📦 Dependencies

### Python
- `requests`: HTTP client for API calls
- `numpy`: Numerical computations
- `pandas`: Data manipulation
- `Pillow`: Image processing
- `websockets`: WebSocket server
- `aiohttp`: Async HTTP client

### React/TypeScript
- `@react-three/fiber`: React renderer for Three.js
- `@react-three/drei`: Useful helpers for R3F
- `three`: 3D graphics library
- `typescript`: Type safety
- `vite`: Build tool

## 🐛 Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Ensure the Python WebSocket server is running
   - Check firewall settings for port 8765

2. **Textures Not Loading**
   - Run `python main.py --quick` to download textures
   - Check `web-globe/public/textures/` directory

3. **Performance Issues**
   - Use lower resolution textures: `--resolution=low`
   - Reduce texture quality in browser settings

### Debug Commands

```bash
# Test WebSocket server
python websocket_server.py

# Test climate data fetching
python main.py --coordinates="40.7128,-74.0060"

# Validate existing files
python main.py --validate
```

## 📝 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For issues and questions:
- Open an issue on [GitHub](https://github.com/marcoaccardi/pantha-rei-data-viz/issues)
- Check the [documentation](https://github.com/marcoaccardi/pantha-rei-data-viz/wiki)

## 🙏 Acknowledgments

- NASA for Earth imagery
- NOAA for climate and ocean data
- Three.js and React Three Fiber communities