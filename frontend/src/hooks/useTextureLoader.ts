import { useLoader } from '@react-three/fiber';
import { TextureLoader, Texture } from 'three';
import { useMemo, useState, useEffect } from 'react';

interface TextureOptions {
  resolution?: 'preview' | 'low' | 'medium' | 'high';
  date?: string;
}

// Available texture files based on actual directory listing
const AVAILABLE_TEXTURES = [
  '/textures/sst/erddap_sst_texture_20250618.png',
  '/textures/sst/erddap_sst_texture_20250618_medium.png',
  '/textures/sst/erddap_sst_texture_20250618_low.png',
  '/textures/sst/erddap_sst_texture_20250618_preview.png',
  '/textures/sst/erddap_sst_texture_20250716_medium.png',
  '/textures/sst/erddap_sst_texture_20250716_low.png',
  '/textures/sst/erddap_sst_texture_20250716_preview.png'
];

// Function to find best available texture
function findBestAvailableTexture(preferredDate = '20250716', preferredResolution = 'medium'): string {
  const textureServerUrl = 'http://localhost:5173';
  
  // First try: exact match
  const exactMatch = `/textures/sst/erddap_sst_texture_${preferredDate}_${preferredResolution}.png`;
  if (AVAILABLE_TEXTURES.includes(exactMatch)) {
    console.log(`🎯 Found exact texture match: ${exactMatch}`);
    return `${textureServerUrl}${exactMatch}`;
  }

  // Second try: same date, different resolution
  const sameDate = AVAILABLE_TEXTURES.filter(path => path.includes(preferredDate));
  if (sameDate.length > 0) {
    console.log(`📅 Found same date texture: ${sameDate[0]}`);
    return `${textureServerUrl}${sameDate[0]}`;
  }

  // Third try: different date, same resolution
  const sameResolution = AVAILABLE_TEXTURES.filter(path => path.includes(`_${preferredResolution}.png`));
  if (sameResolution.length > 0) {
    console.log(`🔍 Found same resolution texture: ${sameResolution[0]}`);
    return `${textureServerUrl}${sameResolution[0]}`;
  }

  // Fallback: use first available texture
  const fallback = AVAILABLE_TEXTURES[0];
  console.log(`🔄 Using fallback texture: ${fallback}`);
  return `${textureServerUrl}${fallback}`;
}

export function useTextureLoader() {
  // Use Vite dev server on port 5173 for texture loading
  const textureServerUrl = 'http://localhost:5173';
  
  // Load NASA Earth texture (this should always work)
  const earthTexture = useLoader(TextureLoader, `${textureServerUrl}/textures/earth/nasa_world_topo_bathy.jpg`);
  
  // Load the default SST texture (medium resolution, latest available date)
  const defaultSSTPath = findBestAvailableTexture('20250716', 'medium');
  const sstTexture = useLoader(TextureLoader, defaultSSTPath);
  
  // Function to load specific SST texture with intelligent fallback
  const loadSSTTexture = (options: TextureOptions = {}) => {
    const { resolution = 'medium', date = '20250618' } = options;
    
    const bestPath = useMemo(() => {
      return findBestAvailableTexture(date, resolution);
    }, [resolution, date]);
    
    return useLoader(TextureLoader, bestPath);
  };

  // Log successful texture loading
  useEffect(() => {
    if (sstTexture) {
      console.log(`✅ Successfully loaded SST texture: ${defaultSSTPath}`);
    }
  }, [sstTexture, defaultSSTPath]);

  return {
    earthTexture,
    sstTexture,
    loadSSTTexture,
    availableTextures: AVAILABLE_TEXTURES,
    currentSSTPath: defaultSSTPath
  };
}