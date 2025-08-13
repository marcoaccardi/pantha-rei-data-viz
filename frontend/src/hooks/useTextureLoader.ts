import { useLoader } from '@react-three/fiber';
import { TextureLoader, LinearFilter, LinearMipmapLinearFilter, Texture } from 'three';
import { useMemo, useState, useEffect, startTransition } from 'react';
import * as React from 'react';
import { requestCache } from '../utils/requestCache';

interface TextureOptions {
  resolution?: 'preview' | 'low' | 'medium' | 'high';
  date?: string;
  category?: 'sst';
}

interface TextureMetadata {
  available_textures: Record<string, Record<string, string[]>>;
  summary: {
    total_categories: number;
    categories: Record<string, any>;
    total_textures: number;
  };
}

// Configuration
const API_BASE_URL = 'http://localhost:8000';

// Simple texture URL construction
function buildTextureApiUrl(category: string, date?: string): string {
  const params = new URLSearchParams();
  if (date) params.append('date', date);
  return `${API_BASE_URL}/textures/${category}?${params.toString()}`;
}

// Function to get texture metadata from API
async function fetchTextureMetadata(): Promise<TextureMetadata | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/textures/metadata`);
    if (!response.ok) {
      throw new Error(`API responded with status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    return null;
  }
}

export function useTextureLoader(externalCategory?: string, externalDate?: string) {
  // State for texture metadata
  const [metadata, setMetadata] = useState<TextureMetadata | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('sst');
  const [selectedDate, setSelectedDate] = useState<string | undefined>(new Date().toISOString().split('T')[0]);
  
  // State for data texture
  const [dataTexture, setDataTexture] = useState<Texture | null>(null);
  const [isLoadingTexture, setIsLoadingTexture] = useState<boolean>(false);
  const [textureLoadError, setTextureLoadError] = useState<boolean>(false);
  const [isLoadingEarthTexture, setIsLoadingEarthTexture] = useState<boolean>(true);
  const [earthTexture, setEarthTexture] = useState<Texture | null>(null);
  
  // Use external category and date if provided, otherwise use internal state
  const activeCategory = externalCategory || selectedCategory;
  const activeDate = externalDate || selectedDate;
  
  // Load NASA Earth texture with proper loading states
  useEffect(() => {
    const loader = new TextureLoader();
    setIsLoadingEarthTexture(true);
    
    loader.load(
      `${API_BASE_URL}/textures/earth/nasa_world_topo_bathy.jpg`,
      (texture) => {
        // Configure earth texture
        texture.flipY = true;
        texture.generateMipmaps = true;
        texture.magFilter = LinearFilter;
        texture.minFilter = LinearMipmapLinearFilter;
        
        setEarthTexture(texture);
        setIsLoadingEarthTexture(false);
      },
      undefined,
      (error) => {
        setIsLoadingEarthTexture(false);
      }
    );
  }, []);
  
  // Fetch texture metadata on mount
  useEffect(() => {
    fetchTextureMetadata().then(setMetadata);
  }, []);
  
  // Build current texture URL based on selections
  const currentTextureUrl = useMemo(() => {
    return buildTextureApiUrl(activeCategory, activeDate);
  }, [activeCategory, activeDate]);
  
  // Load data texture when URL changes - key fix for date synchronization
  useEffect(() => {
    let isMounted = true;
    setIsLoadingTexture(true);
    setTextureLoadError(false);
    
    const loader = new TextureLoader();
    
    // Load new texture
    loader.load(
      currentTextureUrl,
      // On success
      (texture) => {
        if (!isMounted) {
          texture.dispose();
          return;
        }
        
        // Configure texture
        texture.flipY = true;
        texture.generateMipmaps = true;
        texture.magFilter = LinearFilter;
        texture.minFilter = LinearMipmapLinearFilter;
        
        setDataTexture(prevTexture => {
          // Dispose previous texture
          if (prevTexture) {
            prevTexture.dispose();
          }
          return texture;
        });
        setIsLoadingTexture(false);
        setTextureLoadError(false);
      },
      // On progress (optional)
      undefined,
      // On error
      (error) => {
        if (isMounted) {
          setIsLoadingTexture(false);
          setTextureLoadError(true);
        }
      }
    );
    
    // Cleanup function
    return () => {
      isMounted = false;
    };
  }, [currentTextureUrl, activeCategory, activeDate]); // Added activeCategory and activeDate as deps
  
  // Cleanup effect - dispose textures on unmount
  useEffect(() => {
    return () => {
      if (dataTexture) {
        dataTexture.dispose();
      }
    };
  }, [dataTexture]);
  
  // Function to change texture category
  const changeCategory = (category: string, date?: string) => {
    startTransition(() => {
      setSelectedCategory(category);
      setSelectedDate(date);
    });
  };
  
  // Get available options for current category
  const getAvailableOptions = (category: string) => {
    if (!metadata?.available_textures[category]) {
      return { dates: [], resolutions: [] };
    }
    
    const categoryData = metadata.available_textures[category];
    const dates = Object.keys(categoryData);
    
    return {
      dates: dates.sort()
    };
  };
  

  return {
    // Textures
    earthTexture,
    dataTexture, // Current data overlay texture
    
    // Loading states
    isLoadingTexture,
    isLoadingEarthTexture,
    textureLoadError,
    
    // Category management
    selectedCategory: activeCategory, // Return the active category (external or internal)
    selectedDate: activeDate,
    changeCategory,
    
    // Available options
    metadata,
    getAvailableOptions,
    availableCategories: metadata ? Object.keys(metadata.available_textures).filter(cat => 
      Object.keys(metadata.available_textures[cat]).length > 0
    ) : [],
    
    // Current texture info
    currentTextureUrl,
    
    // Legacy compatibility (for SST)
    sstTexture: dataTexture
  };
}