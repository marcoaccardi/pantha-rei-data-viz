import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faInfo,
  faLocationDot,
  faCalendar,
  faFlask,
  faWater,
  faTemperatureHigh,
  faBottleWater
} from '@fortawesome/free-solid-svg-icons';
import { MultiDatasetOceanResponse, OceanDataValue, OceanPointData } from '../utils/types';
import { classifyMeasurement, formatDirection } from '../services/oceanDataService';
import { analyzeSectionHealth } from '../utils/oceanHealthAnalyzer';
import ParameterExplanation from './ParameterExplanation';
import OceanHealthInfo from './OceanHealthInfo';

interface DataPanelProps {
  data: MultiDatasetOceanResponse | null;
  isLoading: boolean;
  error: string | null;
  hoveredMicroplastic?: {
    position: [number, number, number];
    concentration: number;
    confidence: number;
    dataSource: 'real' | 'synthetic';
    date: string;
    concentrationClass: string;
    coordinates: [number, number]; // [lon, lat]
  } | null;
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

const DataPanel: React.FC<DataPanelProps> = ({ data, isLoading, error, hoveredMicroplastic }) => {
  const { t } = useTranslation();
  const [expandedParameters, setExpandedParameters] = useState<string[]>([]);
  const [activeHealthInfo, setActiveHealthInfo] = useState<'temperature' | 'chemistry' | 'currents' | null>(null);
  const [isClosing, setIsClosing] = useState(false);
  const [isOpening, setIsOpening] = useState(false);
  
  const handleOpenHealthInfo = (sectionType: 'temperature' | 'chemistry' | 'currents') => {
    if (activeHealthInfo === sectionType) return; // Already open
    
    setActiveHealthInfo(sectionType);
    setIsOpening(true);
    
    // Trigger fade-in animation
    requestAnimationFrame(() => {
      setIsOpening(false);
    });
  };
  
  const handleCloseHealthInfo = () => {
    setIsClosing(true);
    setTimeout(() => {
      setActiveHealthInfo(null);
      setIsClosing(false);
    }, 300); // Match the transition duration
  };
  
  const getConcentrationColor = (concentrationClass: string): string => {
    switch (concentrationClass) {
      case 'Very Low':
        return '#bb88ff';  // Light purple
      case 'Low':
        return '#9944ff';  // Medium purple
      case 'Medium':
        return '#ff44aa';  // Pink
      case 'High':
        return '#ff9944';  // Orange
      case 'Very High':
        return '#ff4444';  // Red
      default:
        return '#888888';  // Gray
    }
  };

  const renderMicroplasticHover = () => {
    return (
      <div style={{
        marginTop: designSystem.spacing.lg,
        paddingTop: designSystem.spacing.lg,
        borderTop: `1px solid rgba(156, 163, 175, 0.3)`,
        padding: designSystem.spacing.lg,
        backgroundColor: 'transparent',
        borderRadius: designSystem.spacing.sm,
        border: '1px solid rgba(156, 163, 175, 0.3)'
      }}>
        <h4 style={{
          color: designSystem.colors.primary,
          marginBottom: designSystem.spacing.md,
          fontSize: designSystem.typography.heading,
          fontWeight: '600',
          margin: '0 0 12px 0',
          display: 'flex',
          alignItems: 'center',
          gap: designSystem.spacing.sm
        }}>
          <FontAwesomeIcon icon={faBottleWater} /> {t('dataPanel.microplastics.title')}
        </h4>
        
        {/* Location and Date on same line */}
        <div style={{
          marginBottom: designSystem.spacing.md,
          fontSize: designSystem.typography.body,
          color: designSystem.colors.text.muted,
          display: 'flex',
          justifyContent: 'space-between'
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: designSystem.spacing.xs }}>
            <FontAwesomeIcon icon={faLocationDot} />
            {hoveredMicroplastic ? 
              `${hoveredMicroplastic.coordinates[1].toFixed(4)}°, ${hoveredMicroplastic.coordinates[0].toFixed(4)}°` : 
              t('dataPanel.microplastics.hoverPrompt')
            }
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: designSystem.spacing.xs }}>
            <FontAwesomeIcon icon={faCalendar} />
            {hoveredMicroplastic ? hoveredMicroplastic.date : t('dataPanel.microplastics.noData')}
          </span>
        </div>
        
        {/* Class and Concentration below */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: designSystem.typography.body
        }}>
          <div>
            <span style={{ color: designSystem.colors.text.secondary, marginRight: designSystem.spacing.xs }}>{t('dataPanel.microplastics.class')}</span>
            <span style={{
              color: hoveredMicroplastic ? getConcentrationColor(hoveredMicroplastic.concentrationClass) : designSystem.colors.text.muted,
              fontWeight: '600'
            }}>
              {hoveredMicroplastic ? hoveredMicroplastic.concentrationClass : t('dataPanel.microplastics.notAvailable')}
            </span>
          </div>
          <div>
            <span style={{ color: designSystem.colors.text.secondary, marginRight: designSystem.spacing.xs }}>{t('dataPanel.microplastics.concentration')}</span>
            <span style={{
              color: hoveredMicroplastic ? designSystem.colors.text.primary : designSystem.colors.text.muted,
              fontWeight: '500'
            }}>
              {hoveredMicroplastic ? `${hoveredMicroplastic.concentration.toFixed(3)} ${t('dataPanel.microplastics.units')}` : t('dataPanel.microplastics.notAvailable')}
            </span>
          </div>
        </div>
      </div>
    );
  };
  const getFormattedLabel = (parameter: string, longName?: string): string => {
    // Use translation keys for parameter names
    const translationKey = `dataPanel.parameters.${parameter}`;
    const translatedLabel = t(translationKey);
    
    // If translation exists (not just the key), use it
    if (translatedLabel !== translationKey) {
      return translatedLabel;
    }
    
    // Fallback to longName or parameter name
    return longName || parameter;
  };

  const renderValue = (value: OceanDataValue, parameter: string): JSX.Element => {
    if (!value.valid || value.value === null) {
      return <span style={{ color: designSystem.colors.text.muted }}>{t('dataPanel.status.noData')}</span>;
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
        return <span style={{ color: designSystem.colors.text.muted }}>{t('dataPanel.status.noData')}</span>;
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
          🌊 {t('dataPanel.ecosystem.title')}
          <span style={{ fontSize: designSystem.typography.caption, fontWeight: 'normal', color: designSystem.colors.text.muted }}>
            ({t('dataPanel.ecosystem.parametersAnalyzed', { count: insights.measurement_count })})
          </span>
        </h4>
        
        <div style={{ fontSize: designSystem.typography.body }}>
          {insights.insights.map((insight: string, index: number) => (
            <div 
            key={index} 
            style={{
            marginBottom: designSystem.spacing.sm,
            padding: `${designSystem.spacing.sm} ${designSystem.spacing.md}`,
            backgroundColor: 'transparent',
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
      const sections: Record<string, { title: string; icon: JSX.Element }> = {
        sst: { title: t('dataPanel.sections.temperature'), icon: <FontAwesomeIcon icon={faTemperatureHigh} /> },
        currents: { title: t('dataPanel.sections.currents'), icon: <FontAwesomeIcon icon={faWater} /> },
        acidity: { title: t('dataPanel.sections.chemistry'), icon: <FontAwesomeIcon icon={faFlask} /> }
      };
      
      const section = sections[datasetName] || { title: datasetName.toUpperCase(), icon: <FontAwesomeIcon icon={faWater} /> };
      
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
            {dataset.error.includes('timeout') ? t('dataPanel.status.requestTimedOut') : 
             dataset.error.includes('not found') ? t('dataPanel.status.dataNotAvailable') :
             t('dataPanel.status.noDataAvailable')}
          </div>
          {dataset.error.includes('timeout') && (
            <div style={{ 
              color: designSystem.colors.warning, 
              fontSize: designSystem.typography.caption,
              marginTop: designSystem.spacing.xs
            }}>
              {t('dataPanel.status.tryDifferent')}
            </div>
          )}
        </div>
      );
    }

    const data = dataset as OceanPointData;
    
    // Define sections and their variables with improved organization
    const sections: Record<string, { title: string; icon: JSX.Element; variables: string[] }> = {
      sst: {
        title: t('dataPanel.sections.temperature'),
        icon: <FontAwesomeIcon icon={faTemperatureHigh} />,
        variables: ['sst', 'ice']
      },
      currents: {
        title: t('dataPanel.sections.currents'),
        icon: <FontAwesomeIcon icon={faWater} />,
        variables: ['uo', 'vo', 'u', 'v', 'ug', 'vg', 'current_speed', 'current_direction', 'thetao', 'so']
      },
      acidity: {
        title: t('dataPanel.sections.chemistry'),
        icon: <FontAwesomeIcon icon={faFlask} />,
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
            {t('dataPanel.status.noDataAvailable')}
          </div>
        </div>
      );
    }

    // Analyze section health
    const sectionType = datasetName === 'sst' ? 'temperature' : 
                       datasetName === 'acidity' ? 'chemistry' : 'currents';
    const healthAnalysis = analyzeSectionHealth(sectionType, data, t);

    return (
      <div key={datasetName} style={{ 
        marginBottom: designSystem.spacing.xxl,
        padding: designSystem.spacing.lg,
        backgroundColor: 'transparent',
        borderRadius: designSystem.spacing.sm,
        border: '1px solid rgba(156, 163, 175, 0.3)'
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
            onClick={() => handleOpenHealthInfo(sectionType)}
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
              transition: 'all 0.3s ease',
              transform: 'scale(1)'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = `${healthAnalysis.overallColor}20`;
              e.currentTarget.style.transform = 'scale(1.05)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.transform = 'scale(1)';
            }}
            onMouseDown={(e) => {
              e.currentTarget.style.transform = 'scale(0.95)';
            }}
            onMouseUp={(e) => {
              e.currentTarget.style.transform = 'scale(1.05)';
            }}
            title={t('dataPanel.healthInfo.viewHealthInfo', { section: section.title.toLowerCase() })}
          >
            i
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
                  fontSize: designSystem.typography.body,
                  whiteSpace: 'nowrap'
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
        width: '480px',
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
          🌊 {t('dataPanel.title')}
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
          }}>{t('dataPanel.loading')}</div>
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
        width: '480px',
        backdropFilter: 'blur(10px)',
        border: `1px solid ${designSystem.colors.error}40`
      }}>
        <h3 style={{ 
          margin: `0 0 ${designSystem.spacing.lg} 0`, 
          fontSize: designSystem.typography.title, 
          color: designSystem.colors.error,
          fontWeight: '600'
        }}>
          🌊 {t('dataPanel.title')} Error
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
        width: '480px',
        backdropFilter: 'blur(10px)',
        border: `1px solid ${designSystem.colors.text.muted}40`
      }}>
        <h3 style={{ 
          margin: `0 0 ${designSystem.spacing.lg} 0`, 
          fontSize: designSystem.typography.title, 
          color: designSystem.colors.primary,
          fontWeight: '600'
        }}>
          🌊 {t('dataPanel.title')}
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
          }}>{t('dataPanel.clickToView')}</div>
          <div style={{ 
            fontSize: designSystem.typography.caption, 
            color: designSystem.colors.text.muted
          }}>
            {t('dataPanel.useRandomButton')}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      position: 'absolute',
      top: designSystem.spacing.xl,
      right: designSystem.spacing.xl,
      width: '480px',
      height: '90vh',
      borderRadius: designSystem.spacing.md
    }}>
      {/* Main Data Panel */}
      <div 
        className="elegant-scrollbar" 
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          color: designSystem.colors.text.primary,
          padding: designSystem.spacing.xl,
          borderRadius: designSystem.spacing.md,
          maxHeight: '80vh',
          overflowY: 'auto',
          backdropFilter: 'blur(10px)',
          border: 'none',
          opacity: activeHealthInfo && !isClosing ? 0 : 1,
          transition: 'opacity 0.3s ease-in-out',
          pointerEvents: activeHealthInfo && !isClosing ? 'none' : 'auto'
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
          fontWeight: '600',
          display: 'flex',
          alignItems: 'center',
          gap: designSystem.spacing.sm
        }}>
          <FontAwesomeIcon icon={faWater} />
          {t('dataPanel.title')}
        </h3>
      </div>
      
      <div style={{ 
        marginBottom: designSystem.spacing.lg, 
        fontSize: designSystem.typography.body, 
        color: designSystem.colors.text.muted,
        display: 'flex',
        justifyContent: 'space-between'
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: designSystem.spacing.xs }}>
          <FontAwesomeIcon icon={faLocationDot} />
          {data.location.lat.toFixed(4)}°, {data.location.lon.toFixed(4)}°
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: designSystem.spacing.xs }}>
          <FontAwesomeIcon icon={faCalendar} />
          {data.date}
        </span>
      </div>
      
      {renderEcosystemInsights()}
      
      {Object.entries(data.datasets)
        .filter(([name]) => name !== '_ecosystem_insights' && name !== 'microplastics') // Filter out insights and microplastics from regular dataset display
        .map(([name, dataset]) => renderDataset(name, dataset)
      )}
      
      {renderMicroplasticHover()}
      
      </div>
      
      {/* Health Info Overlay */}
      {activeHealthInfo && data && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          opacity: isClosing ? 0 : (isOpening ? 0 : 1),
          transition: 'opacity 0.3s ease-in-out',
          pointerEvents: (isClosing || isOpening) ? 'none' : 'auto'
        }}>
          <OceanHealthInfo
            sectionName={activeHealthInfo}
            analysis={analyzeSectionHealth(
              activeHealthInfo, 
              activeHealthInfo === 'temperature' ? data.datasets.sst :
              activeHealthInfo === 'chemistry' ? data.datasets.acidity :
              data.datasets.currents, 
              t
            )}
            location={data.location}
            date={data.date}
            onClose={handleCloseHealthInfo}
          />
        </div>
      )}
      
    </div>
  );
};

export default DataPanel;