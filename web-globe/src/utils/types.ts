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
  type: 'texture_update' | 'coordinate_data' | 'climate_data' | 'progress' | 'error' | 'connection';
  payload: {
    coordinates?: Coordinates;
    texturePath?: string;
    climateData?: ClimateDataResponse[];
    progress?: number;
    message?: string;
    timestamp: string;
  };
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