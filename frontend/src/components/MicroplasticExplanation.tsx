import React, { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTimes, faLocationDot, faCalendar, faBottleWater } from '@fortawesome/free-solid-svg-icons';

interface MicroplasticExplanationProps {
  microplastic: {
    position: [number, number, number];
    concentration: number;
    confidence: number;
    dataSource: 'real' | 'synthetic';
    date: string;
    concentrationClass: string;
    coordinates: [number, number]; // [lon, lat]
  };
  onClose: () => void;
}

// Design system constants matching the rest of the app
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

const MicroplasticExplanation: React.FC<MicroplasticExplanationProps> = ({
  microplastic,
  onClose
}) => {
  const [isClosing, setIsClosing] = useState(false);
  const [isOpening, setIsOpening] = useState(true);

  // Handle fade-in animation on mount
  useEffect(() => {
    requestAnimationFrame(() => {
      setIsOpening(false);
    });
  }, []);

  // Handle close with fade-out animation
  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      onClose();
    }, 300); // Match transition duration
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

  const getHealthImpactLevel = (concentrationClass: string): { level: string; color: string; description: string } => {
    switch (concentrationClass) {
      case 'Very Low':
        return {
          level: 'Minimal Concern',
          color: designSystem.colors.success,
          description: 'Low concentrations with limited ecological impact'
        };
      case 'Low':
        return {
          level: 'Low Concern',
          color: '#34d399',
          description: 'Detectable but manageable pollution levels'
        };
      case 'Medium':
        return {
          level: 'Moderate Concern',
          color: designSystem.colors.warning,
          description: 'Notable pollution requiring monitoring'
        };
      case 'High':
        return {
          level: 'High Concern',
          color: '#f97316',
          description: 'Significant pollution impacting marine life'
        };
      case 'Very High':
        return {
          level: 'Critical Concern',
          color: designSystem.colors.error,
          description: 'Severe pollution requiring immediate attention'
        };
      default:
        return {
          level: 'Unknown',
          color: designSystem.colors.text.muted,
          description: 'Impact level not determined'
        };
    }
  };

  const healthImpact = getHealthImpactLevel(microplastic.concentrationClass);

  return (
    <div className="elegant-scrollbar" style={{
      position: 'absolute',
      top: '0',
      left: '0',
      right: '0',
      bottom: '0',
      minHeight: '90vh',
      height: 'auto',
      backgroundColor: 'rgba(0, 0, 0, 0.6)',
      color: 'white',
      padding: '20px',
      borderRadius: '12px',
      overflowY: 'auto',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(156, 163, 175, 0.3)',
      zIndex: 10,
      scrollbarWidth: 'thin',
      scrollbarColor: 'rgba(156, 163, 175, 0.5) transparent',
      opacity: isClosing ? 0 : (isOpening ? 0 : 1),
      transition: 'opacity 0.3s ease-in-out',
      pointerEvents: (isClosing || isOpening) ? 'none' : 'auto'
    }}>
      {/* Header with close button */}
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
            color: '#e5e7eb'
          }}>
            <FontAwesomeIcon icon={faBottleWater} /> Microplastic Pollution Analysis
          </h2>
          <div style={{
            fontSize: '0.85em',
            color: '#9ca3af'
          }}>
            <FontAwesomeIcon icon={faLocationDot} /> {microplastic.coordinates[1].toFixed(4)}°, {microplastic.coordinates[0].toFixed(4)}° • <FontAwesomeIcon icon={faCalendar} /> {microplastic.date}
          </div>
        </div>
        
        <button
          onClick={handleClose}
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
            e.currentTarget.style.backgroundColor = `rgba(156, 163, 175, 0.2)`;
            e.currentTarget.style.borderColor = '#6b7280';
            e.currentTarget.style.color = '#6b7280';
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.borderColor = 'rgba(156, 163, 175, 0.5)';
            e.currentTarget.style.color = '#9ca3af';
          }}
          title="Close microplastic information panel"
        >
          <FontAwesomeIcon icon={faTimes} />
        </button>
      </div>


      {/* Concentration Classification */}
      <div style={{
        marginBottom: '24px',
        padding: '16px',
        backgroundColor: 'transparent',
        border: '1px solid rgba(156, 163, 175, 0.3)',
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
            color: healthImpact.color
          }}>
            Pollution Level Status
          </div>
          <div style={{
            backgroundColor: healthImpact.color,
            color: 'white',
            padding: '4px 12px',
            borderRadius: '16px',
            fontSize: '0.8em',
            fontWeight: '600',
            textTransform: 'uppercase'
          }}>
            {microplastic.concentrationClass}
          </div>
        </div>
        
        <div style={{
          color: '#e5e7eb',
          fontSize: '0.95em',
          lineHeight: '1.4',
          marginBottom: '12px'
        }}>
          {healthImpact.description}
        </div>
        
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.9em'
        }}>
          <span style={{ color: '#9ca3af' }}>Concentration:</span>
          <div style={{
            backgroundColor: healthImpact.color,
            color: 'white',
            padding: '2px 8px',
            borderRadius: '12px',
            fontWeight: '600'
          }}>
            {microplastic.concentration.toFixed(3)} pieces/m³
          </div>
          <span style={{ color: '#d1d5db' }}>({healthImpact.level})</span>
        </div>
      </div>

      {/* What Are Microplastics */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{
          color: '#e5e7eb',
          marginBottom: '12px',
          fontSize: '1.1em'
        }}>
          What Are Microplastics?
        </h3>
        
        <div style={{
          padding: '16px',
          backgroundColor: 'transparent',
          border: '1px solid rgba(156, 163, 175, 0.3)',
          borderRadius: '8px',
          marginBottom: '12px',
        }}>
          <p style={{
            color: '#e5e7eb',
            fontSize: '0.9em',
            lineHeight: '1.5',
            margin: '0 0 12px 0'
          }}>
            Microplastics are tiny plastic particles smaller than 5mm that result from the breakdown of larger plastic waste, synthetic clothing fibers, and industrial processes. They persist in marine environments for decades and accumulate in the food chain.
          </p>
          
          <p style={{
            color: '#d1d5db',
            fontSize: '0.85em',
            lineHeight: '1.4',
            margin: 0,
            fontStyle: 'italic'
          }}>
            <strong>Sources:</strong> Plastic bottles, bags, fishing nets, synthetic textiles, tire wear. 
            <strong>Persistence:</strong> Can persist in marine environments for 100+ years.
          </p>
        </div>
      </div>

      {/* Environmental Impact */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{
          color: '#e5e7eb',
          marginBottom: '12px',
          fontSize: '1.1em'
        }}>
          Environmental Impact
        </h3>
        
        <div style={{
          padding: '16px',
          backgroundColor: 'transparent',
          border: '1px solid rgba(156, 163, 175, 0.3)',
          borderRadius: '8px',
          marginBottom: '12px',
        }}>
          <p style={{
            color: '#e5e7eb',
            fontSize: '0.9em',
            lineHeight: '1.5',
            margin: '0 0 12px 0'
          }}>
            Microplastics affect marine ecosystems through multiple pathways, causing significant environmental damage.
          </p>
          
          <div style={{
            color: '#d1d5db',
            fontSize: '0.85em',
            lineHeight: '1.4',
            margin: 0
          }}>
            <div style={{ marginBottom: '8px' }}>
              <strong>Marine Life:</strong> Ingestion by fish, seabirds, and marine mammals can cause intestinal blockage and malnutrition
            </div>
            <div style={{ marginBottom: '8px' }}>
              <strong>Food Chain:</strong> Bioaccumulation through the food web from plankton to top predators
            </div>
            <div>
              <strong>Ocean Chemistry:</strong> Can transport harmful chemicals and affect marine chemical processes
            </div>
          </div>
        </div>
      </div>

      {/* Health Implications */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{
          color: '#e5e7eb',
          marginBottom: '12px',
          fontSize: '1.1em'
        }}>
          Human Health Implications
        </h3>
        
        <div style={{
          padding: '16px',
          backgroundColor: 'transparent',
          border: '1px solid rgba(156, 163, 175, 0.3)',
          borderRadius: '8px',
          marginBottom: '12px',
        }}>
          <p style={{
            color: '#e5e7eb',
            fontSize: '0.9em',
            lineHeight: '1.5',
            margin: '0 0 12px 0'
          }}>
            Microplastics enter human systems primarily through seafood consumption and can have various health effects.
          </p>
          
          <div style={{
            color: '#d1d5db',
            fontSize: '0.85em',
            lineHeight: '1.4',
            margin: 0
          }}>
            <div style={{ marginBottom: '8px' }}>
              <strong>Physical Effects:</strong> Inflammation, cellular damage, potential immune system disruption
            </div>
            <div>
              <strong>Chemical Transport:</strong> Can carry toxic chemicals and additives into human tissues
            </div>
          </div>
        </div>
      </div>

      {/* Data Information */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{
          color: '#e5e7eb',
          marginBottom: '12px',
          fontSize: '1.1em'
        }}>
          Measurement Information
        </h3>
        
        <div style={{
          padding: '16px',
          backgroundColor: 'transparent',
          border: '1px solid rgba(156, 163, 175, 0.3)',
          borderRadius: '8px',
          marginBottom: '12px',
        }}>
          <div style={{ 
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '16px',
            fontSize: '0.85em',
            marginBottom: '12px'
          }}>
            <div>
              <strong style={{ color: '#e5e7eb' }}>Units:</strong>
              <div style={{ color: '#d1d5db' }}>pieces/m³</div>
            </div>
            <div>
              <strong style={{ color: '#e5e7eb' }}>Method:</strong>
              <div style={{ color: '#d1d5db' }}>Marine sampling</div>
            </div>
            <div>
              <strong style={{ color: '#e5e7eb' }}>Analysis:</strong>
              <div style={{ color: '#d1d5db' }}>Microscopy & spectroscopy</div>
            </div>
            <div>
              <strong style={{ color: '#e5e7eb' }}>Classification:</strong>
              <div style={{ color: '#d1d5db' }}>Environmental impact studies</div>
            </div>
          </div>
          
          <div style={{
            color: '#9ca3af',
            fontSize: '0.8em',
            lineHeight: '1.3',
            fontStyle: 'italic'
          }}>
            Microplastic concentrations are measured through water sampling and laboratory analysis using microscopy and spectroscopy techniques.
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        paddingTop: '16px',
        fontSize: '0.75em',
        color: '#6b7280',
        textAlign: 'center'
      }}>
        Microplastic analysis based on real-time data from multiple scientific sources.
      </div>
    </div>
  );
};

export default MicroplasticExplanation;