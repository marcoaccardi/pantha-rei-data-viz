import React from 'react';
import { ConnectionStatus } from '../services/connectionMonitor';

interface ConnectionStatusBarProps {
  status: ConnectionStatus;
  details?: string;
}

const ConnectionStatusBar: React.FC<ConnectionStatusBarProps> = ({ status, details }) => {
  if (status === 'connected') {
    return null; // Don't show bar when connected
  }

  const getStatusColor = () => {
    switch (status) {
      case 'disconnected':
        return 'bg-red-500';
      case 'reconnecting':
        return 'bg-yellow-500';
      case 'error':
        return 'bg-red-700';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'disconnected':
        return 'Backend server disconnected';
      case 'reconnecting':
        return details || 'Reconnecting to backend...';
      case 'error':
        return details || 'Connection error';
      default:
        return 'Unknown status';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'disconnected':
        return '⚠️';
      case 'reconnecting':
        return '🔄';
      case 'error':
        return '❌';
      default:
        return '❓';
    }
  };

  return (
    <div className={`fixed top-0 left-0 right-0 z-50 ${getStatusColor()} text-white px-4 py-2 text-center shadow-lg`}>
      <div className="flex items-center justify-center space-x-2">
        <span className="text-lg animate-pulse">{getStatusIcon()}</span>
        <span className="font-medium">{getStatusText()}</span>
        {status === 'reconnecting' && (
          <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
        )}
      </div>
    </div>
  );
};

export default ConnectionStatusBar;