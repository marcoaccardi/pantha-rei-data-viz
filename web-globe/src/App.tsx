import { useState } from 'react';
import Globe from './components/Globe';
import { useWebSocket } from './hooks/useWebSocket';
import type { Coordinates, ClimateDataResponse } from './utils/types';

function App() {
  const [coordinates, setCoordinates] = useState<Coordinates>({ lat: 0, lng: 0 });
  const [climateData, setClimateData] = useState<ClimateDataResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showSSTOverlay, setShowSSTOverlay] = useState(false);

  // Function to generate random ocean coordinates
  const generateRandomOceanLocation = () => {
    // Ocean coordinates (avoiding land masses)
    const oceanLocations = [
      { lat: 40.7589, lng: -73.9851 }, // North Atlantic
      { lat: -34.6037, lng: -58.3816 }, // South Atlantic  
      { lat: 35.6762, lng: 139.6503 }, // North Pacific
      { lat: -33.8688, lng: 151.2093 }, // South Pacific
      { lat: 25.2048, lng: 55.2708 }, // Arabian Sea
      { lat: -26.2041, lng: 28.0473 }, // Indian Ocean
      { lat: 64.2008, lng: -149.4937 }, // Arctic Ocean
      { lat: -70.0000, lng: 2.0000 }, // Southern Ocean
    ];
    
    const randomLocation = oceanLocations[Math.floor(Math.random() * oceanLocations.length)];
    
    // Add some random variation
    const lat = randomLocation.lat + (Math.random() - 0.5) * 10;
    const lng = randomLocation.lng + (Math.random() - 0.5) * 20;
    
    return { 
      lat: Math.max(-85, Math.min(85, lat)), 
      lng: Math.max(-180, Math.min(180, lng)) 
    };
  };

  const { sendMessage, isConnected } = useWebSocket({
    onMessage: (message) => {
      switch (message.type) {
        case 'climate_data':
          if (message.payload.climateData) {
            setClimateData(message.payload.climateData);
          }
          setIsLoading(false);
          break;
        case 'progress':
          console.log('Progress:', message.payload.message);
          break;
        case 'error':
          console.error('WebSocket error:', message.payload.message);
          setIsLoading(false);
          break;
      }
    }
  });

  const handleLocationChange = (coords: Coordinates) => {
    setCoordinates(coords);
    setIsLoading(true);
    
    if (isConnected) {
      sendMessage({
        type: 'coordinate_data',
        payload: {
          coordinates: coords,
          timestamp: new Date().toISOString()
        }
      });
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', margin: 0, padding: 0, overflow: 'hidden' }}>
      <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        <Globe 
          coordinates={coordinates}
          onLocationChange={handleLocationChange}
          isLoading={isLoading}
          showSSTOverlay={showSSTOverlay}
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
          border: '1px solid rgba(255, 255, 255, 0.1)'
        }}>
          <div style={{ fontSize: '0.95em' }}>
            <div><strong>Coordinates:</strong> {coordinates.lat.toFixed(4)}°, {coordinates.lng.toFixed(4)}°</div>
            <div><strong>Status:</strong> <span style={{ color: isConnected ? '#4ade80' : '#f87171' }}>
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </span></div>
            <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button 
                onClick={() => setShowSSTOverlay(!showSSTOverlay)}
                style={{
                  backgroundColor: showSSTOverlay ? '#4a90e2' : '#64748b',
                  color: 'white',
                  border: 'none',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.9em'
                }}
              >
                {showSSTOverlay ? '🌡️ Hide SST Overlay' : '🌡️ Show SST Overlay'}
              </button>
              
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
                🎲 Random Ocean Location
              </button>
            </div>
          </div>
        </div>
        
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
              ⏳ Loading climate data...
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
                {climateData.map((data, index) => {
                  const displayValue = typeof data.value === 'number' ? 
                    data.value.toFixed(2) : data.value;
                  
                  const qualityColor = data.quality === 'V' ? '#4ade80' : 
                                     data.quality === 'S' ? '#3b82f6' :
                                     data.quality === 'C' ? '#fbbf24' : '#f87171';
                  
                  return (
                    <div key={index} style={{ 
                      marginBottom: '10px', 
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
                        {data.description || data.parameter.replace('_', ' ')}
                      </div>
                      <div style={{ 
                        color: '#cbd5e1', 
                        fontSize: '1.2em', 
                        margin: '6px 0',
                        fontWeight: '600'
                      }}>
                        {displayValue} {data.units}
                      </div>
                      <div style={{ fontSize: '0.75em', color: '#94a3b8', lineHeight: '1.4' }}>
                        <div>Source: {data.data_source}</div>
                        <div>Quality: <span style={{ color: qualityColor, fontWeight: '600' }}>{data.quality}</span>
                        {data.confidence && ` | Confidence: ${(data.confidence * 100).toFixed(0)}%`}</div>
                        <div>Zone: {data.climate_zone}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;