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
    try {
      const ws = new WebSocket('ws://localhost:8765');
      
      ws.onopen = () => {
        setIsConnected(true);
        wsRef.current = ws;
        onConnect?.();
        
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          onMessage?.(message);
        } catch (error) {
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        onDisconnect?.();
        
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectDelay);
      };

      ws.onerror = (error) => {
      };

    } catch (error) {
      reconnectTimeoutRef.current = setTimeout(connect, reconnectDelay);
    }
  };

  const sendMessage = (message: WebSocketMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
    }
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
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