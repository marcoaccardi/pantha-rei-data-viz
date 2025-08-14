import { useState, useCallback, useEffect, startTransition } from 'react';
import Globe from './components/Globe';
import DataPanel from './components/DataPanel';
import MicroplasticExplanation from './components/MicroplasticExplanation';
import AppHelpOverlay from './components/AppHelpOverlay';
import { useWebSocket } from './hooks/useWebSocket';
import { useTextureLoader } from './hooks/useTextureLoader';
import { fetchMultiPointData, transformToLegacyFormat, getLatestAvailableDate } from './services/oceanDataService';
import type { Coordinates, ClimateDataResponse, OceanMeasurement, DateRange, MultiDatasetOceanResponse } from './utils/types';
import { 
  generateRandomDate, 
  validateDate, 
  getGuaranteedDateRange, 
  formatDateWithCoverage,
  getDataAvailabilityDescription,
  getSafeInitialDate,
  TEMPORAL_COVERAGE
} from './utils/dateUtils';
import { useConnectionStatus } from './services/connectionMonitor';
import ConnectionStatusBar from './components/ConnectionStatusBar';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faCalendar, 
  faLocationDot, 
  faDice, 
  faTemperatureHigh, 
  faBottleWater, 
  faWater,
  faCircleInfo
} from '@fortawesome/free-solid-svg-icons';

// Design system constants for consistent styling
const designSystem = {
  colors: {
    primary: '#64748b',        // blue-gray-500 for buttons
    primaryHover: '#475569',   // blue-gray-600 for hover
    primaryActive: '#3b82f6',  // blue-500 for active state
    secondary: '#6366f1',
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    text: {
      primary: '#f9fafb',
      secondary: '#e5e7eb',
      muted: '#9ca3af'
    },
    backgrounds: {
      primary: 'rgba(0, 0, 0, 0.85)',
      secondary: 'rgba(255, 255, 255, 0.05)',
      accent: 'rgba(59, 130, 246, 0.1)'
    }
  },
  typography: {
    title: '1.1rem',
    body: '0.875rem',
    caption: '0.75rem',
    small: '0.6875rem'
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '20px'
  }
};

function App() {
  const [coordinates, setCoordinates] = useState<Coordinates>({ lat: 0, lng: 0 });
  const [climateData, setClimateData] = useState<ClimateDataResponse[]>([]);
  const [oceanData, setOceanData] = useState<MultiDatasetOceanResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progressMessage, setProgressMessage] = useState<string | null>(null);
  const [showDataOverlay, setShowDataOverlay] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [showMicroplastics, setShowMicroplastics] = useState(false);
  const [hoveredMicroplastic, setHoveredMicroplastic] = useState<any>(null);
  const [clickedMicroplastic, setClickedMicroplastic] = useState<any>(null);
  const [showHelpOverlay, setShowHelpOverlay] = useState(false);
  
  // Date management state - must be defined before texture loader
  const [selectedDate, setSelectedDate] = useState<string>(getSafeInitialDate());
  
  // Texture management - pass selectedDate to sync texture with date selection
  const { 
    selectedCategory, 
    availableCategories, 
    changeCategory, 
    getAvailableOptions,
    metadata 
  } = useTextureLoader(undefined, selectedDate);
  const [dateValidation, setDateValidation] = useState(validateDate(getSafeInitialDate()));
  
  // Connection status
  const { status: connectionStatus, details: connectionDetails, isConnected } = useConnectionStatus();

  // Error message auto-clear with proper cleanup
  useEffect(() => {
    if (errorMessage) {
      const timeoutId = setTimeout(() => setErrorMessage(null), 5000);
      return () => clearTimeout(timeoutId);
    }
  }, [errorMessage]);

  // Animation controller now handles debouncing internally
  
  // Function to generate random ocean coordinates (strictly avoiding all land)
  const generateRandomOceanLocation = () => {
    // PREMIUM LOCATIONS - Complete coverage for ALL 3 datasets (SST + Acidity + Currents)
    // Tested and confirmed working (2025-01-26)
    const premiumDataPoints = [
      { name: "North Pacific", lat: 30.0, lng: -150.0 },
      { name: "Central Pacific", lat: 20.0, lng: -160.0 },
      { name: "Eastern Pacific", lat: 10.0, lng: -140.0 },
      { name: "Equatorial Pacific", lat: 0.0, lng: -140.0 },
      { name: "South Pacific", lat: -20.0, lng: -120.0 },
      { name: "Mid Atlantic", lat: 30.0, lng: -50.0 },
      { name: "West Atlantic", lat: 20.0, lng: -40.0 },
      { name: "Indian Ocean South", lat: -20.0, lng: 90.0 },
    ];

    // VERIFIED COMPLETE DATA COVERAGE POINTS - All have SST + Acidity + Currents data
    // Tested and confirmed working with the ocean data API (2025-01-26)
    const verifiedDataPoints = [
      { name: "North Atlantic Deep", lat: 40.0, lng: -70.0 },
      { name: "North Atlantic Central", lat: 45.0, lng: -35.0 },
      { name: "North Atlantic Gyre", lat: 35.0, lng: -40.0 },
      { name: "Labrador Current", lat: 50.0, lng: -30.0 },
      { name: "Sargasso Sea", lat: 28.0, lng: -55.0 },
      { name: "Tropical Atlantic West", lat: 10.0, lng: -50.0 },
      { name: "Equatorial Atlantic", lat: 0.0, lng: -30.0 },
      { name: "Cape Verde Basin", lat: 15.0, lng: -25.0 },
      { name: "South Atlantic Gyre", lat: -30.0, lng: -25.0 },
      { name: "Brazil Basin", lat: -20.0, lng: -30.0 },
      { name: "Cape Basin", lat: -40.0, lng: 5.0 },
      { name: "Central Pacific", lat: 20.0, lng: -160.0 },
      { name: "North Pacific", lat: 30.0, lng: -150.0 },
      { name: "Equatorial Pacific", lat: 0.0, lng: -140.0 },
      { name: "South Pacific", lat: -25.0, lng: -120.0 },
      { name: "Eastern Pacific", lat: 25.0, lng: -120.0 },
      { name: "Central Indian", lat: -10.0, lng: 80.0 },
      { name: "Arabian Sea", lat: 5.0, lng: 75.0 },
      { name: "Southwest Indian", lat: -30.0, lng: 55.0 },
      { name: "Southeast Indian", lat: -20.0, lng: 90.0 },
    ];

    // Additional ocean coordinates for variety (may have partial data coverage)
    const additionalOceanPoints = [
      // ATLANTIC OCEAN - Verified Points (29 points)
      { name: "North Atlantic Gyre", lat: 35.0, lng: -40.0 },
      { name: "North Atlantic Deep", lat: 45.0, lng: -35.0 },
      { name: "Sargasso Sea Central", lat: 28.0, lng: -55.0 },
      { name: "Labrador Sea", lat: 58.0, lng: -50.0 },
      { name: "North Atlantic Central", lat: 50.0, lng: -30.0 },
      { name: "Newfoundland Basin", lat: 42.0, lng: -45.0 },
      { name: "Azores Deep", lat: 40.0, lng: -25.0 },
      { name: "Madeira Abyssal Plain", lat: 30.0, lng: -20.0 },
      { name: "North American Basin", lat: 38.0, lng: -50.0 },
      { name: "European Basin", lat: 48.0, lng: -20.0 },
      { name: "North Atlantic Ridge", lat: 55.0, lng: -25.0 },
      { name: "Canary Basin", lat: 25.0, lng: -20.0 },
      { name: "Cape Verde Basin", lat: 15.0, lng: -25.0 },
      { name: "Mid-Atlantic Deep", lat: -5.0, lng: -25.0 },
      { name: "Equatorial Atlantic West", lat: 0.0, lng: -30.0 },
      { name: "Sierra Leone Basin", lat: 8.0, lng: -20.0 },
      { name: "Gambia Abyssal Plain", lat: 12.0, lng: -22.0 },
      { name: "Mid-Atlantic Ridge Equatorial", lat: 0.0, lng: -25.0 },
      { name: "South Atlantic Gyre", lat: -30.0, lng: -25.0 },
      { name: "Brazil Basin", lat: -20.0, lng: -30.0 },
      { name: "Cape Basin", lat: -40.0, lng: 5.0 },
      { name: "South African Basin", lat: -45.0, lng: 10.0 },
      { name: "Agulhas Basin", lat: -38.0, lng: 15.0 },
      { name: "Pernambuco Abyssal Plain", lat: -10.0, lng: -30.0 },
      { name: "Drake Passage Central", lat: -58.0, lng: -65.0 },
      { name: "South Atlantic Ridge", lat: -45.0, lng: -20.0 },
      { name: "Meteor Deep", lat: -52.0, lng: -15.0 },
      { name: "Tristan da Cunha Deep", lat: -40.0, lng: -10.0 },
      { name: "Gough Island Deep", lat: -42.0, lng: -8.0 },
      
      // PACIFIC OCEAN - Verified Points (35 points)
      { name: "Eastern Pacific", lat: 25.0, lng: -120.0 },
      { name: "Central Pacific", lat: 20.0, lng: -160.0 },
      { name: "Bering Sea Deep", lat: 58.0, lng: -175.0 },
      { name: "Molokai Deep", lat: 25.0, lng: -155.0 },
      { name: "Hawaiian Deep", lat: 20.0, lng: -155.0 },
      { name: "Clipperton Deep", lat: 10.0, lng: -105.0 },
      { name: "Equatorial Pacific West", lat: 0.0, lng: -170.0 },
      { name: "Equatorial Pacific Central", lat: 0.0, lng: -140.0 },
      { name: "Equatorial Pacific East", lat: 0.0, lng: -110.0 },
      { name: "Galapagos Deep", lat: -2.0, lng: -95.0 },
      { name: "Ecuador Deep", lat: -5.0, lng: -85.0 },
      { name: "ITCZ Pacific", lat: 8.0, lng: -130.0 },
      { name: "Doldrums Deep", lat: 5.0, lng: -120.0 },
      { name: "Christmas Island Deep", lat: 2.0, lng: -157.0 },
      { name: "Line Islands Deep", lat: 5.0, lng: -160.0 },
      { name: "Phoenix Deep", lat: -5.0, lng: -170.0 },
      { name: "South Pacific Gyre", lat: -25.0, lng: -120.0 },
      { name: "Southwest Pacific", lat: -35.0, lng: -170.0 },
      { name: "Chile Basin", lat: -40.0, lng: -90.0 },
      { name: "Peru Basin", lat: -15.0, lng: -85.0 },
      { name: "Easter Island Deep", lat: -25.0, lng: -110.0 },
      { name: "Samoa Deep", lat: -15.0, lng: -170.0 },
      { name: "Fiji Deep", lat: -20.0, lng: 175.0 },
      { name: "Tonga Deep", lat: -25.0, lng: -175.0 },
      { name: "Vanuatu Deep", lat: -18.0, lng: 168.0 },
      { name: "New Caledonia Deep", lat: -25.0, lng: 165.0 },
      { name: "Tasman Sea Central", lat: -40.0, lng: 160.0 },
      { name: "Chatham Deep", lat: -45.0, lng: -175.0 },
      { name: "Campbell Deep", lat: -55.0, lng: 170.0 },
      { name: "Macquarie Deep", lat: -55.0, lng: 160.0 },
      { name: "South Pacific Ridge", lat: -50.0, lng: -110.0 },
      { name: "East Pacific Rise", lat: -30.0, lng: -105.0 },
      { name: "Tahiti Deep", lat: -20.0, lng: -150.0 },
      { name: "Marquesas Deep", lat: -10.0, lng: -140.0 },
      { name: "Society Deep", lat: -18.0, lng: -155.0 },
      { name: "Cook Deep", lat: -22.0, lng: -160.0 },
      { name: "Austral Deep", lat: -25.0, lng: -145.0 },
      { name: "Tuamotu Deep", lat: -15.0, lng: -145.0 },
      { name: "Pitcairn Deep", lat: -25.0, lng: -130.0 },
      
      // INDIAN OCEAN - Verified Points (28 points)
      { name: "Central Indian Ocean", lat: -10.0, lng: 80.0 },
      { name: "Mid-Indian Ocean", lat: 5.0, lng: 75.0 },
      { name: "Southwest Indian Ocean", lat: -30.0, lng: 55.0 },
      { name: "Maldives Deep", lat: 2.0, lng: 73.0 },
      { name: "Chagos Deep", lat: -8.0, lng: 72.0 },
      { name: "Mascarene Deep", lat: -20.0, lng: 60.0 },
      { name: "Seychelles Deep", lat: -8.0, lng: 55.0 },
      { name: "Carlsberg Ridge", lat: 5.0, lng: 65.0 },
      { name: "Central Indian Ridge", lat: -15.0, lng: 70.0 },
      { name: "Rodriguez Deep", lat: -22.0, lng: 65.0 },
      { name: "Mauritius Deep", lat: -25.0, lng: 58.0 },
      { name: "Reunion Deep", lat: -25.0, lng: 55.0 },
      { name: "Agulhas Deep", lat: -40.0, lng: 25.0 },
      { name: "Crozet Deep", lat: -45.0, lng: 50.0 },
      { name: "Kerguelen Deep", lat: -50.0, lng: 70.0 },
      { name: "Heard Deep", lat: -55.0, lng: 75.0 },
      { name: "Amsterdam Deep", lat: -40.0, lng: 80.0 },
      { name: "St. Paul Deep", lat: -42.0, lng: 78.0 },
      { name: "Perth Deep", lat: -35.0, lng: 105.0 },
      { name: "Diamantina Deep", lat: -40.0, lng: 100.0 },
      { name: "Broken Ridge Deep", lat: -30.0, lng: 95.0 },
      { name: "Ninety East Ridge", lat: -20.0, lng: 90.0 },
      { name: "Wharton Deep", lat: -15.0, lng: 100.0 },
      { name: "Java Deep", lat: -12.0, lng: 105.0 },
      { name: "Christmas Island Basin", lat: -15.0, lng: 105.0 },
      { name: "Cocos Deep", lat: -15.0, lng: 95.0 },
      { name: "Sri Lanka Deep", lat: 5.0, lng: 82.0 },
      { name: "South Indian Basin", lat: -50.0, lng: 90.0 },
      
      // SOUTHERN OCEAN - Verified Points (19 points)
      { name: "Drake Passage Deep", lat: -58.0, lng: -65.0 },
      { name: "Tasman Deep Southern", lat: -50.0, lng: 160.0 },
      { name: "Ross Sea Central", lat: -75.0, lng: 180.0 },
      { name: "Weddell Sea Deep", lat: -70.0, lng: -45.0 },
      { name: "Bellingshausen Sea", lat: -72.0, lng: -75.0 },
      { name: "Amundsen Sea", lat: -73.0, lng: -110.0 },
      { name: "Ross Ice Shelf Deep", lat: -78.0, lng: 175.0 },
      { name: "Marie Byrd Land Deep", lat: -75.0, lng: -125.0 },
      { name: "Enderby Deep", lat: -65.0, lng: 50.0 },
      { name: "Mac Robertson Deep", lat: -67.0, lng: 65.0 },
      { name: "Princess Elizabeth Deep", lat: -68.0, lng: 80.0 },
      { name: "Wilhelm II Deep", lat: -66.0, lng: 95.0 },
      { name: "Queen Mary Deep", lat: -67.0, lng: 100.0 },
      { name: "Wilkes Deep", lat: -66.0, lng: 110.0 },
      { name: "Adelie Deep", lat: -67.0, lng: 140.0 },
      { name: "George V Deep", lat: -67.0, lng: 150.0 },
      { name: "Oates Deep", lat: -67.0, lng: 155.0 },
      { name: "Victoria Deep", lat: -72.0, lng: 165.0 },
      { name: "Antarctic Peninsula Deep", lat: -70.0, lng: -60.0 },
      
      // ARCTIC OCEAN - Verified Points (5 points)
      { name: "Beaufort Sea Deep", lat: 75.0, lng: -135.0 },
      { name: "Canada Basin", lat: 80.0, lng: -125.0 },
      { name: "Makarov Basin", lat: 85.0, lng: 160.0 },
      { name: "Fram Strait Deep", lat: 80.0, lng: 0.0 },
      { name: "Lomonosov Ridge", lat: 85.0, lng: 90.0 }
    ];
    
    // Selection logic: Premium (50%) > Verified (30%) > Additional (20%)
    const rand = Math.random();
    let sourcePoints;
    let sourceType;
    let variation;
    
    if (rand < 0.5) {
      // 50% chance: Premium locations with complete 4-dataset coverage
      sourcePoints = premiumDataPoints;
      sourceType = 'PREMIUM (all 4 datasets)';
      variation = 2.0; // Smaller variation to stay in data-rich areas
    } else if (rand < 0.8) {
      // 30% chance: Verified locations with 3-dataset coverage  
      sourcePoints = verifiedDataPoints;
      sourceType = 'VERIFIED (3 datasets)';
      variation = 3.0;
    } else {
      // 20% chance: Additional points for variety
      sourcePoints = [...verifiedDataPoints, ...additionalOceanPoints];
      sourceType = 'ADDITIONAL (partial data)';
      variation = 5.0;
    }
    
    // Select a random point from the chosen source
    const basePoint = sourcePoints[Math.floor(Math.random() * sourcePoints.length)];
    
    // Apply variation based on source type
    const lat = basePoint.lat + (Math.random() - 0.5) * variation;
    const lng = basePoint.lng + (Math.random() - 0.5) * variation;
    
    // Final bounds check
    const finalLat = Math.max(-80, Math.min(80, lat));
    const finalLng = Math.max(-180, Math.min(180, lng));
    
    console.log(`🌊 Generated ocean coordinates from ${sourceType}: ${finalLat.toFixed(4)}°, ${finalLng.toFixed(4)}° (${basePoint.name})`);
    
    return { 
      lat: finalLat, 
      lng: finalLng 
    };
  };

  // Date management functions with improved error handling
  const handleDateChange = useCallback((newDate: string) => {
    const validation = validateDate(newDate);
    
    // Batch state updates to prevent race conditions
    setSelectedDate(newDate);
    setDateValidation(validation);
    
    if (validation.isValid) {
      // Development logging
      console.log(`📅 Date changed to: ${newDate} - ${getDataAvailabilityDescription(newDate)}`);
      setErrorMessage(null);
    } else {
      setErrorMessage(`Invalid date: ${validation.errors.join(', ')}`);
    }
  }, []);

  const generateRandomDateOnly = () => {
    const randomDate = generateRandomDate({ preferRecent: true, guaranteedOnly: false });
    handleDateChange(randomDate);
    // Only update date for texture change, no data fetch
  };

  const generateRandomDateAndLocation = () => {
    const randomDate = generateRandomDate({ preferRecent: true, guaranteedOnly: false });
    const randomCoords = generateRandomOceanLocation();
    
    handleDateChange(randomDate);
    setCoordinates(randomCoords);
    // Only update coordinates and date for texture change, no data fetch
  };

  const useGuaranteedDate = () => {
    const guaranteedRange = getGuaranteedDateRange();
    const guaranteedDate = generateRandomDate({ 
      guaranteedOnly: true, 
      preferRecent: true 
    });
    handleDateChange(guaranteedDate);
    // Trigger data fetch with current coordinates and new date
    handleLocationChange(coordinates, guaranteedDate);
  };

  // Transform new real data format to old format for compatibility
  const transformOceanDataToClimateData = (measurements: OceanMeasurement[]): ClimateDataResponse[] => {
    return measurements.map(measurement => ({
      latitude: coordinates.lat,
      longitude: coordinates.lng,
      date: new Date().toISOString().split('T')[0],
      data_source: measurement.source.replace('NOAA/ERDDAP/', '').replace('/', '_'),
      parameter: measurement.parameter,
      value: measurement.value,
      units: measurement.units,
      description: measurement.description,
      quality: measurement.quality === 'R' ? 'Real' : measurement.quality === 'S' ? 'Synthetic' : measurement.quality,
      confidence: measurement.confidence,
      climate_zone: measurement.zone,
      weather_labels: ['marine', 'oceanographic'],
      timestamp: new Date().toISOString()
    }));
  };

  const { sendMessage, isConnected: wsConnected } = useWebSocket({
    onMessage: (message) => {
      console.log('📨 WebSocket message received:', message.type);
      
      switch (message.type) {
        case 'climate_data':
          // Handle old format (backward compatibility)
          if (message.payload.climateData) {
            setClimateData(message.payload.climateData);
          }
          setIsLoading(false);
          break;
          
        case 'oceanData':
          // Handle new real data format from real_data_websocket_server.py
          console.log('🌊 Real ocean data received:', message.payload);
          
          if (message.payload.measurements) {
            const transformedData = transformOceanDataToClimateData(message.payload.measurements);
            console.log('📊 Transformed data:', transformedData);
            setClimateData(transformedData);
          }
          setIsLoading(false);
          setErrorMessage(null); // Clear any previous error messages
          
          // Log data summary
          if (message.payload.data_summary) {
            const summary = message.payload.data_summary;
            console.log(`✅ Data retrieval: ${summary.successful_retrievals} successful, ${summary.failed_retrievals} failed (${(summary.success_rate * 100).toFixed(1)}% success rate)`);
            
            if (summary.failed_sources && summary.failed_sources.length > 0) {
              console.warn('⚠️ Failed sources:', summary.failed_sources);
            }
          }
          
          // Log ocean validation
          if (message.payload.ocean_validation) {
            const validation = message.payload.ocean_validation;
            const oceanStatus = validation.is_over_ocean ? '🌊 OCEAN' : '🏞️ LAND';
            console.log(`${oceanStatus} (${(validation.confidence * 100).toFixed(1)}% confidence) - ${validation.ocean_zone || 'Unknown zone'}`);
          }
          
          // Log data policy confirmation
          if (message.payload.data_policy) {
            console.log('📋 Data Policy:', message.payload.data_policy);
          }
          break;
          
        // Handle backend-api climate data server responses
        case 'temperature_data':
        case 'salinity_data':
        case 'wave_data':
        case 'currents_data':
        case 'chlorophyll_data':
        case 'ph_data':
        case 'biodiversity_data':
        case 'microplastics_data':
          console.log(`🌊 ${message.type} received from backend-api`);
          
          // Clear progress message when data arrives
          setProgressMessage(null);
          
          if (message.data && (message.data.status === 'success' || (message.data.data && message.data.data.data && message.data.data.data.measurements))) {
            // Transform the backend-api response to match our expected format
            const backendData = message.data.data?.data?.measurements || [];
            const transformedBackendData = backendData.map((item: any) => ({
              latitude: message.coordinates?.lat || coordinates.lat,
              longitude: (message.coordinates as any)?.lon || coordinates.lng,
              date: selectedDate,
              data_source: message.type.replace('_data', '').replace('_', ' '),
              parameter: item.parameter || message.type.replace('_data', ''),
              value: item.value || 0,
              units: item.units || '',
              description: item.description || `${message.type.replace('_data', '').replace('_', ' ')} measurement`,
              quality: item.quality || 'Real',
              confidence: item.confidence || 0.9,
              climate_zone: item.zone || 'Ocean',
              weather_labels: ['marine', 'oceanographic'],
              timestamp: message.timestamp || new Date().toISOString()
            }));
            
            setClimateData(transformedBackendData);
            console.log(`📊 Processed ${transformedBackendData.length} ${message.type} measurements`);
            
            // Show cache status if available
            if (message.cached) {
              console.log('💾 Data loaded from cache');
            } else {
              console.log('🌐 Fresh data downloaded and cached');
            }
          } else {
            // Handle different error formats from backend
            const errorMsg = message.data?.error || message.data?.message || 'Unknown error';
            console.warn(`⚠️ ${message.type} request failed:`, errorMsg);
            setErrorMessage(`${message.type} data unavailable: ${errorMsg}`);
          }
          
          setIsLoading(false);
          break;
          
        case 'connection':
          console.log('🔗 WebSocket connection confirmed');
          if (message.payload?.system_info) {
            console.log('🔧 System info:', message.payload.system_info);
          }
          break;
          
        case 'progress':
          console.log('⏳ Progress:', message.payload?.message);
          setProgressMessage(message.payload?.message || 'Processing...');
          break;
          
        case 'error':
          console.error('❌ WebSocket error:', message.payload?.message);
          setErrorMessage(message.payload?.message || 'Unknown error occurred');
          setIsLoading(false);
          // Error message will auto-clear via useEffect
          break;
          
        default:
          console.log('🔍 Unknown message type:', message.type);
      }
    }
  });

  const handleLocationChange = useCallback(async (coords: Coordinates, useDate?: string) => {
    // This function is now only called when the user explicitly wants to fetch data
    // Random buttons no longer use this function
    startTransition(() => {
      setCoordinates(coords);
      setIsLoading(true);
      setApiError(null);
    });
    
    const queryDate = useDate || selectedDate;
    
    try {
      // Fetch data from REST API
      const response = await fetchMultiPointData(coords.lat, coords.lng, queryDate);
      
      startTransition(() => {
        setOceanData(response);
        
        // Transform to legacy format for backward compatibility
        const legacyData = transformToLegacyFormat(response, coords);
        setClimateData(legacyData);
        
        setIsLoading(false);
        setErrorMessage(null);
        setApiError(null);
      });
      
      // Ocean data retrieved successfully
      
    } catch (error) {
      console.error('❌ Error fetching ocean data:', error);
      
      // User-friendly error handling based on connection status
      startTransition(() => {
        setIsLoading(false);
        
        // Set appropriate error message
        if (!isConnected) {
          setApiError('Cannot fetch ocean data - backend server is disconnected. Please wait for reconnection.');
        } else if (error instanceof Error) {
          const message = error.message.toLowerCase();
          if (message.includes('timeout')) {
            setApiError('Request timed out. The server is taking too long to respond. Please try again.');
          } else if (message.includes('network') || message.includes('fetch')) {
            setApiError('Network error occurred. Please check your connection and try again.');
          } else {
            setApiError('Failed to fetch ocean data. Please try again later.');
          }
        } else {
          setApiError('An unexpected error occurred. Please try again.');
        }
        
        // Still show the panel but with no data
        setOceanData({
          location: { lat: coords.lat, lon: coords.lng },
          date: queryDate,
          datasets: {},
          total_extraction_time_ms: 0
        });
        setClimateData([]);
      });
    }
  }, [selectedDate]);

  return (
    <div style={{ width: '100vw', height: '100vh', margin: 0, padding: 0, overflow: 'hidden' }}>
      <ConnectionStatusBar status={connectionStatus} details={connectionDetails} />
      <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        <Globe 
          coordinates={coordinates}
          onLocationChange={handleLocationChange}
          isLoading={isLoading}
          showDataOverlay={showDataOverlay}
          dataCategory={selectedCategory}
          selectedDate={selectedDate}
          onZoomFunctionsReady={() => {}}
          showMicroplastics={showMicroplastics}
          onMicroplasticsPointHover={setHoveredMicroplastic}
          onMicroplasticsPointClick={(point) => {
            console.log('Microplastic point clicked:', point);
            setClickedMicroplastic(point);
          }}
          onDoubleClick={handleLocationChange}
        />
        
        {/* Control Panel */}
        <div style={{
          position: 'absolute',
          top: designSystem.spacing.xl,
          left: designSystem.spacing.xl,
          backgroundColor: designSystem.colors.backgrounds.primary,
          color: designSystem.colors.text.primary,
          padding: `${designSystem.spacing.lg} ${designSystem.spacing.xl}`,
          borderRadius: designSystem.spacing.md,
          zIndex: 1000,
          backdropFilter: 'blur(10px)',
          border: `1px solid ${designSystem.colors.text.muted}40`,
          minWidth: '320px'
        }}>
          <div style={{ fontSize: designSystem.typography.body }}>
            
            {/* Date Controls */}
            <div style={{ 
              padding: designSystem.spacing.sm, 
              backgroundColor: designSystem.colors.backgrounds.secondary, 
              borderRadius: designSystem.spacing.xs
            }}>
              <div style={{ 
                fontSize: designSystem.typography.body, 
                marginBottom: designSystem.spacing.xs, 
                color: designSystem.colors.text.secondary,
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                gap: designSystem.spacing.sm
              }}>
                <FontAwesomeIcon icon={faCalendar} />
                Date Selection
              </div>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: designSystem.spacing.sm, 
                marginBottom: designSystem.spacing.sm
              }}>
                <input
                  type="date"
                  value={selectedDate}
                  min={TEMPORAL_COVERAGE.HISTORICAL_START}
                  max={TEMPORAL_COVERAGE.GUARANTEED_END}
                  onChange={(e) => handleDateChange(e.target.value)}
                  aria-label="Select date for ocean data query"
                  aria-describedby="date-validation-info"
                  style={{
                    backgroundColor: designSystem.colors.backgrounds.secondary,
                    color: designSystem.colors.text.primary,
                    border: `1px solid ${dateValidation.isValid ? designSystem.colors.text.muted : designSystem.colors.error}`,
                    borderRadius: designSystem.spacing.xs,
                    padding: `${designSystem.spacing.xs} ${designSystem.spacing.sm}`,
                    fontSize: designSystem.typography.caption,
                    flex: 1
                  }}
                />
              </div>
              
              {/* Date validation info */}
              {!dateValidation.isValid && (
                <div id="date-validation-info" style={{ 
                  fontSize: designSystem.typography.caption, 
                  color: designSystem.colors.error, 
                  marginBottom: designSystem.spacing.xs
                }} role="alert">
                  ⚠️ {dateValidation.errors[0]}
                </div>
              )}
              {dateValidation.warnings.length > 0 && (
                <div style={{ 
                  fontSize: designSystem.typography.caption, 
                  color: designSystem.colors.warning, 
                  marginBottom: designSystem.spacing.xs
                }} role="status">
                  ℹ️ {dateValidation.warnings[0]}
                </div>
              )}
              
            </div>
            
            {/* Auto Data Fetching Info */}
            <div style={{ 
              marginTop: designSystem.spacing.lg, 
              padding: designSystem.spacing.sm, 
              backgroundColor: designSystem.colors.backgrounds.secondary, 
              borderRadius: designSystem.spacing.xs
            }}>
              <div style={{ 
                fontSize: designSystem.typography.body, 
                marginBottom: designSystem.spacing.xs, 
                color: designSystem.colors.text.secondary,
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                gap: designSystem.spacing.sm
              }}>
                <FontAwesomeIcon icon={faWater} />
                Ocean Data
              </div>
              <div style={{ 
                fontSize: designSystem.typography.caption, 
                color: designSystem.colors.text.muted
              }}>
                Data fetches automatically when you change location or date
              </div>
              {isLoading && (
                <div style={{ 
                  fontSize: designSystem.typography.caption, 
                  color: designSystem.colors.warning, 
                  marginTop: designSystem.spacing.xs
                }}>
                  ⏳ Loading ocean data...
                </div>
              )}
            </div>
            
            {/* Random Controls */}
            <div style={{ 
              marginTop: designSystem.spacing.md, 
              display: 'flex', 
              gap: designSystem.spacing.xs, 
              justifyContent: 'space-between'
            }}>
              <button 
                onClick={() => {
                  const randomCoords = generateRandomOceanLocation();
                  handleLocationChange(randomCoords);
                }}
                aria-label="Generate random ocean location and fetch data"
                title="Random Location"
                style={{
                  backgroundColor: designSystem.colors.primary,
                  color: designSystem.colors.text.primary,
                  border: 'none',
                  padding: `${designSystem.spacing.md} ${designSystem.spacing.lg}`,
                  borderRadius: designSystem.spacing.xs,  
                  cursor: 'pointer',
                  fontSize: designSystem.typography.body,
                  flex: '1',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'background-color 0.2s ease'
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = designSystem.colors.primaryHover}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = designSystem.colors.primary}
              >
                <FontAwesomeIcon icon={faLocationDot} />
              </button>
              <button 
                onClick={() => {
                  const randomDate = generateRandomDate({ preferRecent: true, guaranteedOnly: false });
                  handleDateChange(randomDate);
                  handleLocationChange(coordinates, randomDate);
                }}
                aria-label="Generate random date and fetch data"
                title="Random Date"
                style={{
                  backgroundColor: designSystem.colors.primary,
                  color: designSystem.colors.text.primary,
                  border: 'none',
                  padding: `${designSystem.spacing.md} ${designSystem.spacing.lg}`,
                  borderRadius: designSystem.spacing.xs,  
                  cursor: 'pointer',
                  fontSize: designSystem.typography.body,
                  flex: '1',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'background-color 0.2s ease'
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = designSystem.colors.primaryHover}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = designSystem.colors.primary}
              >
                <FontAwesomeIcon icon={faCalendar} />
              </button>
              <button 
                onClick={() => {
                  const randomDate = generateRandomDate({ preferRecent: true, guaranteedOnly: false });
                  const randomCoords = generateRandomOceanLocation();
                  handleDateChange(randomDate);
                  handleLocationChange(randomCoords, randomDate);
                }}
                aria-label="Generate random date and ocean location combination"
                title="Random Date & Location"
                style={{
                  backgroundColor: designSystem.colors.primary,
                  color: designSystem.colors.text.primary,
                  border: 'none',
                  padding: `${designSystem.spacing.md} ${designSystem.spacing.lg}`,
                  borderRadius: designSystem.spacing.xs,  
                  cursor: 'pointer',
                  fontSize: designSystem.typography.body,
                  flex: '1',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'background-color 0.2s ease'
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = designSystem.colors.primaryHover}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = designSystem.colors.primary}
              >
                <FontAwesomeIcon icon={faDice} />
              </button>
            </div>
            
            {/* SST Texture Controls */}
            <div style={{ 
              marginTop: designSystem.spacing.lg, 
              padding: designSystem.spacing.sm, 
              backgroundColor: designSystem.colors.backgrounds.secondary, 
              borderRadius: designSystem.spacing.xs
            }}>
              
              {/* SST Texture Show/Hide Toggle */}
              <div style={{ 
                marginTop: designSystem.spacing.md, 
                paddingTop: designSystem.spacing.md, 
                borderTop: `1px solid ${designSystem.colors.text.muted}40`
              }}>
                <button
                  onClick={() => setShowDataOverlay(!showDataOverlay)}
                  style={{
                    backgroundColor: designSystem.colors.primary,
                    color: designSystem.colors.text.primary,
                    border: 'none',
                    padding: `${designSystem.spacing.md} ${designSystem.spacing.lg}`,
                    borderRadius: designSystem.spacing.xs,
                    cursor: 'pointer',
                    fontSize: designSystem.typography.body,
                    transition: 'all 0.2s ease',
                    width: '100%',
                    fontWeight: '500',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: designSystem.spacing.sm
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.backgroundColor = designSystem.colors.primaryHover;
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.backgroundColor = designSystem.colors.primary;
                  }}
                >
                  <FontAwesomeIcon icon={faTemperatureHigh} />
                  {showDataOverlay ? 'Hide SST Texture' : 'Show SST Texture'}
                </button>
              </div>
              
              
              {/* Microplastics overlay toggle */}
              <div style={{ 
                marginTop: designSystem.spacing.lg, 
                paddingTop: designSystem.spacing.lg, 
                borderTop: `1px solid ${designSystem.colors.text.muted}40`
              }}>
                <button
                  onClick={() => setShowMicroplastics(!showMicroplastics)}
                  style={{
                    backgroundColor: designSystem.colors.primary,
                    color: designSystem.colors.text.primary,
                    border: 'none',
                    padding: `${designSystem.spacing.md} ${designSystem.spacing.lg}`,
                    borderRadius: designSystem.spacing.xs,
                    cursor: 'pointer',
                    fontSize: designSystem.typography.body,
                    transition: 'all 0.2s ease',
                    width: '100%',
                    fontWeight: '500',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: designSystem.spacing.sm
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.backgroundColor = designSystem.colors.primaryHover;
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.backgroundColor = designSystem.colors.primary;
                  }}
                >
                  <FontAwesomeIcon icon={faBottleWater} />
                  {showMicroplastics ? 'Hide Microplastics' : 'Show Microplastics'}
                </button>
                
              </div>
            </div>
          </div>
        </div>
        
        {/* Error Message Display */}
        {errorMessage && (
          <div style={{
            position: 'absolute',
            top: designSystem.spacing.xl,
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: `${designSystem.colors.error}f0`,
            color: designSystem.colors.text.primary,
            padding: `${designSystem.spacing.md} ${designSystem.spacing.xl}`,
            borderRadius: designSystem.spacing.sm,
            zIndex: 1001,
            backdropFilter: 'blur(10px)',
            border: `1px solid ${designSystem.colors.error}`,
            maxWidth: '400px',
            textAlign: 'center',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
            animation: 'slideDown 0.3s ease-out'
          }}>
            <div style={{ 
              fontSize: designSystem.typography.body, 
              fontWeight: 'bold', 
              marginBottom: designSystem.spacing.xs
            }}>
              🚫 Invalid Location
            </div>
            <div style={{ fontSize: designSystem.typography.body }}>
              {errorMessage}
            </div>
          </div>
        )}
        
        {/* Microplastic Explanation Panel */}
        {clickedMicroplastic && (
          <div style={{
            position: 'absolute',
            top: designSystem.spacing.xl,
            right: designSystem.spacing.xl,
            width: '450px',
            height: '90vh',
            borderRadius: designSystem.spacing.md,
            zIndex: 1002
          }}>
            <MicroplasticExplanation
              microplastic={clickedMicroplastic}
              onClose={() => setClickedMicroplastic(null)}
            />
          </div>
        )}

        {/* Data Panel */}
        {!clickedMicroplastic && (
          <DataPanel 
            data={oceanData}
            isLoading={isLoading}
            error={apiError}
            hoveredMicroplastic={hoveredMicroplastic}
          />
        )}
        
        {/* Help Button - Bottom Right */}
        <button
          onClick={() => setShowHelpOverlay(true)}
          style={{
            position: 'absolute',
            bottom: designSystem.spacing.xl,
            right: designSystem.spacing.xl,
            backgroundColor: designSystem.colors.primary,
            color: designSystem.colors.text.primary,
            border: 'none',
            padding: designSystem.spacing.lg,
            borderRadius: '50%',
            cursor: 'pointer',
            fontSize: '1.2rem',
            zIndex: 1000,
            backdropFilter: 'blur(10px)',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
            transition: 'all 0.2s ease',
            width: '56px',
            height: '56px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.backgroundColor = designSystem.colors.primaryHover;
            e.currentTarget.style.transform = 'scale(1.05)';
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.backgroundColor = designSystem.colors.primary;
            e.currentTarget.style.transform = 'scale(1)';
          }}
          title="App Help & Instructions"
          aria-label="Open application help and usage instructions"
        >
          <FontAwesomeIcon icon={faCircleInfo} />
        </button>
        
        {/* Help Overlay */}
        {showHelpOverlay && (
          <AppHelpOverlay onClose={() => setShowHelpOverlay(false)} />
        )}
      </div>
    </div>
  );
}

export default App;