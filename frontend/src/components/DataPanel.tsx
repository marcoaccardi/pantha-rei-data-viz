import React, { useState } from 'react';
import { MultiDatasetOceanResponse, OceanDataValue, OceanPointData } from '../utils/types';
import { classifyMeasurement, formatDirection } from '../services/oceanDataService';
import ParameterExplanation from './ParameterExplanation';

interface DataPanelProps {
  data: MultiDatasetOceanResponse | null;
  isLoading: boolean;
  error: string | null;
}

const DataPanel: React.FC<DataPanelProps> = ({ data, isLoading, error }) => {
  const [showDetailedMode, setShowDetailedMode] = useState(false);
  const [expandedParameters, setExpandedParameters] = useState<string[]>([]);
  const getFormattedLabel = (parameter: string, longName?: string): string => {
    const labelMap: Record<string, string> = {
      // SST parameters
      'sst': 'Sea Surface Temperature',
      'analysed_sst': 'Sea Surface Temperature',
      'ice': 'Sea ice concentration',
      'anom': 'Temperature anomaly',
      'err': 'Analysis error',
      
      // Acidity parameters  
      'ph': 'pH',
      'ph_insitu': 'pH (in situ)',
      'ph_insitu_total': 'pH (total scale)',
      'dissic': 'Dissolved inorganic carbon concentration',
      'dic': 'Dissolved inorganic carbon',  
      'talk': 'Total alkalinity',
      'pco2': 'Partial pressure CO₂',
      'revelle': 'Revelle factor',
      'o2': 'Dissolved oxygen',
      'no3': 'Nitrate concentration',
      'po4': 'Phosphate concentration', 
      'si': 'Silicate concentration',
      'chl': 'Chlorophyll-a',
      'nppv': 'Net primary production',
      
      // Currents parameters
      'uo': 'Eastward velocity',
      'vo': 'Northward velocity',
      'speed': 'Current speed',
      'direction': 'Current direction',
      'thetao': 'Sea water potential temperature',
      'so': 'Sea water salinity'
    };
    
    return labelMap[parameter] || longName || parameter;
  };

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

    // Special formatting for ice concentration (convert to percentage)
    if (parameter === 'ice') {
      if (numValue === 0 || isNaN(numValue)) {
        return <span style={{ color: '#6b7280' }}>No data</span>;
      }
      return (
        <span>
          {(numValue * 100).toFixed(1)}%
        </span>
      );
    }

    // Special formatting for temperature (ensure Celsius)
    if (parameter === 'sst' || parameter === 'analysed_sst') {
      return (
        <span style={{ color: classifyMeasurement(parameter, numValue).color }}>
          {numValue.toFixed(2)} Celsius
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

  const renderEcosystemInsights = () => {
    const insights = (data?.datasets as any)?._ecosystem_insights;
    if (!insights?.insights || insights.insights.length === 0) {
      return null;
    }

    return (
      <div style={{
        marginBottom: '24px',
        padding: '16px',
        backgroundColor: 'rgba(124, 58, 237, 0.1)',
        borderRadius: '8px',
        border: '2px solid rgba(124, 58, 237, 0.3)'
      }}>
        <h4 style={{
          color: '#a78bfa',
          marginBottom: '12px',
          fontSize: '1.1em',
          fontWeight: '600',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          🌊 Ecosystem Health Analysis
          <span style={{ fontSize: '0.8em', fontWeight: 'normal', color: '#9ca3af' }}>
            ({insights.measurement_count} parameters analyzed)
          </span>
        </h4>
        
        <div style={{ fontSize: '0.9em' }}>
          {insights.insights.map((insight: string, index: number) => (
            <div 
              key={index} 
              style={{
                marginBottom: '8px',
                padding: '8px 12px',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                borderRadius: '6px',
                color: '#e5e7eb',
                lineHeight: '1.4'
              }}
            >
              {insight}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderDataset = (datasetName: string, dataset: OceanPointData | { error: string }) => {
    if ('error' in dataset) {
      const sections: Record<string, { title: string; icon: string }> = {
        sst: { title: 'Temperature', icon: '🌡️' },
        currents: { title: 'Currents', icon: '🌀' },
        acidity: { title: 'Ocean Chemistry', icon: '🧪' }
      };
      
      const section = sections[datasetName] || { title: datasetName.toUpperCase(), icon: '📊' };
      
      return (
        <div key={datasetName} style={{ marginBottom: '20px' }}>
          <h4 style={{ color: '#6b7280', marginBottom: '8px' }}>
            {section.icon} {section.title}
          </h4>
          <div style={{ color: '#9ca3af', fontSize: '0.9em', fontStyle: 'italic' }}>
            {dataset.error.includes('timeout') ? 'Request timed out - server may be processing data' : 
             dataset.error.includes('not found') ? 'Data not available for this location/date' :
             'Data not available'}
          </div>
          {dataset.error.includes('timeout') && (
            <div style={{ color: '#fbbf24', fontSize: '0.8em', marginTop: '4px' }}>
              Try a different location or date, or wait and retry
            </div>
          )}
        </div>
      );
    }

    const data = dataset as OceanPointData;
    
    // Define sections and their variables with improved organization
    const sections: Record<string, { title: string; icon: string; variables: string[] }> = {
      sst: {
        title: 'Temperature',
        icon: '🌡️',
        variables: ['sst', 'ice']
      },
      currents: {
        title: 'Currents',
        icon: '🌀',
        variables: ['uo', 'vo', 'speed', 'direction', 'thetao', 'so']
      },
      acidity: {
        title: 'Ocean Chemistry',
        icon: '🧪',
        variables: ['ph', 'ph_insitu', 'ph_insitu_total', 'dissic', 'dic', 'talk', 'pco2', 'revelle', 'o2', 'no3', 'po4', 'si', 'chl', 'nppv']
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
        
        <div>
          {availableVars.map(varName => {
            const varData = data.data[varName];
            if (!varData) return null;
            
            if (showDetailedMode) {
              // Use enhanced parameter explanation for detailed mode
              return (
                <ParameterExplanation
                  key={varName}
                  parameterName={varName}
                  data={varData}
                  showExpanded={expandedParameters.includes(varName)}
                />
              );
            } else {
              // Simple display for compact mode
              return (
                <div key={varName} style={{ 
                  marginBottom: '6px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  padding: '2px 0',
                  gap: '8px'
                }}>
                  <span style={{ 
                    color: '#d1d5db', 
                    fontSize: '0.9em',
                    lineHeight: '1.3',
                    minWidth: '0',
                    flexShrink: 0
                  }}>
                    {getFormattedLabel(varName, varData.long_name)}:
                  </span>
                  <span style={{ 
                    fontWeight: '500', 
                    textAlign: 'right',
                    lineHeight: '1.3'
                  }}>
                    {renderValue(varData, varName)}
                  </span>
                </div>
              );
            }
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
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '16px',
        paddingBottom: '8px',
        borderBottom: '2px solid rgba(96, 165, 250, 0.3)'
      }}>
        <h3 style={{ 
          margin: 0, 
          fontSize: '1.3em', 
          color: '#60a5fa'
        }}>
          🌊 Ocean Data Analysis
        </h3>
        
        <button
          onClick={() => setShowDetailedMode(!showDetailedMode)}
          style={{
            backgroundColor: showDetailedMode ? '#3b82f6' : 'rgba(59, 130, 246, 0.2)',
            border: '1px solid #3b82f6',
            borderRadius: '6px',
            padding: '4px 8px',
            color: showDetailedMode ? 'white' : '#60a5fa',
            fontSize: '0.8em',
            cursor: 'pointer',
            fontWeight: '500'
          }}
        >
          {showDetailedMode ? '📊 Simple' : '🎓 Detailed'}
        </button>
      </div>
      
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
      
      {renderEcosystemInsights()}
      
      {Object.entries(data.datasets)
        .filter(([name]) => name !== '_ecosystem_insights' && name !== 'microplastics') // Filter out insights and microplastics from regular dataset display
        .map(([name, dataset]) => renderDataset(name, dataset)
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