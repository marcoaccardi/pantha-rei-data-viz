/**
 * Ultra-Fast Ocean Data API Service
 * 
 * Service for fetching ocean data from the FastAPI backend with high-performance caching.
 * Handles all dataset queries including SST, currents, acidity, and microplastics.
 * Features:
 * - Request deduplication to prevent duplicate API calls
 * - Intelligent caching with browser storage persistence
 * - Automatic cache management and cleanup
 */

import { requestCache } from '../utils/requestCache';

const API_BASE_URL = 'http://localhost:8000';

export interface DataValue {
  value: number | string | null;
  units: string;
  long_name: string;
  valid: boolean;
}

export interface Coordinates {
  lat: number;
  lon: number;
}

export interface PointDataResponse {
  dataset: string;
  location: Coordinates;
  actual_location: Coordinates;
  date: string;
  data: Record<string, DataValue>;
  extraction_time_ms: number;
  file_source: string;
}

export interface MultiDatasetResponse {
  location: Coordinates;
  date: string;
  datasets: Record<string, PointDataResponse | { error: string }>;
  total_extraction_time_ms: number;
}

export interface DatasetInfo {
  name: string;
  description: string;
  variables: string[];
  temporal_coverage: {
    start: string;
    end: string;
  };
  spatial_resolution: string;
  file_count: number;
  latest_date: string | null;
}

/**
 * Fetch data from multiple datasets at a specific point with ultra-fast caching
 */
export async function fetchMultiPointData(
  lat: number,
  lon: number,
  date?: string
): Promise<MultiDatasetResponse> {
  const datasets = ['sst', 'acidity', 'currents', 'microplastics'];
  const cacheKey = requestCache.createOceanDataKey(lat, lon, date || 'latest', datasets);

  return requestCache.get(
    cacheKey,
    async () => {
      // Original fetch logic with optimizations
      const params = new URLSearchParams({
        lat: lat.toString(),
        lon: lon.toString(),
        datasets: datasets.join(',')
      });
      
      if (date) {
        params.append('date', date);
      }

      // Add timeout to prevent hanging - increased for large files
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 seconds for large files
      
      const startTime = Date.now();
      try {
        console.log(`🌊 FETCHING OCEAN DATA: ${cacheKey}`);
        
        const response = await fetch(`${API_BASE_URL}/multi/point?${params}`, {
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
          throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        const requestTime = Date.now() - startTime;
        console.log(`✅ OCEAN DATA FETCHED: ${cacheKey} in ${requestTime}ms`);
        
        return data;
      } catch (error) {
        clearTimeout(timeoutId);
        if (error instanceof Error && error.name === 'AbortError') {
          // Fallback to individual dataset requests for better reliability
          console.warn('Multi-dataset request timed out, falling back to individual requests');
          try {
            // Fetch all datasets individually in parallel
            const individualRequests = datasets.map(async (dataset) => {
              try {
                const params = new URLSearchParams({
                  lat: lat.toString(),
                  lon: lon.toString()
                });
                if (date) params.append('date', date);
                
                const response = await fetch(`${API_BASE_URL}/${dataset}/point?${params}`);
                if (response.ok) {
                  const result = await response.json();
                  return { dataset, result };
                } else {
                  throw new Error(`${dataset} request failed: ${response.status}`);
                }
              } catch (err) {
                console.warn(`Failed to fetch ${dataset}:`, err);
                return { 
                  dataset, 
                  result: { 
                    error: err instanceof Error ? err.message : 'Unknown error',
                    dataset 
                  }
                };
              }
            });
            
            // Wait for all individual requests to complete
            const individualResults = await Promise.allSettled(individualRequests);
            
            // Build the multi-dataset response format
            const fallbackData: any = {
              location: { lat, lon },
              date: date || 'latest',
              datasets: {},
              total_extraction_time_ms: Date.now() - startTime
            };
            
            individualResults.forEach((result) => {
              if (result.status === 'fulfilled' && result.value) {
                const { dataset, result: dataResult } = result.value;
                fallbackData.datasets[dataset] = dataResult;
              }
            });
            
            console.log(`✅ FALLBACK COMPLETED: fetched ${Object.keys(fallbackData.datasets).length} datasets individually`);
            return fallbackData;
            
          } catch (fallbackError) {
            console.error('Individual fallback requests also failed:', fallbackError);
          }
        }
        console.error('Ocean data request failed:', error);
        throw error;
      }
    },
    { ttl: 2 * 60 * 1000 } // 2 minute cache for ocean data
  );
}

/**
 * Fetch data from a single dataset at a specific point
 */
export async function fetchSingleDataset(
  dataset: 'sst' | 'currents' | 'acidity_historical' | 'acidity_current' | 'acidity' | 'microplastics',
  lat: number,
  lon: number,
  date?: string
): Promise<PointDataResponse> {
  const params = new URLSearchParams({
    lat: lat.toString(),
    lon: lon.toString()
  });
  
  if (date) {
    params.append('date', date);
  }

  const response = await fetch(`${API_BASE_URL}/${dataset}/point?${params}`);
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get information about all available datasets
 */
export async function fetchDatasetInfo(): Promise<Record<string, DatasetInfo>> {
  const response = await fetch(`${API_BASE_URL}/datasets`);
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get available dates for all datasets
 */
export async function fetchAvailableDates(): Promise<Record<string, string[]>> {
  const response = await fetch(`${API_BASE_URL}/available-dates`);
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Get the latest available date from all datasets
 */
export async function getLatestAvailableDate(): Promise<string> {
  try {
    const availableDates = await fetchAvailableDates();
    
    // Flatten all dates from all datasets (excluding microplastics which has a range)
    const allDates: string[] = [];
    
    for (const [dataset, dates] of Object.entries(availableDates)) {
      if (dataset === 'microplastics') continue; // Skip microplastics as it has a date range
      
      dates.forEach(date => {
        if (date && !date.includes(' to ')) { // Ensure it's a single date
          allDates.push(date);
        }
      });
    }
    
    if (allDates.length === 0) {
      // Fallback to latest available texture date
      console.warn('No available dates found, using fallback date');
      return '2025-07-31'; // Latest available texture date
    }
    
    // Sort dates and return the most recent
    allDates.sort();
    return allDates[allDates.length - 1];
  } catch (error) {
    console.error('Error fetching available dates:', error);
    // Return latest available texture date as fallback
    return '2025-07-31';
  }
}

/**
 * Transform multi-dataset response to a flat array for compatibility with existing code
 */
export function transformToLegacyFormat(
  response: MultiDatasetResponse,
  coordinates: { lat: number; lng: number }
): any[] {
  const results: any[] = [];
  
  for (const [datasetName, datasetData] of Object.entries(response.datasets)) {
    if ('error' in datasetData) {
      continue; // Skip datasets with errors
    }
    
    const dataset = datasetData as PointDataResponse;
    
    // Transform each variable in the dataset
    for (const [varName, varData] of Object.entries(dataset.data)) {
      if (varData.valid && varData.value !== null) {
        results.push({
          latitude: coordinates.lat,
          longitude: coordinates.lng,
          date: dataset.date,
          data_source: datasetName,
          parameter: varName,
          value: typeof varData.value === 'number' ? varData.value : 0,
          units: varData.units,
          description: varData.long_name,
          quality: 'Real',
          confidence: 1.0,
          climate_zone: 'Ocean',
          weather_labels: ['marine', 'oceanographic'],
          timestamp: new Date().toISOString()
        });
      }
    }
  }
  
  return results;
}

/**
 * Helper function to classify ocean measurements
 */
export function classifyMeasurement(parameter: string, value: number): {
  classification: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  color: string;
} {
  switch (parameter) {
    case 'sst':
    case 'analysed_sst':
      if (value < 10) return { classification: 'Cold', severity: 'low', color: '#3b82f6' };
      if (value < 20) return { classification: 'Cool', severity: 'low', color: '#06b6d4' };
      if (value < 25) return { classification: 'Moderate', severity: 'medium', color: '#10b981' };
      if (value < 30) return { classification: 'Warm', severity: 'medium', color: '#f59e0b' };
      return { classification: 'Hot', severity: 'high', color: '#ef4444' };
      
    case 'ph':
      if (value < 7.8) return { classification: 'Acidic', severity: 'critical', color: '#ef4444' };
      if (value < 8.0) return { classification: 'Low pH', severity: 'high', color: '#f59e0b' };
      if (value < 8.2) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      return { classification: 'Basic', severity: 'medium', color: '#3b82f6' };
      
    case 'speed': // Current speed
      if (value < 0.1) return { classification: 'Slow', severity: 'low', color: '#10b981' };
      if (value < 0.3) return { classification: 'Moderate', severity: 'medium', color: '#f59e0b' };
      if (value < 0.5) return { classification: 'Fast', severity: 'high', color: '#ef4444' };
      return { classification: 'Very Fast', severity: 'critical', color: '#991b1b' };
      
    case 'spco2': // Surface partial pressure of CO2
      if (value < 200) return { classification: 'Low CO₂', severity: 'low', color: '#10b981' };
      if (value < 350) return { classification: 'Normal CO₂', severity: 'low', color: '#06b6d4' };
      if (value < 400) return { classification: 'Elevated CO₂', severity: 'medium', color: '#f59e0b' };
      if (value < 500) return { classification: 'High CO₂', severity: 'high', color: '#ef4444' };
      return { classification: 'Very High CO₂', severity: 'critical', color: '#991b1b' };
      
    case 'o2': // Dissolved oxygen
      if (value < 150) return { classification: 'Hypoxic', severity: 'critical', color: '#ef4444' };
      if (value < 200) return { classification: 'Low O₂', severity: 'high', color: '#f59e0b' };
      if (value < 300) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      return { classification: 'High O₂', severity: 'medium', color: '#3b82f6' };
      
    case 'ph_insitu': // In situ pH
    case 'ph_insitu_total': // Total scale in situ pH  
      if (value < 7.8) return { classification: 'Acidic', severity: 'critical', color: '#ef4444' };
      if (value < 8.0) return { classification: 'Low pH', severity: 'high', color: '#f59e0b' };
      if (value < 8.2) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      return { classification: 'Basic', severity: 'medium', color: '#3b82f6' };
      
    case 'talk': // Total alkalinity
      if (value < 2.0) return { classification: 'Low Alkalinity', severity: 'high', color: '#f59e0b' };
      if (value < 2.3) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      if (value < 2.5) return { classification: 'High', severity: 'medium', color: '#06b6d4' };
      return { classification: 'Very High', severity: 'medium', color: '#3b82f6' };
      
    case 'dic': // Dissolved inorganic carbon
      if (value < 1.8) return { classification: 'Low DIC', severity: 'medium', color: '#06b6d4' };
      if (value < 2.1) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      if (value < 2.3) return { classification: 'Elevated', severity: 'medium', color: '#f59e0b' };
      return { classification: 'High DIC', severity: 'high', color: '#ef4444' };
      
    case 'pco2': // Partial pressure of CO2
      if (value < 300) return { classification: 'Low pCO₂', severity: 'low', color: '#10b981' };
      if (value < 400) return { classification: 'Normal', severity: 'low', color: '#06b6d4' };
      if (value < 500) return { classification: 'Elevated', severity: 'medium', color: '#f59e0b' };
      if (value < 600) return { classification: 'High pCO₂', severity: 'high', color: '#ef4444' };
      return { classification: 'Very High', severity: 'critical', color: '#991b1b' };
      
    case 'revelle': // Revelle factor (buffer capacity)
      if (value < 8) return { classification: 'High Buffer', severity: 'low', color: '#10b981' };
      if (value < 12) return { classification: 'Normal', severity: 'low', color: '#06b6d4' };
      if (value < 16) return { classification: 'Low Buffer', severity: 'medium', color: '#f59e0b' };
      return { classification: 'Very Low Buffer', severity: 'high', color: '#ef4444' };
      
    case 'no3': // Nitrate
      if (value < 5) return { classification: 'Low Nitrate', severity: 'medium', color: '#06b6d4' };
      if (value < 15) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      if (value < 30) return { classification: 'High', severity: 'medium', color: '#f59e0b' };
      return { classification: 'Very High', severity: 'high', color: '#ef4444' };
      
    case 'po4': // Phosphate
      if (value < 0.5) return { classification: 'Low Phosphate', severity: 'medium', color: '#06b6d4' };
      if (value < 1.5) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      if (value < 3.0) return { classification: 'High', severity: 'medium', color: '#f59e0b' };
      return { classification: 'Very High', severity: 'high', color: '#ef4444' };
      
    case 'si': // Silicate
      if (value < 10) return { classification: 'Low Silicate', severity: 'medium', color: '#06b6d4' };
      if (value < 50) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      if (value < 100) return { classification: 'High', severity: 'medium', color: '#f59e0b' };
      return { classification: 'Very High', severity: 'high', color: '#ef4444' };
      
    case 'chl': // Chlorophyll-a
      if (value < 0.1) return { classification: 'Very Low', severity: 'medium', color: '#3b82f6' };
      if (value < 1.0) return { classification: 'Low', severity: 'low', color: '#06b6d4' };
      if (value < 5.0) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      if (value < 20.0) return { classification: 'High', severity: 'medium', color: '#f59e0b' };
      return { classification: 'Very High', severity: 'high', color: '#ef4444' };
      
    case 'nppv': // Net Primary Production
      if (value < 50) return { classification: 'Low Productivity', severity: 'medium', color: '#06b6d4' };
      if (value < 200) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      if (value < 500) return { classification: 'High', severity: 'medium', color: '#f59e0b' };
      return { classification: 'Very High', severity: 'high', color: '#ef4444' };
      
    case 'dissic': // Dissolved inorganic carbon
      if (value < 1.8) return { classification: 'Low DIC', severity: 'medium', color: '#06b6d4' };
      if (value < 2.1) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      if (value < 2.3) return { classification: 'Elevated', severity: 'medium', color: '#f59e0b' };
      return { classification: 'High DIC', severity: 'high', color: '#ef4444' };
      
    default:
      return { classification: 'Normal', severity: 'low', color: '#6b7280' };
  }
}

/**
 * Format compass direction
 */
export function formatDirection(degrees: number): string {
  const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const index = Math.round(degrees / 22.5) % 16;
  return directions[index];
}

/**
 * Check if dataset contains discrete sample data
 */
export function isDiscreteSampleData(data: Record<string, DataValue>): boolean {
  return data._data_type?.value === 'discrete_sample';
}

/**
 * Get discrete sample metadata for display
 */
export function getDiscreteSampleInfo(data: Record<string, DataValue>): {
  isDiscrete: boolean;
  sampleDistance?: number;
  sampleDistanceText?: string;
  dataQuality?: string;
} {
  const isDiscrete = isDiscreteSampleData(data);
  
  if (!isDiscrete) {
    return { isDiscrete: false };
  }
  
  const distance = data._sample_distance?.value as number;
  const distanceText = distance ? `${distance} km from nearest sample` : 'Unknown distance';
  
  // Determine data quality based on sample distance
  let dataQuality = 'excellent';
  if (distance > 100) dataQuality = 'poor';
  else if (distance > 50) dataQuality = 'fair';
  else if (distance > 20) dataQuality = 'good';
  
  return {
    isDiscrete: true,
    sampleDistance: distance,
    sampleDistanceText: distanceText,
    dataQuality
  };
}

/**
 * Format parameter name for display with discrete sample indicator
 */
export function formatParameterName(parameter: string, data: Record<string, DataValue>): string {
  const sampleInfo = getDiscreteSampleInfo(data);
  const baseNames: Record<string, string> = {
    'ph': 'pH',
    'ph_insitu': 'pH (in situ)',
    'ph_insitu_total': 'pH (total scale)',
    'talk': 'Total Alkalinity',
    'dic': 'Dissolved Inorganic Carbon',
    'pco2': 'Partial Pressure CO₂',
    'revelle': 'Revelle Factor',
    'spco2': 'Surface pCO₂',
    'no3': 'Nitrate',
    'po4': 'Phosphate', 
    'si': 'Silicate',
    'o2': 'Dissolved Oxygen',
    'chl': 'Chlorophyll-a',
    'nppv': 'Net Primary Production',
    'dissic': 'Dissolved Inorganic Carbon'
  };
  
  const baseName = baseNames[parameter] || parameter.replace('_', ' ').toUpperCase();
  
  if (sampleInfo.isDiscrete) {
    return `${baseName} (discrete sample)`;
  }
  
  return baseName;
}