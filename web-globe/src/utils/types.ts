// TypeScript interfaces for the NOAA Globe Application

import { Vector3 } from 'three';

export interface Coordinates {
  lat: number;
  lng: number;
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

export interface WebSocketMessage {
  type: 'texture_update' | 'coordinate_data' | 'climate_data' | 'progress' | 'error' | 'connection' | 'getOceanData' | 'oceanData' | 'pong';
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
  };
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
  showSSTOverlay?: boolean;
  onZoomFunctionsReady?: (zoomIn: () => void, zoomOut: () => void) => void;
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