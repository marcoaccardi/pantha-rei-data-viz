import React from 'react';
import { useTranslation } from 'react-i18next';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faXmark, faLocationDot, faCalendar, faTemperatureHigh, faFlask, faWater } from '@fortawesome/free-solid-svg-icons';
import { SectionHealthAnalysis, formatValueWithUnits, getHealthScoreDescription } from '../utils/oceanHealthAnalyzer';

interface OceanHealthInfoProps {
  sectionName: 'temperature' | 'chemistry' | 'currents';
  analysis: SectionHealthAnalysis;
  location: { lat: number; lon: number };
  date: string;
  onClose: () => void;
}

const OceanHealthInfo: React.FC<OceanHealthInfoProps> = ({ 
  sectionName, 
  analysis, 
  location, 
  date, 
  onClose 
}) => {
  const { t } = useTranslation();
  
  const getSectionInfo = () => {
    switch (sectionName) {
      case 'temperature':
        return {
          title: <><FontAwesomeIcon icon={faTemperatureHigh} /> {t('oceanHealth.title.temperature')}</>,
          description: t('oceanHealth.description.temperature'),
          importance: t('oceanHealth.importance.temperature')
        };
      case 'chemistry':
        return {
          title: <><FontAwesomeIcon icon={faFlask} /> {t('oceanHealth.title.chemistry')}</>,
          description: t('oceanHealth.description.chemistry'),
          importance: t('oceanHealth.importance.chemistry')
        };
      case 'currents':
        return {
          title: <><FontAwesomeIcon icon={faWater} /> {t('oceanHealth.title.currents')}</>,
          description: t('oceanHealth.description.currents'),
          importance: t('oceanHealth.importance.currents')
        };
    }
  };

  const sectionInfo = getSectionInfo();
  
  // Get appropriate colors for health score
  const getHealthScoreColor = () => {
    if (analysis.healthScore >= 0.7) return '#10b981'; // Green for good health
    if (analysis.healthScore >= 0.4) return '#f59e0b'; // Orange for medium health  
    return '#ef4444'; // Red for poor health
  };
  
  const healthScoreColor = getHealthScoreColor();
  
  return (
    <div className="elegant-scrollbar" style={{
      position: 'absolute',
      top: '0',
      left: '0',
      right: '0',
      bottom: '0',
      minHeight: '90vh',
      height: 'auto',
      backgroundColor: 'rgba(0, 0, 0, 0.95)',
      color: 'white',
      padding: '20px',
      borderRadius: '12px',
      overflowY: 'auto',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(156, 163, 175, 0.3)', // Transparent gray border
      zIndex: 10,
      // Elegant scrollbar styling for Firefox
      scrollbarWidth: 'thin',
      scrollbarColor: 'rgba(156, 163, 175, 0.5) transparent'
    }}>
      
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '20px',
        paddingBottom: '16px',
        borderBottom: '1px solid rgba(156, 163, 175, 0.3)'
      }}>
        <div>
          <h2 style={{
            margin: '0 0 8px 0',
            fontSize: '1.4em',
            color: '#e5e7eb' // Clean gray instead of status color
          }}>
            {sectionInfo.title}
          </h2>
          <div style={{
            fontSize: '0.85em',
            color: '#9ca3af'
          }}>
            <FontAwesomeIcon icon={faLocationDot} /> {location.lat.toFixed(4)}°, {location.lon.toFixed(4)}° • <FontAwesomeIcon icon={faCalendar} /> {date}
          </div>
        </div>
        
        <button
          onClick={onClose}
          style={{
            backgroundColor: 'transparent',
            border: '1px solid rgba(156, 163, 175, 0.5)',
            borderRadius: '50%',
            padding: '8px',
            color: '#9ca3af',
            cursor: 'pointer',
            fontSize: '1.2em',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '32px',
            height: '32px',
            transition: 'all 0.2s ease'
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.backgroundColor = `rgba(239, 68, 68, 0.2)`;
            e.currentTarget.style.borderColor = '#ef4444';
            e.currentTarget.style.color = '#ef4444';
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.borderColor = 'rgba(156, 163, 175, 0.5)';
            e.currentTarget.style.color = '#9ca3af';
          }}
          title={t('oceanHealth.close')}
        >
          <FontAwesomeIcon icon={faXmark} />
        </button>
      </div>

      {/* Health Summary */}
      <div style={{
        marginBottom: '24px',
        padding: '16px',
        backgroundColor: `${healthScoreColor}20`,
        borderRadius: '8px'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          marginBottom: '12px'
        }}>
          <div style={{
            fontSize: '1.1em',
            fontWeight: '600',
            color: healthScoreColor
          }}>
            {t('oceanHealth.status')}
          </div>
          <div style={{
            backgroundColor: healthScoreColor,
            color: 'white',
            padding: '4px 12px',
            borderRadius: '16px',
            fontSize: '0.8em',
            fontWeight: '600',
            textTransform: 'uppercase'
          }}>
            {analysis.overallSeverity}
          </div>
        </div>
        
        <div style={{
          color: '#e5e7eb',
          fontSize: '0.95em',
          lineHeight: '1.4',
          marginBottom: '12px'
        }}>
          {analysis.summary}
        </div>
        
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.9em'
        }}>
          <span style={{ color: '#9ca3af' }}>{t('oceanHealth.healthScore')}</span>
          <div style={{
            backgroundColor: healthScoreColor,
            color: 'white',
            padding: '2px 8px',
            borderRadius: '12px',
            fontWeight: '600'
          }}>
            {(analysis.healthScore * 100).toFixed(0)}%
          </div>
          <span style={{ color: '#d1d5db' }}>
            ({getHealthScoreDescription(analysis.healthScore, t)})
          </span>
        </div>
      </div>

      {/* Section Description */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{
          color: '#e5e7eb',
          marginBottom: '12px',
          fontSize: '1.1em'
        }}>
          {t('oceanHealth.whyMatters')}
        </h3>
        
        <div style={{
          padding: '16px',
          backgroundColor: 'rgba(255, 255, 255, 0.05)',
          borderRadius: '8px',
          marginBottom: '12px'
        }}>
          <p style={{
            color: '#e5e7eb',
            fontSize: '0.9em',
            lineHeight: '1.5',
            margin: '0 0 12px 0'
          }}>
            {sectionInfo.description}
          </p>
          
          <p style={{
            color: '#d1d5db',
            fontSize: '0.85em',
            lineHeight: '1.4',
            margin: 0,
            fontStyle: 'italic'
          }}>
            <strong>{t('oceanHealth.impact')}</strong> {sectionInfo.importance}
          </p>
        </div>
      </div>

      {/* No Data Message or Key Findings */}
      {analysis.specificImpacts.length === 0 ? (
        <div style={{ marginBottom: '24px' }}>
          <div style={{
            padding: '20px',
            backgroundColor: 'rgba(156, 163, 175, 0.1)',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <h3 style={{
              color: '#9ca3af',
              marginBottom: '12px',
              fontSize: '1.1em'
            }}>
              {t('oceanHealth.noDataAvailable')}
            </h3>
            <p style={{
              color: '#d1d5db',
              fontSize: '0.9em',
              lineHeight: '1.4',
              margin: '0 0 12px 0'
            }}>
              {t('oceanHealth.noDataMessage', { section: sectionName.charAt(0).toUpperCase() + sectionName.slice(1) })}
            </p>
            <p style={{
              color: '#9ca3af',
              fontSize: '0.8em',
              margin: 0,
              fontStyle: 'italic'
            }}>
              {t('oceanHealth.tryDifferent', { section: sectionName })}
            </p>
          </div>
        </div>
      ) : (
        analysis.keyFindings.length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{
              color: '#e5e7eb',
              marginBottom: '12px',
              fontSize: '1.1em'
            }}>
              {t('oceanHealth.keyFindings')}
            </h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {analysis.keyFindings.map((finding, index) => (
                <div
                  key={index}
                  style={{
                    padding: '12px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '6px',
                    color: '#e5e7eb',
                    fontSize: '0.9em',
                    lineHeight: '1.4'
                  }}
                >
                  {finding}
                </div>
              ))}
            </div>
          </div>
        )
      )}

      {/* Detailed Parameter Analysis */}
      {analysis.specificImpacts.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{
            color: '#e5e7eb',
            marginBottom: '12px',
            fontSize: '1.1em'
          }}>
            {t('oceanHealth.detailedAnalysis')}
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {analysis.specificImpacts.map((impact, index) => (
              <div
                key={index}
                style={{
                  padding: '16px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  borderRadius: '8px'
                }}
              >
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '8px'
                }}>
                  <div style={{
                    fontWeight: '600',
                    color: '#e5e7eb',
                    fontSize: '0.95em'
                  }}>
                    {impact.displayName}
                  </div>
                  
                  <div style={{
                    backgroundColor: impact.severity === 'critical' ? '#991b1b' : 
                                     impact.severity === 'high' ? '#ef4444' :
                                     impact.severity === 'medium' ? '#f59e0b' : '#10b981',
                    color: 'white',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '0.75em',
                    fontWeight: '600',
                    textTransform: 'uppercase'
                  }}>
                    {impact.severity}
                  </div>
                </div>
                
                <div style={{
                  color: '#e5e7eb',
                  fontSize: '0.9em',
                  fontWeight: '600',
                  marginBottom: '4px'
                }}>
                  {t('oceanHealth.currentValue')} {formatValueWithUnits(impact.currentValue, impact.units)}
                </div>
                
                <div style={{
                  color: '#d1d5db',
                  fontSize: '0.85em',
                  marginBottom: '8px'
                }}>
                  {t('oceanHealth.classification')} {impact.classification}
                </div>
                
                <div style={{
                  color: '#d1d5db',
                  fontSize: '0.85em',
                  lineHeight: '1.4',
                  marginBottom: '6px'
                }}>
                  <strong>{t('oceanHealth.environmentalImpact')}</strong> {impact.impact}
                </div>
                
                <div style={{
                  color: '#9ca3af',
                  fontSize: '0.8em',
                  lineHeight: '1.3',
                  fontStyle: 'italic'
                }}>
                  {impact.context}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}


      {/* Footer */}
      <div style={{
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        paddingTop: '16px',
        fontSize: '0.75em',
        color: '#6b7280',
        textAlign: 'center'
      }}>
        {t('oceanHealth.footer')}
      </div>
    </div>
  );
};

export default OceanHealthInfo;