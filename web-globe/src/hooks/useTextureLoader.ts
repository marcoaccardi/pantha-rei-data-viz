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
  // First try: exact match
  const exactMatch = `/textures/sst/erddap_sst_texture_${preferredDate}_${preferredResolution}.png`;
  if (AVAILABLE_TEXTURES.includes(exactMatch)) {
    console.log(`🎯 Found exact texture match: ${exactMatch}`);
    return exactMatch;
  }

  // Second try: same date, different resolution
  const sameDate = AVAILABLE_TEXTURES.filter(path => path.includes(preferredDate));
  if (sameDate.length > 0) {
    console.log(`📅 Found same date texture: ${sameDate[0]}`);
    return sameDate[0];
  }

  // Third try: different date, same resolution
  const sameResolution = AVAILABLE_TEXTURES.filter(path => path.includes(`_${preferredResolution}.png`));
  if (sameResolution.length > 0) {
    console.log(`🔍 Found same resolution texture: ${sameResolution[0]}`);
    return sameResolution[0];
  }

  // Fallback: use first available texture
  const fallback = AVAILABLE_TEXTURES[0];
  console.log(`🔄 Using fallback texture: ${fallback}`);
  return fallback;
}

export function useTextureLoader() {
  // Load NASA Earth texture (this should always work)
  const earthTexture = useLoader(TextureLoader, '/textures/earth/nasa_world_topo_bathy.jpg');
  
  // Temporarily disable SST texture loading due to server issues
  const safeSSTPath = '/textures/earth/nasa_world_topo_bathy.jpg'; // Use earth texture as fallback
  
  // Load the safe SST texture (temporarily using earth texture)
  const sstTexture = useLoader(TextureLoader, safeSSTPath);
  
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
      console.log(`✅ Successfully loaded SST texture: ${safeSSTPath}`);
    }
  }, [sstTexture, safeSSTPath]);

  return {
    earthTexture,
    sstTexture,
    loadSSTTexture,
    availableTextures: AVAILABLE_TEXTURES,
    currentSSTPath: safeSSTPath
  };
}