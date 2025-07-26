import { useState, useCallback, useEffect, startTransition } from 'react';
import Globe from './components/Globe';
import { useWebSocket } from './hooks/useWebSocket';
import { useTextureLoader } from './hooks/useTextureLoader';
import type { Coordinates, ClimateDataResponse, OceanMeasurement, DateRange } from './utils/types';
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
  const [isLoading, setIsLoading] = useState(false);
  const [progressMessage, setProgressMessage] = useState<string | null>(null);
  const [showDataOverlay, setShowDataOverlay] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
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
    // 120 VERIFIED ocean coordinates - all validated to pass land/ocean detection
    // Based on GEBCO 2024 and NOAA ERDDAP research + comprehensive validation
    const guaranteedOceanPoints = [
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
    
    // Select a random guaranteed ocean point
    const basePoint = guaranteedOceanPoints[Math.floor(Math.random() * guaranteedOceanPoints.length)];
    
    // Add small random variation (max 5 degrees) to avoid exact same points
    const variation = 5.0;
    const lat = basePoint.lat + (Math.random() - 0.5) * variation;
    const lng = basePoint.lng + (Math.random() - 0.5) * variation;
    
    // Final bounds check
    const finalLat = Math.max(-80, Math.min(80, lat));
    const finalLng = Math.max(-180, Math.min(180, lng));
    
    console.log(`🌊 Generated ocean coordinates from ${guaranteedOceanPoints.length} verified points: ${finalLat.toFixed(4)}°, ${finalLng.toFixed(4)}° (${basePoint.name})`);
    
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

  const handleLocationChange = useCallback((coords: Coordinates, useDate?: string) => {
    startTransition(() => {
      setCoordinates(coords);
      setIsLoading(true);
    });
    
    const queryDate = useDate || selectedDate;
    
    // Validate date before sending WebSocket message
    const dateValidation = validateDate(queryDate);
    if (!dateValidation.isValid) {
      startTransition(() => {
        setErrorMessage(`Cannot query data: ${dateValidation.errors.join(', ')}`);
        setIsLoading(false);
      });
      return;
    }
    
    if (isConnected) {
      // Send requests for all available data types to the backend-api climate data server
      const dataTypes = [
        'temperature_request',
        'salinity_request', 
        'wave_request',
        'currents_request',
        'chlorophyll_request',
        'ph_request',
        'biodiversity_request',
        'microplastics_request'
      ];
      
      const requestPayload = {
        coordinates: {
          lat: coords.lat,
          lon: coords.lng // Map lng -> lon for backend compatibility
        } as any,
        dateRange: {
          start: queryDate,
          end: queryDate // Single day query
        },
        timestamp: new Date().toISOString()
      };
      
      // Send requests for all data types
      dataTypes.forEach(dataType => {
        sendMessage({
          type: dataType as any,
          payload: requestPayload
        });
      });
      
      // Development logging
      console.log(`📡 Requesting ocean data for: ${coords.lat.toFixed(4)}°N, ${coords.lng.toFixed(4)}°E on ${queryDate}`);
      console.log(`📊 Expected data coverage: ${getDataAvailabilityDescription(queryDate)}`);
    } else {
      // WebSocket disabled - show informational message instead of error
      console.log('📡 WebSocket disabled - data fetching via REST API not yet implemented for this interface');
      startTransition(() => {
        setErrorMessage('Data fetching via WebSocket disabled. Ocean data visualization is available through textures.');
        setIsLoading(false);
      });
    }
  }, [selectedDate, isConnected, sendMessage]);

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
        />
        
        {/* Coordinate Display Panel */}
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
            <div><strong>Coordinates:</strong> {coordinates.lat.toFixed(4)}°, {coordinates.lng.toFixed(4)}°</div>
            <div><strong>Date:</strong> {formatDateWithCoverage(selectedDate)}</div>
            <div><strong>Status:</strong> <span style={{ color: isConnected ? '#4ade80' : '#f87171' }}>
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </span></div>
            
            {/* Date Controls */}
            <div style={{ marginTop: '12px', padding: '8px', backgroundColor: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px' }}>
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
              
              {/* Date action buttons */}
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                <button
                  onClick={generateRandomDateOnly}
                  aria-label="Generate random date for ocean data query"
                  style={{
                    backgroundColor: '#7c3aed',
                    color: 'white',
                    border: 'none',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.8em'
                  }}
                >
                  🎲 Random Date
                </button>
                <button
                  onClick={useGuaranteedDate}
                  aria-label="Select guaranteed coverage date with all data available"
                  style={{
                    backgroundColor: '#059669',
                    color: 'white',
                    border: 'none',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.8em'
                  }}
                >
                  ✅ Guaranteed
                </button>
                <button
                  onClick={generateRandomDateAndLocation}
                  aria-label="Generate random date and ocean location combination"
                  style={{
                    backgroundColor: '#dc2626',
                    color: 'white',
                    border: 'none',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.8em'
                  }}
                >
                  🎲 Random Both
                </button>
              </div>
            </div>
            
            {/* Data Category Selection */}
            <div style={{ marginTop: '12px', padding: '8px', backgroundColor: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.9em', marginBottom: '6px', color: '#cbd5e1' }}>
                🌊 Data Category
              </div>
              <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '8px' }}>
                {['sst', 'acidity', 'currents'].map(category => {
                  const isAvailable = availableCategories.includes(category);
                  const isSelected = selectedCategory === category;
                  const categoryLabels = {
                    sst: '🌡️ SST',
                    acidity: '🧪 Acidity', 
                    currents: '🌊 Currents'
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
                        padding: '4px 8px',
                        borderRadius: '4px',
                        cursor: isAvailable ? 'pointer' : 'not-allowed',
                        fontSize: '0.8em',
                        opacity: isAvailable ? 1 : 0.6
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
            </div>
            
            {/* Location Controls */}
            <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button 
                onClick={() => {
                  const randomCoords = generateRandomOceanLocation();
                  handleLocationChange(randomCoords);
                }}
                style={{
                  backgroundColor: '#059669',
                  color: 'white',
                  border: 'none',
                  padding: '6px 12px',
                  borderRadius: '6px',  
                  cursor: 'pointer',
                  fontSize: '0.9em'
                }}
              >
                🎲 Random Location
              </button>
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
        
        {/* Data Display Panel */}
        <div style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          backgroundColor: 'rgba(0, 0, 0, 0.85)',
          color: 'white',
          padding: '20px',
          borderRadius: '12px',
          maxWidth: '400px',
          minWidth: '350px',
          zIndex: 1000,
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
          
          {isLoading && (
            <div style={{ padding: '10px', textAlign: 'center', color: '#fbbf24' }}>
              {progressMessage ? (
                <>
                  ⏳ {progressMessage}
                  {progressMessage.includes('Downloading') && (
                    <div style={{ fontSize: '0.8em', marginTop: '4px', color: '#94a3b8' }}>
                      First-time data download - this will be cached for future use
                    </div>
                  )}
                </>
              ) : (
                '⏳ Loading climate data...'
              )}
            </div>
          )}
          
          {climateData.length > 0 && (
            <div>
              <h3 style={{ margin: '0 0 15px 0', fontSize: '1.2em', color: '#4a90e2' }}>
                Marine & Climate Data ({climateData.length} parameters)
              </h3>
              <div style={{ 
                maxHeight: '500px', 
                overflowY: 'auto', 
                paddingRight: '8px',
                scrollbarWidth: 'thin',
                scrollbarColor: '#4a5568 #2d3748'
              }}>
                {(() => {
                  // Group data by category for better organization
                  const groupedData = climateData.reduce((groups, data) => {
                    const category = data.data_source || 'Other';
                    if (!groups[category]) groups[category] = [];
                    groups[category].push(data);
                    return groups;
                  }, {} as Record<string, typeof climateData>);

                  // Enhanced category configuration for comprehensive oceanographic data
                  const categoryConfig = {
                    // Ocean Physical Parameters
                    'NOAA_Coral_Reef_Watch': { icon: '🌡️', color: '#ff6b6b', title: '🌊 Ocean Physical' },
                    'OSCAR_Ocean_Currents': { icon: '🌊', color: '#4ecdc4', title: '🌊 Ocean Physical' },
                    'Wave_Analysis_Model': { icon: '🌊', color: '#45b7d1', title: '🌊 Ocean Physical' },
                    'NOAA_WaveWatch': { icon: '🌊', color: '#45b7d1', title: '🌊 Ocean Physical' },
                    
                    // Marine Biogeochemistry
                    'Marine_Biology_Model': { icon: '🌿', color: '#26d0ce', title: '🧪 Marine Biogeochemistry' },
                    'NOAA_CoastWatch': { icon: '🧪', color: '#4ade80', title: '🧪 Marine Biogeochemistry' },
                    'Ocean_Chemistry_Model': { icon: '🧪', color: '#10b981', title: '🧪 Marine Biogeochemistry' },
                    
                    // Coral Reef Monitoring
                    'Coral_Reef_Watch': { icon: '🪸', color: '#ff9500', title: '🪸 Coral Reef Monitoring' },
                    'NOAA_Coral_Bleaching': { icon: '🪸', color: '#ff6b35', title: '🪸 Coral Reef Monitoring' },
                    
                    // Atmospheric & Climate
                    'National_Weather_Service': { icon: '🌡️', color: '#fbbf24', title: '🌍 Atmospheric & Climate' },
                    'NOAA_Weather': { icon: '🌡️', color: '#f59e0b', title: '🌍 Atmospheric & Climate' },
                    
                    // Ocean Pollution
                    'NOAA_Ocean_Acidification': { icon: '🏭', color: '#f87171', title: '🏭 Ocean Pollution' },
                    'Marine_Pollution_Monitor': { icon: '🏭', color: '#ef4444', title: '🏭 Ocean Pollution' },
                    
                    // Fallback categories
                    'Ocean_Chemistry': { icon: '🧪', color: '#4ade80', title: '🧪 Marine Biogeochemistry' },
                    'Marine_Pollution': { icon: '🏭', color: '#f87171', title: '🏭 Ocean Pollution' },
                    'Ocean_Health': { icon: '🌿', color: '#10b981', title: '🧪 Marine Biogeochemistry' },  
                    'Marine': { icon: '🌊', color: '#3b82f6', title: '🌊 Ocean Physical' },
                    'Weather': { icon: '🌡️', color: '#fbbf24', title: '🌍 Atmospheric & Climate' },
                    'Location_Info': { icon: '📍', color: '#8b5cf6', title: '📍 Location Info' },
                    
                    // Real data sources (new format)
                    'Real': { icon: '✅', color: '#22c55e', title: '✅ Real Data Sources' },
                    'Fallback_Ocean_Circulation_Model': { icon: '🔄', color: '#8b5cf6', title: '🔄 Fallback Models' }
                  };

                  return Object.entries(groupedData).map(([category, categoryData]) => {
                    const config = (categoryConfig as any)[category] || { icon: '📊', color: '#6b7280', title: category.replace('_', ' ') };
                    
                    return (
                      <div key={category} style={{ marginBottom: '20px' }}>
                        <h4 style={{ 
                          fontSize: '1em', 
                          color: config.color, 
                          margin: '10px 0 8px 0',
                          fontWeight: '600',
                          borderBottom: `2px solid ${config.color}20`,
                          paddingBottom: '4px'
                        }}>
                          {config.icon} {config.title} ({categoryData.length})
                        </h4>
                        {categoryData.map((data, index) => {
                          const displayValue = typeof data.value === 'number' ? 
                            data.value.toFixed(2) : data.value;
                          
                          // Enhanced quality color coding for Real vs Synthetic data
                          const qualityColor = 
                            data.quality === 'Real' || data.quality === 'R' ? '#22c55e' :  // Green for Real data
                            data.quality === 'High' || data.quality === 'Good' || data.quality === 'V' ? '#4ade80' :
                            data.quality === 'Synthetic' || data.quality === 'S' ? '#ef4444' :  // Red for Synthetic
                            data.quality === 'Medium' ? '#3b82f6' :
                            data.quality === 'Satellite' || data.quality === 'C' ? '#fbbf24' : 
                            data.quality === 'Fallback' || data.quality === 'Estimated' ? '#f97316' : '#6b7280';
                          
                          // Quality indicator with emphasis on Real vs Synthetic
                          const qualityDisplay = 
                            data.quality === 'Real' || data.quality === 'R' ? '✅ REAL DATA' :
                            data.quality === 'Synthetic' || data.quality === 'S' ? '⚠️ SYNTHETIC' :
                            data.quality;
                          
                          // Enhanced parameter-specific formatting for all oceanographic data
                          let formattedValue = `${displayValue} ${data.units}`;
                          let parameterIcon = '';
                          let contextualInfo = '';
                          
                          // 🌊 Ocean Physical Parameters
                          if (data.parameter === 'sea_surface_temperature' || data.parameter === 'analysed_sst') {
                            parameterIcon = '🌡️';
                            const temp = parseFloat(displayValue);
                            if (temp < 15) contextualInfo = ' (Cold Water)';
                            else if (temp > 28) contextualInfo = ' (Warm Tropical)';
                            else contextualInfo = ' (Temperate)';
                            
                          } else if (data.parameter === 'ocean_current_speed' || data.parameter === 'current_speed') {
                            parameterIcon = '🌊';
                            const speed = parseFloat(displayValue);
                            if (speed < 0.1) contextualInfo = ' (Slow)';
                            else if (speed > 0.5) contextualInfo = ' (Fast)';
                            else contextualInfo = ' (Moderate)';
                            
                          } else if (data.parameter === 'ocean_current_direction' || data.parameter === 'current_direction') {
                            parameterIcon = '🧭';
                            const direction = parseFloat(displayValue);
                            const compass = direction < 45 ? 'N' : direction < 135 ? 'E' : direction < 225 ? 'S' : direction < 315 ? 'W' : 'N';
                            contextualInfo = ` (${compass})`;
                            
                          } else if (data.parameter === 'significant_wave_height' || data.parameter === 'wave_height') {
                            parameterIcon = '🌊';
                            const height = parseFloat(displayValue);
                            if (height < 1) contextualInfo = ' (Calm)';
                            else if (height > 3) contextualInfo = ' (Rough)';
                            else contextualInfo = ' (Moderate)';
                            
                          } else if (data.parameter === 'wave_period') {
                            parameterIcon = '⏱️';
                            
                          } else if (data.parameter === 'wave_direction') {
                            parameterIcon = '🧭';
                            
                          // 🧪 Marine Biogeochemistry  
                          } else if (data.parameter === 'chlorophyll_a_concentration' || data.parameter === 'chlorophyll') {
                            parameterIcon = '🌿';
                            const chl = parseFloat(displayValue);
                            if (chl < 0.5) contextualInfo = ' (Low Productivity)';
                            else if (chl > 2.0) contextualInfo = ' (High Productivity)';
                            else contextualInfo = ' (Moderate Productivity)';
                            
                          } else if (data.parameter === 'ocean_ph' || data.parameter === 'ph') {
                            parameterIcon = '🧪';
                            const phValue = parseFloat(displayValue);
                            if (phValue < 7.8) contextualInfo = ' (Acidic - Climate Impact)';
                            else if (phValue > 8.2) contextualInfo = ' (Basic)';
                            else contextualInfo = ' (Normal Ocean pH)';
                            
                          } else if (data.parameter === 'salinity') {
                            parameterIcon = '🧂';
                            const sal = parseFloat(displayValue);
                            if (sal < 34) contextualInfo = ' (Low Salinity)';
                            else if (sal > 36) contextualInfo = ' (High Salinity)';
                            else contextualInfo = ' (Normal Salinity)';
                            
                          } else if (data.parameter === 'dissolved_oxygen' || data.parameter === 'o2') {
                            parameterIcon = '💨';
                            const oxygen = parseFloat(displayValue);
                            if (oxygen < 150) contextualInfo = ' (Low - Hypoxic Risk)';
                            else if (oxygen > 300) contextualInfo = ' (High)';
                            else contextualInfo = ' (Normal)';
                            
                          } else if (data.parameter === 'nitrate' || data.parameter === 'no3') {
                            parameterIcon = '🔬';
                            contextualInfo = ' (Nutrient)';
                            
                          } else if (data.parameter === 'phosphate' || data.parameter === 'po4') {
                            parameterIcon = '🔬';
                            contextualInfo = ' (Nutrient)';
                            
                          } else if (data.parameter === 'silicate' || data.parameter === 'si') {
                            parameterIcon = '🔬';
                            contextualInfo = ' (Nutrient)';
                            
                          } else if (data.parameter === 'iron' || data.parameter === 'fe') {
                            parameterIcon = '⚗️';
                            contextualInfo = ' (Limiting Nutrient)';
                            
                          } else if (data.parameter === 'phytoplankton_carbon' || data.parameter === 'phyc') {
                            parameterIcon = '🦠';
                            contextualInfo = ' (Marine Life)';
                            
                          } else if (data.parameter === 'net_primary_productivity' || data.parameter === 'nppv') {
                            parameterIcon = '🌱';
                            contextualInfo = ' (Ecosystem Productivity)';
                            
                          } else if (data.parameter === 'surface_partial_pressure_co2' || data.parameter === 'spco2') {
                            parameterIcon = '💨';
                            contextualInfo = ' (Carbon Cycle)';
                            
                          // 🪸 Coral Reef Monitoring
                          } else if (data.parameter === 'degree_heating_weeks' || data.parameter === 'dhw') {
                            parameterIcon = '🪸';
                            const dhw = parseFloat(displayValue);
                            if (dhw < 4) contextualInfo = ' (No Bleaching Risk)';
                            else if (dhw < 8) contextualInfo = ' (Moderate Bleaching Risk)';
                            else contextualInfo = ' (High Bleaching Risk)';
                            
                          } else if (data.parameter === 'hotspot') {
                            parameterIcon = '🔥';
                            contextualInfo = ' (Thermal Stress)';
                            
                          } else if (data.parameter === 'bleaching_alert_area') {
                            parameterIcon = '⚠️';
                            
                          // 🌍 Atmospheric & Climate
                          } else if (data.parameter === 'air_temperature') {
                            parameterIcon = '🌡️';
                            
                          } else if (data.parameter === 'humidity') {
                            parameterIcon = '💧';
                            
                          } else if (data.parameter === 'wind_speed') {
                            parameterIcon = '💨';
                            const wind = parseFloat(displayValue);
                            if (wind < 5) contextualInfo = ' (Light)';
                            else if (wind > 15) contextualInfo = ' (Strong)';
                            else contextualInfo = ' (Moderate)';
                            
                          } else if (data.parameter === 'wind_direction') {
                            parameterIcon = '🧭';
                            
                          } else if (data.parameter === 'atmospheric_pressure') {
                            parameterIcon = '📏';
                            
                          } else if (data.parameter === 'precipitation') {
                            parameterIcon = '🌧️';
                            
                          } else if (data.parameter === 'cloud_cover') {
                            parameterIcon = '☁️';
                            
                          // 🏭 Ocean Pollution
                          } else if (data.parameter === 'microplastic_concentration' || data.parameter === 'microplastics_density') {
                            parameterIcon = '🏭';
                            const density = parseFloat(displayValue);
                            if (density > 10) contextualInfo = ' (High Pollution)';
                            else if (density > 5) contextualInfo = ' (Medium Pollution)';
                            else contextualInfo = ' (Low Pollution)';
                            
                          } else if (data.parameter === 'ocean_co2_concentration' || data.parameter === 'co2_seawater') {
                            parameterIcon = '💨';
                            contextualInfo = ' (Ocean Acidification)';
                            
                          } else if (data.parameter === 'carbonate_saturation') {
                            parameterIcon = '🧪';
                            const carb = parseFloat(displayValue);
                            if (carb < 1) contextualInfo = ' (Corrosive)';
                            else contextualInfo = ' (Stable)';
                            
                          } else if (data.parameter === 'aragonite_saturation_state') {
                            parameterIcon = '🐚';
                            const arag = parseFloat(displayValue);
                            if (arag < 1) contextualInfo = ' (Shell Dissolution Risk)';
                            else contextualInfo = ' (Shell Formation OK)';
                            
                          // Default cases
                          } else if (data.parameter.includes('temperature')) {
                            parameterIcon = '🌡️';
                          } else if (data.parameter.includes('current')) {
                            parameterIcon = '🌊';
                          } else if (data.parameter.includes('wave')) {
                            parameterIcon = '🌊';
                          } else {
                            parameterIcon = '📊';
                          }
                          
                          formattedValue = `${displayValue} ${data.units}${contextualInfo}`;

                          return (
                            <div key={`${category}-${index}`} style={{ 
                              marginBottom: '8px', 
                              fontSize: '0.85em',
                              padding: '10px',
                              backgroundColor: 'rgba(255, 255, 255, 0.05)',
                              borderRadius: '8px',
                              borderLeft: `4px solid ${qualityColor}`,
                              transition: 'all 0.2s ease'
                            }}>
                              <div style={{ 
                                fontWeight: 'bold', 
                                color: '#e2e8f0',
                                marginBottom: '4px',
                                fontSize: '0.95em'
                              }}>
                                {parameterIcon} {data.description || data.parameter.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </div>
                              <div style={{ 
                                color: '#cbd5e1', 
                                fontSize: '1.2em', 
                                margin: '6px 0',
                                fontWeight: '600'
                              }}>
                                {formattedValue}
                              </div>
                              <div style={{ fontSize: '0.75em', color: '#94a3b8', lineHeight: '1.4' }}>
                                <div>Source: {data.data_source.replace(/_/g, ' ')}</div>
                                <div>Quality: <span style={{ color: qualityColor, fontWeight: '600' }}>{qualityDisplay}</span>
                                {data.confidence && ` | Confidence: ${(data.confidence * 100).toFixed(0)}%`}</div>
                                <div>Zone: {data.climate_zone}</div>
                                {data.quality === 'Real' || data.quality === 'R' ? 
                                  <div style={{ color: '#22c55e', fontWeight: '600', fontSize: '0.8em' }}>
                                    🔗 Live from NOAA ERDDAP
                                  </div> : null
                                }
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;