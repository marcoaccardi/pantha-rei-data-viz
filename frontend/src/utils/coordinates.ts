// Coordinate conversion utilities for the globe

import { Vector3 } from 'three';
import type { Coordinates } from './types';

/**
 * Convert latitude/longitude to 3D position on a unit sphere
 */
export function latLngToVector3(lat: number, lng: number, radius: number = 1): Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);

  const x = -(radius * Math.sin(phi) * Math.cos(theta));
  const z = (radius * Math.sin(phi) * Math.sin(theta));
  const y = (radius * Math.cos(phi));

  return new Vector3(x, y, z);
}

/**
 * Convert 3D position back to latitude/longitude
 */
export function vector3ToLatLng(position: Vector3, radius: number = 1): Coordinates {
  const normalizedPos = position.clone().normalize().multiplyScalar(radius);
  
  const lat = 90 - (Math.acos(normalizedPos.y / radius) * 180 / Math.PI);
  
  // Fixed longitude calculation to handle all quadrants correctly
  // The formula should convert from x,z coordinates back to longitude
  // Given x = -sin(phi) * cos(theta) and z = sin(phi) * sin(theta)
  // We can derive longitude as: lng = atan2(z, -x) * 180/PI - 180
  // But we need to ensure proper wrapping
  let lng = Math.atan2(normalizedPos.z, -normalizedPos.x) * 180 / Math.PI;
  
  // Convert from the internal coordinate system back to standard longitude
  // Our internal system has 0° at x=-1, z=0, so we need to subtract 180°
  lng = lng - 180;
  
  // Ensure longitude is in the range [-180, 180]
  while (lng > 180) lng -= 360;
  while (lng < -180) lng += 360;

  return {
    lat: Math.max(-85, Math.min(85, lat)),
    lng: Math.max(-180, Math.min(180, lng))
  };
}

/**
 * Calculate distance between two coordinates in kilometers
 */
export function calculateDistance(coord1: Coordinates, coord2: Coordinates): number {
  const R = 6371; // Earth's radius in kilometers
  const dLat = (coord2.lat - coord1.lat) * Math.PI / 180;
  const dLng = (coord2.lng - coord1.lng) * Math.PI / 180;
  
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(coord1.lat * Math.PI / 180) * Math.cos(coord2.lat * Math.PI / 180) * 
    Math.sin(dLng/2) * Math.sin(dLng/2);
  
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}