/**
 * Ocean Data Sonifier - Unified Edition with Sequential Mode
 * 
 * Reads ocean health CSV data and outputs normalized data streams plus detailed raw components
 * for controlling audio synthesis and visual effects in Max/MSP
 * 
 * DUAL MODE OPERATION:
 * - Mode 0 (Spatial): Current approach - each location uses latest/optimal data (20 minutes)
 * - Mode 1 (Sequential): Temporal cycling - each location plays 2003→2010→2025 (20 minutes)
 * 
 * CORE NORMALIZED OUTLETS (0-1 range for real-time control):
 * - temperature_norm, health_score_norm, acidification_norm, oxygen_norm
 * - marine_life_norm, currents_norm, threat_level_norm, sea_ice_norm, microplastics_norm
 * 
 * CORE RAW DATA OUTLETS (scientific units):
 * - temperature_raw (°C), health_score_raw (0-1), ph_raw (pH), oxygen_raw (mmol/m³)
 * - chlorophyll_raw (mg/m³), current_speed_raw (m/s), threat_level_raw (0-1)
 * - sea_ice_raw (%), microplastics_raw (pieces/m³)
 * 
 * COMPONENT RAW DATA OUTLETS (for detailed analysis):
 * - current_u_raw, current_v_raw (m/s), current_direction_raw (degrees)
 * - nitrate_raw, phosphate_raw, silicate_raw (mmol/m³)
 * - dic_raw, alkalinity_raw (mmol/m³)
 * - marine_life_production_raw (mg/m³/day)
 * - microplastics_2003_raw, microplastics_2010_raw (pieces/m³)
 * 
 * TEMPORAL MODE OUTLETS (sequential mode only):
 * - time_period, time_period_display, temporal_progress, time_progress
 * 
 * LOCATION CONTEXT OUTLETS:
 * - location_name, latitude, longitude, region, ocean_basin, ecosystem_type, climate_zone
 * 
 * Marine Life = Net Primary Productivity (ocean ecosystem productivity)
 * All component parameters preserve full scientific detail for specialized applications
 */

const Max = require('max-api');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
    csvFile: path.join(__dirname, 'ocean_health_data.csv'),
    sampleEvery: 5,          // Read every 5th row (100 total locations)
    intervalMs: 12000,       // 12.0 seconds per location (20 min total)
    playbackSpeed: 1.0,      // Speed multiplier
    avoidZeros: false,       // If true, maps 0 values to small positive numbers for audio synthesis
    sequentialMode: false    // If true, cycles through time periods within each location
};

// Global state
let oceanData = [];
let currentIndex = 0;
let currentTimePeriod = 0; // 0=2003, 1=2010, 2=2025 (sequential mode only)
let playbackTimer = null;
let isPlaying = false;
let totalLocations = 0;

// Time periods configuration for sequential mode
const TIME_PERIODS = [
    {
        name: '2003',
        suffix: '_2003',
        display: '2003 (Baseline)'
    },
    {
        name: '2010', 
        suffix: '_2010',
        display: '2010 (Transition)'
    },
    {
        name: '2025',
        suffix: '_2025', 
        display: '2025 (Current Crisis)'
    }
];

// Data normalization ranges (based on CSV analysis) - can be dynamically updated
let DATA_RANGES = {
    sst: { min: -1.8, max: 31.04 },
    ph: { min: 7.847, max: 8.313 },
    oxygen: { min: 196.6, max: 412.8 },
    chlorophyll: { min: 0.026, max: 5.752 },
    marineLifeProduction: { min: 0, max: 109.442 },
    currentSpeed: { min: 0, max: 1.942 },
    nitrate: { min: 0, max: 29.031 },
    seaIce: { min: 0, max: 1.0 },
    microplastics: { min: 0.0001, max: 0.15 }  // pieces/m³ - plastic pollution indicator
};

/**
 * Validate and update data ranges based on loaded dataset
 */
function validateAndUpdateRanges(data) {
    const ranges = {
        sst: { min: Infinity, max: -Infinity },
        ph: { min: Infinity, max: -Infinity },
        oxygen: { min: Infinity, max: -Infinity },
        chlorophyll: { min: Infinity, max: -Infinity },
        currentSpeed: { min: Infinity, max: -Infinity },
        seaIce: { min: Infinity, max: -Infinity },
        microplastics: { min: Infinity, max: -Infinity }
    };
    
    data.forEach(location => {
        // SST validation
        ['SST_2003_C', 'SST_2010_C', 'SST_2025_C'].forEach(field => {
            if (location[field] !== null && !isNaN(location[field])) {
                ranges.sst.min = Math.min(ranges.sst.min, location[field]);
                ranges.sst.max = Math.max(ranges.sst.max, location[field]);
            }
        });
        
        // pH validation
        if (location.pH_2025 !== null && !isNaN(location.pH_2025)) {
            ranges.ph.min = Math.min(ranges.ph.min, location.pH_2025);
            ranges.ph.max = Math.max(ranges.ph.max, location.pH_2025);
        }
        
        // Oxygen validation
        if (location.Oxygen_2010_mmol_m3 !== null && !isNaN(location.Oxygen_2010_mmol_m3)) {
            ranges.oxygen.min = Math.min(ranges.oxygen.min, location.Oxygen_2010_mmol_m3);
            ranges.oxygen.max = Math.max(ranges.oxygen.max, location.Oxygen_2010_mmol_m3);
        }
        
        // Chlorophyll validation
        if (location.Chlorophyll_2010_mg_m3 !== null && !isNaN(location.Chlorophyll_2010_mg_m3)) {
            ranges.chlorophyll.min = Math.min(ranges.chlorophyll.min, location.Chlorophyll_2010_mg_m3);
            ranges.chlorophyll.max = Math.max(ranges.chlorophyll.max, location.Chlorophyll_2010_mg_m3);
        }
        
        // Current speed validation
        if (location.Current_Speed_2025_m_s !== null && !isNaN(location.Current_Speed_2025_m_s)) {
            ranges.currentSpeed.min = Math.min(ranges.currentSpeed.min, location.Current_Speed_2025_m_s);
            ranges.currentSpeed.max = Math.max(ranges.currentSpeed.max, location.Current_Speed_2025_m_s);
        }
        
        // Sea ice validation
        if (location.Sea_Ice_2025_percent !== null && !isNaN(location.Sea_Ice_2025_percent)) {
            ranges.seaIce.min = Math.min(ranges.seaIce.min, location.Sea_Ice_2025_percent);
            ranges.seaIce.max = Math.max(ranges.seaIce.max, location.Sea_Ice_2025_percent);
        }
        
        // Microplastics validation
        ['Microplastics_2003_pieces_m3', 'Microplastics_2010_pieces_m3', 'Microplastics_2025_pieces_m3'].forEach(field => {
            if (location[field] !== null && !isNaN(location[field])) {
                ranges.microplastics.min = Math.min(ranges.microplastics.min, location[field]);
                ranges.microplastics.max = Math.max(ranges.microplastics.max, location[field]);
            }
        });
    });
    
    // Update global ranges with validated data, keeping existing ranges as fallback
    Object.keys(ranges).forEach(key => {
        if (ranges[key].min !== Infinity && ranges[key].max !== -Infinity) {
            DATA_RANGES[key] = ranges[key];
        }
    });
    
    Max.post('Data ranges validated and updated:');
    Max.post(JSON.stringify(DATA_RANGES, null, 2));
}

/**
 * Normalize value to 0-1 range with improved null handling
 */
function normalize(value, min, max, fallback = 0.5) {
    if (value === null || value === undefined || isNaN(value) || value === '') {
        return fallback;
    }
    return Math.max(0, Math.min(1, (value - min) / (max - min)));
}

/**
 * Apply zero-avoidance if configured (useful for audio synthesis)
 */
function applyZeroAvoidance(value, minValue = 0.001) {
    if (!CONFIG.avoidZeros) {
        return value;
    }
    return value === 0 ? minValue : value;
}

/**
 * Parse CSV data into structured format
 */
function parseCSVLine(line, headers) {
    const values = line.split(',');
    const data = {};
    
    headers.forEach((header, index) => {
        const value = values[index];
        if (value === '' || value === 'undefined' || value === 'null') {
            data[header] = null;
        } else if (!isNaN(value) && value !== '') {
            data[header] = parseFloat(value);
        } else {
            data[header] = value;
        }
    });
    
    return data;
}

/**
 * Get value for specific time period with fallback logic (sequential mode)
 */
function getTemporalValue(location, baseField, timePeriod, fallback) {
    const fieldName = baseField + TIME_PERIODS[timePeriod].suffix;
    const value = location[fieldName];
    
    if (value !== null && value !== undefined && !isNaN(value)) {
        return value;
    }
    
    // Try other time periods if current one missing
    for (let i = 0; i < TIME_PERIODS.length; i++) {
        if (i !== timePeriod) {
            const altFieldName = baseField + TIME_PERIODS[i].suffix;
            const altValue = location[altFieldName];
            if (altValue !== null && altValue !== undefined && !isNaN(altValue)) {
                return altValue;
            }
        }
    }
    
    return fallback;
}

/**
 * Calculate composite ocean health score with weighted factors
 */
function calculateHealthScore(location, timePeriod = null) {
    let healthFactors = [];
    let weights = [];
    
    // Get temperature based on mode
    let tempValue;
    if (CONFIG.sequentialMode && timePeriod !== null) {
        tempValue = getTemporalValue(location, 'SST', timePeriod, 15.0);
    } else {
        tempValue = location.SST_2025_C !== null ? location.SST_2025_C : 15.0;
    }
    
    // Temperature health (cooler is healthier in current climate) - Weight: 0.3
    const tempScore = 1 - normalize(tempValue, DATA_RANGES.sst.min, 25, 0.5); // 25°C as danger threshold
    healthFactors.push(tempScore);
    weights.push(0.3);
    
    // pH health (higher pH is healthier) - Weight: 0.25
    if (location.pH_2025 !== null) {
        const phScore = normalize(location.pH_2025, DATA_RANGES.ph.min, DATA_RANGES.ph.max, 0.5);
        healthFactors.push(phScore);
        weights.push(0.25);
    }
    
    // Oxygen health (higher oxygen is healthier) - Weight: 0.25
    let oxygenValue;
    if (CONFIG.sequentialMode && timePeriod !== null && timePeriod < 2) {
        oxygenValue = getTemporalValue(location, 'Oxygen', timePeriod, 270);
    } else {
        oxygenValue = location.Oxygen_2010_mmol_m3 !== null ? location.Oxygen_2010_mmol_m3 : 270;
    }
    const oxygenScore = normalize(oxygenValue, DATA_RANGES.oxygen.min, DATA_RANGES.oxygen.max, 0.5);
    healthFactors.push(oxygenScore);
    weights.push(0.25);
    
    // Marine productivity health - Weight: 0.1
    let chlorophyllValue;
    if (CONFIG.sequentialMode && timePeriod !== null && timePeriod < 2) {
        chlorophyllValue = getTemporalValue(location, 'Chlorophyll', timePeriod, 0.3);
    } else {
        chlorophyllValue = location.Chlorophyll_2010_mg_m3 !== null ? location.Chlorophyll_2010_mg_m3 : 0.3;
    }
    const productivityScore = normalize(chlorophyllValue, DATA_RANGES.chlorophyll.min, DATA_RANGES.chlorophyll.max, 0.5);
    healthFactors.push(productivityScore);
    weights.push(0.1);
    
    // Current health (moderate currents are healthier than stagnant) - Weight: 0.1
    if (location.Current_Speed_2025_m_s !== null) {
        const optimalSpeed = 0.5; // m/s
        const currentScore = 1 - Math.abs(location.Current_Speed_2025_m_s - optimalSpeed) / optimalSpeed;
        healthFactors.push(Math.max(0, Math.min(1, currentScore)));
        weights.push(0.1);
    }
    
    // Microplastics health (lower concentration is healthier) - Weight: 0.1
    let microplasticsValue;
    if (CONFIG.sequentialMode && timePeriod !== null) {
        microplasticsValue = getTemporalValue(location, 'Microplastics', timePeriod, 0.005);
    } else {
        microplasticsValue = location.Microplastics_2025_pieces_m3 !== null ? location.Microplastics_2025_pieces_m3 : 0.005;
    }
    const microplasticsScore = 1 - normalize(microplasticsValue, DATA_RANGES.microplastics.min, DATA_RANGES.microplastics.max, 0.5);
    healthFactors.push(microplasticsScore);
    weights.push(0.1);
    
    // Calculate weighted average
    if (healthFactors.length > 0) {
        const totalWeight = weights.reduce((a, b) => a + b, 0);
        const weightedSum = healthFactors.reduce((sum, factor, index) => sum + factor * weights[index], 0);
        return weightedSum / totalWeight;
    }
    
    return 0.5;
}

/**
 * Calculate threat level with multiple weighted indicators
 */
function calculateThreatLevel(location, timePeriod = null) {
    let threatFactors = [];
    let weights = [];
    
    // Temperature warming trend - Weight: 0.35
    if (location.SST_2003_C !== null && location.SST_2025_C !== null) {
        const warming = location.SST_2025_C - location.SST_2003_C;
        const warmingThreat = normalize(warming, -2, 5, 0.3); // -2°C to +5°C range
        threatFactors.push(warmingThreat);
        weights.push(0.35);
    }
    
    // Acidification threat (lower pH = higher threat) - Weight: 0.25
    if (location.pH_2025 !== null) {
        const acidThreat = 1 - normalize(location.pH_2025, DATA_RANGES.ph.min, DATA_RANGES.ph.max, 0.5);
        threatFactors.push(acidThreat);
        weights.push(0.25);
    }
    
    // Oxygen depletion threat - Weight: 0.25
    let oxygenValue;
    if (CONFIG.sequentialMode && timePeriod !== null && timePeriod < 2) {
        oxygenValue = getTemporalValue(location, 'Oxygen', timePeriod, 270);
    } else {
        oxygenValue = location.Oxygen_2010_mmol_m3 !== null ? location.Oxygen_2010_mmol_m3 : 270;
    }
    const oxygenThreat = 1 - normalize(oxygenValue, DATA_RANGES.oxygen.min, DATA_RANGES.oxygen.max, 0.5);
    threatFactors.push(oxygenThreat);
    weights.push(0.25);
    
    // Extreme temperature threat - Weight: 0.1
    let tempValue;
    if (CONFIG.sequentialMode && timePeriod !== null) {
        tempValue = getTemporalValue(location, 'SST', timePeriod, 15.0);
    } else {
        tempValue = location.SST_2025_C !== null ? location.SST_2025_C : 15.0;
    }
    const tempThreat = normalize(tempValue, 20, DATA_RANGES.sst.max, 0.2); // 20°C as baseline
    threatFactors.push(tempThreat);
    weights.push(0.1);
    
    // Microplastics pollution threat - Weight: 0.05
    let microplasticsValue;
    if (CONFIG.sequentialMode && timePeriod !== null) {
        microplasticsValue = getTemporalValue(location, 'Microplastics', timePeriod, 0.005);
    } else {
        microplasticsValue = location.Microplastics_2025_pieces_m3 !== null ? location.Microplastics_2025_pieces_m3 : 0.005;
    }
    const pollutionThreat = normalize(microplasticsValue, DATA_RANGES.microplastics.min, DATA_RANGES.microplastics.max, 0.2);
    threatFactors.push(pollutionThreat);
    weights.push(0.05);
    
    // Calculate weighted average
    if (threatFactors.length > 0) {
        const totalWeight = weights.reduce((a, b) => a + b, 0);
        const weightedSum = threatFactors.reduce((sum, factor, index) => sum + factor * weights[index], 0);
        return weightedSum / totalWeight;
    }
    
    return 0.5;
}

/**
 * Load and parse CSV data with enhanced error handling
 */
async function loadData() {
    try {
        Max.post('Loading ocean data from:', CONFIG.csvFile);
        
        if (!fs.existsSync(CONFIG.csvFile)) {
            throw new Error(`CSV file not found: ${CONFIG.csvFile}`);
        }
        
        const csvContent = fs.readFileSync(CONFIG.csvFile, 'utf8');
        if (!csvContent || csvContent.trim().length === 0) {
            throw new Error('CSV file is empty or unreadable');
        }
        
        const lines = csvContent.trim().split('\n');
        if (lines.length < 2) {
            throw new Error('CSV file must contain at least a header and one data row');
        }
        
        const headers = lines[0].split(',');
        if (headers.length === 0) {
            throw new Error('CSV file has no valid headers');
        }
        
        Max.post(`CSV headers found: ${headers.length} columns`);
        
        oceanData = [];
        let validRows = 0;
        let skippedRows = 0;
        
        // Sample every Nth row as configured
        for (let i = 1; i < lines.length; i += CONFIG.sampleEvery) {
            if (lines[i] && lines[i].trim().length > 0) {
                try {
                    const location = parseCSVLine(lines[i], headers);
                    
                    // Basic validation - require at least coordinates
                    if (location.Latitude !== null && location.Longitude !== null) {
                        oceanData.push(location);
                        validRows++;
                    } else {
                        skippedRows++;
                        Max.post(`Skipped row ${i}: missing coordinates`);
                    }
                } catch (parseError) {
                    skippedRows++;
                    Max.post(`Error parsing row ${i}: ${parseError.message}`);
                }
            }
        }
        
        if (oceanData.length === 0) {
            throw new Error('No valid data rows found after parsing');
        }
        
        totalLocations = oceanData.length;
        
        // Validate and update data ranges based on loaded data
        validateAndUpdateRanges(oceanData);
        
        Max.post(`Successfully loaded ${totalLocations} ocean locations (${validRows} valid, ${skippedRows} skipped)`);
        Max.post(`Sampling: every ${CONFIG.sampleEvery} rows from ${lines.length - 1} total data rows`);
        Max.post(`Mode: ${CONFIG.sequentialMode ? 'Sequential (temporal)' : 'Spatial (current state)'}`);
        Max.outlet('status', 'loaded');
        Max.outlet('total_locations', totalLocations);
        Max.outlet('valid_rows', validRows);
        Max.outlet('skipped_rows', skippedRows);
        Max.outlet('sequential_mode', CONFIG.sequentialMode ? 1 : 0);
        
    } catch (error) {
        Max.post('Error loading data:', error.message);
        Max.outlet('error', 'load_failed');
        Max.outlet('error_message', error.message);
        
        // Reset state on error
        oceanData = [];
        totalLocations = 0;
    }
}

/**
 * Play next location data with error handling
 */
function playNext() {
    try {
        if (currentIndex >= oceanData.length) {
            stopPlayback();
            Max.outlet('status', 'completed');
            return;
        }
        
        const location = oceanData[currentIndex];
        if (!location) {
            Max.post(`Warning: No data at index ${currentIndex}, skipping`);
            currentIndex++;
            return;
        }
        
        // Send essential location data for Max patch display
        const locationName = location.Location_Name || `Location_${currentIndex + 1}`;
        const locationId = location.Location_ID || currentIndex + 1;
        const latitude = location.Latitude || 0;
        const longitude = location.Longitude || 0;
        const region = location.Region || 'Unknown';
        const oceanBasin = location.Ocean_Basin || 'Unknown';
        const ecosystemType = location.Ecosystem_Type || 'Unknown';
        const climateZone = location.Climate_Zone || 'Unknown';
        
        // Output location data as individual outlets
        Max.outlet('location_name', locationName);
        Max.outlet('location_id', locationId);
        Max.outlet('latitude', latitude);
        Max.outlet('longitude', longitude);
        Max.outlet('region', region);
        Max.outlet('ocean_basin', oceanBasin);
        Max.outlet('ecosystem_type', ecosystemType);
        Max.outlet('climate_zone', climateZone);
        
        // Mode-specific data extraction
        let modeData;
        if (CONFIG.sequentialMode) {
            // Sequential mode: use specific time period
            const periodInfo = TIME_PERIODS[currentTimePeriod];
            Max.outlet('time_period', periodInfo.name);
            Max.outlet('time_period_display', periodInfo.display);
            Max.outlet('temporal_progress', currentTimePeriod / (TIME_PERIODS.length - 1)); // 0, 0.5, 1
            
            modeData = {
                temperature: getTemporalValue(location, 'SST', currentTimePeriod, 15.0),
                microplastics: getTemporalValue(location, 'Microplastics', currentTimePeriod, 0.005),
                seaIce: getTemporalValue(location, 'Sea_Ice', currentTimePeriod, 0.0),
                ph: currentTimePeriod === 2 ? (location.pH_2025 || 8.1) : 8.1, // pH only in 2025
                chlorophyll: currentTimePeriod < 2 ? getTemporalValue(location, 'Chlorophyll', currentTimePeriod, 0.3) : 0.3,
                oxygen: currentTimePeriod < 2 ? getTemporalValue(location, 'Oxygen', currentTimePeriod, 270) : 270,
                nitrate: currentTimePeriod < 2 ? getTemporalValue(location, 'Nitrate', currentTimePeriod, 5.0) : 5.0,
                marineProduction: currentTimePeriod < 2 ? getTemporalValue(location, 'Marine_Life_Production', currentTimePeriod, 5.0) : 5.0,
                currentSpeed: currentTimePeriod === 2 ? (location.Current_Speed_2025_m_s || 0.1) : 0.1,
                currentU: currentTimePeriod === 2 ? (location.Current_U_2025_m_s || 0.0) : 0.0,
                currentV: currentTimePeriod === 2 ? (location.Current_V_2025_m_s || 0.0) : 0.0
            };
        } else {
            // Spatial mode: use latest/optimal data (existing approach)
            modeData = {
                temperature: location.SST_2025_C !== null ? location.SST_2025_C : 15.0,
                microplastics: location.Microplastics_2025_pieces_m3 !== null ? location.Microplastics_2025_pieces_m3 : 0.005,
                seaIce: location.Sea_Ice_2025_percent !== null ? location.Sea_Ice_2025_percent : 0.0,
                ph: location.pH_2025 !== null ? location.pH_2025 : 8.1,
                chlorophyll: location.Chlorophyll_2010_mg_m3 !== null ? location.Chlorophyll_2010_mg_m3 : 0.3,
                oxygen: location.Oxygen_2010_mmol_m3 !== null ? location.Oxygen_2010_mmol_m3 : 270,
                nitrate: location.Nitrate_2010_mmol_m3 !== null ? location.Nitrate_2010_mmol_m3 : 5.0,
                marineProduction: location.Marine_Life_Production_2010_mg_m3_day !== null ? location.Marine_Life_Production_2010_mg_m3_day : 5.0,
                currentSpeed: location.Current_Speed_2025_m_s !== null ? location.Current_Speed_2025_m_s : 0.1,
                currentU: location.Current_U_2025_m_s !== null ? location.Current_U_2025_m_s : 0.0,
                currentV: location.Current_V_2025_m_s !== null ? location.Current_V_2025_m_s : 0.0
            };
        }
        
        // Calculate health and threat scores based on current mode
        const healthScore = calculateHealthScore(location, CONFIG.sequentialMode ? currentTimePeriod : null);
        const threatLevel = calculateThreatLevel(location, CONFIG.sequentialMode ? currentTimePeriod : null);
        
        // Calculate normalized values for sliders (0-1 range)
        const sliderValues = [
            normalize(modeData.temperature, DATA_RANGES.sst.min, DATA_RANGES.sst.max, 0.5),        // Temperature
            healthScore,                                                                            // Health score
            modeData.ph ? 1 - normalize(modeData.ph, DATA_RANGES.ph.min, DATA_RANGES.ph.max, 0.5) : 0.5, // Acidification (inverted)
            normalize(modeData.oxygen, DATA_RANGES.oxygen.min, DATA_RANGES.oxygen.max, 0.5),       // Oxygen
            (normalize(modeData.chlorophyll, DATA_RANGES.chlorophyll.min, DATA_RANGES.chlorophyll.max, 0.5) + 
             normalize(modeData.marineProduction, DATA_RANGES.marineLifeProduction.min, DATA_RANGES.marineLifeProduction.max, 0.5)) / 2, // Marine life
            normalize(modeData.currentSpeed, DATA_RANGES.currentSpeed.min, DATA_RANGES.currentSpeed.max, 0.5), // Currents
            threatLevel,                                                                            // Threat level
            modeData.seaIce !== null ? normalize(modeData.seaIce, 0, 1, 0) : 0,                   // Sea ice (0 for non-Arctic)
            normalize(modeData.microplastics, DATA_RANGES.microplastics.min, DATA_RANGES.microplastics.max, 0.1) // Microplastics pollution
        ];
        
        // Output normalized slider values with meaningful names (0-1 range)
        const temperatureNorm = isNaN(sliderValues[0]) ? 0.5 : Math.max(0, Math.min(1, sliderValues[0]));
        const healthScoreNorm = isNaN(sliderValues[1]) ? 0.5 : Math.max(0, Math.min(1, sliderValues[1]));
        const acidificationNorm = isNaN(sliderValues[2]) ? 0.5 : Math.max(0, Math.min(1, sliderValues[2]));
        const oxygenNorm = isNaN(sliderValues[3]) ? 0.5 : Math.max(0, Math.min(1, sliderValues[3]));
        const marineLifeNorm = isNaN(sliderValues[4]) ? 0.5 : Math.max(0, Math.min(1, sliderValues[4]));
        const currentsNorm = isNaN(sliderValues[5]) ? 0.5 : Math.max(0, Math.min(1, sliderValues[5]));
        const threatLevelNorm = isNaN(sliderValues[6]) ? 0.5 : Math.max(0, Math.min(1, sliderValues[6]));
        const seaIceNorm = isNaN(sliderValues[7]) ? 0.5 : Math.max(0, Math.min(1, sliderValues[7]));
        const microplasticsNorm = isNaN(sliderValues[8]) ? 0.1 : Math.max(0, Math.min(1, sliderValues[8]));
        
        Max.outlet('temperature_norm', temperatureNorm);
        Max.outlet('health_score_norm', healthScoreNorm);
        Max.outlet('acidification_norm', acidificationNorm);
        Max.outlet('oxygen_norm', oxygenNorm);
        Max.outlet('marine_life_norm', marineLifeNorm);
        Max.outlet('currents_norm', currentsNorm);
        Max.outlet('threat_level_norm', threatLevelNorm);
        Max.outlet('sea_ice_norm', seaIceNorm);
        Max.outlet('microplastics_norm', microplasticsNorm);
        
        // Output raw values with meaningful names (realistic fallbacks + optional zero avoidance)
        const temperatureRaw = applyZeroAvoidance(modeData.temperature);
        const healthScoreRaw = applyZeroAvoidance(healthScore, 0.01); // Neutral health (min 1%)
        const phRaw = modeData.ph;                                     // Pre-industrial baseline (pH never 0)
        const oxygenRaw = applyZeroAvoidance(modeData.oxygen, 50);     // Typical surface oxygen (min 50)
        const chlorophyllRaw = applyZeroAvoidance(modeData.chlorophyll, 0.01); // Oligotrophic average (min 0.01)
        const currentSpeedRaw = applyZeroAvoidance(modeData.currentSpeed, 0.001); // Typical current (min 0.001 m/s)
        const threatLevelRaw = applyZeroAvoidance(threatLevel, 0.01);   // Moderate threat (min 1%)
        const seaIceRaw = applyZeroAvoidance(modeData.seaIce, 0.001);   // Sea ice (min 0.1% if avoiding zeros)
        const microplasticsRaw = applyZeroAvoidance(modeData.microplastics, 0.0001); // Microplastics (min 0.0001 pieces/m³)
        
        Max.outlet('temperature_raw', temperatureRaw);
        Max.outlet('health_score_raw', healthScoreRaw);
        Max.outlet('ph_raw', phRaw);
        Max.outlet('oxygen_raw', oxygenRaw);
        Max.outlet('chlorophyll_raw', chlorophyllRaw);
        Max.outlet('current_speed_raw', currentSpeedRaw);
        Max.outlet('threat_level_raw', threatLevelRaw);
        Max.outlet('sea_ice_raw', seaIceRaw);
        Max.outlet('microplastics_raw', microplasticsRaw);
        
        // Additional raw component parameters for detailed analysis
        const componentParameters = {
            // Current vector components
            current_u: modeData.currentU,
            current_v: modeData.currentV,
            current_direction: location.Current_Direction_2025_deg !== null ? location.Current_Direction_2025_deg : 0.0,
            
            // Detailed ocean chemistry (2010 data for nutrients, 2025 for carbon)
            nitrate_2010: modeData.nitrate,
            phosphate_2010: location.Phosphate_2010_mmol_m3 !== null ? location.Phosphate_2010_mmol_m3 : 0.5,
            silicate_2010: location.Silicate_2010_mmol_m3 !== null ? location.Silicate_2010_mmol_m3 : 10.0,
            
            // Carbon chemistry (2025 data)
            dic_2025: location.DIC_2025_mmol_m3 !== null ? location.DIC_2025_mmol_m3 : 2100.0,
            alkalinity_2025: location.Alkalinity_2025_mmol_m3 !== null ? location.Alkalinity_2025_mmol_m3 : 2300.0,
            
            // Marine productivity components
            marine_life_production: modeData.marineProduction,
            
            // Historical microplastics for trend analysis
            microplastics_2003: location.Microplastics_2003_pieces_m3 !== null ? location.Microplastics_2003_pieces_m3 : 0.001,
            microplastics_2010: location.Microplastics_2010_pieces_m3 !== null ? location.Microplastics_2010_pieces_m3 : 0.003
        };
        
        // Output component parameters for detailed analysis
        Max.outlet('current_u_raw', applyZeroAvoidance(componentParameters.current_u, 0.001));
        Max.outlet('current_v_raw', applyZeroAvoidance(componentParameters.current_v, 0.001));
        Max.outlet('current_direction_raw', componentParameters.current_direction);
        
        // Output detailed chemistry parameters
        Max.outlet('nitrate_raw', applyZeroAvoidance(componentParameters.nitrate_2010, 0.1));
        Max.outlet('phosphate_raw', applyZeroAvoidance(componentParameters.phosphate_2010, 0.01));
        Max.outlet('silicate_raw', applyZeroAvoidance(componentParameters.silicate_2010, 0.5));
        Max.outlet('dic_raw', componentParameters.dic_2025);
        Max.outlet('alkalinity_raw', componentParameters.alkalinity_2025);
        
        // Output marine productivity component
        Max.outlet('marine_life_production_raw', applyZeroAvoidance(componentParameters.marine_life_production, 0.1));
        
        // Output historical microplastics for trend analysis
        Max.outlet('microplastics_2003_raw', applyZeroAvoidance(componentParameters.microplastics_2003, 0.0001));
        Max.outlet('microplastics_2010_raw', applyZeroAvoidance(componentParameters.microplastics_2010, 0.0001));
        
        // Calculate and output derived parameters for analysis
        const derivedParameters = {
            // Current analysis
            current_magnitude: Math.sqrt(componentParameters.current_u * componentParameters.current_u + 
                                       componentParameters.current_v * componentParameters.current_v),
            
            // Nutrient ratios (Redfield ratios for ecosystem analysis)
            n_p_ratio: componentParameters.nitrate_2010 / Math.max(componentParameters.phosphate_2010, 0.001),
            
            // Microplastics trend (pollution acceleration)
            microplastics_trend: componentParameters.microplastics_2010 > 0 ? 
                               (microplasticsRaw / componentParameters.microplastics_2003) : 1.0,
            
            // Carbonate chemistry (ocean acidification indicator)
            carbonate_saturation: componentParameters.alkalinity_2025 - componentParameters.dic_2025
        };
        
        // Output derived analysis parameters
        Max.outlet('current_magnitude_raw', derivedParameters.current_magnitude);
        Max.outlet('n_p_ratio_raw', Math.min(derivedParameters.n_p_ratio, 50)); // Cap at 50:1
        Max.outlet('microplastics_trend_raw', Math.min(derivedParameters.microplastics_trend, 10)); // Cap at 10x increase
        Max.outlet('carbonate_saturation_raw', derivedParameters.carbonate_saturation);
        
        // Output temporal trends in sequential mode
        if (CONFIG.sequentialMode && currentTimePeriod === 2) { // At 2025, show full trends
            const temp2003 = location.SST_2003_C;
            const temp2025 = location.SST_2025_C;
            const mp2003 = location.Microplastics_2003_pieces_m3;
            const mp2025 = location.Microplastics_2025_pieces_m3;
            
            if (temp2003 && temp2025) {
                const warming = temp2025 - temp2003;
                Max.outlet('warming_trend_raw', warming);
            }
            
            if (mp2003 && mp2025 && mp2003 > 0) {
                const pollution_increase = mp2025 / mp2003;
                Max.outlet('pollution_acceleration_raw', Math.min(pollution_increase, 10));
            }
        }
        
        // Send progress info
        let progress;
        if (CONFIG.sequentialMode) {
            const totalTimeSlices = totalLocations * TIME_PERIODS.length;
            const currentTimeSlice = currentIndex * TIME_PERIODS.length + currentTimePeriod;
            progress = currentTimeSlice / totalTimeSlices;
            Max.outlet('time_progress', currentTimePeriod / (TIME_PERIODS.length - 1));
        } else {
            progress = (currentIndex + 1) / totalLocations;
        }
        
        Max.outlet('progress', progress);
        Max.outlet('current_index', currentIndex + 1);
        Max.outlet('total_locations', totalLocations);
        
        const modeStr = CONFIG.sequentialMode ? `${TIME_PERIODS[currentTimePeriod].display}` : 'Current State';
        Max.post(`Playing location ${currentIndex + 1}/${totalLocations}: ${locationName} (${modeStr})`);
        
        // Advance indices based on mode
        if (CONFIG.sequentialMode) {
            // Sequential mode: advance time period first
            currentTimePeriod++;
            if (currentTimePeriod >= TIME_PERIODS.length) {
                currentIndex++;
                currentTimePeriod = 0;
            }
        } else {
            // Spatial mode: advance location
            currentIndex++;
        }
        
    } catch (error) {
        Max.post(`Error playing location ${currentIndex + 1}: ${error.message}`);
        Max.outlet('error', 'playback_error');
        Max.outlet('error_location', currentIndex + 1);
        Max.outlet('error_message', error.message);
        
        // Skip to next location on error
        currentIndex++;
        if (CONFIG.sequentialMode) {
            currentTimePeriod = 0;
        }
        if (currentIndex < oceanData.length) {
            setTimeout(playNext, 100); // Brief delay before retry
        } else {
            stopPlayback();
        }
    }
}

/**
 * Start playback
 */
function startPlayback() {
    if (oceanData.length === 0) {
        Max.post('No data loaded. Please load data first.');
        return;
    }
    
    if (isPlaying) {
        return;
    }
    
    isPlaying = true;
    
    // Calculate interval based on mode
    let intervalMs;
    if (CONFIG.sequentialMode) {
        // Sequential mode: 20 minutes / (100 locations × 3 time periods) = 4 seconds per time slice
        intervalMs = (CONFIG.intervalMs / TIME_PERIODS.length) / CONFIG.playbackSpeed;
    } else {
        // Spatial mode: 20 minutes / 100 locations = 12 seconds per location
        intervalMs = CONFIG.intervalMs / CONFIG.playbackSpeed;
    }
    
    const modeDesc = CONFIG.sequentialMode ? 'Sequential (temporal cycling)' : 'Spatial (current state)';
    Max.post(`Starting playback: ${totalLocations} locations, ${intervalMs}ms intervals, ${modeDesc}`);
    Max.outlet('status', 'playing');
    Max.outlet('playback_mode', CONFIG.sequentialMode ? 'sequential_temporal' : 'spatial_current');
    
    // Play first location immediately
    playNext();
    
    // Set up timer for subsequent locations
    playbackTimer = setInterval(() => {
        playNext();
    }, intervalMs);
}

/**
 * Stop playback
 */
function stopPlayback() {
    if (playbackTimer) {
        clearInterval(playbackTimer);
        playbackTimer = null;
    }
    isPlaying = false;
    Max.post('Playback stopped');
    Max.outlet('status', 'stopped');
}

/**
 * Pause/resume playback
 */
function pausePlayback() {
    if (isPlaying) {
        stopPlayback();
        Max.outlet('status', 'paused');
    } else {
        startPlayback();
    }
}

/**
 * Reset to beginning
 */
function resetPlayback() {
    stopPlayback();
    currentIndex = 0;
    currentTimePeriod = 0;
    Max.post('Reset to beginning');
    Max.outlet('status', 'reset');
}

/**
 * Set playback speed
 */
function setSpeed(speed) {
    CONFIG.playbackSpeed = Math.max(0.1, Math.min(5.0, speed));
    Max.post(`Playback speed set to ${CONFIG.playbackSpeed}x`);
    
    // Restart timer if playing
    if (isPlaying) {
        stopPlayback();
        startPlayback();
    }
}

/**
 * Jump to specific location
 */
function jumpToLocation(index) {
    if (index >= 0 && index < totalLocations) {
        currentIndex = index;
        currentTimePeriod = 0; // Reset time period when jumping
        Max.post(`Jumped to location ${index + 1}`);
        
        if (isPlaying) {
            playNext();
        }
    }
}

/**
 * Set zero avoidance mode
 */
function setZeroAvoidance(avoid) {
    CONFIG.avoidZeros = avoid ? true : false;
    Max.post(`Zero avoidance ${CONFIG.avoidZeros ? 'enabled' : 'disabled'}`);
    Max.outlet('zero_avoidance', CONFIG.avoidZeros ? 1 : 0);
}

/**
 * Set sequential mode (0 = spatial, 1 = sequential)
 */
function setSequentialMode(mode) {
    const wasPlaying = isPlaying;
    if (wasPlaying) {
        stopPlayback();
    }
    
    CONFIG.sequentialMode = mode ? true : false;
    currentTimePeriod = 0; // Reset time period when changing modes
    
    const modeStr = CONFIG.sequentialMode ? 'Sequential (temporal cycling)' : 'Spatial (current state)';
    Max.post(`Sonification mode set to: ${modeStr}`);
    Max.outlet('sequential_mode', CONFIG.sequentialMode ? 1 : 0);
    
    if (wasPlaying) {
        startPlayback();
    }
}

/**
 * Get current data statistics
 */
function getStats() {
    const stats = {
        totalLocations: totalLocations,
        currentIndex: currentIndex,
        currentTimePeriod: currentTimePeriod,
        isPlaying: isPlaying,
        sequentialMode: CONFIG.sequentialMode,
        dataRanges: DATA_RANGES,
        config: CONFIG
    };
    
    Max.outlet('stats_total_locations', stats.totalLocations);
    Max.outlet('stats_current_index', stats.currentIndex);
    Max.outlet('stats_current_time_period', stats.currentTimePeriod);
    Max.outlet('stats_is_playing', stats.isPlaying ? 1 : 0);
    Max.outlet('sequential_mode', CONFIG.sequentialMode ? 1 : 0);
    Max.outlet('zero_avoidance', CONFIG.avoidZeros ? 1 : 0);
    Max.post('Current statistics:', JSON.stringify(stats, null, 2));
    return stats;
}

// Max API handlers
Max.addHandler('loadData', loadData);
Max.addHandler('start', startPlayback);
Max.addHandler('stop', stopPlayback);
Max.addHandler('pause', pausePlayback);
Max.addHandler('reset', resetPlayback);
Max.addHandler('speed', setSpeed);
Max.addHandler('jump', jumpToLocation);
Max.addHandler('stats', getStats);
Max.addHandler('avoidZeros', setZeroAvoidance);
Max.addHandler('sequential', setSequentialMode);  // NEW: 0/1 to toggle sequential mode

// Initialize
Max.post('Ocean Data Sonifier - Unified Edition v2.5:');
Max.post('- DUAL MODE: Send "sequential 0" for spatial mode, "sequential 1" for temporal mode');
Max.post('- SPATIAL MODE (0): Current state approach (20 minutes, each location uses latest/optimal data)');
Max.post('- SEQUENTIAL MODE (1): Temporal cycling (20 minutes, each location cycles 2003→2010→2025)');
Max.post('- 9 Core Normalized Outlets: temperature, health, acidification, oxygen, marine_life, currents, threat, sea_ice, microplastics');
Max.post('- Core Raw Data: temperature_raw, health_score_raw, ph_raw, oxygen_raw, chlorophyll_raw, current_speed_raw, threat_level_raw, sea_ice_raw, microplastics_raw');
Max.post('- Component Raw Data: current_u_raw, current_v_raw, current_direction_raw');
Max.post('- Chemistry Raw Data: nitrate_raw, phosphate_raw, silicate_raw, dic_raw, alkalinity_raw');
Max.post('- Productivity Raw Data: marine_life_production_raw');
Max.post('- Historical Raw Data: microplastics_2003_raw, microplastics_2010_raw');
Max.post('- Sequential Mode Outlets: time_period, time_period_display, temporal_progress, time_progress');
Max.post('- Scientific Units: °C, %, pH, mmol/m³, mg/m³/day, m/s, degrees, pieces/m³');
Max.post('- Location data: location_name, latitude, longitude, region, ecosystem, climate_zone');
Max.post('- Marine Life = Net Primary Productivity (ocean ecosystem productivity)');
Max.post('Available commands: loadData, start, stop, pause, reset, speed <0.1-5.0>, jump <index>, stats, avoidZeros <0|1>, sequential <0|1>');

// Auto-load data on startup
loadData();