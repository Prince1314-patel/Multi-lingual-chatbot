import { useEffect, useRef, useState, useCallback } from 'react';
import { getWebSocketUrl, config, debugLog } from '@/lib/config';

export interface WebSocketMessage {
  type: string;
  [key: string]: unknown;
}

export interface WebSocketError {
  code: string;
  message: string;
  timestamp: string;
}

export interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  onBinaryMessage?: (data: ArrayBuffer) => void;
  onError?: (error: WebSocketError) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoReconnect?: boolean;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  isConnecting: boolean;
  error: WebSocketError | null;
  sendMessage: (message: WebSocketMessage) => boolean;
  sendBinaryMessage?: (data: ArrayBuffer) => boolean;
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
}

export const useWebSocket = (
  roomId: string,
  options: UseWebSocketOptions = {},
  userPreferences?: { displayName?: string; preferredLanguage?: string }
): UseWebSocketReturn => {
  const {
    onMessage,
    onBinaryMessage,
    onError,
    onConnect,
    onDisconnect,
    autoReconnect = true
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<WebSocketError | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptsRef = useRef(0);
  const connectionTimeoutRef = useRef<NodeJS.Timeout>();
  const shouldStopReconnecting = useRef(false);

  const createError = (code: string, message: string): WebSocketError => ({
    code,
    message,
    timestamp: new Date().toISOString()
  });

  const clearTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
      connectionTimeoutRef.current = undefined;
    }
  }, []);

  const handleError = useCallback((errorCode: string, errorMessage: string) => {
    const wsError = createError(errorCode, errorMessage);
    setError(wsError);
    onError?.(wsError);
    debugLog('WebSocket error:', wsError);
  }, [onError]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      debugLog('WebSocket already connected');
      return;
    }

    if (isConnecting) {
      debugLog('WebSocket connection already in progress');
      return;
    }

    if (shouldStopReconnecting.current) {
      debugLog('WebSocket reconnection stopped due to server rejection');
      return;
    }

    setIsConnecting(true);
    setError(null);
    clearTimeouts();

    try {
      const wsUrl = getWebSocketUrl(roomId, userPreferences);
      debugLog('Connecting to WebSocket:', wsUrl);
      debugLog('Current window location:', typeof window !== 'undefined' ? window.location.href : 'SSR');
      debugLog('User preferences:', userPreferences);
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      // Connection timeout
      connectionTimeoutRef.current = setTimeout(() => {
        if (ws.readyState === WebSocket.CONNECTING) {
          ws.close();
          handleError('CONNECTION_TIMEOUT', 'Connection timeout');
          setIsConnecting(false);
        }
      }, config.connectionTimeout);

      ws.onopen = () => {
        debugLog('WebSocket connected to room:', roomId);
        clearTimeouts();
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
        reconnectAttemptsRef.current = 0;
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          // Handle binary messages
          if (event.data instanceof ArrayBuffer) {
            debugLog('WebSocket binary message received:', event.data.byteLength, 'bytes');
            onBinaryMessage?.(event.data);
            return;
          }
          
          // Handle Blob messages (convert to ArrayBuffer)
          if (event.data instanceof Blob) {
            debugLog('WebSocket blob message received:', event.data.size, 'bytes');
            event.data.arrayBuffer().then((arrayBuffer) => {
              onBinaryMessage?.(arrayBuffer);
            }).catch((error) => {
              debugLog('Error converting blob to ArrayBuffer:', error);
              handleError('BLOB_CONVERSION_ERROR', 'Failed to convert blob message');
            });
            return;
          }
          
          // Handle text messages (JSON)
          if (typeof event.data === 'string') {
            const message: WebSocketMessage = JSON.parse(event.data);
            debugLog('WebSocket message received:', message);
            onMessage?.(message);
            return;
          }
          
          // Unknown message type
          debugLog('Unknown WebSocket message type:', typeof event.data, event.data);
          handleError('UNKNOWN_MESSAGE_TYPE', `Unknown message type: ${typeof event.data}`);
          
        } catch (parseError) {
          debugLog('WebSocket message parse error:', parseError, 'Raw data:', event.data);
          handleError('INVALID_MESSAGE_FORMAT', `Failed to parse message: ${parseError}`);
        }
      };

      ws.onclose = (event) => {
        debugLog('WebSocket disconnected:', event.code, event.reason);
        clearTimeouts();
        setIsConnected(false);
        setIsConnecting(false);
        
        // Check for specific error codes that should stop reconnection
        const shouldStopReconnectingCodes = [
          4003, // Connection limit exceeded (custom code)
          4001, // Unauthorized
          4004, // Rate limited
          1002, // Protocol error
          1003, // Unsupported data
          1007, // Invalid frame payload data
          1008, // Policy violation
          1011  // Internal server error
        ];
        
        if (shouldStopReconnectingCodes.includes(event.code)) {
          shouldStopReconnecting.current = true;
          debugLog('Stopping reconnection due to error code:', event.code);
        }
        
        // Don't treat code 1001 (going away) as an error for reconnection
        if (event.code !== 1000 && event.code !== 1001) { // Not a normal closure or going away
          const errorMessage = event.reason || 'Unknown reason';
          if (event.code === 4003 || errorMessage.includes('connection limit') || errorMessage.includes('CONNECTION_LIMIT_EXCEEDED')) {
            handleError('CONNECTION_LIMIT_EXCEEDED', 'Connection limit exceeded. Please try again later.');
            shouldStopReconnecting.current = true;
          } else {
            handleError('CONNECTION_CLOSED', `Connection closed: ${errorMessage}`);
          }
        }
        
        onDisconnect?.();

        // Auto-reconnect logic - only if we shouldn't stop reconnecting and it's not a normal close
        if (autoReconnect && 
            !shouldStopReconnecting.current && 
            event.code !== 1000 && // Normal close
            event.code !== 1001 && // Going away (page refresh/navigation)
            reconnectAttemptsRef.current < config.reconnectAttempts) {
          const delay = config.reconnectDelay * Math.pow(2, reconnectAttemptsRef.current); // Exponential backoff
          debugLog(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${config.reconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, delay);
        } else if (autoReconnect && shouldStopReconnecting.current) {
          handleError('RECONNECTION_STOPPED', 'Reconnection stopped due to server rejection');
        } else if (autoReconnect && reconnectAttemptsRef.current >= config.reconnectAttempts) {
          handleError('MAX_RECONNECT_ATTEMPTS', 'Maximum reconnection attempts reached');
        }
      };

      ws.onerror = (event) => {
        debugLog('WebSocket error event:', event);
        clearTimeouts();
        setIsConnecting(false);
        handleError('CONNECTION_ERROR', 'WebSocket connection error');
      };

    } catch (error) {
      setIsConnecting(false);
      handleError('CONNECTION_FAILED', `Failed to create WebSocket connection: ${error}`);
    }
  }, [roomId, handleError, clearTimeouts]); // Removed problematic dependencies

  const disconnect = useCallback(() => {
    debugLog('Disconnecting WebSocket');
    clearTimeouts();
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setIsConnecting(false);
    setError(null);
    reconnectAttemptsRef.current = 0;
    shouldStopReconnecting.current = false; // Reset the flag on manual disconnect
  }, [clearTimeouts]);

  const reconnect = useCallback(() => {
    debugLog('Manual reconnect requested');
    shouldStopReconnecting.current = false; // Reset the flag on manual reconnect
    clearTimeouts();
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual reconnect');
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setIsConnecting(false);
    setError(null);
    reconnectAttemptsRef.current = 0;
    
    setTimeout(() => {
      connect();
    }, 100); // Small delay to ensure cleanup
  }, [connect, clearTimeouts]);

  const sendMessage = useCallback((message: WebSocketMessage): boolean => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      handleError('NOT_CONNECTED', 'WebSocket is not connected');
      return false;
    }

    try {
      const messageStr = JSON.stringify(message);
      wsRef.current.send(messageStr);
      debugLog('WebSocket message sent:', message);
      return true;
    } catch (error) {
      handleError('SEND_FAILED', `Failed to send message: ${error}`);
      return false;
    }
  }, [handleError]);

  const sendBinaryMessage = useCallback((data: ArrayBuffer): boolean => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      handleError('NOT_CONNECTED', 'WebSocket is not connected');
      return false;
    }

    try {
      wsRef.current.send(data);
      debugLog('WebSocket binary message sent:', data.byteLength, 'bytes');
      return true;
    } catch (error) {
      handleError('SEND_FAILED', `Failed to send binary message: ${error}`);
      return false;
    }
  }, [handleError]);

  // Connect on mount and room change
  useEffect(() => {
    connect();
    return () => {
      debugLog('Cleaning up WebSocket connection for room:', roomId);
      clearTimeouts();
      if (wsRef.current) {
        wsRef.current.close(1000, 'Room changed');
        wsRef.current = null;
      }
      setIsConnected(false);
      setIsConnecting(false);
      reconnectAttemptsRef.current = 0;
      shouldStopReconnecting.current = false;
    };
  }, [roomId]); // Only depend on roomId

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimeouts();
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
      }
    };
  }, [clearTimeouts]);

  return {
    isConnected,
    isConnecting,
    error,
    sendMessage,
    sendBinaryMessage,
    connect,
    disconnect,
    reconnect
  };
};