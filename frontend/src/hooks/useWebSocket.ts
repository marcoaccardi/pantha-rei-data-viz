import { useEffect, useRef, useState } from 'react';
import type { WebSocketMessage } from '../utils/types';

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectDelay?: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { onMessage, onConnect, onDisconnect, reconnectDelay = 3000 } = options;
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = () => {
    // REST API only - no WebSocket server exists
    // Simulate immediate connection for compatibility
    setIsConnected(true);
    onConnect?.();
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  };

  const sendMessage = (message: WebSocketMessage) => {
    // REST API only - WebSocket messages not supported
    // This function is kept for compatibility but does nothing
    console.warn('WebSocket sendMessage called but only REST API is available');
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    // REST API only - no WebSocket connection to close
    setIsConnected(false);
    onDisconnect?.();
  };

  useEffect(() => {
    // Simulate connection when using REST API instead
    setIsConnected(true);
    
    return () => {
      disconnect();
    };
  }, []);

  return {
    isConnected,
    sendMessage,
    disconnect
  };
}