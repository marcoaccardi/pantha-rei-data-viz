import { useLoader } from '@react-three/fiber';
import { TextureLoader, Texture } from 'three';
import { useMemo } from 'react';

interface TextureOptions {
  resolution?: 'preview' | 'low' | 'medium' | 'high';
  date?: string;
}

export function useTextureLoader() {
  // Load NASA Earth texture (always high resolution)
  const earthTexture = useLoader(TextureLoader, '/textures/earth/nasa_world_topo_bathy.jpg');
  
  // Load latest available SST texture (medium resolution by default)
  const sstTexture = useLoader(TextureLoader, '/textures/sst/erddap_sst_texture_20250716_medium.png');
  
  // Function to load SST texture with specific options
  const loadSSTTexture = (options: TextureOptions = {}) => {
    const { resolution = 'medium', date = '20250716' } = options;
    
    const sstPath = useMemo(() => {
      if (resolution === 'high') {
        return `/textures/sst/erddap_sst_texture_${date}.png`;
      }
      return `/textures/sst/erddap_sst_texture_${date}_${resolution}.png`;
    }, [resolution, date]);
    
    return useLoader(TextureLoader, sstPath);
  };

  return {
    earthTexture,
    sstTexture,
    loadSSTTexture
  };
}