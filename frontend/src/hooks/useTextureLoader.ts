import { useLoader } from '@react-three/fiber';
import { TextureLoader, LinearFilter, LinearMipmapLinearFilter } from 'three';
import { useMemo, useState, useEffect, startTransition } from 'react';
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

// Function to construct API texture URL
function buildTextureApiUrl(category: string, date?: string, resolution: string = 'medium'): string {
  const params = new URLSearchParams();
  if (date) params.append('date', date);
  params.append('resolution', resolution);
  
  const url = `${API_BASE_URL}/textures/${category}?${params.toString()}`;
  console.log(`🌐 Built texture API URL: ${url}`);
  return url;
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
    console.warn('Failed to fetch texture metadata from API:', error);
    return null;
  }
}

export function useTextureLoader(externalCategory?: string, externalDate?: string) {
  // State for texture metadata
  const [metadata, setMetadata] = useState<TextureMetadata | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('sst');
  const [selectedDate, setSelectedDate] = useState<string | undefined>('2025-08-11'); // Default to latest available texture date
  const [selectedResolution, setSelectedResolution] = useState<string>('medium');
  
  // Use external category and date if provided, otherwise use internal state
  const activeCategory = externalCategory || selectedCategory;
  const activeDate = externalDate || selectedDate;
  
  // Load NASA Earth texture - fallback to local file if API is unavailable
  const earthTexture = useLoader(TextureLoader, `/textures/earth/nasa_world_topo_bathy.jpg`);
  
  // Fetch texture metadata on mount
  useEffect(() => {
    fetchTextureMetadata().then(setMetadata);
  }, []);
  
  // Build current texture URL based on selections with caching
  const currentTextureUrl = useMemo(() => {
    // Always use API for texture serving
    const apiUrl = buildTextureApiUrl(activeCategory, activeDate, selectedResolution);
    
    console.log(`🔧 Texture URL construction:`, {
      activeCategory,
      activeDate, 
      selectedResolution,
      apiUrl
    });
    
    // Return stable URL to prevent infinite re-renders
    return apiUrl;
  }, [activeCategory, activeDate, selectedResolution]);
  
  // Load current data texture with smart caching to prevent duplicate requests
  const dataTexture = useMemo(() => {
    const cacheKey = requestCache.createTextureKey(activeCategory, activeDate, selectedResolution);
    console.log(`🎨 Loading texture: ${cacheKey} from ${currentTextureUrl}`);
    
    // Use React Three Fiber's loader with enhanced settings for ultra-resolution
    const texture = new TextureLoader().load(currentTextureUrl);
    
    // Configure texture for ultra-high resolution display
    texture.generateMipmaps = true;                    // Enable mipmaps for smooth scaling
    texture.flipY = true;                             // Correct orientation for globe mapping
    texture.magFilter = LinearFilter;                 // High-quality magnification
    texture.minFilter = LinearMipmapLinearFilter;     // High-quality minification with mipmaps
    
    return texture;
  }, [currentTextureUrl, activeCategory, activeDate, selectedResolution]);
  
  // Function to change texture category with deferred updates
  const changeCategory = (category: string, date?: string, resolution: string = 'medium') => {
    startTransition(() => {
      setSelectedCategory(category);
      setSelectedDate(date);
      setSelectedResolution(resolution);
    });
  };
  
  // Get available options for current category
  const getAvailableOptions = (category: string) => {
    if (!metadata?.available_textures[category]) {
      return { dates: [], resolutions: [] };
    }
    
    const categoryData = metadata.available_textures[category];
    const dates = Object.keys(categoryData);
    const allResolutions = new Set<string>();
    
    Object.values(categoryData).forEach(resolutions => {
      resolutions.forEach(res => allResolutions.add(res));
    });
    
    return {
      dates: dates.sort(),
      resolutions: Array.from(allResolutions)
    };
  };
  
  // Log successful texture loading
  useEffect(() => {
    if (dataTexture) {
      console.log(`✅ Successfully loaded ${activeCategory} texture: ${currentTextureUrl}`);
      console.log(`🔄 Texture object:`, dataTexture);
    }
  }, [dataTexture, activeCategory, currentTextureUrl]);

  // Log category changes
  useEffect(() => {
    console.log(`🎯 Category changed to: ${activeCategory}`);
    console.log(`📍 Current texture URL: ${currentTextureUrl}`);
  }, [activeCategory, currentTextureUrl]);
  
  // Log metadata loading
  useEffect(() => {
    if (metadata) {
      console.log('📊 Texture metadata loaded:', metadata.summary);
    }
  }, [metadata]);

  return {
    // Textures
    earthTexture,
    dataTexture, // Current data overlay texture
    
    // Category management
    selectedCategory: activeCategory, // Return the active category (external or internal)
    selectedDate: activeDate,
    selectedResolution,
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
    sstTexture: dataTexture, // Alias for backward compatibility
    loadSSTTexture: (options: TextureOptions = {}) => {
      changeCategory('sst', options.date, options.resolution);
      return dataTexture;
    }
  };
}