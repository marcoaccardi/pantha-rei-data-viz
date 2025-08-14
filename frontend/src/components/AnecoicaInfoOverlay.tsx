import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faXmark, 
  faWater,
  faUsers,
  faFlask,
  faGlobe,
  faExternalLinkAlt
} from '@fortawesome/free-solid-svg-icons';

interface AnecoicaInfoOverlayProps {
  onClose: () => void;
}

const AnecoicaInfoOverlay: React.FC<AnecoicaInfoOverlayProps> = ({ onClose }) => {
  
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
          maxWidth: '900px',
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
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '16px' }}>
            <img
              src="/anecoica_logo.png"
              alt="Anecoica Logo"
              style={{
                width: '80px',
                height: 'auto',
                filter: 'invert(1)',
                opacity: 0.9
              }}
            />
            <div>
              <h1 style={{
                margin: '0 0 8px 0',
                fontSize: '2rem',
                color: '#e5e7eb',
                fontWeight: '700'
              }}>
                Anecoica Studio
              </h1>
              <p style={{
                fontSize: '1.1rem',
                color: '#9ca3af',
                margin: 0,
                lineHeight: '1.5'
              }}>
                Berlin new media art company
              </p>
            </div>
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
            title="Close info overlay (Press Esc)"
          >
            <FontAwesomeIcon icon={faXmark} />
          </button>
        </div>

        {/* Studio Section */}
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
            <FontAwesomeIcon icon={faGlobe} />
            About the Studio
          </h2>
          
          <div style={{
            padding: '24px',
            backgroundColor: 'transparent',
            borderRadius: '16px',
            border: '1px solid rgba(156, 163, 175, 0.4)',
            display: 'flex',
            gap: '20px',
            alignItems: 'flex-start'
          }}>
            <div style={{ flex: 1 }}>
              <p style={{
                fontSize: '1.05rem',
                color: '#e5e7eb',
                lineHeight: '1.6',
                margin: '0 0 16px 0'
              }}>
                We are a Berlin new media art company focused on quantum AI technology, exploring the intersections 
                of science, creativity, and technology. We push the boundaries of perception and innovation through 
                experimentation, crafting meaningful experiences that merge art, design, and advanced technologies.
              </p>
              <div style={{
                fontSize: '1rem',
                color: '#d1d5db',
                lineHeight: '1.6',
                margin: 0
              }}>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Focus:</strong> Bridging the gap between human and machine expression
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Expertise:</strong> Music, sound design, computer graphics, AI, and web development  
                </div>
                <div>
                  <strong>Mission:</strong> Redefining creativity at the intersection of art, technology, and science
                </div>
              </div>
            </div>
            
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '8px',
              flexShrink: 0
            }}>
              <img
                src="data:image/png;base64,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"
                alt="QR Code for anecoica.net"
                style={{
                  width: '80px',
                  height: '80px',
                  border: '1px solid rgba(156, 163, 175, 0.3)',
                  borderRadius: '8px',
                  padding: '4px',
                  backgroundColor: 'white'
                }}
              />
              <div style={{
                fontSize: '0.75rem',
                color: '#9ca3af',
                textAlign: 'center'
              }}>
                Scan to visit<br />anecoica.net
              </div>
            </div>
          </div>
        </section>

        {/* Project Section */}
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
            <FontAwesomeIcon icon={faWater} />
            About "Panta Rhei"
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
              An immersive audiovisual art installation that transforms real-time ocean data into a responsive, 
              interactive environment exploring humanity's relationship with marine ecosystems. Named after the 
              ancient Greek principle meaning "everything flows," the installation creates a living artwork 
              that mirrors the constant flux of oceanic systems.
            </p>
            <div style={{
              fontSize: '1rem',
              color: '#d1d5db',
              lineHeight: '1.6',
              margin: 0
            }}>
              <div style={{ marginBottom: '8px' }}>
                <strong>Technology:</strong> AI, computer vision, and live oceanographic data integration
              </div>
              <div style={{ marginBottom: '8px' }}>
                <strong>Experience:</strong> Gesture-responsive visualizations and generative soundscapes
              </div>
              <div>
                <strong>Purpose:</strong> Environmental awareness through embodied data experiences
              </div>
            </div>
          </div>
        </section>

        {/* Credits Section */}
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
            <FontAwesomeIcon icon={faUsers} />
            Credits
          </h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div style={{
              padding: '20px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(156, 163, 175, 0.4)',
              borderRadius: '12px'
            }}>
              <h3 style={{ color: '#e5e7eb', fontSize: '1rem', marginBottom: '12px', fontWeight: '600' }}>
                Creative Team
              </h3>
              <div style={{ fontSize: '0.9rem', color: '#d1d5db', lineHeight: '1.5' }}>
                <div style={{ marginBottom: '6px' }}>
                  <strong>Marco Accardi</strong><br />
                  Art Director, Software Engineer
                </div>
                <div>
                  <strong>Alessandro De Angelis</strong><br />
                  Studio Manager
                </div>
              </div>
            </div>
            
            <div style={{
              padding: '20px',
              backgroundColor: 'transparent',
              border: '1px solid rgba(156, 163, 175, 0.4)',
              borderRadius: '12px'
            }}>
              <h3 style={{ color: '#e5e7eb', fontSize: '1rem', marginBottom: '12px', fontWeight: '600' }}>
                Scientific Collaboration
              </h3>
              <div style={{ fontSize: '0.9rem', color: '#d1d5db', lineHeight: '1.5' }}>
                <div style={{ marginBottom: '6px' }}>
                  <strong>NOAA, NCEI</strong><br />
                  Oceanographic Data Partnership
                </div>
                <div>
                  <strong>Erick Geiger, Ebenezer Nyadjro</strong><br />
                  Scientific Advisors
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Data Sources Section */}
        <section style={{ marginBottom: '24px' }}>
          <h2 style={{
            fontSize: '1.4rem',
            color: '#e5e7eb',
            marginBottom: '20px',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <FontAwesomeIcon icon={faFlask} />
            Data Sources
          </h2>
          
          <div style={{
            padding: '20px',
            backgroundColor: 'transparent',
            borderRadius: '12px',
            border: '1px solid rgba(156, 163, 175, 0.4)'
          }}>
            <div style={{
              fontSize: '1rem',
              color: '#d1d5db',
              lineHeight: '1.6'
            }}>
              <div style={{ marginBottom: '8px' }}>
                <strong>Primary:</strong> NOAA National Centers for Environmental Information (NCEI)
              </div>
              <div style={{ marginBottom: '8px' }}>
                <strong>Secondary:</strong> Copernicus Marine Service, OSCAR Currents Database
              </div>
              <div style={{ marginBottom: '16px' }}>
                <strong>Coverage:</strong> Real-time ocean temperature, chemistry, currents, and microplastics data
              </div>
              <div style={{ fontSize: '0.9rem', color: '#9ca3af', fontStyle: 'italic' }}>
                All data used with proper attribution and in accordance with scientific data policies
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <div style={{
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          paddingTop: '24px',
          textAlign: 'center'
        }}>
          <p style={{
            fontSize: '0.9rem',
            color: '#6b7280',
            margin: '0 0 8px 0'
          }}>
            "Panta Rhei" • Everything Flows
          </p>
          <p style={{
            fontSize: '0.8rem',
            color: '#6b7280',
            margin: 0
          }}>
            An art-science collaboration exploring our relationship with marine ecosystems
          </p>
        </div>
      </div>
    </div>
  );
};

export default AnecoicaInfoOverlay;