import React from 'react';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error?: Error; resetError: () => void }>;
}

const DefaultErrorFallback: React.FC<{ error?: Error; resetError: () => void }> = ({ error, resetError }) => (
  <div style={{
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    backgroundColor: '#000011',
    color: 'white',
    padding: '20px',
    textAlign: 'center'
  }}>
    <h2>🌊 Ocean Data Visualization</h2>
    <p>Loading ocean data textures...</p>
    <div style={{
      width: '50px',
      height: '50px',
      border: '3px solid #333',
      borderTop: '3px solid #4a90e2',
      borderRadius: '50%',
      animation: 'spin 1s linear infinite',
      margin: '20px 0'
    }}></div>
    <p style={{ fontSize: '0.9em', opacity: 0.7 }}>
      {error ? 'Retrying texture loading...' : 'Initializing globe...'}
    </p>
    <button 
      onClick={resetError}
      style={{
        backgroundColor: '#4a90e2',
        color: 'white',
        border: 'none',
        padding: '8px 16px',
        borderRadius: '4px',
        cursor: 'pointer',
        marginTop: '10px'
      }}
    >
      Retry
    </button>
    <style>{`
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `}</style>
  </div>
);

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    
    // If it's a texture loading error, we can try to recover
    if (error.message.includes('Could not load') || error.message.includes('texture')) {
      // Auto-retry after a short delay
      setTimeout(() => {
        this.setState({ hasError: false, error: undefined });
      }, 2000);
    }
  }

  resetError = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback;
      return <FallbackComponent error={this.state.error} resetError={this.resetError} />;
    }

    return this.props.children;
  }
}

export default ErrorBoundary;