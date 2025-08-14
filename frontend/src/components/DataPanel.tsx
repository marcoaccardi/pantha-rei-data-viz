import React, { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCircleInfo } from '@fortawesome/free-solid-svg-icons';
import { MultiDatasetOceanResponse, OceanDataValue, OceanPointData } from '../utils/types';
import { classifyMeasurement, formatDirection } from '../services/oceanDataService';
import { analyzeSectionHealth } from '../utils/oceanHealthAnalyzer';
import ParameterExplanation from './ParameterExplanation';
import OceanHealthInfo from './OceanHealthInfo';

interface DataPanelProps {
  data: MultiDatasetOceanResponse | null;
  isLoading: boolean;
  error: string | null;
}

// Design system constants
const designSystem = {
  colors: {
    primary: '#3b82f6',
    secondary: '#6366f1', 
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    text: {
      primary: '#f9fafb',
      secondary: '#d1d5db',
      muted: '#9ca3af'
    },
    backgrounds: {
      primary: 'rgba(0, 0, 0, 0.9)',
      secondary: 'rgba(255, 255, 255, 0.05)',
      accent: 'rgba(59, 130, 246, 0.1)'
    }
  },
  typography: {
    title: '1.25rem',
    heading: '1.1rem', 
    body: '0.875rem',
    caption: '0.75rem',
    small: '0.6875rem'
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '20px',
    xxl: '24px'
  }
};

const DataPanel: React.FC<DataPanelProps> = ({ data, isLoading, error }) => {
  const [expandedParameters, setExpandedParameters] = useState<string[]>([]);
  const [activeHealthInfo, setActiveHealthInfo] = useState<'temperature' | 'chemistry' | 'currents' | null>(null);
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
      'current_speed': 'Current speed',
      'current_direction': 'Current direction',
      'thetao': 'Sea water potential temperature',
      'so': 'Sea water salinity'
    };
    
    return labelMap[parameter] || longName || parameter;
  };

  const renderValue = (value: OceanDataValue, parameter: string): JSX.Element => {
    if (!value.valid || value.value === null) {
      return <span style={{ color: designSystem.colors.text.muted }}>No data</span>;
    }

    const numValue = typeof value.value === 'number' ? value.value : parseFloat(value.value as string);
    
    // Special formatting for different parameter types
    if (parameter.includes('direction') || parameter === 'VMDR' || parameter === 'MWD' || parameter === 'current_direction') {
      return (
        <span style={{ 
          color: designSystem.colors.text.secondary,
          fontSize: designSystem.typography.body,
          fontWeight: '500'
        }}>
          {numValue.toFixed(1)}° <span style={{ fontSize: designSystem.typography.small }}>({formatDirection(numValue)})</span>
        </span>
      );
    }

    // Special formatting for ice concentration (convert to percentage)
    if (parameter === 'ice') {
      if (numValue === 0 || isNaN(numValue)) {
        return <span style={{ color: designSystem.colors.text.muted }}>No data</span>;
      }
      return (
        <span style={{ 
          color: designSystem.colors.text.secondary,
          fontSize: designSystem.typography.body,
          fontWeight: '500'
        }}>
          {(numValue * 100).toFixed(1)}%
        </span>
      );
    }

    // Special formatting for temperature (ensure Celsius)
    if (parameter === 'sst' || parameter === 'analysed_sst') {
      return (
        <span style={{ 
          color: designSystem.colors.text.secondary,
          fontSize: designSystem.typography.body,
          fontWeight: '500'
        }}>
          {numValue.toFixed(2)} Celsius
        </span>
      );
    }

    // All other values - uniform styling
    return (
      <span style={{ 
        color: designSystem.colors.text.secondary,
        fontSize: designSystem.typography.body,
        fontWeight: '500'
      }}>
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
    marginBottom: designSystem.spacing.xxl,
    padding: designSystem.spacing.lg,
    backgroundColor: designSystem.colors.backgrounds.accent,
    borderRadius: designSystem.spacing.sm,
    border: `1px solid ${designSystem.colors.secondary}40`
    }}>
        <h4 style={{
          color: designSystem.colors.secondary,
          marginBottom: designSystem.spacing.md,
          fontSize: designSystem.typography.heading,
          fontWeight: '600',
          display: 'flex',
          alignItems: 'center',
          gap: designSystem.spacing.sm
        }}>
          🌊 Ecosystem Health Analysis
          <span style={{ fontSize: designSystem.typography.caption, fontWeight: 'normal', color: designSystem.colors.text.muted }}>
            ({insights.measurement_count} parameters analyzed)
          </span>
        </h4>
        
        <div style={{ fontSize: designSystem.typography.body }}>
          {insights.insights.map((insight: string, index: number) => (
            <div 
            key={index} 
            style={{
            marginBottom: designSystem.spacing.sm,
            padding: `${designSystem.spacing.sm} ${designSystem.spacing.md}`,
            backgroundColor: designSystem.colors.backgrounds.secondary,
            borderRadius: designSystem.spacing.xs,
            color: designSystem.colors.text.secondary,
            lineHeight: '1.4',
              fontSize: designSystem.typography.body
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
        <div key={datasetName} style={{ marginBottom: designSystem.spacing.xl }}>
          <h4 style={{ 
            color: designSystem.colors.text.muted, 
            marginBottom: designSystem.spacing.sm,
            fontSize: designSystem.typography.heading,
            fontWeight: '600'
          }}>
            {section.icon} {section.title}
          </h4>
          <div style={{ 
            color: designSystem.colors.text.muted, 
            fontSize: designSystem.typography.body,
            fontStyle: 'italic'
          }}>
            {dataset.error.includes('timeout') ? 'Request timed out - server may be processing data' : 
             dataset.error.includes('not found') ? 'Data not available for this location/date' :
             'Data not available'}
          </div>
          {dataset.error.includes('timeout') && (
            <div style={{ 
              color: designSystem.colors.warning, 
              fontSize: designSystem.typography.caption,
              marginTop: designSystem.spacing.xs
            }}>
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
        variables: ['uo', 'vo', 'u', 'v', 'ug', 'vg', 'current_speed', 'current_direction', 'thetao', 'so']
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
        <div key={datasetName} style={{ marginBottom: designSystem.spacing.xl }}>
          <h4 style={{ 
            color: designSystem.colors.text.muted, 
            marginBottom: designSystem.spacing.sm,
            fontSize: designSystem.typography.heading,
            fontWeight: '600'
          }}>
            {section.icon} {section.title}
          </h4>
          <div style={{ 
            color: designSystem.colors.text.muted, 
            fontSize: designSystem.typography.body
          }}>
            No data available
          </div>
        </div>
      );
    }

    // Analyze section health
    const sectionType = datasetName === 'sst' ? 'temperature' : 
                       datasetName === 'acidity' ? 'chemistry' : 'currents';
    const healthAnalysis = analyzeSectionHealth(sectionType, data);

    return (
      <div key={datasetName} style={{ 
        marginBottom: designSystem.spacing.xxl,
        padding: designSystem.spacing.lg,
        backgroundColor: designSystem.colors.backgrounds.secondary,
        borderRadius: designSystem.spacing.sm,
        border: `1px solid ${healthAnalysis.overallColor}40`
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: designSystem.spacing.md
        }}>
          <h4 style={{ 
            color: designSystem.colors.primary, 
            fontSize: designSystem.typography.heading,
            fontWeight: '600',
            margin: 0
          }}>
            {section.icon} {section.title}
          </h4>
          
          <button
            onClick={() => setActiveHealthInfo(sectionType)}
            style={{
              backgroundColor: 'transparent',
              border: `1px solid ${healthAnalysis.overallColor}`,
              borderRadius: '50%',
              padding: designSystem.spacing.xs,
              color: healthAnalysis.overallColor,
              cursor: 'pointer',
              fontSize: designSystem.typography.body,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '32px',
              height: '32px',
              transition: 'all 0.2s ease'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = `${healthAnalysis.overallColor}20`;
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
            title={`View ocean health information for ${section.title.toLowerCase()}`}
          >
            <FontAwesomeIcon icon={faCircleInfo} />
          </button>
        </div>
        
        <div>
          {availableVars.map(varName => {
            const varData = data.data[varName];
            if (!varData) return null;
            
            // Simple display mode
            return (
              <div key={varName} style={{ 
                marginBottom: designSystem.spacing.xs,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                padding: `${designSystem.spacing.xs} 0`,
                gap: designSystem.spacing.sm
              }}>
                <span style={{ 
                  color: designSystem.colors.text.secondary, 
                  fontSize: designSystem.typography.body,
                  lineHeight: '1.3',
                  minWidth: '0',
                  flexShrink: 0
                }}>
                  {getFormattedLabel(varName, varData.long_name)}:
                </span>
                <span style={{ 
                  fontWeight: '500', 
                  textAlign: 'right',
                  lineHeight: '1.3',
                  fontSize: designSystem.typography.body
                }}>
                  {renderValue(varData, varName)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div style={{
        position: 'absolute',
        top: designSystem.spacing.xl,
        right: designSystem.spacing.xl,
        backgroundColor: designSystem.colors.backgrounds.primary,
        color: designSystem.colors.text.primary,
        padding: designSystem.spacing.xl,
        borderRadius: designSystem.spacing.md,
        width: '400px',
        maxHeight: '80vh',
        overflowY: 'auto',
        backdropFilter: 'blur(10px)',
        border: `1px solid ${designSystem.colors.text.muted}40`
      }}>
        <h3 style={{ 
          margin: `0 0 ${designSystem.spacing.lg} 0`, 
          fontSize: designSystem.typography.title, 
          color: designSystem.colors.primary,
          fontWeight: '600'
        }}>
          🌊 Ocean Data
        </h3>
        <div style={{ 
          textAlign: 'center', 
          padding: '40px 0', 
          color: designSystem.colors.primary
        }}>
          <div style={{ 
            fontSize: '2rem', 
            marginBottom: designSystem.spacing.sm
          }}>⏳</div>
          <div style={{ 
            fontSize: designSystem.typography.body,
            color: designSystem.colors.text.secondary
          }}>Loading ocean data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        position: 'absolute',
        top: designSystem.spacing.xl,
        right: designSystem.spacing.xl,
        backgroundColor: designSystem.colors.backgrounds.primary,
        color: designSystem.colors.text.primary,
        padding: designSystem.spacing.xl,
        borderRadius: designSystem.spacing.md,
        width: '400px',
        backdropFilter: 'blur(10px)',
        border: `1px solid ${designSystem.colors.error}40`
      }}>
        <h3 style={{ 
          margin: `0 0 ${designSystem.spacing.lg} 0`, 
          fontSize: designSystem.typography.title, 
          color: designSystem.colors.error,
          fontWeight: '600'
        }}>
          🌊 Ocean Data Error
        </h3>
        <div style={{ 
          color: designSystem.colors.error, 
          fontSize: designSystem.typography.body
        }}>
          {error}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{
        position: 'absolute',
        top: designSystem.spacing.xl,
        right: designSystem.spacing.xl,
        backgroundColor: designSystem.colors.backgrounds.primary,
        color: designSystem.colors.text.primary,
        padding: designSystem.spacing.xl,
        borderRadius: designSystem.spacing.md,
        width: '400px',
        backdropFilter: 'blur(10px)',
        border: `1px solid ${designSystem.colors.text.muted}40`
      }}>
        <h3 style={{ 
          margin: `0 0 ${designSystem.spacing.lg} 0`, 
          fontSize: designSystem.typography.title, 
          color: designSystem.colors.primary,
          fontWeight: '600'
        }}>
          🌊 Ocean Data
        </h3>
        <div style={{ 
          color: designSystem.colors.text.muted, 
          fontSize: designSystem.typography.body,
          textAlign: 'center', 
          padding: `${designSystem.spacing.xl} 0`
        }}>
          <div style={{ 
            marginBottom: designSystem.spacing.md,
            color: designSystem.colors.text.secondary
          }}>Click on the globe to view ocean data</div>
          <div style={{ 
            fontSize: designSystem.typography.caption, 
            color: designSystem.colors.text.muted
          }}>
            Or use the <strong style={{ color: designSystem.colors.primary }}>🎲 Random Location</strong> button to explore available data
          </div>
        </div>
      </div>
    );
  }

  // Show ocean health info overlay if active
  if (activeHealthInfo && data) {
    const dataset = activeHealthInfo === 'temperature' ? data.datasets.sst :
                   activeHealthInfo === 'chemistry' ? data.datasets.acidity :
                   data.datasets.currents;
    
    const healthAnalysis = analyzeSectionHealth(activeHealthInfo, dataset);
    
    return (
      <div style={{
        position: 'absolute',
        top: designSystem.spacing.xl,
        right: designSystem.spacing.xl,
        width: '450px',
        height: '90vh',
        borderRadius: designSystem.spacing.md
      }}>
        <OceanHealthInfo
          sectionName={activeHealthInfo}
          analysis={healthAnalysis}
          location={data.location}
          date={data.date}
          onClose={() => setActiveHealthInfo(null)}
        />
      </div>
    );
  }

  return (
    <div style={{
      position: 'absolute',
      top: designSystem.spacing.xl,
      right: designSystem.spacing.xl,
      backgroundColor: designSystem.colors.backgrounds.primary,
      color: designSystem.colors.text.primary,
      padding: designSystem.spacing.xl,
      borderRadius: designSystem.spacing.md,
      width: '420px',
      maxHeight: '80vh',
      overflowY: 'auto',
      backdropFilter: 'blur(10px)',
      border: `1px solid ${designSystem.colors.text.muted}40`,
      scrollbarWidth: 'thin',
      scrollbarColor: `${designSystem.colors.text.muted} transparent`
    }}>
      <div style={{
        marginBottom: designSystem.spacing.lg,
        paddingBottom: designSystem.spacing.sm,
        borderBottom: `2px solid ${designSystem.colors.primary}40`
      }}>
        <h3 style={{ 
          margin: 0, 
          fontSize: designSystem.typography.title, 
          color: designSystem.colors.primary,
          fontWeight: '600'
        }}>
          🌊 Ocean Data Analysis
        </h3>
      </div>
      
      <div style={{ 
        marginBottom: designSystem.spacing.lg, 
        fontSize: designSystem.typography.body, 
        color: designSystem.colors.text.muted,
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
        marginTop: designSystem.spacing.lg, 
        paddingTop: designSystem.spacing.lg, 
        borderTop: `1px solid ${designSystem.colors.text.muted}40`,
        fontSize: designSystem.typography.caption,
        color: designSystem.colors.text.muted
      }}>
        <div style={{ color: designSystem.colors.text.secondary }}>⚡ Response time: {data.total_extraction_time_ms.toFixed(0)}ms</div>
      </div>
    </div>
  );
};

export default DataPanel;