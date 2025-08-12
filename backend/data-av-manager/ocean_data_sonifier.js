/**
 * Ocean Data Sonifier - Node for Max Script
 * 
 * Reads ocean health CSV data and outputs 10 streams of normalized data
 * for controlling audio synthesis and visual effects in Max/MSP
 * 
 * Data flows through 10 outlets:
 * 1. Location metadata (name, region, coordinates)
 * 2. Temporal data (date range, time period info)
 * 3. Spatial context (region, ecosystem, climate zone)
 * 4. Temperature data (SST trends, normalized 0-1)  
 * 5. Ocean health score (composite index 0-1)
 * 6. Acidification level (pH normalized, inverted for danger)
 * 7. Oxygen status (dissolved O2 normalized)
 * 8. Marine life index (chlorophyll + marine life production)
 * 9. Current dynamics (speed + direction)
 * 10. Threat level (crisis indicator 0-1)
 */

const Max = require('max-api');
const fs = require('fs');
const path = require('path');

// Configuration
const CONFIG = {
    csvFile: path.join(__dirname, 'ocean_health_data.csv'),
    sampleEvery: 5,          // Read every 5th row (115 total locations)
    intervalMs: 10400,       // 10.4 seconds per location (20 min total)
    playbackSpeed: 1.0       // Speed multiplier
};

// Global state
let oceanData = [];
let currentIndex = 0;
let playbackTimer = null;
let isPlaying = false;
let totalLocations = 0;

// Data normalization ranges (based on CSV analysis) - can be dynamically updated
let DATA_RANGES = {
    sst: { min: -1.8, max: 31.04 },
    ph: { min: 7.847, max: 8.313 },
    oxygen: { min: 196.6, max: 412.8 },
    chlorophyll: { min: 0.026, max: 5.752 },
    marineLifeProduction: { min: 0, max: 109.442 },
    currentSpeed: { min: 0, max: 1.942 },
    nitrate: { min: 0, max: 29.031 },
    seaIce: { min: 0, max: 1.0 }
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
        seaIce: { min: Infinity, max: -Infinity }
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
 * Calculate composite ocean health score with weighted factors
 */
function calculateHealthScore(location) {
    let healthFactors = [];
    let weights = [];
    
    // Temperature health (cooler is healthier in current climate) - Weight: 0.3
    if (location.SST_2025_C !== null) {
        const tempScore = 1 - normalize(location.SST_2025_C, DATA_RANGES.sst.min, 25, 0.5); // 25°C as danger threshold
        healthFactors.push(tempScore);
        weights.push(0.3);
    }
    
    // pH health (higher pH is healthier) - Weight: 0.25
    if (location.pH_2025 !== null) {
        const phScore = normalize(location.pH_2025, DATA_RANGES.ph.min, DATA_RANGES.ph.max, 0.5);
        healthFactors.push(phScore);
        weights.push(0.25);
    }
    
    // Oxygen health (higher oxygen is healthier) - Weight: 0.25
    if (location.Oxygen_2010_mmol_m3 !== null) {
        const oxygenScore = normalize(location.Oxygen_2010_mmol_m3, DATA_RANGES.oxygen.min, DATA_RANGES.oxygen.max, 0.5);
        healthFactors.push(oxygenScore);
        weights.push(0.25);
    }
    
    // Marine productivity health - Weight: 0.1
    if (location.Chlorophyll_2010_mg_m3 !== null) {
        const productivityScore = normalize(location.Chlorophyll_2010_mg_m3, DATA_RANGES.chlorophyll.min, DATA_RANGES.chlorophyll.max, 0.5);
        healthFactors.push(productivityScore);
        weights.push(0.1);
    }
    
    // Current health (moderate currents are healthier than stagnant) - Weight: 0.1
    if (location.Current_Speed_2025_m_s !== null) {
        const optimalSpeed = 0.5; // m/s
        const currentScore = 1 - Math.abs(location.Current_Speed_2025_m_s - optimalSpeed) / optimalSpeed;
        healthFactors.push(Math.max(0, Math.min(1, currentScore)));
        weights.push(0.1);
    }
    
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
function calculateThreatLevel(location) {
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
    if (location.Oxygen_2010_mmol_m3 !== null) {
        const oxygenThreat = 1 - normalize(location.Oxygen_2010_mmol_m3, DATA_RANGES.oxygen.min, DATA_RANGES.oxygen.max, 0.5);
        threatFactors.push(oxygenThreat);
        weights.push(0.25);
    }
    
    // Extreme temperature threat - Weight: 0.15
    if (location.SST_2025_C !== null) {
        const tempThreat = normalize(location.SST_2025_C, 20, DATA_RANGES.sst.max, 0.2); // 20°C as baseline
        threatFactors.push(tempThreat);
        weights.push(0.15);
    }
    
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
        Max.outlet('status', 'loaded');
        Max.outlet('total_locations', totalLocations);
        Max.outlet('valid_rows', validRows);
        Max.outlet('skipped_rows', skippedRows);
        
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
        
        // Calculate normalized values for sliders (0-1 range)
        const sliderValues = [
            normalize(location.SST_2025_C, DATA_RANGES.sst.min, DATA_RANGES.sst.max, 0.5),        // Temperature
            calculateHealthScore(location),                                                        // Health score
            location.pH_2025 ? 1 - normalize(location.pH_2025, DATA_RANGES.ph.min, DATA_RANGES.ph.max, 0.5) : 0.5, // Acidification (inverted)
            normalize(location.Oxygen_2010_mmol_m3, DATA_RANGES.oxygen.min, DATA_RANGES.oxygen.max, 0.5),     // Oxygen
            (normalize(location.Chlorophyll_2010_mg_m3, DATA_RANGES.chlorophyll.min, DATA_RANGES.chlorophyll.max, 0.5) + 
             normalize(location.Marine_Life_Production_2010_mg_m3_day, DATA_RANGES.marineLifeProduction.min, DATA_RANGES.marineLifeProduction.max, 0.5)) / 2, // Marine life
            normalize(location.Current_Speed_2025_m_s, DATA_RANGES.currentSpeed.min, DATA_RANGES.currentSpeed.max, 0.5), // Currents
            calculateThreatLevel(location),                                                        // Threat level
            normalize(location.Sea_Ice_2025_percent, 0, 1, 0)                                     // Sea ice
        ];
        
        // Raw values for data display (actual measurements)
        const rawValues = [
            location.SST_2025_C || 0,                       // Temperature (°C)
            calculateHealthScore(location),                 // Health score (0-1)
            location.pH_2025 || 8.1,                       // pH value
            location.Oxygen_2010_mmol_m3 || 300,          // Oxygen (mmol/m³)
            location.Chlorophyll_2010_mg_m3 || 0.5,       // Chlorophyll (mg/m³)
            location.Current_Speed_2025_m_s || 0,          // Current speed (m/s)
            calculateThreatLevel(location),                 // Threat level (0-1)
            location.Sea_Ice_2025_percent || 0              // Sea ice (%)
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
        
        Max.outlet('temperature_norm', temperatureNorm);
        Max.outlet('health_score_norm', healthScoreNorm);
        Max.outlet('acidification_norm', acidificationNorm);
        Max.outlet('oxygen_norm', oxygenNorm);
        Max.outlet('marine_life_norm', marineLifeNorm);
        Max.outlet('currents_norm', currentsNorm);
        Max.outlet('threat_level_norm', threatLevelNorm);
        Max.outlet('sea_ice_norm', seaIceNorm);
        
        // Output raw values with meaningful names
        const temperatureRaw = isNaN(rawValues[0]) ? 0 : rawValues[0];
        const healthScoreRaw = isNaN(rawValues[1]) ? 0 : rawValues[1];
        const phRaw = isNaN(rawValues[2]) ? 8.1 : rawValues[2];
        const oxygenRaw = isNaN(rawValues[3]) ? 300 : rawValues[3];
        const chlorophyllRaw = isNaN(rawValues[4]) ? 0.5 : rawValues[4];
        const currentSpeedRaw = isNaN(rawValues[5]) ? 0 : rawValues[5];
        const threatLevelRaw = isNaN(rawValues[6]) ? 0 : rawValues[6];
        const seaIceRaw = isNaN(rawValues[7]) ? 0 : rawValues[7];
        
        Max.outlet('temperature_raw', temperatureRaw);
        Max.outlet('health_score_raw', healthScoreRaw);
        Max.outlet('ph_raw', phRaw);
        Max.outlet('oxygen_raw', oxygenRaw);
        Max.outlet('chlorophyll_raw', chlorophyllRaw);
        Max.outlet('current_speed_raw', currentSpeedRaw);
        Max.outlet('threat_level_raw', threatLevelRaw);
        Max.outlet('sea_ice_raw', seaIceRaw);
        
        // Send progress info
        const progress = (currentIndex + 1) / totalLocations;
        Max.outlet('progress', progress);
        Max.outlet('current_index', currentIndex + 1);
        Max.outlet('total_locations', totalLocations);
        
        Max.post(`Playing location ${currentIndex + 1}/${totalLocations}: ${locationName}`);
        
        currentIndex++;
        
    } catch (error) {
        Max.post(`Error playing location ${currentIndex + 1}: ${error.message}`);
        Max.outlet('error', 'playback_error');
        Max.outlet('error_location', currentIndex + 1);
        Max.outlet('error_message', error.message);
        
        // Skip to next location on error
        currentIndex++;
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
    const intervalMs = CONFIG.intervalMs / CONFIG.playbackSpeed;
    
    Max.post(`Starting playback: ${totalLocations} locations, ${intervalMs}ms intervals`);
    Max.outlet('status', 'playing');
    
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
        Max.post(`Jumped to location ${index + 1}`);
        
        if (isPlaying) {
            playNext();
        }
    }
}

/**
 * Get current data statistics
 */
function getStats() {
    const stats = {
        totalLocations: totalLocations,
        currentIndex: currentIndex,
        isPlaying: isPlaying,
        dataRanges: DATA_RANGES,
        config: CONFIG
    };
    
    Max.outlet('stats_total_locations', stats.totalLocations);
    Max.outlet('stats_current_index', stats.currentIndex);
    Max.outlet('stats_is_playing', stats.isPlaying ? 1 : 0);
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

// Initialize
Max.post('Ocean Data Sonifier v2.2 - Named Outlets Edition:');
Max.post('- Meaningful outlet names: temperature_norm, health_score_norm, etc.');
Max.post('- Individual outlets: no JSON data, separate values for each parameter');
Max.post('- Location data: location_name, latitude, longitude, region, etc.');
Max.post('- Raw values: temperature_raw, ph_raw, oxygen_raw, etc.');
Max.post('Available commands: loadData, start, stop, pause, reset, speed <0.1-5.0>, jump <index>, stats');

// Auto-load data on startup
loadData();