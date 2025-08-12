# Ocean Data AV Manager
**Real-time Ocean Health Data Sonification and Visualization for Max/MSP**

Transform 22 years of ocean health crisis data into immersive audiovisual experiences using Node for Max and real NetCDF scientific data.

## 📊 **What This Package Contains**

### **Files:**
- `ocean_data_sonifier.js` - Node for Max script with 8 data streams
- `ocean_sonification.maxpat` - Main Max/MSP interface with controls and faders  
- `ocean_health_data.csv` - 575 real ocean locations with 39 parameters (2003-2025)
- `examples/basic_sonification.maxpat` - Simple sonification example
- `README.md` - This documentation

### **Real Data Coverage:**
- **575 Global Locations**: Arctic to Antarctic, all major ocean basins
- **39 Parameters**: Temperature, pH, oxygen, currents, biochemistry, ecosystem data
- **22-Year Timeline**: Dramatic changes from 2003 to 2025
- **100% Authentic**: Extracted from real NetCDF scientific datasets

---

## 🎵 **10 Data Streams (Outlets)**

### **Outlet 1: Location Metadata**
```javascript
{
  id: 1,
  name: "ARC_002", 
  latitude: 65.12,
  longitude: -0.65
}
```

### **Outlet 2: Temporal Data** (Time Context)
```javascript
{
  date_early: "2003-01-15",
  date_mid: "2010-01-15", 
  date_late: "2025-01-15",
  time_span_years: 22,
  current_era: "Multi_Temporal_Analysis"
}
```

### **Outlet 3: Spatial Context** (Geographic Classification)
```javascript
{
  region: "Arctic",                    // From CSV: Arctic, North_Pacific, etc.
  ocean_basin: "Arctic_Ocean",         // From CSV: Arctic_Ocean, Pacific_Ocean, etc.
  ecosystem_type: "Subpolar_Marine",   // From CSV: Polar_Marine, Subpolar_Marine, etc.
  climate_zone: "Temperate"           // From CSV: Polar, Temperate, Tropical, etc.
}
```

### **Outlet 4: Temperature Data** (Normalized 0-1)
```javascript
{
  sst_2003: 0.256,        // Sea surface temp 2003
  sst_2010: 0.261,        // Sea surface temp 2010  
  sst_2025: 0.225,        // Sea surface temp 2025
  warming_trend: 0.4,     // Temperature change trend
  sea_ice: 0.0            // Sea ice coverage
}
```

### **Outlet 5: Ocean Health Score** (0-1, higher = healthier)
- Composite index combining temperature, pH, oxygen, and circulation
- **1.0** = Pristine Arctic waters
- **0.0** = Critical crisis zones

### **Outlet 6: Acidification Level** (0-1, higher = more acidic/dangerous)
- pH levels inverted (lower pH = higher danger value)
- **0.0** = Healthy pH (>8.1)
- **1.0** = Dangerous acidification (<7.9)

### **Outlet 7: Oxygen Status** (0-1, higher = more oxygen)
- Dissolved oxygen levels normalized
- **0.0** = Hypoxic dead zones
- **1.0** = Well-oxygenated waters

### **Outlet 8: Marine Life Index** (0-1)
```javascript
{
  chlorophyll_2003: 0.15,
  chlorophyll_2010: 0.14,
  marine_life_2003: 0.08,
  marine_life_2010: 0.06,
  combined: 0.10          // Overall marine life support capacity
}
```

### **Outlet 9: Current Dynamics** (Ocean circulation)
```javascript
{
  speed: 0.043,           // Current speed (0-1)
  direction: 0.812,       // Direction (0-1, *360 for degrees)
  u_component: 0.010,     // Eastward velocity
  v_component: -0.026     // Northward velocity
}
```

### **Outlet 10: Threat Level** (0-1, higher = more threatened)
- Combined crisis indicator: warming + acidification + oxygen loss
- **0.0** = Healthy, stable waters  
- **1.0** = Multiple simultaneous threats

---

## 🚀 **Quick Start**

### **1. Setup Requirements:**
- Max/MSP 8+ with Node for Max installed
- Place all files in same directory
- Ensure `ocean_health_data.csv` is in same folder as `.js` file

### **2. Load the Patch:**
```
Open: ocean_sonification.maxpat
```

### **3. Basic Controls:**
- **START**: Begin 20-minute ocean journey
- **PAUSE**: Pause/resume playback  
- **STOP**: Stop and return to beginning
- **RESET**: Reset to first location
- **Speed**: Adjust playback speed (0.1x to 5.0x)

### **4. Data Flow:**
Every **10.4 seconds**, new ocean location data flows through 8 outlets to control:
- Audio synthesis parameters
- Visual shader effects  
- Volume faders
- Real-time displays

---

## 🌊 **The Ocean Story**

### **Playback Strategy:**
- **115 locations** sampled from 575 (every 5th row)
- **10.4 seconds per location** (configurable)
- **20-minute total journey** through ocean health crisis

### **Geographic Journey:**
1. **Arctic Refuges** (0-5 min): Healthy pH, high oxygen, cold temps
2. **Temperate Transitions** (5-10 min): Moderate warming, declining marine life
3. **Tropical Crisis Zones** (10-15 min): Extreme heat, acidification, hypoxia
4. **Global Synthesis** (15-20 min): Dramatic contrasts and composite trends

### **Health Spectrum:**
- **Healthiest**: Arctic location pH 8.150, high oxygen, stable currents
- **Most Threatened**: Pacific location pH 7.847, hypoxic, 27.6°C warming

---

## 🎛️ **Advanced Usage**

### **Custom Playback Speed:**
```javascript
// In Max: send message to node.script
speed 2.0        // 2x faster (10 minutes total)
speed 0.5        // 2x slower (40 minutes total)  
```

### **Jump to Specific Locations:**
```javascript
jump 50          // Jump to location 50/115
jump 0           // Jump to beginning
```

### **Manual Data Loading:**
```javascript
loadData         // Reload CSV if file changed
```

### **Status Monitoring:**
The script outputs status messages:
- `loaded 115` - Data loaded successfully
- `playing` - Playback started
- `completed` - Finished all locations
- `error <message>` - Error occurred

---

## 🎨 **Sonification Ideas**

### **Audio Mapping Strategies:**

#### **Temperature → Pitch/Filtering**
```
Cold Arctic waters: Low frequencies, warm timbres
Hot tropical waters: High frequencies, harsh filtering  
Warming trends: Rising pitch over time
```

#### **pH/Acidification → Harmonicity**
```
Healthy pH (>8.1): Pure harmonic tones
Acidic pH (<7.9): Distorted, noisy textures
Acidification process: Gradual harmonic degradation
```

#### **Oxygen Levels → Amplitude/Breathing**
```
High oxygen: Full, breathing amplitude envelopes
Hypoxic zones: Suffocated, gasping rhythms
Dead zones: Silence or minimal amplitude
```

#### **Marine Life → Harmonic Richness**
```
High marine life: Rich, complex harmonics, full orchestration
Low marine life: Sparse, thin textures, minimal instrumentation
Declining trends: Gradual reduction in harmonic complexity
Ocean deserts: Minimal sound, isolated tones
```

#### **Ocean Currents → Spatialization**
```
Current speed: Rate of spatial movement
Current direction: Panning/3D positioning  
Stagnant waters: Fixed, static positioning
```

#### **Threat Level → Overall Intensity**
```
Low threat: Gentle, peaceful soundscapes
High threat: Urgent, dissonant, overwhelming textures
Crisis zones: Alarm-like, distressed audio signatures
```

---

## 🖥️ **Visual Shader Control**

### **Color Mapping:**
- **Blue spectrum**: Healthy, cold, oxygenated waters
- **Red spectrum**: Warming, acidifying, threatened zones  
- **Green elements**: High productivity, life abundance
- **Gray/black**: Dead zones, data gaps

### **Animation Control:**
- **Current speed**: Particle velocity, flow rates
- **Current direction**: Flow direction vectors
- **Temperature**: Color temperature, thermal shimmer
- **pH levels**: Transparency, corrosion effects
- **Oxygen**: Bubble density, breathing patterns

---

## 📈 **Data Quality & Accuracy**

### **Source Verification:**
- **Real NetCDF extraction**: No synthetic data
- **Scientific datasets**: CMEMS, NOAA, oceanographic institutions
- **80.2% data completeness**: Missing values handled gracefully
- **Coordinate-accurate**: Precise latitude/longitude positioning

### **Normalization Ranges:**
```javascript
Temperature: -1.8°C to 31.04°C
pH: 7.847 to 8.313  
Oxygen: 196.6 to 412.8 mmol/m³
Currents: 0 to 1.942 m/s
Chlorophyll: 0.026 to 5.752 mg/m³
```

---

## 🛠️ **Troubleshooting**

### **Common Issues:**

#### **"CSV file not found" Error:**
```
Solution: Ensure ocean_health_data.csv is in same folder as .js file
Check: File path in CONFIG section of ocean_data_sonifier.js
```

#### **No Data Output:**
```
Solution: Send "loadData" message to node.script
Check: Max console for error messages
Verify: Node for Max is installed and working
```

#### **Playback Too Fast/Slow:**
```
Solution: Use speed control or modify CONFIG.intervalMs in .js file
Default: 10400ms = 10.4 seconds per location
```

#### **Missing Node for Max:**
```
Solution: Install Node for Max from Cycling '74
Check: Max 8+ is required
Verify: node.script object loads without errors
```

---

## 🌍 **The Ocean Crisis Story**

This data tells the dramatic story of our oceans under climate change:

### **The Numbers:**
- **0.42°C average warming** over 22 years
- **Only 5.9%** of oceans remain healthy (pH >8.1)  
- **93.3%** show concerning acidification
- **-9.5% decline** in primary productivity
- **6.9%** have hypoxic conditions

### **The Locations:**
- **Healthiest**: Arctic waters still maintaining pH 8.15, high oxygen
- **Most Threatened**: Tropical Pacific with pH 7.84, hypoxic, overheated
- **Most Dramatic Change**: +9.08°C warming in North Pacific locations

### **The Urgency:**
Every 10.4 seconds of this sonification represents a real ocean location's struggle with climate change. The data flows from pristine Arctic refuges to critically threatened tropical seas, making the ocean crisis audible and emotionally impactful.

---

## 📝 **License & Credits**

- **Ocean Data**: Derived from public oceanographic datasets (CMEMS, NOAA)
- **Processing**: Panta Rhei Data Visualization Project  
- **Code**: Open source, customize freely
- **Usage**: Educational, artistic, and research purposes

**Making Ocean Data Audible - One Location at a Time** 🌊🎵