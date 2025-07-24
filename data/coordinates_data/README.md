# Coordinates Data Files

This folder contains all files used to retrieve and handle coordinate data in the Corals ocean monitoring system.

## Coordinate Data Sources

### JSON Files
- **`areas_name_and_coords.json`** - Main coordinate database containing lat/lon coordinates for 216+ coral reef areas worldwide
- **`stationData.js`** - Array of coral reef station names used for coordinate lookups
- **`stationDataES5.js`** - ES5 version of station data array
- **`stations_data_array.js`** - Station array for coordinate indexing

### Coordinate Extraction Scripts
- **`get_area_info.js`** - Extracts lat/lon from station JSON files based on station index
- **`get_coral_bleaching_monitor__db.js`** - Handles coordinate bounds for NOAA coral bleaching API calls
- **`ocean_waves_api__server.js`** - Processes lat/lon parameters for wave data retrieval

### Ocean Data Processing (Coordinate-based)
- **`ocean_currents__server.py`** - Retrieves ocean current data using lat/lon coordinates
- **`ocean_biological__server.py`** - Retrieves biological ocean data using lat/lon coordinates
- **`socket-pythonserver.py`** - WebSocket server that receives coordinates and returns ocean data

### User Interface
- **`Map.jsx`** - React component that handles coordinate input from Cesium 3D map interface

## Coordinate Flow
1. **Input**: Coordinates come from map interface, WebSocket messages, or station indices
2. **Processing**: Scripts extract/validate coordinates and convert formats as needed
3. **Data Retrieval**: Ocean data APIs and NetCDF processors use coordinates to fetch relevant data
4. **Output**: Coordinate-specific ocean data (currents, biology, waves, SST) returned to client

## File Dependencies
- Station files depend on `areas_name_and_coords.json` for coordinate lookup
- Python servers require NetCDF ocean datasets
- JavaScript servers connect to NOAA ERDDAP APIs
- React component integrates with Cesium mapping library