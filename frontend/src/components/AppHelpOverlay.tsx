import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faXmark, 
  faLocationDot, 
  faCalendar, 
  faDice,
  faTemperatureHigh, 
  faBottleWater, 
  faWater,
  faFlask,
  faCircleInfo,
  faMousePointer,
  faCog,
  faChartBar,
  faHandPointer
} from '@fortawesome/free-solid-svg-icons';

interface AppHelpOverlayProps {
  onClose: () => void;
}

const AppHelpOverlay: React.FC<AppHelpOverlayProps> = ({ onClose }) => {
  
  // Handle escape key to close overlay
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div 
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.4)',
        backdropFilter: 'blur(10px)',
        zIndex: 2000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px'
      }}
      onClick={onClose}
    >
      <div 
        className="elegant-scrollbar"
        style={{
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          color: 'white',
          padding: '40px',
          borderRadius: '20px',
          maxWidth: '1000px',
          maxHeight: '90vh',
          width: '100%',
          overflowY: 'auto',
          border: '1px solid rgba(156, 163, 175, 0.3)',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          position: 'relative',
          backdropFilter: 'blur(15px)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '40px',
          paddingBottom: '24px',
          borderBottom: '1px solid rgba(156, 163, 175, 0.3)'
        }}>
          <div>
            <h1 style={{
              margin: '0 0 12px 0',
              fontSize: '2rem',
              color: '#3b82f6',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <FontAwesomeIcon icon={faWater} />
              How to Use Ocean Data Explorer
            </h1>
            <p style={{
              fontSize: '1.1rem',
              color: '#9ca3af',
              margin: 0,
              lineHeight: '1.5'
            }}>
              Your guide to exploring real-time ocean data and understanding marine ecosystems
            </p>
          </div>
          
          <button
            onClick={onClose}
            style={{
              backgroundColor: 'transparent',
              border: '1px solid rgba(156, 163, 175, 0.5)',
              borderRadius: '50%',
              padding: '12px',
              color: '#9ca3af',
              cursor: 'pointer',
              fontSize: '1.3em',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '44px',
              height: '44px',
              transition: 'all 0.2s ease'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(156, 163, 175, 0.2)';
              e.currentTarget.style.borderColor = '#6b7280';
              e.currentTarget.style.color = '#6b7280';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.borderColor = 'rgba(156, 163, 175, 0.5)';
              e.currentTarget.style.color = '#9ca3af';
            }}
            title="Close help overlay (Press Esc)"
          >
            <FontAwesomeIcon icon={faXmark} />
          </button>
        </div>

        {/* App Overview */}
        <section style={{ marginBottom: '48px' }}>
          <h2 style={{
            fontSize: '1.4rem',
            color: '#e5e7eb',
            marginBottom: '20px',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <FontAwesomeIcon icon={faCircleInfo} />
            What is Ocean Data Explorer?
          </h2>
          
          <div style={{
            padding: '24px',
            backgroundColor: 'transparent',
            borderRadius: '16px',
            border: '1px solid rgba(156, 163, 175, 0.4)'
          }}>
            <p style={{
              fontSize: '1.05rem',
              color: '#e5e7eb',
              lineHeight: '1.6',
              margin: '0 0 16px 0'
            }}>
              This interactive globe allows you to explore real-time ocean data from scientific sources including 
              NOAA, Copernicus Marine Service, and other oceanographic institutions.
            </p>
            <div style={{
              fontSize: '1rem',
              color: '#d1d5db',
              lineHeight: '1.6',
              margin: 0
            }}>
              <div style={{ marginBottom: '8px' }}>
                <strong>Visualize:</strong> Sea surface temperature, ocean chemistry, currents, and microplastic pollution
              </div>
              <div style={{ marginBottom: '8px' }}>
                <strong>Analyze:</strong> Ocean health indicators and ecosystem conditions
              </div>
              <div>
                <strong>Explore:</strong> Historical and real-time oceanographic data worldwide
              </div>
            </div>
          </div>
        </section>

        {/* Navigation Guide */}
        <section style={{ marginBottom: '48px' }}>
          <h2 style={{
            fontSize: '1.25rem',
            color: '#e5e7eb',
            marginBottom: '16px',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <FontAwesomeIcon icon={faMousePointer} />
            How to Navigate
          </h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div style={{
              padding: '20px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(156, 163, 175, 0.4)',
              borderRadius: '12px'
            }}>
              <h3 style={{ color: '#10b981', fontSize: '1rem', marginBottom: '8px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FontAwesomeIcon icon={faMousePointer} /> Click Globe
              </h3>
              <p style={{ color: '#d1d5db', fontSize: '0.9rem', lineHeight: '1.4', margin: 0 }}>
                Single-click anywhere on the globe to fetch ocean data for that location and display comprehensive analysis.
              </p>
            </div>
            
            <div style={{
              padding: '20px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(156, 163, 175, 0.4)',
              borderRadius: '12px'
            }}>
              <h3 style={{ color: '#10b981', fontSize: '1rem', marginBottom: '8px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FontAwesomeIcon icon={faMousePointer} /> Double-Click
              </h3>
              <p style={{ color: '#d1d5db', fontSize: '0.9rem', lineHeight: '1.4', margin: 0 }}>
                Double-click to quickly zoom to a location and automatically fetch its ocean data.
              </p>
            </div>
            
            <div style={{
              padding: '20px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(156, 163, 175, 0.4)',
              borderRadius: '12px'
            }}>
              <h3 style={{ color: '#10b981', fontSize: '1rem', marginBottom: '8px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FontAwesomeIcon icon={faHandPointer} /> Drag & Rotate
              </h3>
              <p style={{ color: '#d1d5db', fontSize: '0.9rem', lineHeight: '1.4', margin: 0 }}>
                Drag to rotate the globe freely. Use mouse wheel or pinch gestures to zoom in and out.
              </p>
            </div>
          </div>
        </section>

        {/* Control Panel Guide */}
        <section style={{ marginBottom: '48px' }}>
          <h2 style={{
            fontSize: '1.25rem',
            color: '#e5e7eb',
            marginBottom: '16px',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <FontAwesomeIcon icon={faCog} />
            Control Panel (Top Left)
          </h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{
              padding: '16px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(156, 163, 175, 0.4)',
              borderRadius: '8px'
            }}>
              <h3 style={{
                color: '#e5e7eb',
                fontSize: '1rem',
                marginBottom: '8px',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <FontAwesomeIcon icon={faCalendar} />
                Date Selection
              </h3>
              <p style={{ color: '#d1d5db', fontSize: '0.9rem', lineHeight: '1.4', margin: 0 }}>
                Choose any date from 2003 to present. Recent dates (2020-2025) have the best data coverage. 
                Data automatically updates when you change dates.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
              <div style={{
                padding: '16px',
                backgroundColor: 'transparent',
                border: '1px solid rgba(156, 163, 175, 0.4)',
                borderRadius: '12px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>
                  <FontAwesomeIcon icon={faLocationDot} />
                </div>
                <h4 style={{ color: '#e5e7eb', fontSize: '0.9rem', marginBottom: '4px', fontWeight: '600' }}>
                  Random Location
                </h4>
                <p style={{ color: '#d1d5db', fontSize: '0.8rem', margin: 0 }}>
                  Jump to verified ocean locations with guaranteed data coverage
                </p>
              </div>
              
              <div style={{
                padding: '12px',
                backgroundColor: 'transparent',
                border: '1px solid rgba(156, 163, 175, 0.4)',
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>
                  <FontAwesomeIcon icon={faCalendar} />
                </div>
                <h4 style={{ color: '#e5e7eb', fontSize: '0.9rem', marginBottom: '4px', fontWeight: '600' }}>
                  Random Date
                </h4>
                <p style={{ color: '#d1d5db', fontSize: '0.8rem', margin: 0 }}>
                  Select a random date with good data availability
                </p>
              </div>
              
              <div style={{
                padding: '12px',
                backgroundColor: 'transparent',
                border: '1px solid rgba(156, 163, 175, 0.4)',
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>
                  <FontAwesomeIcon icon={faDice} />
                </div>
                <h4 style={{ color: '#e5e7eb', fontSize: '0.9rem', marginBottom: '4px', fontWeight: '600' }}>
                  Random Both
                </h4>
                <p style={{ color: '#d1d5db', fontSize: '0.8rem', margin: 0 }}>
                  Generate random date and location combination
                </p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div style={{
                padding: '12px',
                backgroundColor: 'transparent',
                border: '1px solid rgba(156, 163, 175, 0.4)',
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <h4 style={{
                  color: '#e5e7eb',
                  fontSize: '0.9rem',
                  marginBottom: '8px',
                  fontWeight: '600',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}>
                  <FontAwesomeIcon icon={faTemperatureHigh} />
                  SST Texture
                </h4>
                <p style={{ color: '#d1d5db', fontSize: '0.8rem', margin: 0 }}>
                  Toggle sea surface temperature overlay on the globe
                </p>
              </div>
              
              <div style={{
                padding: '12px',
                backgroundColor: 'transparent',
                border: '1px solid rgba(156, 163, 175, 0.4)',
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <h4 style={{
                  color: '#e5e7eb',
                  fontSize: '0.9rem',
                  marginBottom: '8px',
                  fontWeight: '600',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}>
                  <FontAwesomeIcon icon={faBottleWater} />
                  Microplastics
                </h4>
                <p style={{ color: '#d1d5db', fontSize: '0.8rem', margin: 0 }}>
                  Show microplastic pollution data points as 3D spheres
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Data Panel Guide */}
        <section style={{ marginBottom: '48px' }}>
          <h2 style={{
            fontSize: '1.25rem',
            color: '#e5e7eb',
            marginBottom: '16px',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <FontAwesomeIcon icon={faChartBar} />
            Data Panel (Right Side)
          </h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{
              padding: '16px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(156, 163, 175, 0.4)',
              borderRadius: '8px'
            }}>
              <h3 style={{
                color: '#ef4444',
                fontSize: '1rem',
                marginBottom: '8px',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <FontAwesomeIcon icon={faTemperatureHigh} />
                Temperature Data
              </h3>
              <p style={{ color: '#d1d5db', fontSize: '0.9rem', lineHeight: '1.4', margin: 0 }}>
                Sea surface temperature, ice concentration, and temperature anomalies. 
                Includes ocean health analysis and climate impact indicators.
              </p>
            </div>
            
            <div style={{
              padding: '16px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(156, 163, 175, 0.4)',
              borderRadius: '8px'
            }}>
              <h3 style={{
                color: '#10b981',
                fontSize: '1rem',
                marginBottom: '8px',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <FontAwesomeIcon icon={faFlask} />
                Ocean Chemistry
              </h3>
              <p style={{ color: '#d1d5db', fontSize: '0.9rem', lineHeight: '1.4', margin: 0 }}>
                pH levels, dissolved oxygen, nutrients (nitrate, phosphate), and carbon chemistry. 
                Critical for understanding ocean acidification and marine ecosystem health.
              </p>
            </div>
            
            <div style={{
              padding: '16px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(156, 163, 175, 0.4)',
              borderRadius: '8px'
            }}>
              <h3 style={{
                color: '#3b82f6',
                fontSize: '1rem',
                marginBottom: '8px',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <FontAwesomeIcon icon={faWater} />
                Ocean Currents
              </h3>
              <p style={{ color: '#d1d5db', fontSize: '0.9rem', lineHeight: '1.4', margin: 0 }}>
                Current speed and direction, water temperature at depth, and salinity. 
                Essential for understanding ocean circulation and marine habitat connectivity.
              </p>
            </div>

            <div style={{
              padding: '20px',
              backgroundColor: 'transparent',
              borderRadius: '12px',
              border: '1px solid rgba(156, 163, 175, 0.4)'
            }}>
              <h3 style={{
                color: '#6366f1',
                fontSize: '1rem',
                marginBottom: '8px',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <FontAwesomeIcon icon={faCircleInfo} />
                Health Analysis
              </h3>
              <p style={{ color: '#d1d5db', fontSize: '0.9rem', lineHeight: '1.4', margin: 0 }}>
                Click the info icons next to each section to view detailed ocean health analysis, 
                environmental impacts, and scientific context for the measurements.
              </p>
            </div>
          </div>
        </section>



        {/* Footer */}
        <div style={{
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          paddingTop: '32px',
          marginTop: '20px',
          textAlign: 'center'
        }}>
          <p style={{
            fontSize: '0.85rem',
            color: '#6b7280',
            margin: '0 0 8px 0'
          }}>
            Ocean Data Explorer • Real-time oceanographic data visualization
          </p>
          <p style={{
            fontSize: '0.8rem',
            color: '#6b7280',
            margin: 0
          }}>
            Data sources: NOAA, Copernicus Marine Service, and scientific research institutions
          </p>
        </div>
      </div>
    </div>
  );
};

export default AppHelpOverlay;