# Ocean Data Retrieval Files

This folder contains all the files needed to retrieve the various types of ocean data used by the Corals monitoring system.

## Complete List of Ocean Data Retrieved

### 1. **Biological/Biogeochemical Data (12 parameters)**
**Files:**
- `ocean_biological__server.py` - Main retrieval function using xarray/NetCDF
- `update_biological_dataset.sh` - Daily download script using motuclient

**Parameters Retrieved:**
- **spco2** - Surface CO₂ partial pressure (Pa)
- **o2** - Dissolved oxygen (mmol m⁻³)
- **chl** - Chlorophyll-a concentration (mg m⁻³)
- **no3** - Nitrate concentration (mmol m⁻³)
- **po4** - Phosphate concentration (mmol m⁻³)
- **phyc** - Phytoplankton carbon (mg m⁻³)
- **si** - Silicate concentration (mmol m⁻³)
- **ph** - pH (dimensionless)
- **talk** - Total alkalinity (mmol m⁻³)
- **nppv** - Net primary productivity (mg C m⁻² day⁻¹)
- **dissic** - Dissolved inorganic carbon (mmol m⁻³)
- **fe** - Iron concentration (mmol m⁻³)

**Source:** Copernicus Marine Environment Monitoring Service (CMEMS)
**API:** GLOBAL_ANALYSIS_FORECAST_BIO_001_028-TDS
**Format:** NetCDF files (daily, 0.25° resolution)

### 2. **Ocean Currents Data (2 parameters)**
**Files:**
- `ocean_currents__server.py` - Main retrieval function using netCDF4

**Parameters Retrieved:**
- **u** - Eastward velocity component (m/s)
- **v** - Northward velocity component (m/s)

**Source:** NASA OSCAR (Ocean Surface Current Analyses Real-time)
**Format:** NetCDF files from EarthData
**Coverage:** 2021-2023 historical data

### 3. **Wave Data (9 parameters)**
**Files:**
- `ocean_waves_api__server.js` - API client for ERDDAP wave data

**Parameters Retrieved:**
- **Tdir** - Total wave direction (degrees from north)
- **Tper** - Total wave period (seconds)
- **Thgt** - Total wave height (meters)
- **sdir** - Swell direction (degrees from north)
- **sper** - Swell period (seconds)
- **shgt** - Swell height (meters)
- **wdir** - Wind wave direction (degrees from north)
- **wper** - Wind wave period (seconds)
- **whgt** - Wind wave height (meters)

**Source:** WAVEWATCH III Global Wave Model via PacIOOS ERDDAP
**API:** `https://pae-paha.pacioos.hawaii.edu/erddap/griddap/ww3_global.json`
**Coverage:** Historical data from 2010 onwards

### 4. **Coral Bleaching Monitoring Data (6 parameters)**
**Files:**
- `coral_bleaching_monitor_api__server.js` - Max/MSP interface server
- (Referenced: `get_coral_bleaching_monitor__db.js` - Database handler)

**Parameters Retrieved:**
- **CRW_BAA** - Bleaching Alert Area
- **CRW_BAA_7D_MAX** - 7-day maximum Bleaching Alert Area
- **CRW_DHW** - Degree Heating Weeks
- **CRW_HOTSPOT** - Hotspot values
- **CRW_SST** - Sea Surface Temperature (°C)
- **CRW_SSTANOMALY** - SST Anomaly (°C)

**Source:** NOAA Coral Reef Watch via PacIOOS ERDDAP
**API:** `https://pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km.json`
**Resolution:** 5km global coverage

### 5. **Sea Surface Temperature Data (Station-based)**
**Files:**
- `get_sst_min-max.js` - Station-specific SST retrieval

**Parameters Retrieved:**
- **SST_MIN** - Daily minimum Sea Surface Temperature (°C)
- **SST_MAX** - Daily maximum Sea Surface Temperature (°C)

**Source:** NOAA Coral Reef Watch Virtual Stations
**Coverage:** 216+ coral reef monitoring stations worldwide
**Format:** Station-specific JSON files with historical time series

## Supporting Files

### Dependencies
- `requirements.txt` - Python package dependencies (xarray, netCDF4, numpy, etc.)
- `package.json` - Node.js dependencies (express, socket.io, axios, etc.)

### Data Sources Summary
- **NOAA Coral Reef Watch** - SST data, coral bleaching alerts
- **Copernicus Marine Service** - Biological/biogeochemical parameters
- **NASA OSCAR** - Ocean surface currents
- **WAVEWATCH III** - Global wave model data
- **PacIOOS ERDDAP** - Real-time data access gateway

### Access Methods
- **NetCDF Processing** - Direct file reading with xarray/netCDF4
- **API Requests** - HTTPS GET requests to ERDDAP endpoints
- **Automated Downloads** - Shell scripts with motuclient and curl
- **WebSocket Communication** - Real-time data streaming

### Data Coverage
- **Spatial:** Global ocean coverage with focus on coral reef regions
- **Temporal:** Daily resolution with historical archives and real-time updates
- **Geographic:** 216+ predefined coral reef monitoring stations worldwide

### Total Parameters: 29 distinct ocean data variables across all categories