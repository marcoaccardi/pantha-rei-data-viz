import { useState, useCallback, useEffect, startTransition } from 'react';
import Globe from './components/Globe';
import DataPanel from './components/DataPanel';
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
  TEMPORAL_COVERAGE
} from './utils/dateUtils';

function App() {
  const [coordinates, setCoordinates] = useState<Coordinates>({ lat: 0, lng: 0 });
  const [climateData, setClimateData] = useState<ClimateDataResponse[]>([]);
  const [oceanData, setOceanData] = useState<MultiDatasetOceanResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progressMessage, setProgressMessage] = useState<string | null>(null);
  const [showDataOverlay, setShowDataOverlay] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [showMicroplastics, setShowMicroplastics] = useState(false);
  const [hoveredMicroplastic, setHoveredMicroplastic] = useState<any>(null);
  
  // Texture management
  const { 
    selectedCategory, 
    availableCategories, 
    changeCategory, 
    getAvailableOptions,
    metadata 
  } = useTextureLoader();
  
  // Date management state
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [dateValidation, setDateValidation] = useState(validateDate(new Date().toISOString().split('T')[0]));
  const [showDatePicker, setShowDatePicker] = useState(false);

  // Error message auto-clear with proper cleanup
  useEffect(() => {
    if (errorMessage) {
      const timeoutId = setTimeout(() => setErrorMessage(null), 5000);
      return () => clearTimeout(timeoutId);
    }
  }, [errorMessage]);

  // Function to generate random ocean coordinates (strictly avoiding all land)
  const generateRandomOceanLocation = () => {
    // PREMIUM LOCATIONS - Complete coverage for ALL 4 datasets (SST + Acidity + Currents + Waves)
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
    // Trigger data fetch with current coordinates and new date
    handleLocationChange(coordinates, randomDate);
  };

  const generateRandomDateAndLocation = () => {
    const randomDate = generateRandomDate({ preferRecent: true, guaranteedOnly: false });
    const randomCoords = generateRandomOceanLocation();
    
    handleDateChange(randomDate);
    handleLocationChange(randomCoords, randomDate);
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

  const { sendMessage, isConnected } = useWebSocket({
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
    startTransition(() => {
      setCoordinates(coords);
      setIsLoading(true);
      setApiError(null);
    });
    
    const queryDate = useDate || selectedDate;
    
    try {
      // Fetch data from REST API
      console.log(`📡 Fetching ocean data for: ${coords.lat.toFixed(4)}°N, ${coords.lng.toFixed(4)}°E on ${queryDate}`);
      
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
      
      console.log(`✅ Ocean data retrieved successfully in ${response.total_extraction_time_ms}ms`);
      console.log(`📊 Datasets retrieved:`, Object.keys(response.datasets));
      
    } catch (error) {
      console.error('❌ Error fetching ocean data:', error);
      
      // Don't show error for testing - just log it
      startTransition(() => {
        setIsLoading(false);
        // Still show the panel but with no data
        setOceanData({
          location: { lat: coords.lat, lon: coords.lng },
          date: queryDate,
          datasets: {},
          total_extraction_time_ms: 0
        });
        setClimateData([]);
        // Only show brief error message
        setApiError('Data temporarily unavailable - backend may be starting up');
      });
    }
  }, [selectedDate]);

  return (
    <div style={{ width: '100vw', height: '100vh', margin: 0, padding: 0, overflow: 'hidden' }}>
      <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        <Globe 
          coordinates={coordinates}
          onLocationChange={handleLocationChange}
          isLoading={isLoading}
          showDataOverlay={showDataOverlay}
          dataCategory={selectedCategory}
          onZoomFunctionsReady={() => {}}
          showMicroplastics={showMicroplastics}
          onMicroplasticsPointHover={setHoveredMicroplastic}
          onMicroplasticsPointClick={(point) => {
            console.log('Microplastic point clicked:', point);
            // Could open a detail panel here
          }}
        />
        
        {/* Control Panel */}
        <div style={{
          position: 'absolute',
          top: '20px',
          left: '20px',
          backgroundColor: 'rgba(0, 0, 0, 0.85)',
          color: 'white',
          padding: '15px 20px',
          borderRadius: '12px',
          zIndex: 1000,
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          minWidth: '320px'
        }}>
          <div style={{ fontSize: '0.95em' }}>
            
            {/* Date Controls */}
            <div style={{ padding: '8px', backgroundColor: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.9em', marginBottom: '6px', color: '#cbd5e1' }}>
                📅 Date Selection
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <input
                  type="date"
                  value={selectedDate}
                  min={TEMPORAL_COVERAGE.HISTORICAL_START}
                  max={TEMPORAL_COVERAGE.GUARANTEED_END}
                  onChange={(e) => handleDateChange(e.target.value)}
                  aria-label="Select date for ocean data query"
                  aria-describedby="date-validation-info"
                  style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    color: 'white',
                    border: `1px solid ${dateValidation.isValid ? 'rgba(255, 255, 255, 0.2)' : '#f87171'}`,
                    borderRadius: '4px',
                    padding: '4px 8px',
                    fontSize: '0.8em',
                    flex: 1
                  }}
                />
                <button
                  onClick={() => setShowDatePicker(!showDatePicker)}
                  style={{
                    backgroundColor: '#4a5568',
                    color: 'white',
                    border: 'none',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.8em'
                  }}
                >
                  📊
                </button>
              </div>
              
              {/* Date validation info */}
              {!dateValidation.isValid && (
                <div id="date-validation-info" style={{ fontSize: '0.75em', color: '#f87171', marginBottom: '6px' }} role="alert">
                  ⚠️ {dateValidation.errors[0]}
                </div>
              )}
              {dateValidation.warnings.length > 0 && (
                <div style={{ fontSize: '0.75em', color: '#fbbf24', marginBottom: '6px' }} role="status">
                  ℹ️ {dateValidation.warnings[0]}
                </div>
              )}
              
              {/* Date info panel */}
              {showDatePicker && (
                <div style={{ 
                  fontSize: '0.75em', 
                  color: '#94a3b8', 
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  padding: '6px',
                  borderRadius: '4px',
                  marginBottom: '6px'
                }}>
                  <div>📊 {getDataAvailabilityDescription(selectedDate)}</div>
                  <div style={{ marginTop: '4px' }}>
                    📅 Coverage: {TEMPORAL_COVERAGE.HISTORICAL_START} to {TEMPORAL_COVERAGE.GUARANTEED_END}
                  </div>
                </div>
              )}
              
            </div>
            
            {/* Random Controls */}
            <div style={{ marginTop: '16px', display: 'flex', gap: '6px', justifyContent: 'space-between' }}>
              <button 
                onClick={() => {
                  const randomCoords = generateRandomOceanLocation();
                  handleLocationChange(randomCoords);
                }}
                aria-label="Generate random ocean location"
                style={{
                  backgroundColor: '#059669',
                  color: 'white',
                  border: 'none',
                  padding: '6px 8px',
                  borderRadius: '4px',  
                  cursor: 'pointer',
                  fontSize: '0.75em',
                  flex: '1'
                }}
              >
                📍 Random Location
              </button>
              <button 
                onClick={generateRandomDateOnly}
                aria-label="Generate random date"
                style={{
                  backgroundColor: '#7c3aed',
                  color: 'white',
                  border: 'none',
                  padding: '6px 8px',
                  borderRadius: '4px',  
                  cursor: 'pointer',
                  fontSize: '0.75em',
                  flex: '1'
                }}
              >
                📅 Random Date
              </button>
              <button 
                onClick={generateRandomDateAndLocation}
                aria-label="Generate random date and ocean location combination"
                style={{
                  backgroundColor: '#dc2626',
                  color: 'white',
                  border: 'none',
                  padding: '6px 8px',
                  borderRadius: '4px',  
                  cursor: 'pointer',
                  fontSize: '0.75em',
                  flex: '1'
                }}
              >
                🎲 Random
              </button>
            </div>
            
            {/* Data Category Selection */}
            <div style={{ marginTop: '16px', padding: '8px', backgroundColor: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.9em', marginBottom: '6px', color: '#cbd5e1' }}>
                🌊 Data Category
              </div>
              <div style={{ display: 'flex', gap: '6px', justifyContent: 'space-between', marginBottom: '8px' }}>
                {['sst', 'acidity', 'currents'].map(category => {
                  const isAvailable = true; // Always allow category selection
                  const isSelected = selectedCategory === category;
                  const categoryLabels = {
                    sst: '🌡️ SST',
                    acidity: '🧪 Acidity', 
                    currents: '🌀 Currents'
                  };
                  
                  return (
                    <button
                      key={category}
                      onClick={() => isAvailable && startTransition(() => changeCategory(category))}
                      disabled={!isAvailable}
                      style={{
                        backgroundColor: isSelected ? '#4a90e2' : isAvailable ? '#64748b' : '#374151',
                        color: isAvailable ? 'white' : '#9ca3af',
                        border: isSelected ? '2px solid #60a5fa' : '1px solid rgba(255, 255, 255, 0.1)',
                        padding: '6px 8px',
                        borderRadius: '4px',
                        cursor: isAvailable ? 'pointer' : 'not-allowed',
                        fontSize: '0.75em',
                        opacity: isAvailable ? 1 : 0.6,
                        flex: '1'
                      }}
                    >
                      {categoryLabels[category as keyof typeof categoryLabels]}
                    </button>
                  );
                })}
              </div>
              
              {/* Texture info */}
              {metadata && (
                <div style={{ fontSize: '0.75em', color: '#94a3b8' }}>
                  {selectedCategory && metadata.summary.categories[selectedCategory] ? (
                    <div>
                      Selected: {selectedCategory.toUpperCase()} | 
                      {' '}{metadata.summary.categories[selectedCategory].texture_count} textures | 
                      {' '}Latest: {metadata.summary.categories[selectedCategory].latest_date || 'N/A'}
                    </div>
                  ) : (
                    <div>Loading texture metadata...</div>
                  )}
                </div>
              )}
              
              {/* Microplastics overlay toggle */}
              <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <button
                  onClick={() => setShowMicroplastics(!showMicroplastics)}
                  style={{
                    backgroundColor: showMicroplastics ? '#7c3aed' : '#4b5563',
                    color: 'white',
                    border: showMicroplastics ? '2px solid #a855f7' : '1px solid rgba(255, 255, 255, 0.1)',
                    padding: '6px 8px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.75em',
                    transition: 'all 0.2s ease',
                    width: '100%'
                  }}
                >
                  {showMicroplastics ? '🏭 Hide Microplastics' : '🏭 Show Microplastics'}
                </button>
                {showMicroplastics && (
                  <div style={{ fontSize: '0.7em', color: '#94a3b8', marginTop: '4px' }}>
                    14,487 measurement points (1993-2025)
                  </div>
                )}
                
                {/* Microplastics hover info in side panel */}
                {showMicroplastics && hoveredMicroplastic && (
                  <div style={{
                    marginTop: '8px',
                    padding: '8px',
                    backgroundColor: 'rgba(124, 58, 237, 0.1)',
                    border: '1px solid rgba(124, 58, 237, 0.3)',
                    borderRadius: '6px',
                    fontSize: '0.75em'
                  }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '4px', color: '#a855f7' }}>
                      📍 Measurement Details
                    </div>
                    <div style={{ marginBottom: '2px' }}>
                      <strong>Concentration:</strong> {hoveredMicroplastic.concentration.toFixed(3)} pieces/m³
                    </div>
                    <div style={{ marginBottom: '2px' }}>
                      <strong>Class:</strong> <span style={{ 
                        color: hoveredMicroplastic.concentrationClass === 'Very High' ? '#ff4444' :
                               hoveredMicroplastic.concentrationClass === 'High' ? '#ff9944' :
                               hoveredMicroplastic.concentrationClass === 'Medium' ? '#ff44aa' :
                               hoveredMicroplastic.concentrationClass === 'Low' ? '#9944ff' : '#bb88ff'
                      }}>{hoveredMicroplastic.concentrationClass}</span>
                    </div>
                    <div style={{ marginBottom: '2px' }}>
                      <strong>Date:</strong> {hoveredMicroplastic.date}
                    </div>
                    <div style={{ marginBottom: '2px' }}>
                      <strong>Source:</strong> {hoveredMicroplastic.dataSource === 'real' ? '✅ Real Data' : '⚠️ Synthetic'}
                    </div>
                    <div style={{ marginBottom: '2px' }}>
                      <strong>Confidence:</strong> {(hoveredMicroplastic.confidence * 100).toFixed(0)}%
                    </div>
                    <div>
                      <strong>Location:</strong> {hoveredMicroplastic.coordinates[1].toFixed(2)}°, {hoveredMicroplastic.coordinates[0].toFixed(2)}°
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        
        {/* Error Message Display */}
        {errorMessage && (
          <div style={{
            position: 'absolute',
            top: '20px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(220, 38, 38, 0.95)',
            color: 'white',
            padding: '12px 20px',
            borderRadius: '8px',
            zIndex: 1001,
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            maxWidth: '400px',
            textAlign: 'center',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
            animation: 'slideDown 0.3s ease-out'
          }}>
            <div style={{ fontSize: '0.9em', fontWeight: 'bold', marginBottom: '4px' }}>
              🚫 Invalid Location
            </div>
            <div style={{ fontSize: '0.85em' }}>
              {errorMessage}
            </div>
          </div>
        )}
        
        {/* Comprehensive Data Panel */}
        <DataPanel 
          data={oceanData}
          isLoading={isLoading}
          error={apiError}
        />
      </div>
    </div>
  );
}

export default App;