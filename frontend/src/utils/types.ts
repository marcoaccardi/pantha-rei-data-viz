// TypeScript interfaces for the NOAA Globe Application

import { Vector3 } from 'three';

export interface Coordinates {
  lat: number;
  lng: number; // Frontend uses 'lng', backend expects 'lon' - handled in message transformation
}

export interface CameraPosition {
  position: [number, number, number];
  target: [number, number, number];
  zoom: number;
}

export interface ClimateDataResponse {
  latitude: number;
  longitude: number;
  date: string;
  data_source: string;
  parameter: string;
  value: number;
  units: string;
  description: string;
  quality: string;
  confidence: number;
  climate_zone: string;
  weather_labels: string[];
  timestamp: string;
}

export interface DateRange {
  start: string;
  end: string;
}

export interface WebSocketMessage {
  type: 'texture_update' | 'coordinate_data' | 'climate_data' | 'progress' | 'error' | 'connection' | 'getOceanData' | 'oceanData' | 'pong' | 'temperature_request' | 'salinity_request' | 'wave_request' | 'currents_request' | 'chlorophyll_request' | 'ph_request' | 'biodiversity_request' | 'microplastics_request' | 'temperature_data' | 'salinity_data' | 'wave_data' | 'currents_data' | 'chlorophyll_data' | 'ph_data' | 'biodiversity_data' | 'microplastics_data';
  payload: {
    coordinates?: Coordinates;
    texturePath?: string;
    climateData?: ClimateDataResponse[];
    progress?: number;
    message?: string;
    timestamp: string;
    // New real data format
    lat?: number;
    lng?: number;
    longitude?: number;
    latitude?: number;
    parameters?: string[];
    measurements?: OceanMeasurement[];
    // Date-related fields
    dateRange?: DateRange;
    selectedDate?: string;
    data_summary?: {
      successful_retrievals: number;
      failed_retrievals: number;
      success_rate: number;
      failed_sources?: string[];
    };
    ocean_validation?: {
      is_over_ocean: boolean;
      confidence: number;
      ocean_zone?: string;
      depth_estimate?: string;
    };
    data_policy?: string;
    system?: string;
    system_info?: string;
  };
  // Backend response fields
  data?: any;
  coordinates?: Coordinates;
  timestamp?: string;
  cached?: boolean;
}

export interface OceanMeasurement {
  model: string;
  parameter: string;
  value: number;
  units: string;
  description: string;
  source: string;
  quality: string; // 'R' for Real, 'S' for Synthetic
  confidence: number;
  zone: string;
}

// Enhanced ocean data types with educational context
export interface ParameterClassification {
  classification: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  color: string;
  description: string;
  environmental_impact: string;
  context: string;
}

export interface EducationalContext {
  short_description: string;
  scientific_context: string;
  unit_explanation: string;
  health_implications: { [key: string]: string };
  measurement_context: { [key: string]: string };
}

export interface OceanDataValue {
  value: number | string | null;
  units: string;
  long_name: string;
  valid: boolean;
  classification?: ParameterClassification;
  educational_context?: EducationalContext;
}

export interface OceanPointData {
  dataset: string;
  location: {
    lat: number;
    lon: number;
  };
  actual_location: {
    lat: number;
    lon: number;
  };
  date: string;
  data: Record<string, OceanDataValue>;
  extraction_time_ms: number;
  file_source: string;
}

export interface MultiDatasetOceanResponse {
  location: {
    lat: number;
    lon: number;
  };
  date: string;
  datasets: Record<string, OceanPointData | { error: string }>;
  total_extraction_time_ms: number;
}

export interface TextureInfo {
  path: string;
  resolution: 'high' | 'medium' | 'low' | 'preview';
  size: string;
  timestamp: string;
}

export interface GlobeProps {
  coordinates?: Coordinates;
  onLocationChange?: (coords: Coordinates) => void;
  isLoading?: boolean;
  showDataOverlay?: boolean;
  dataCategory?: string;
  showSSTOverlay?: boolean; // Legacy prop for backward compatibility
  onZoomFunctionsReady?: (zoomIn: () => void, zoomOut: () => void) => void;
  showMicroplastics?: boolean;
  onMicroplasticsPointHover?: (point: any) => void;
  onMicroplasticsPointClick?: (point: any) => void;
}

export interface AnimationConfig {
  duration: number;
  easing: (t: number) => number;
  zoomLevel: number;
}

export interface CameraControlsRef {
  setLookAt: (x1: number, y1: number, z1: number, x2: number, y2: number, z2: number, enableTransition?: boolean) => void;
  getPosition: () => Vector3;
  getTarget: () => Vector3;
}