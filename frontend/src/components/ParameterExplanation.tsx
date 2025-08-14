import React, { useState } from 'react';
import { OceanDataValue, ParameterClassification, EducationalContext } from '../utils/types';

interface ParameterExplanationProps {
  parameterName: string;
  data: OceanDataValue;
  showExpanded?: boolean;
}

const ParameterExplanation: React.FC<ParameterExplanationProps> = ({
  parameterName,
  data,
  showExpanded = false
}) => {
  const [isExpanded, setIsExpanded] = useState(showExpanded);
  
  const getFormattedValue = () => {
    if (!data.valid || data.value === null) {
      return <span style={{ color: '#6b7280' }}>No data</span>;
    }
    
    const numValue = typeof data.value === 'number' ? data.value : parseFloat(data.value as string);
    
    // Special formatting for directions
    if (parameterName.includes('direction') || parameterName === 'VMDR' || parameterName === 'MWD') {
      const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
      const index = Math.round(numValue / 22.5) % 16;
      return <span>{numValue.toFixed(1)}° ({directions[index]})</span>;
    }
    
    // Special formatting for ice (convert to percentage)
    if (parameterName === 'ice') {
      if (numValue === 0 || isNaN(numValue)) {
        return <span style={{ color: '#6b7280' }}>No ice</span>;
      }
      return <span>{(numValue * 100).toFixed(1)}%</span>;
    }
    
    // Use classification color if available
    const color = data.classification?.color || '#e5e7eb';
    
    return (
      <span style={{ color }}>
        {typeof data.value === 'number' ? data.value.toFixed(2) : data.value} {data.units}
      </span>
    );
  };
  
  const getSeverityIcon = (severity: string) => {
    const icons = {
      'low': '✅',
      'medium': '⚠️', 
      'high': '🔴',
      'critical': '💀'
    };
    return icons[severity as keyof typeof icons] || '';
  };
  
  const getSeverityColor = (severity: string) => {
    const colors = {
      'low': '#10b981',
      'medium': '#f59e0b',
      'high': '#ef4444', 
      'critical': '#991b1b'
    };
    return colors[severity as keyof typeof colors] || '#6b7280';
  };
  
  if (!data.classification && !data.educational_context) {
    // Fallback to simple display if no enhanced data
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '4px 0'
      }}>
        <span style={{ color: '#d1d5db' }}>{data.long_name}:</span>
        <span style={{ fontWeight: '500' }}>{getFormattedValue()}</span>
      </div>
    );
  }
  
  return (
    <div style={{
      marginBottom: '12px',
      padding: '12px',
      backgroundColor: 'transparent',
      border: '1px solid rgba(156, 163, 175, 0.3)',
      borderRadius: '8px',
      border: `1px solid ${data.classification?.color || 'rgba(255, 255, 255, 0.1)'}`
    }}>
      {/* Parameter Header */}
      <div 
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          cursor: 'pointer',
          marginBottom: '8px'
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{ flex: 1 }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px',
            marginBottom: '4px'
          }}>
            <span style={{ 
              fontSize: '0.9em', 
              fontWeight: '600', 
              color: '#e5e7eb' 
            }}>
              {data.long_name}
            </span>
            {data.classification && (
              <span style={{ fontSize: '0.8em' }}>
                {getSeverityIcon(data.classification.severity)}
              </span>
            )}
            <span style={{ 
              fontSize: '0.7em', 
              color: '#9ca3af',
              cursor: 'pointer' 
            }}>
              {isExpanded ? '▼' : '▶'} Learn More
            </span>
          </div>
          
          {/* Value and Classification */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            <div style={{ fontWeight: '600', fontSize: '1.1em' }}>
              {getFormattedValue()}
            </div>
            {data.classification && (
              <div style={{
                backgroundColor: data.classification.color + '20',
                color: data.classification.color,
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '0.8em',
                fontWeight: '500'
              }}>
                {data.classification.classification}
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Expanded Educational Content */}
      {isExpanded && (
        <div style={{
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          paddingTop: '12px',
          fontSize: '0.85em',
          lineHeight: '1.4'
        }}>
          {/* Quick Description */}
          {data.classification?.description && (
            <div style={{ 
              marginBottom: '8px',
              padding: '8px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(156, 163, 175, 0.3)',
              borderRadius: '4px',
              color: '#93c5fd'
            }}>
              <strong>Current Status:</strong> {data.classification.description}
            </div>
          )}
          
          {/* What This Measures */}
          {data.educational_context?.short_description && (
            <div style={{ marginBottom: '8px' }}>
              <strong style={{ color: '#60a5fa' }}>What this measures:</strong>
              <div style={{ color: '#d1d5db', marginTop: '4px' }}>
                {data.educational_context.short_description}
              </div>
            </div>
          )}
          
          {/* Environmental Impact */}
          {data.classification?.environmental_impact && (
            <div style={{ marginBottom: '8px' }}>
              <strong style={{ color: '#34d399' }}>Environmental Impact:</strong>
              <div style={{ color: '#d1d5db', marginTop: '4px' }}>
                {data.classification.environmental_impact}
              </div>
            </div>
          )}
          
          {/* Context */}
          {data.classification?.context && (
            <div style={{ marginBottom: '8px' }}>
              <strong style={{ color: '#fbbf24' }}>Context:</strong>
              <div style={{ color: '#d1d5db', marginTop: '4px' }}>
                {data.classification.context}
              </div>
            </div>
          )}
          
          {/* Scientific Context */}
          {data.educational_context?.scientific_context && (
            <div style={{ marginBottom: '8px' }}>
              <strong style={{ color: '#a78bfa' }}>Scientific Significance:</strong>
              <div style={{ color: '#d1d5db', marginTop: '4px' }}>
                {data.educational_context.scientific_context}
              </div>
            </div>
          )}
          
          {/* Health Implications */}
          {data.educational_context?.health_implications && Object.keys(data.educational_context.health_implications).length > 0 && (
            <div style={{ marginBottom: '8px' }}>
              <strong style={{ color: '#f87171' }}>Health & Ecosystem Impacts:</strong>
              <div style={{ marginTop: '4px' }}>
                {Object.entries(data.educational_context.health_implications).map(([key, value]) => (
                  <div key={key} style={{ color: '#d1d5db', marginBottom: '2px' }}>
                    <strong style={{ textTransform: 'capitalize' }}>{key}:</strong> {value}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Units Explanation */}
          {data.educational_context?.unit_explanation && (
            <div style={{ 
              fontSize: '0.8em',
              color: '#9ca3af',
              fontStyle: 'italic',
              borderTop: '1px solid rgba(255, 255, 255, 0.1)',
              paddingTop: '8px',
              marginTop: '8px'
            }}>
              <strong>Units:</strong> {data.educational_context.unit_explanation}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ParameterExplanation;