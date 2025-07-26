import React from 'react';
import { MultiDatasetOceanResponse, OceanDataValue, OceanPointData } from '../utils/types';
import { classifyMeasurement, formatDirection } from '../services/oceanDataService';

interface DataPanelProps {
  data: MultiDatasetOceanResponse | null;
  isLoading: boolean;
  error: string | null;
}

const DataPanel: React.FC<DataPanelProps> = ({ data, isLoading, error }) => {
  const renderValue = (value: OceanDataValue, parameter: string): JSX.Element => {
    if (!value.valid || value.value === null) {
      return <span style={{ color: '#6b7280' }}>No data</span>;
    }

    const numValue = typeof value.value === 'number' ? value.value : parseFloat(value.value as string);
    
    // Special formatting for different parameter types
    if (parameter.includes('direction') || parameter === 'VMDR' || parameter === 'MWD') {
      return (
        <span>
          {numValue.toFixed(1)}° ({formatDirection(numValue)})
        </span>
      );
    }

    // Apply classification coloring for certain parameters
    const classification = classifyMeasurement(parameter, numValue);
    
    return (
      <span style={{ color: classification.color }}>
        {typeof value.value === 'number' ? value.value.toFixed(2) : value.value} {value.units}
      </span>
    );
  };

  const renderDataset = (datasetName: string, dataset: OceanPointData | { error: string }) => {
    if ('error' in dataset) {
      return (
        <div key={datasetName} style={{ marginBottom: '20px' }}>
          <h4 style={{ color: '#ef4444', marginBottom: '8px' }}>
            {datasetName.toUpperCase()} - Error
          </h4>
          <div style={{ color: '#f87171', fontSize: '0.9em' }}>
            {dataset.error}
          </div>
        </div>
      );
    }

    const data = dataset as OceanPointData;
    
    // Define sections and their variables
    const sections: Record<string, { title: string; icon: string; variables: string[] }> = {
      sst: {
        title: 'Sea Surface Temperature',
        icon: '🌡️',
        variables: ['sst', 'anom', 'err', 'ice']
      },
      currents: {
        title: 'Ocean Currents',
        icon: '🌊',
        variables: ['uo', 'vo', 'speed', 'direction', 'thetao', 'so']
      },
      waves: {
        title: 'Ocean Waves',
        icon: '🌊',
        variables: ['VHM0', 'VMDR', 'VTPK', 'MWD', 'PP1D', 'VTM10']
      },
      acidity: {
        title: 'Ocean Chemistry',
        icon: '🧪',
        variables: ['ph', 'dissic', 'dic', 'talk', 'o2', 'no3', 'po4', 'si']
      },
      microplastics: {
        title: 'Microplastics',
        icon: '🏭',
        variables: ['microplastics_concentration', 'confidence', 'data_source', 'concentration_class']
      }
    };

    const section = sections[datasetName];
    if (!section) return null;

    // Filter available variables
    const availableVars = section.variables.filter(v => v in data.data);
    if (availableVars.length === 0) {
      return (
        <div key={datasetName} style={{ marginBottom: '20px' }}>
          <h4 style={{ color: '#6b7280', marginBottom: '8px' }}>
            {section.icon} {section.title}
          </h4>
          <div style={{ color: '#9ca3af', fontSize: '0.9em' }}>
            No data available
          </div>
        </div>
      );
    }

    return (
      <div key={datasetName} style={{ 
        marginBottom: '24px',
        padding: '16px',
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        borderRadius: '8px',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        <h4 style={{ 
          color: '#60a5fa', 
          marginBottom: '12px',
          fontSize: '1.1em',
          fontWeight: '600'
        }}>
          {section.icon} {section.title}
        </h4>
        
        <div style={{ fontSize: '0.85em', color: '#e5e7eb' }}>
          {availableVars.map(varName => {
            const varData = data.data[varName];
            if (!varData) return null;
            
            return (
              <div key={varName} style={{ 
                marginBottom: '8px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '4px 0',
                borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
              }}>
                <span style={{ color: '#9ca3af' }}>
                  {varData.long_name || varName}:
                </span>
                <span style={{ fontWeight: '500' }}>
                  {renderValue(varData, varName)}
                </span>
              </div>
            );
          })}
        </div>
        
        {/* Special visualizations for certain datasets */}
        {datasetName === 'currents' && data.data.speed && data.data.direction && (
          <div style={{ 
            marginTop: '12px', 
            padding: '8px',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderRadius: '4px'
          }}>
            <div style={{ fontSize: '0.8em', color: '#60a5fa' }}>
              Current Vector: {data.data.speed.value} m/s @ {formatDirection(data.data.direction.value as number)}
            </div>
          </div>
        )}
        
        {datasetName === 'microplastics' && data.data.concentration_class && (
          <div style={{
            marginTop: '12px',
            padding: '8px',
            backgroundColor: 'rgba(124, 58, 237, 0.1)',
            borderRadius: '4px'
          }}>
            <div style={{ 
              fontSize: '0.9em', 
              color: classifyMeasurement('microplastics_concentration', 
                data.data.microplastics_concentration?.value as number || 0).color,
              fontWeight: '600'
            }}>
              {data.data.concentration_class.value}
            </div>
          </div>
        )}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div style={{
        position: 'absolute',
        top: '20px',
        right: '20px',
        backgroundColor: 'rgba(0, 0, 0, 0.9)',
        color: 'white',
        padding: '20px',
        borderRadius: '12px',
        width: '400px',
        maxHeight: '80vh',
        overflowY: 'auto',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '1.3em', color: '#60a5fa' }}>
          🌊 Ocean Data
        </h3>
        <div style={{ textAlign: 'center', padding: '40px 0', color: '#60a5fa' }}>
          <div style={{ fontSize: '2em', marginBottom: '8px' }}>⏳</div>
          <div>Loading ocean data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        position: 'absolute',
        top: '20px',
        right: '20px',
        backgroundColor: 'rgba(0, 0, 0, 0.9)',
        color: 'white',
        padding: '20px',
        borderRadius: '12px',
        width: '400px',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '1.3em', color: '#ef4444' }}>
          🌊 Ocean Data Error
        </h3>
        <div style={{ color: '#f87171', fontSize: '0.9em' }}>
          {error}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{
        position: 'absolute',
        top: '20px',
        right: '20px',
        backgroundColor: 'rgba(0, 0, 0, 0.9)',
        color: 'white',
        padding: '20px',
        borderRadius: '12px',
        width: '400px',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '1.3em', color: '#60a5fa' }}>
          🌊 Ocean Data
        </h3>
        <div style={{ color: '#9ca3af', fontSize: '0.9em', textAlign: 'center', padding: '20px 0' }}>
          <div style={{ marginBottom: '12px' }}>Click on the globe to view ocean data</div>
          <div style={{ fontSize: '0.8em', color: '#6b7280' }}>
            Or use the <strong>🎲 Random Location</strong> button to explore available data
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      position: 'absolute',
      top: '20px',
      right: '20px',
      backgroundColor: 'rgba(0, 0, 0, 0.9)',
      color: 'white',
      padding: '20px',
      borderRadius: '12px',
      width: '420px',
      maxHeight: '80vh',
      overflowY: 'auto',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      scrollbarWidth: 'thin',
      scrollbarColor: '#4a5568 #1a202c'
    }}>
      <h3 style={{ 
        margin: '0 0 16px 0', 
        fontSize: '1.3em', 
        color: '#60a5fa',
        borderBottom: '2px solid rgba(96, 165, 250, 0.3)',
        paddingBottom: '8px'
      }}>
        🌊 Ocean Data Analysis
      </h3>
      
      <div style={{ 
        marginBottom: '16px', 
        fontSize: '0.85em', 
        color: '#9ca3af',
        display: 'flex',
        justifyContent: 'space-between'
      }}>
        <span>📍 {data.location.lat.toFixed(4)}°, {data.location.lon.toFixed(4)}°</span>
        <span>📅 {data.date}</span>
      </div>
      
      {Object.entries(data.datasets).map(([name, dataset]) => 
        renderDataset(name, dataset)
      )}
      
      <div style={{ 
        marginTop: '16px', 
        paddingTop: '16px', 
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        fontSize: '0.75em',
        color: '#6b7280'
      }}>
        <div>⚡ Response time: {data.total_extraction_time_ms.toFixed(0)}ms</div>
      </div>
    </div>
  );
};

export default DataPanel;