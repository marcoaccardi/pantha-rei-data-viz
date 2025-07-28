/**
 * Connection Monitor Service
 * 
 * Monitors backend API health and automatically detects when the server
 * restarts or becomes unavailable, providing real-time status updates.
 */

import React from 'react';
import { requestCache } from '../utils/requestCache';

export type ConnectionStatus = 'connected' | 'disconnected' | 'reconnecting' | 'error';

interface ConnectionStatusListener {
  (status: ConnectionStatus, details?: string): void;
}

class ConnectionMonitor {
  private status: ConnectionStatus = 'disconnected';
  private listeners: Set<ConnectionStatusListener> = new Set();
  private monitorInterval: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private healthCheckUrl = '/health';
  private baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  
  // Health check intervals
  private normalInterval = 30000; // 30 seconds when connected
  private fastInterval = 5000;    // 5 seconds when reconnecting
  private errorInterval = 10000;  // 10 seconds after errors

  constructor() {
    // Start monitoring immediately
    this.startMonitoring();
  }

  /**
   * Start monitoring the backend connection
   */
  private startMonitoring() {
    // Initial check
    this.checkConnection();
    
    // Set up periodic checks
    this.scheduleNextCheck(this.fastInterval);
  }

  /**
   * Schedule the next health check
   */
  private scheduleNextCheck(interval: number) {
    if (this.monitorInterval) {
      clearTimeout(this.monitorInterval);
    }
    
    this.monitorInterval = setTimeout(() => {
      this.checkConnection();
    }, interval);
  }

  /**
   * Check backend connection health
   */
  private async checkConnection() {
    try {
      const response = await fetch(`${this.baseUrl}${this.healthCheckUrl}`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000), // 5 second timeout
        headers: {
          'Accept': 'application/json',
        }
      });

      if (response.ok) {
        const wasDisconnected = this.status !== 'connected';
        this.updateStatus('connected');
        this.reconnectAttempts = 0;
        
        if (wasDisconnected) {
          console.log('✅ Backend connection restored');
          // Clear cache on reconnection to ensure fresh data
          requestCache.clearAll();
        }
        
        // Schedule next check with normal interval
        this.scheduleNextCheck(this.normalInterval);
      } else {
        throw new Error(`Health check failed with status: ${response.status}`);
      }
    } catch (error) {
      this.handleConnectionError(error);
    }
  }

  /**
   * Handle connection errors
   */
  private handleConnectionError(error: any) {
    console.warn('🔌 Backend connection error:', error.message);
    
    if (this.status === 'connected') {
      // Just disconnected
      this.updateStatus('disconnected', 'Backend server unavailable');
    }
    
    // Attempt reconnection
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      this.updateStatus('reconnecting', `Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      this.scheduleNextCheck(this.fastInterval);
    } else {
      // Max attempts reached
      this.updateStatus('error', 'Unable to connect to backend server');
      this.scheduleNextCheck(this.errorInterval);
    }
  }

  /**
   * Update connection status and notify listeners
   */
  private updateStatus(status: ConnectionStatus, details?: string) {
    if (this.status !== status) {
      this.status = status;
      console.log(`🔌 Connection status: ${status}${details ? ` - ${details}` : ''}`);
      
      // Notify all listeners
      this.listeners.forEach(listener => {
        try {
          listener(status, details);
        } catch (error) {
          console.error('Error in connection status listener:', error);
        }
      });
    }
  }

  /**
   * Get current connection status
   */
  getStatus(): ConnectionStatus {
    return this.status;
  }

  /**
   * Subscribe to connection status changes
   */
  subscribe(listener: ConnectionStatusListener): () => void {
    this.listeners.add(listener);
    
    // Immediately notify of current status
    listener(this.status);
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Force a connection check
   */
  forceCheck() {
    this.checkConnection();
  }

  /**
   * Reset reconnection attempts
   */
  resetReconnectAttempts() {
    this.reconnectAttempts = 0;
  }

  /**
   * Stop monitoring
   */
  stopMonitoring() {
    if (this.monitorInterval) {
      clearTimeout(this.monitorInterval);
      this.monitorInterval = null;
    }
  }
}

// Export singleton instance
export const connectionMonitor = new ConnectionMonitor();

// Export hook for React components
export function useConnectionStatus() {
  const [status, setStatus] = React.useState<ConnectionStatus>(connectionMonitor.getStatus());
  const [details, setDetails] = React.useState<string | undefined>();

  React.useEffect(() => {
    const unsubscribe = connectionMonitor.subscribe((newStatus, newDetails) => {
      setStatus(newStatus);
      setDetails(newDetails);
    });

    return unsubscribe;
  }, []);

  return { status, details, isConnected: status === 'connected' };
}

// Make it available globally for debugging
if (typeof window !== 'undefined') {
  (window as any).connectionMonitor = connectionMonitor;
}