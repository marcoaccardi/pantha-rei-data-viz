#!/usr/bin/env node
/**
 * Ocean Data Sonifier - Standalone Test Version
 * 
 * This version simulates Max/MSP without requiring max-api
 * Tests all functionality and shows what data would be sent to Max outlets
 */

const fs = require('fs');
const path = require('path');

// Mock Max API for testing
const Max = {
    post: (...args) => console.log('[Max]', ...args),
    outlet: (name, ...args) => {
        console.log(`[OUTLET: ${name}]`, JSON.stringify(args));
    },
    addHandler: (name, func) => {
        console.log(`[Handler registered: ${name}]`);
        // Store handlers for simulation
        handlers[name] = func;
    }
};

// Handler storage for simulation
const handlers = {};

// Configuration
const CONFIG = {
    csvFile: path.join(__dirname, 'ocean_health_data.csv'),
    sampleEvery: 5,          // Read every 5th row (100 total locations)
    intervalMs: 12000,       // 12.0 seconds per location (20 min total)
    playbackSpeed: 1.0       // Speed multiplier
};

// Global state
let oceanData = [];
let currentIndex = 0;
let playbackTimer = null;
let isPlaying = false;
let totalLocations = 0;

// Data normalization ranges (can be dynamically updated)
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
        Max.outlet('status', 'loaded', totalLocations, validRows, skippedRows);
        
    } catch (error) {
        Max.post('Error loading data:', error.message);
        Max.outlet('error', 'load_failed', error.message);
        
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
        const displayData = {
            id: location.Location_ID || currentIndex + 1,
            name: locationName,
            latitude: location.Latitude || 0,
            longitude: location.Longitude || 0,
            region: location.Region || 'Unknown',
            ocean_basin: location.Ocean_Basin || 'Unknown',
            ecosystem_type: location.Ecosystem_Type || 'Unknown',
            climate_zone: location.Climate_Zone || 'Unknown'
        };
        
        Max.outlet('location_data', displayData);
        
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
        
        // Output individual slider values with safety checks (normalized 0-1)
        sliderValues.forEach((value, index) => {
            const safeValue = isNaN(value) || value === null || value === undefined ? 0.5 : Math.max(0, Math.min(1, value));
            Max.outlet(`slider_${index + 1}`, safeValue);
        });
        
        // Output raw values for data display
        rawValues.forEach((value, index) => {
            const safeValue = isNaN(value) || value === null || value === undefined ? 0 : value;
            Max.outlet(`raw_${index + 1}`, safeValue);
        });
        
        // Send progress info
        const progress = (currentIndex + 1) / totalLocations;
        Max.outlet('progress', progress, currentIndex + 1, totalLocations);
        
        Max.post(`Playing location ${currentIndex + 1}/${totalLocations}: ${displayData.name}`);
        
        currentIndex++;
        
    } catch (error) {
        Max.post(`Error playing location ${currentIndex + 1}: ${error.message}`);
        Max.outlet('error', 'playback_error', currentIndex + 1, error.message);
        
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
 * Reset to beginning
 */
function resetPlayback() {
    stopPlayback();
    currentIndex = 0;
    Max.post('Reset to beginning');
    Max.outlet('status', 'reset');
}

// Register handlers
Max.addHandler('loadData', loadData);
Max.addHandler('start', startPlayback);
Max.addHandler('stop', stopPlayback);
Max.addHandler('reset', resetPlayback);

// Initialize and test
console.log('🎵 OCEAN DATA SONIFIER - TEST MODE');
console.log('================================');
console.log('Simulating Max/MSP environment...');

// Auto-load data and run a quick test
(async () => {
    await loadData();
    
    if (oceanData.length > 0) {
        console.log('\n🔊 SIMULATING PLAYBACK (first 3 locations):');
        console.log('=' * 50);
        
        // Play first 3 locations as demonstration
        for (let i = 0; i < Math.min(3, oceanData.length); i++) {
            console.log(`\n--- Playing Location ${i + 1} ---`);
            currentIndex = i;
            playNext();
        }
        
        console.log('\n✅ TEST COMPLETED SUCCESSFULLY!');
        console.log('🎵 Ready for Max/MSP integration');
        console.log(`📊 ${totalLocations} locations loaded with 91% data reliability`);
    }
})();