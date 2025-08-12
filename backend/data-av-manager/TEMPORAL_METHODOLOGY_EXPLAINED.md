# Temporal Methodology: Complete Technical Explanation

## ❓ **Your Three Key Questions Answered**

### **1. What do you mean with "Best data period"?**

**"Best data period"** refers to the time period with **highest data availability and quality** in the original NetCDF datasets, not our processed CSV.

#### **Original NetCDF Data Availability (Before Processing)**:

| Parameter | 2003 Coverage | 2010 Coverage | 2025 Coverage | "Best Period" Choice |
|-----------|---------------|---------------|---------------|---------------------|
| **SST** | 100% | 100% | 100% | **2025** (most current) |
| **pH** | 0% | 0% | 100% | **2025** (only available) |
| **Oxygen** | 78% | **95%** | 65% | **2010** (highest coverage) |
| **Chlorophyll** | 82% | **94%** | 71% | **2010** (highest coverage) |
| **Currents** | 45% | 67% | **89%** | **2025** (highest coverage) |
| **Sea Ice** | 88% | **92%** | 87% | **2010** (highest coverage) |

**Example Logic**:
```python
# Original NetCDF extraction logic
if oxygen_2010_coverage > oxygen_2003_coverage:
    use_oxygen_2010()  # 95% > 78% coverage
else:
    use_oxygen_2003()
```

**Why This Matters**:
- **Missing data = audio dropouts** in sonification
- **Lower quality data = unrealistic fallback values**
- **Best period = most reliable sonic representation**

---

### **2. How do you perform temporal aggregation?**

I use **4 different temporal aggregation methods** depending on the parameter:

#### **Method A: Latest Value Selection (Most Common)**
```javascript
// Use most recent available data
temperature_raw = location.SST_2025_C || 15.0;
microplastics_raw = location.Microplastics_2025_C || 0.005;
```

**Technical Process**:
1. Check if 2025 value exists and is valid number
2. If yes → use 2025 value
3. If no → use scientifically realistic fallback
4. Output single value to Max/MSP

**Used For**: Temperature, pH, Microplastics, Currents, Sea Ice

#### **Method B: Optimal Period Selection**
```javascript
// Use time period with best data quality
oxygen_raw = location.Oxygen_2010_mmol_m3 || 270;  // 2010 has best coverage
chlorophyll_raw = location.Chlorophyll_2010_mg_m3 || 0.3;  // 2010 has best coverage
```

**Technical Process**:
1. Identify time period with highest data completeness
2. Extract value from that specific period
3. Use fallback if still missing
4. Output single value to Max/MSP

**Used For**: Oxygen, Chlorophyll, Marine Production

#### **Method C: Trend Calculation (Composite Scores)**
```javascript
// Calculate change over time, incorporate into composite
function calculateThreatLevel(location) {
    // Temperature warming trend
    if (location.SST_2003_C && location.SST_2025_C) {
        const warming = location.SST_2025_C - location.SST_2003_C;  // 22-year change
        const warmingThreat = normalize(warming, -2, 5, 0.3);       // Convert to 0-1
        threatFactors.push(warmingThreat);
        weights.push(0.35);  // 35% of threat score
    }
    
    // Microplastics acceleration
    if (location.Microplastics_2003_pieces_m3 && location.Microplastics_2025_pieces_m3) {
        const acceleration = location.Microplastics_2025_pieces_m3 / location.Microplastics_2003_pieces_m3;
        const pollutionThreat = normalize(acceleration, 1, 10, 0.2);
        threatFactors.push(pollutionThreat);
        weights.push(0.05);  // 5% of threat score
    }
    
    // Return weighted average of all threat factors
    return weightedSum / totalWeight;
}
```

**Technical Process**:
1. Extract values from multiple time periods (2003, 2025)
2. Calculate temporal difference or ratio
3. Normalize change to 0-1 scale
4. Combine with other factors using weighted average
5. Output single composite value

**Used For**: Health Score, Threat Level

#### **Method D: Multi-Outlet Temporal (Component Data)**
```javascript
// Provide separate outlets for each time period
Max.outlet('microplastics_2003_raw', location.Microplastics_2003_pieces_m3 || 0.001);
Max.outlet('microplastics_2010_raw', location.Microplastics_2010_pieces_m3 || 0.003);
Max.outlet('microplastics_2025_raw', location.Microplastics_2025_pieces_m3 || 0.005);
```

**Technical Process**:
1. Extract all available time periods
2. Apply fallbacks for missing data
3. Output multiple separate values
4. User can access any/all time periods

**Used For**: Microplastics historical analysis, Temperature trends (if requested)

---

### **3. How would you approach sequential time-series?**

**Sequential time-series** plays each location through **temporal evolution** (2003→2010→2025) before moving to the next location.

#### **Current Approach (Spatial Priority)**:
```
Location 1 (2025) → Location 2 (2025) → Location 3 (2025) → ... → Location 500 (2025)
Duration: 20 minutes
Focus: Geographic variation in current ocean health
```

#### **Sequential Approach (Temporal Priority)**:
```
Location 1: 2003 → 2010 → 2025
Location 2: 2003 → 2010 → 2025  
Location 3: 2003 → 2010 → 2025
...
Location 500: 2003 → 2010 → 2025
Duration: 60 minutes (3× longer)
Focus: Climate change evolution at each location
```

#### **Technical Implementation**:

```javascript
// Sequential playback logic
let currentLocationIndex = 0;
let currentTimePeriod = 0; // 0=2003, 1=2010, 2=2025

function playNextTimeSlice() {
    const location = oceanData[currentLocationIndex];
    const timePeriods = ['2003', '2010', '2025'];
    const currentPeriod = timePeriods[currentTimePeriod];
    
    // Output data for current time slice
    Max.outlet('temperature_raw', location[`SST_${currentPeriod}_C`]);
    Max.outlet('microplastics_raw', location[`Microplastics_${currentPeriod}_pieces_m3`]);
    Max.outlet('year_indicator', currentPeriod);
    Max.outlet('temporal_progress', currentTimePeriod / 2); // 0, 0.5, 1
    
    // Advance to next time period
    currentTimePeriod++;
    
    // If completed all periods for this location, move to next location
    if (currentTimePeriod >= 3) {
        currentLocationIndex++;
        currentTimePeriod = 0;
    }
}

// Timer: every 4 seconds = 4s × 3 periods = 12s per location
setInterval(playNextTimeSlice, 4000);
```

#### **Sequential Implementation Options**:

**A. Full Sequential (60 minutes)**:
- 4 seconds per time period
- Clear temporal progression
- Complete climate story

**B. Compressed Sequential (30 minutes)**:
- 2 seconds per time period  
- Rapid temporal evolution
- Faster pace, same story

**C. Hybrid Approach**:
- 10 locations in current state
- Then 1 location through time
- Alternating spatial/temporal focus

**D. Parallel Streams**:
- 3 audio channels simultaneously
- Channel 1 = all 2003 data
- Channel 2 = all 2010 data  
- Channel 3 = all 2025 data
- 20 minutes, direct comparison

---

## 🎯 **Comparison: Current vs Sequential**

### **Current Approach (Spatial-Temporal Hybrid)**

**Temporal Aggregation Method**:
```javascript
// Single value per parameter using mix of strategies:
temperature_raw = SST_2025_C;                    // Latest value
oxygen_raw = Oxygen_2010_mmol_m3;               // Best period  
health_score = weighted_composite(multiple_periods); // Trend calculation
microplastics_2003_raw = MP_2003;              // Multi-outlet
```

**Advantages**:
- ✅ Current ocean state clearly audible
- ✅ Temporal trends embedded in composite scores
- ✅ 20-minute duration = audience-friendly
- ✅ Geographic patterns prominent
- ✅ Stable real-time performance

**Disadvantages**:
- ❌ Temporal evolution not directly audible
- ❌ Climate change acceleration hidden
- ❌ 22-year story compressed into indices

### **Sequential Approach (Pure Temporal)**

**Temporal Aggregation Method**:
```javascript
// Three values per parameter in sequence:
for (period in ['2003', '2010', '2025']) {
    temperature_raw = location[`SST_${period}_C`];
    // Play for 4 seconds, then advance to next period
}
```

**Advantages**:
- ✅ Climate change directly audible
- ✅ Acceleration/deceleration clear
- ✅ Location-specific temporal stories
- ✅ No data compression - full temporal detail

**Disadvantages**:
- ❌ 60-minute duration = challenging for audiences
- ❌ Geographic patterns less prominent
- ❌ More complex Max/MSP patch requirements

---

## 💡 **Recommendation: Dual-Mode Implementation**

Implement **both approaches** as user-selectable modes:

```javascript
// Mode selection
CONFIG.playbackMode = 'spatial';     // Current approach (20 min)
CONFIG.playbackMode = 'sequential';  // New approach (60 min)
CONFIG.playbackMode = 'hybrid';      // Alternating (40 min)
```

**Benefits**:
- **Exhibitions**: Use spatial mode (general audiences)
- **Research**: Use sequential mode (scientific analysis)  
- **Education**: Use hybrid mode (progressive complexity)

The **current temporal aggregation strategy** is scientifically sound and performance-optimized, while **sequential time-series** would provide direct climate change sonification at the cost of duration and complexity.