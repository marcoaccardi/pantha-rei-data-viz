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

// Data normalization ranges (based on CSV analysis)
const DATA_RANGES = {
    sst: { min: -1.8, max: 31.04 },
    ph: { min: 7.847, max: 8.313 },
    oxygen: { min: 196.6, max: 412.8 },
    chlorophyll: { min: 0.026, max: 5.752 },
    marineLifeProduction: { min: 0, max: 109.442 },
    currentSpeed: { min: 0, max: 1.942 },
    nitrate: { min: 0, max: 29.031 }
};

/**
 * Normalize value to 0-1 range
 */
function normalize(value, min, max) {
    if (value === null || value === undefined || isNaN(value)) {
        return 0;
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
 * Calculate composite ocean health score
 */
function calculateHealthScore(location) {
    let healthFactors = [];
    
    // Temperature health (cooler is healthier in current climate)
    if (location.SST_2025_C !== null) {
        const tempScore = 1 - normalize(location.SST_2025_C, DATA_RANGES.sst.min, 25); // 25°C as danger threshold
        healthFactors.push(tempScore);
    }
    
    // pH health (higher pH is healthier)
    if (location.pH_2025 !== null) {
        const phScore = normalize(location.pH_2025, DATA_RANGES.ph.min, DATA_RANGES.ph.max);
        healthFactors.push(phScore);
    }
    
    // Oxygen health (higher oxygen is healthier)
    if (location.Oxygen_2010_mmol_m3 !== null) {
        const oxygenScore = normalize(location.Oxygen_2010_mmol_m3, DATA_RANGES.oxygen.min, DATA_RANGES.oxygen.max);
        healthFactors.push(oxygenScore);
    }
    
    // Current health (moderate currents are healthier than stagnant)
    if (location.Current_Speed_2025_m_s !== null) {
        const currentScore = Math.min(1, location.Current_Speed_2025_m_s * 5); // Scale up small values
        healthFactors.push(currentScore);
    }
    
    return healthFactors.length > 0 ? healthFactors.reduce((a, b) => a + b) / healthFactors.length : 0.5;
}

/**
 * Calculate threat level (inverse of health + warming trend)
 */
function calculateThreatLevel(location) {
    let threatFactors = [];
    
    // Temperature warming trend
    if (location.SST_2003_C !== null && location.SST_2025_C !== null) {
        const warming = location.SST_2025_C - location.SST_2003_C;
        const warmingThreat = normalize(warming, -2, 5); // -2°C to +5°C range
        threatFactors.push(warmingThreat);
    }
    
    // Acidification threat (lower pH = higher threat)
    if (location.pH_2025 !== null) {
        const acidThreat = 1 - normalize(location.pH_2025, DATA_RANGES.ph.min, DATA_RANGES.ph.max);
        threatFactors.push(acidThreat);
    }
    
    // Oxygen depletion threat
    if (location.Oxygen_2010_mmol_m3 !== null) {
        const oxygenThreat = 1 - normalize(location.Oxygen_2010_mmol_m3, DATA_RANGES.oxygen.min, DATA_RANGES.oxygen.max);
        threatFactors.push(oxygenThreat);
    }
    
    // High temperature threat
    if (location.SST_2025_C !== null) {
        const tempThreat = normalize(location.SST_2025_C, 20, DATA_RANGES.sst.max); // 20°C as baseline
        threatFactors.push(tempThreat);
    }
    
    return threatFactors.length > 0 ? threatFactors.reduce((a, b) => a + b) / threatFactors.length : 0.5;
}

/**
 * Process location data into 10 outlet streams
 */
function processLocation(location) {
    // Outlet 1: Location metadata (basic identification)
    const locationInfo = {
        id: location.Location_ID || 0,
        name: location.Location_Name || 'Unknown',
        latitude: location.Latitude || 0,
        longitude: location.Longitude || 0
    };
    
    // Outlet 2: Temporal data (time context for visuals) - directly from CSV
    const temporalData = {
        date_early: location.Date_Early,        // 2003-01-15
        date_mid: location.Date_Mid,            // 2010-01-15  
        date_late: location.Date_Late,          // 2025-01-15
        time_span_years: 22,
        current_era: 'Multi_Temporal_Analysis'
    };
    
    // Outlet 3: Spatial context (from CSV columns) - all pre-classified
    const spatialContext = {
        region: location.Region,                // Arctic, North_Pacific, etc.
        ocean_basin: location.Ocean_Basin,      // Arctic_Ocean, Pacific_Ocean, etc.
        ecosystem_type: location.Ecosystem_Type, // Polar_Marine, Subpolar_Marine, etc.
        climate_zone: location.Climate_Zone     // Polar, Temperate, Tropical, etc.
    };
    
    // Outlet 4: Temperature data (normalized)
    const temperatureData = {
        sst_2003: normalize(location.SST_2003_C, DATA_RANGES.sst.min, DATA_RANGES.sst.max),
        sst_2010: normalize(location.SST_2010_C, DATA_RANGES.sst.min, DATA_RANGES.sst.max),
        sst_2025: normalize(location.SST_2025_C, DATA_RANGES.sst.min, DATA_RANGES.sst.max),
        warming_trend: location.SST_2003_C && location.SST_2025_C ? 
            normalize(location.SST_2025_C - location.SST_2003_C, -2, 5) : 0.5,
        sea_ice: normalize(location.Sea_Ice_2025_percent, 0, 1)
    };
    
    // Outlet 5: Ocean health score
    const healthScore = calculateHealthScore(location);
    
    // Outlet 6: Acidification level (inverted - higher value = more acidic = more dangerous)
    const acidificationLevel = location.pH_2025 ? 
        1 - normalize(location.pH_2025, DATA_RANGES.ph.min, DATA_RANGES.ph.max) : 0.5;
    
    // Outlet 7: Oxygen status
    const oxygenStatus = normalize(location.Oxygen_2010_mmol_m3, DATA_RANGES.oxygen.min, DATA_RANGES.oxygen.max);
    
    // Outlet 8: Marine life index (productivity)
    const marineLifeIndex = {
        chlorophyll_2003: normalize(location.Chlorophyll_2003_mg_m3, DATA_RANGES.chlorophyll.min, DATA_RANGES.chlorophyll.max),
        chlorophyll_2010: normalize(location.Chlorophyll_2010_mg_m3, DATA_RANGES.chlorophyll.min, DATA_RANGES.chlorophyll.max),
        marine_life_2003: normalize(location.Marine_Life_Production_2003_mg_m3_day, DATA_RANGES.marineLifeProduction.min, DATA_RANGES.marineLifeProduction.max),
        marine_life_2010: normalize(location.Marine_Life_Production_2010_mg_m3_day, DATA_RANGES.marineLifeProduction.min, DATA_RANGES.marineLifeProduction.max),
        combined: (
            normalize(location.Chlorophyll_2010_mg_m3, DATA_RANGES.chlorophyll.min, DATA_RANGES.chlorophyll.max) +
            normalize(location.Marine_Life_Production_2010_mg_m3_day, DATA_RANGES.marineLifeProduction.min, DATA_RANGES.marineLifeProduction.max)
        ) / 2
    };
    
    // Outlet 9: Current dynamics
    const currentDynamics = {
        speed: normalize(location.Current_Speed_2025_m_s, DATA_RANGES.currentSpeed.min, DATA_RANGES.currentSpeed.max),
        direction: location.Current_Direction_2025_deg ? location.Current_Direction_2025_deg / 360 : 0,
        u_component: location.Current_U_2025_m_s || 0,
        v_component: location.Current_V_2025_m_s || 0
    };
    
    // Outlet 10: Threat level
    const threatLevel = calculateThreatLevel(location);
    
    return {
        locationInfo,
        temporalData,
        spatialContext,
        temperatureData, 
        healthScore,
        acidificationLevel,
        oxygenStatus,
        marineLifeIndex,
        currentDynamics,
        threatLevel
    };
}

/**
 * Load and parse CSV data
 */
async function loadData() {
    try {
        Max.post('Loading ocean data from:', CONFIG.csvFile);
        
        if (!fs.existsSync(CONFIG.csvFile)) {
            throw new Error(`CSV file not found: ${CONFIG.csvFile}`);
        }
        
        const csvContent = fs.readFileSync(CONFIG.csvFile, 'utf8');
        const lines = csvContent.trim().split('\n');
        const headers = lines[0].split(',');
        
        oceanData = [];
        
        // Sample every Nth row as configured
        for (let i = 1; i < lines.length; i += CONFIG.sampleEvery) {
            if (lines[i]) {
                const location = parseCSVLine(lines[i], headers);
                oceanData.push(location);
            }
        }
        
        totalLocations = oceanData.length;
        Max.post(`Loaded ${totalLocations} ocean locations (sampled every ${CONFIG.sampleEvery} rows)`);
        Max.outlet('status', 'loaded', totalLocations);
        
    } catch (error) {
        Max.post('Error loading data:', error.message);
        Max.outlet('error', error.message);
    }
}

/**
 * Play next location data
 */
function playNext() {
    if (currentIndex >= oceanData.length) {
        stopPlayback();
        Max.outlet('status', 'completed');
        return;
    }
    
    const location = oceanData[currentIndex];
    const processed = processLocation(location);
    
    // Send data to Max outlets (10 outlets now)
    Max.outlet('location_info', processed.locationInfo);
    Max.outlet('temporal_data', processed.temporalData);
    Max.outlet('spatial_context', processed.spatialContext);
    Max.outlet('temperature', processed.temperatureData);
    Max.outlet('health_score', processed.healthScore);
    Max.outlet('acidification', processed.acidificationLevel);
    Max.outlet('oxygen', processed.oxygenStatus);
    Max.outlet('marine_life', processed.marineLifeIndex);
    Max.outlet('currents', processed.currentDynamics);
    Max.outlet('threat_level', processed.threatLevel);
    
    // Send progress info
    const progress = (currentIndex + 1) / totalLocations;
    Max.outlet('progress', progress, currentIndex + 1, totalLocations);
    
    Max.post(`Playing location ${currentIndex + 1}/${totalLocations}: ${location.Location_Name}`);
    
    currentIndex++;
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

// Max API handlers
Max.addHandler('loadData', loadData);
Max.addHandler('start', startPlayback);
Max.addHandler('stop', stopPlayback);
Max.addHandler('pause', pausePlayback);
Max.addHandler('reset', resetPlayback);
Max.addHandler('speed', setSpeed);
Max.addHandler('jump', jumpToLocation);

// Initialize
Max.post('Ocean Data Sonifier loaded. Use "loadData" to begin.');
Max.post('Available commands: loadData, start, stop, pause, reset, speed <0.1-5.0>, jump <index>');

// Auto-load data on startup
loadData();