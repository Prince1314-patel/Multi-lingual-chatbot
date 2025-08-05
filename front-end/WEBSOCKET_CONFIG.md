# WebSocket Configuration Guide

This document explains how the frontend WebSocket configuration works and how to customize it.

## Configuration Overview

The frontend uses a centralized configuration system that supports environment variables for flexible deployment across different environments.

## Configuration Files

### Environment Variables

Create a `.env.local` file in the frontend root directory:

```env
# Backend API Configuration
VITE_BACKEND_URL=http://localhost:8000
VITE_WEBSOCKET_URL=ws://localhost:8000

# WebSocket Configuration
VITE_WS_RECONNECT_ATTEMPTS=5
VITE_WS_RECONNECT_DELAY=1000
VITE_WS_CONNECTION_TIMEOUT=10000

# Development Settings
VITE_ENABLE_DEBUG_LOGS=true
```

### Configuration Module

The configuration is managed by `src/lib/config.ts`:

```typescript
import { config, getWebSocketUrl, getApiUrl } from '@/lib/config';

// Get WebSocket URL for a room
const wsUrl = getWebSocketUrl('room-123');
// Result: ws://localhost:8000/ws/chat/room-123

// Get API endpoint URL
const apiUrl = getApiUrl('/health');
// Result: http://localhost:8000/health
```

## WebSocket Hook

The `useWebSocket` hook provides a robust WebSocket connection with:

- **Automatic reconnection** with exponential backoff
- **Connection state management** (connecting, connected, disconnected)
- **Error handling** with detailed error messages
- **Message queuing** during disconnection
- **Connection timeout** handling

### Usage Example

```typescript
import { useWebSocket } from '@/hooks/useWebSocket';

const MyComponent = ({ roomId }: { roomId: string }) => {
  const {
    isConnected,
    isConnecting,
    error,
    sendMessage,
    reconnect
  } = useWebSocket(roomId, {
    onMessage: (message) => {
      console.log('Received:', message);
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    },
    onConnect: () => {
      console.log('Connected to room:', roomId);
    },
    onDisconnect: () => {
      console.log('Disconnected from room:', roomId);
    },
    autoReconnect: true
  });

  const handleSendMessage = () => {
    const success = sendMessage({
      type: 'message',
      text: 'Hello!',
      from: 'user1',
      to: 'user2'
    });
    
    if (!success) {
      console.error('Failed to send message');
    }
  };

  return (
    <div>
      <div>Status: {isConnected ? 'Connected' : 'Disconnected'}</div>
      {error && <div>Error: {error.message}</div>}
      <button onClick={handleSendMessage}>Send Message</button>
      <button onClick={reconnect}>Reconnect</button>
    </div>
  );
};
```

## Configuration Options

### Backend URLs

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_BACKEND_URL` | `http://localhost:8000` | HTTP API base URL |
| `VITE_WEBSOCKET_URL` | `ws://localhost:8000` | WebSocket base URL |

### WebSocket Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_WS_RECONNECT_ATTEMPTS` | `5` | Maximum reconnection attempts |
| `VITE_WS_RECONNECT_DELAY` | `1000` | Initial reconnection delay (ms) |
| `VITE_WS_CONNECTION_TIMEOUT` | `10000` | Connection timeout (ms) |

### Development Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_ENABLE_DEBUG_LOGS` | `true` (dev) | Enable debug logging |

## Environment-Specific Configuration

### Development
```env
VITE_BACKEND_URL=http://localhost:8000
VITE_WEBSOCKET_URL=ws://localhost:8000
VITE_ENABLE_DEBUG_LOGS=true
```

### Production
```env
VITE_BACKEND_URL=https://api.yourdomain.com
VITE_WEBSOCKET_URL=wss://api.yourdomain.com
VITE_ENABLE_DEBUG_LOGS=false
VITE_WS_RECONNECT_ATTEMPTS=10
VITE_WS_RECONNECT_DELAY=2000
```

### Staging
```env
VITE_BACKEND_URL=https://staging-api.yourdomain.com
VITE_WEBSOCKET_URL=wss://staging-api.yourdomain.com
VITE_ENABLE_DEBUG_LOGS=true
```

## Error Handling

The WebSocket system provides detailed error information:

```typescript
interface WebSocketError {
  code: string;           // Error code (e.g., 'CONNECTION_TIMEOUT')
  message: string;        // Human-readable error message
  timestamp: string;      // ISO timestamp when error occurred
}
```

### Common Error Codes

- `CONNECTION_TIMEOUT` - Connection attempt timed out
- `CONNECTION_FAILED` - Failed to establish connection
- `CONNECTION_CLOSED` - Connection was closed unexpectedly
- `INVALID_MESSAGE_FORMAT` - Received invalid message format
- `NOT_CONNECTED` - Attempted to send message while disconnected
- `SEND_FAILED` - Failed to send message
- `MAX_RECONNECT_ATTEMPTS` - Exceeded maximum reconnection attempts

## Connection States

The WebSocket hook provides three connection states:

1. **Disconnected** (`!isConnected && !isConnecting`)
   - Initial state or after disconnection
   - Can attempt to connect

2. **Connecting** (`isConnecting`)
   - Connection attempt in progress
   - Shows loading indicator

3. **Connected** (`isConnected`)
   - Successfully connected to WebSocket
   - Can send and receive messages

## Reconnection Logic

The system uses exponential backoff for reconnection:

1. **Initial delay**: `VITE_WS_RECONNECT_DELAY` ms
2. **Exponential backoff**: Delay doubles with each attempt
3. **Maximum attempts**: `VITE_WS_RECONNECT_ATTEMPTS`
4. **Manual reconnect**: Always available via `reconnect()` function

## Testing Configuration

To test your WebSocket configuration:

1. **Start the backend server**:
   ```bash
   cd backend
   ./start.sh dev
   ```

2. **Start the frontend server**:
   ```bash
   cd front-end
   npm run dev
   ```

3. **Open browser** to `http://localhost:8080/chat/test-room`

4. **Check browser console** for debug logs showing:
   - Configuration values
   - Connection attempts
   - Message sending/receiving

## Troubleshooting

### Connection Issues

1. **Check backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Verify CORS settings** in backend configuration

3. **Check browser console** for error messages

4. **Verify environment variables** are loaded correctly

### Configuration Issues

1. **Check `.env.local` file** exists and has correct values
2. **Restart development server** after changing environment variables
3. **Check browser network tab** for WebSocket connection attempts
4. **Enable debug logs** to see detailed connection information

### Common Solutions

- **CORS errors**: Update backend CORS settings to include frontend URL
- **Connection refused**: Ensure backend is running on correct port
- **Environment variables not loaded**: Restart Vite dev server
- **WebSocket upgrade failed**: Check if backend supports WebSocket upgrades