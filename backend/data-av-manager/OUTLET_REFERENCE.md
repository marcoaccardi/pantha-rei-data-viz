# Ocean Data Sonifier - Complete Outlet Reference

## 🎵 **Core Normalized Outlets (0-1 range)**
*Primary outlets for real-time sonification and visual control*

| Outlet Name | Units | Range | Description |
|-------------|-------|-------|-------------|
| `temperature_norm` | 0-1 | Normalized | Sea surface temperature (cold=0, hot=1) |
| `health_score_norm` | 0-1 | Normalized | Composite ocean health index (crisis=0, healthy=1) |
| `acidification_norm` | 0-1 | Normalized | Ocean acidification level (healthy=0, acidic=1) |
| `oxygen_norm` | 0-1 | Normalized | Dissolved oxygen concentration (hypoxic=0, rich=1) |
| `marine_life_norm` | 0-1 | Normalized | Marine ecosystem productivity (low=0, high=1) |
| `currents_norm` | 0-1 | Normalized | Ocean current speed (stagnant=0, fast=1) |
| `threat_level_norm` | 0-1 | Normalized | Climate crisis indicator (stable=0, crisis=1) |
| `sea_ice_norm` | 0-1 | Normalized | Sea ice coverage (none=0, full=1) |
| `microplastics_norm` | 0-1 | Normalized | Plastic pollution level (clean=0, polluted=1) |

## 📊 **Core Raw Data Outlets**
*Scientific measurements with realistic units and fallbacks*

| Outlet Name | Units | Typical Range | Description |
|-------------|-------|---------------|-------------|
| `temperature_raw` | °C | -1.8 to 30.4 | Sea surface temperature in degrees Celsius |
| `health_score_raw` | 0-1 | 0.1 to 0.9 | Composite health score (weighted average) |
| `ph_raw` | pH units | 7.85 to 8.25 | Ocean acidity level (logarithmic scale) |
| `oxygen_raw` | mmol/m³ | 195 to 400 | Dissolved oxygen concentration |
| `chlorophyll_raw` | mg/m³ | 0.01 to 2.96 | Phytoplankton biomass indicator |
| `current_speed_raw` | m/s | 0.001 to 2.18 | Ocean current velocity magnitude |
| `threat_level_raw` | 0-1 | 0.1 to 0.9 | Climate threat assessment score |
| `sea_ice_raw` | % | 0 to 98 | Sea ice coverage percentage |
| `microplastics_raw` | pieces/m³ | 0.001 to 0.15 | Plastic particle concentration |

## 🔬 **Component Raw Data Outlets**
*Detailed parameters for specialized analysis*

### Ocean Current Components
| Outlet Name | Units | Range | Description |
|-------------|-------|-------|-------------|
| `current_u_raw` | m/s | -2.0 to 2.0 | Eastward current velocity component |
| `current_v_raw` | m/s | -2.0 to 2.0 | Northward current velocity component |
| `current_direction_raw` | degrees | 0 to 360 | Current flow direction |

### Ocean Chemistry Components
| Outlet Name | Units | Typical Range | Description |
|-------------|-------|---------------|-------------|
| `nitrate_raw` | mmol/m³ | 0 to 29 | Nitrate concentration (essential nutrient) |
| `phosphate_raw` | mmol/m³ | 0 to 2.5 | Phosphate concentration (limiting nutrient) |
| `silicate_raw` | mmol/m³ | 0 to 25 | Silicate concentration (diatom nutrient) |
| `dic_raw` | mmol/m³ | 1900 to 2200 | Dissolved inorganic carbon |
| `alkalinity_raw` | mmol/m³ | 2200 to 2400 | Total alkalinity (buffering capacity) |

### Marine Productivity Components
| Outlet Name | Units | Typical Range | Description |
|-------------|-------|---------------|-------------|
| `marine_life_production_raw` | mg/m³/day | 0 to 109 | Net primary productivity (carbon fixation) |

### Historical Pollution Data
| Outlet Name | Units | Typical Range | Description |
|-------------|-------|---------------|-------------|
| `microplastics_2003_raw` | pieces/m³ | 0.0004 to 0.044 | Microplastics concentration in 2003 |
| `microplastics_2010_raw` | pieces/m³ | 0.0006 to 0.060 | Microplastics concentration in 2010 |

## 📈 **Derived Analysis Outlets**
*Calculated parameters for advanced oceanographic analysis*

| Outlet Name | Units | Description |
|-------------|-------|-------------|
| `current_magnitude_raw` | m/s | Calculated current magnitude (√(u² + v²)) |
| `n_p_ratio_raw` | ratio | Nitrate:Phosphate ratio (Redfield ratio analysis) |
| `microplastics_trend_raw` | factor | Pollution acceleration factor (2010/2003 ratio) |
| `carbonate_saturation_raw` | mmol/m³ | Carbonate saturation state (alkalinity - DIC) |

## 🗺️ **Location Context Outlets**
*Geographic and environmental context data*

| Outlet Name | Type | Example Values | Description |
|-------------|------|----------------|-------------|
| `location_name` | string | "ARC_003", "Eq_001" | Unique location identifier |
| `location_id` | number | 1, 2, 3... | Numeric location ID |
| `latitude` | degrees | -85.0 to 85.0 | Geographic latitude |
| `longitude` | degrees | -180.0 to 180.0 | Geographic longitude |
| `region` | string | "Arctic", "Equatorial" | Ocean region classification |
| `ocean_basin` | string | "Atlantic_Ocean", "Pacific_Ocean" | Major ocean basin |
| `ecosystem_type` | string | "Polar_Marine", "Tropical_Marine" | Marine ecosystem type |
| `climate_zone` | string | "Polar", "Temperate", "Tropical" | Climate classification |

## ⚙️ **Control and Status Outlets**
*System status and playback control information*

| Outlet Name | Type | Description |
|-------------|------|-------------|
| `status` | string | Playback status: "loaded", "playing", "stopped", "paused" |
| `progress` | 0-1 | Playback progress through dataset |
| `current_index` | number | Current location index (1-based) |
| `total_locations` | number | Total number of locations in dataset |
| `error` | string | Error messages if problems occur |

## 🎛️ **Usage Recommendations**

### For Real-time Sonification:
**Use the 9 normalized outlets** - they provide complete ocean health information in audio-friendly 0-1 range:
```
temperature_norm → Pitch/Frequency
health_score_norm → Amplitude/Volume  
acidification_norm → Distortion/Harmony
oxygen_norm → Filter Cutoff
marine_life_norm → Harmonic Content
currents_norm → Spatial Movement
threat_level_norm → Urgency/Rhythm
sea_ice_norm → Brightness/Timbre
microplastics_norm → Noise/Contamination
```

### For Scientific Analysis:
**Use component raw outlets** for detailed investigation:
```
current_u_raw, current_v_raw → Vector field analysis
nitrate_raw, phosphate_raw → Nutrient limitation studies
microplastics_2003_raw, microplastics_2010_raw → Pollution trend analysis
```

### For Data Visualization:
**Combine normalized and raw outlets**:
```
Normalized → Real-time visual effects, color mapping
Raw → Scientific displays, charts, numerical readouts
```

## ⚠️ **Performance Considerations**

- **Max/MSP Stability**: Monitor CPU usage with all outlets active
- **Selective Use**: Connect only needed outlets to avoid overload
- **Zero Avoidance**: Raw outlets include realistic minimum values for audio synthesis
- **Update Rate**: 12-second intervals (configurable) provide stable real-time performance

This comprehensive outlet system provides both **artistic control** (normalized) and **scientific accuracy** (raw components) for the complete ocean health sonification experience.