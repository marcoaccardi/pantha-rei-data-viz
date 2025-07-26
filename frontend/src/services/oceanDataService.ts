/**
 * Ocean Data API Service
 * 
 * Service for fetching ocean data from the FastAPI backend.
 * Handles all dataset queries including SST, currents, waves, acidity, and microplastics.
 */

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
 * Fetch data from multiple datasets at a specific point
 */
export async function fetchMultiPointData(
  lat: number,
  lon: number,
  date?: string
): Promise<MultiDatasetResponse> {
  const params = new URLSearchParams({
    lat: lat.toString(),
    lon: lon.toString(),
    datasets: 'sst,acidity,currents,waves'  // Request all datasets with fallback handling
  });
  
  if (date) {
    params.append('date', date);
  }

  // Add timeout to prevent hanging
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
  
  try {
    const response = await fetch(`${API_BASE_URL}/multi/point?${params}`, {
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }
    
    return response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      // Fallback to SST only on timeout
      console.warn('Multi-dataset request timed out, falling back to SST only');
      const fallbackParams = new URLSearchParams({
        lat: lat.toString(),
        lon: lon.toString(),
        datasets: 'sst'
      });
      if (date) fallbackParams.append('date', date);
      
      const fallbackResponse = await fetch(`${API_BASE_URL}/multi/point?${fallbackParams}`);
      if (fallbackResponse.ok) {
        return fallbackResponse.json();
      }
    }
    throw error;
  }
}

/**
 * Fetch data from a single dataset at a specific point
 */
export async function fetchSingleDataset(
  dataset: 'sst' | 'waves' | 'currents' | 'acidity' | 'microplastics',
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
      // Fallback to a known available date
      console.warn('No available dates found, using fallback date');
      return '2024-07-24'; // Use a date we know has some data
    }
    
    // Sort dates and return the most recent
    allDates.sort();
    return allDates[allDates.length - 1];
  } catch (error) {
    console.error('Error fetching available dates:', error);
    // Return a known working date as fallback
    return '2024-07-24';
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
      
    case 'VHM0': // Wave height
      if (value < 0.5) return { classification: 'Calm', severity: 'low', color: '#10b981' };
      if (value < 1.5) return { classification: 'Slight', severity: 'low', color: '#06b6d4' };
      if (value < 2.5) return { classification: 'Moderate', severity: 'medium', color: '#f59e0b' };
      if (value < 4.0) return { classification: 'Rough', severity: 'high', color: '#ef4444' };
      return { classification: 'Very Rough', severity: 'critical', color: '#991b1b' };
      
    case 'speed': // Current speed
      if (value < 0.1) return { classification: 'Slow', severity: 'low', color: '#10b981' };
      if (value < 0.3) return { classification: 'Moderate', severity: 'medium', color: '#f59e0b' };
      if (value < 0.5) return { classification: 'Fast', severity: 'high', color: '#ef4444' };
      return { classification: 'Very Fast', severity: 'critical', color: '#991b1b' };
      
    case 'o2': // Dissolved oxygen
      if (value < 150) return { classification: 'Hypoxic', severity: 'critical', color: '#ef4444' };
      if (value < 200) return { classification: 'Low O₂', severity: 'high', color: '#f59e0b' };
      if (value < 300) return { classification: 'Normal', severity: 'low', color: '#10b981' };
      return { classification: 'High O₂', severity: 'medium', color: '#3b82f6' };
      
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