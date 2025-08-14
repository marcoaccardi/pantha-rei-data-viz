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
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
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
          backgroundColor: 'rgba(0, 0, 0, 0.95)',
          color: 'white',
          padding: '40px',
          borderRadius: '20px',
          maxWidth: '900px',
          maxHeight: '90vh',
          width: '100%',
          overflowY: 'auto',
          border: '1px solid rgba(156, 163, 175, 0.2)',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          position: 'relative'
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <img
              src="/anecoica_logo.png"
              alt="Anecoica Logo"
              style={{
                width: '60px',
                height: 'auto',
                filter: 'invert(1)',
                opacity: 0.9
              }}
            />
            <div>
              <h1 style={{
                margin: '0 0 8px 0',
                fontSize: '2rem',
                color: '#3b82f6',
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
              e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.2)';
              e.currentTarget.style.borderColor = '#ef4444';
              e.currentTarget.style.color = '#ef4444';
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
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderRadius: '16px',
            border: '1px solid rgba(59, 130, 246, 0.2)'
          }}>
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
            
            <button
              onClick={() => window.open('https://anecoica.net', '_blank')}
              style={{
                marginTop: '16px',
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                color: '#3b82f6',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                padding: '8px 16px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s ease'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.3)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
              }}
            >
              <FontAwesomeIcon icon={faExternalLinkAlt} />
              Visit Anecoica Studio
            </button>
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
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            borderRadius: '16px',
            border: '1px solid rgba(16, 185, 129, 0.2)'
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
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              borderRadius: '12px'
            }}>
              <h3 style={{ color: '#f59e0b', fontSize: '1rem', marginBottom: '12px', fontWeight: '600' }}>
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
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              borderRadius: '12px'
            }}>
              <h3 style={{ color: '#f59e0b', fontSize: '1rem', marginBottom: '12px', fontWeight: '600' }}>
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
            backgroundColor: 'rgba(99, 102, 241, 0.1)',
            borderRadius: '12px',
            border: '1px solid rgba(99, 102, 241, 0.2)'
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