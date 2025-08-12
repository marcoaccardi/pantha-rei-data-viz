# Temporal Data Strategy: How 3 Dates Become 1 Value

## 🕐 **The Question: 3 Time Points → 1 Sonification Value?**

Each location in our dataset has **3 time snapshots** (2003, 2010, 2025), but the sonifier outputs **1 value per parameter**. Here's exactly how this temporal aggregation works:

---

## 📊 **Current Temporal Strategy in JavaScript**

### **1. "Latest State" Approach (Most Parameters)**
**Strategy**: Use the most recent (2025) data point as the primary value

```javascript
// Example: Temperature
temperature_raw = location.SST_2025_C || 15.0  // Use 2025 temperature

// Example: Microplastics  
microplastics_raw = location.Microplastics_2025_pieces_m3 || 0.005  // Use 2025 pollution
```

**Reasoning**: 
- Represents current ocean health state
- Most relevant for "now" awareness
- 2025 = accumulated climate impact

### **2. "Trend Calculation" Approach (Health & Threat Scores)**
**Strategy**: Calculate change over time and incorporate into composite scores

```javascript
// Temperature warming trend (used in threat calculation)
if (location.SST_2003_C !== null && location.SST_2025_C !== null) {
    const warming = location.SST_2025_C - location.SST_2003_C;  // 22-year change
    const warmingThreat = normalize(warming, -2, 5, 0.3);       // Convert to threat score
}

// Microplastics acceleration (used in health calculation)
const pollutionIncrease = location.Microplastics_2025_pieces_m3 / location.Microplastics_2003_pieces_m3;
```

**Reasoning**:
- Captures temporal dynamics
- Shows acceleration/deceleration patterns
- Incorporates change velocity into health assessment

### **3. "Optimal Period" Approach (Some Parameters)**
**Strategy**: Use the time period with best data availability

```javascript
// Oxygen: Use 2010 data (best historical coverage)
oxygen_raw = location.Oxygen_2010_mmol_m3 || 270

// Chlorophyll: Use 2010 data (consistent with oxygen)
chlorophyll_raw = location.Chlorophyll_2010_mg_m3 || 0.3
```

**Reasoning**:
- Historical biogeochemistry datasets have better 2010 coverage
- Avoids missing data while maintaining scientific accuracy

---

## 🎵 **Alternative Temporal Approaches for Sonification**

### **Option A: Time-Series Sonification (Sequential)**
Play each location 3 times in temporal sequence:

```javascript
// Location 1: 2003 → 2010 → 2025
// Location 2: 2003 → 2010 → 2025  
// etc.
```

**Pros**: Shows clear temporal evolution
**Cons**: 3x longer playback (60 minutes instead of 20)

### **Option B: Temporal Average**
Average across all available time points:

```javascript
temperature_avg = (SST_2003 + SST_2010 + SST_2025) / 3
```

**Pros**: Smooths out temporal noise
**Cons**: Obscures recent crisis acceleration

### **Option C: Weighted Temporal Composite**
Weight recent data more heavily:

```javascript
temperature_weighted = (SST_2003 × 0.2) + (SST_2010 × 0.3) + (SST_2025 × 0.5)
```

**Pros**: Emphasizes current state while preserving history
**Cons**: Arbitrary weighting choices

### **Option D: Multi-Outlet Temporal (Current Implementation Enhanced)**
Separate outlets for each time period:

```javascript
Max.outlet('temperature_2003_raw', location.SST_2003_C);
Max.outlet('temperature_2010_raw', location.SST_2010_C);  
Max.outlet('temperature_2025_raw', location.SST_2025_C);
Max.outlet('temperature_trend_raw', SST_2025 - SST_2003);
```

**Pros**: Complete temporal information available
**Cons**: More outlets to manage in Max/MSP

---

## 🔬 **Current Strategy Justification**

### **Why "Latest State + Trends" Works Best**

#### **For Real-Time Sonification:**
- ✅ **Current relevance**: 2025 data represents "now"
- ✅ **Crisis urgency**: Recent values show accumulated damage
- ✅ **Trend awareness**: Health/threat scores include temporal dynamics
- ✅ **Performance efficiency**: One value per parameter = stable audio

#### **For Scientific Accuracy:**
- ✅ **Data quality**: Uses best available time period for each parameter
- ✅ **Trend detection**: Warming and pollution acceleration captured
- ✅ **Missing data handling**: Fallbacks based on scientific realism
- ✅ **Regional patterns**: 2025 data shows current regional differences

---

## 📈 **Detailed Parameter-by-Parameter Temporal Logic**

| Parameter | Time Used | Reasoning |
|-----------|-----------|-----------|
| **Temperature** | 2025 | Current warming state |
| **pH** | 2025 | Current acidification level |
| **Oxygen** | 2010 | Best historical data coverage |
| **Chlorophyll** | 2010 | Consistent with oxygen period |
| **Currents** | 2025 | Current circulation patterns |
| **Sea Ice** | 2025 | Current polar ice state |
| **Microplastics** | 2025 | Current pollution crisis |
| **Health Score** | **Composite** | Uses 2025 state + trends |
| **Threat Level** | **Composite** | Uses 2003→2025 trends |

### **Health Score Temporal Logic:**
```javascript
// Uses current state (2025) for most factors:
tempHealth = f(SST_2025_C)           // Current temperature stress
phHealth = f(pH_2025)                // Current acidification  
pollutionHealth = f(Microplastics_2025) // Current contamination

// But incorporates some 2010 data where it's more reliable:
oxygenHealth = f(Oxygen_2010_mmol_m3)    // Historical oxygen baseline
productivityHealth = f(Chlorophyll_2010) // Historical productivity
```

### **Threat Level Temporal Logic:**
```javascript
// Explicitly uses temporal trends:
warmingThreat = f(SST_2025_C - SST_2003_C)     // 22-year warming
currentTempThreat = f(SST_2025_C)              // Current heat stress
acidThreat = f(pH_2025)                        // Current chemistry
pollutionThreat = f(Microplastics_2025)        // Current contamination
```

---

## 🎛️ **Enhanced Temporal Access in Raw Outlets**

The current implementation **does** provide access to multiple time periods through raw outlets:

```javascript
// Current temporal outlets available:
Max.outlet('microplastics_2003_raw', ...);  // Historical baseline
Max.outlet('microplastics_2010_raw', ...);  // Mid-period  
Max.outlet('microplastics_raw', ...);       // Current (2025)

// Could be enhanced to include:
Max.outlet('temperature_2003_raw', ...);
Max.outlet('temperature_2010_raw', ...);
Max.outlet('sea_ice_2003_raw', ...);
Max.outlet('sea_ice_2010_raw', ...);
```

---

## 🎵 **Recommendation: Multi-Temporal Sonification Mode**

Would you like me to implement an **enhanced temporal mode** that provides:

1. **Current Mode** (existing): Latest state + trends
2. **Time-Series Mode** (new): Sequential 2003→2010→2025 playback  
3. **All-Periods Mode** (new): Separate outlets for each time period

This would give users complete control over temporal representation while maintaining the optimized current approach for standard sonification.

The current strategy of **"latest state + calculated trends"** provides the most scientifically meaningful and artistically effective approach for ocean health sonification, but I can enhance it to provide complete temporal flexibility if needed.