# Frontend - AI-Powered Multilingual Chat

React TypeScript frontend for the multilingual voice and text communication application.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Open browser to http://localhost:8080
```

## 🏗️ Architecture

### Tech Stack
- **React 18** with TypeScript and functional components
- **Vite** for fast builds and hot reload  
- **Tailwind CSS** with shadcn/ui component library
- **WebSocket** for real-time communication
- **React Router** for dynamic room routing

### Project Structure
```
src/
├── components/
│   ├── chat/              # Chat-specific components
│   │   ├── ChatWindow.tsx     # Main chat interface
│   │   ├── MessageBubble.tsx  # Individual message display
│   │   ├── InputBar.tsx       # Message input with voice recording
│   │   └── TypingIndicator.tsx # Typing status indicator
│   ├── test/              # Development testing components
│   │   └── ConfigTest.tsx     # Configuration testing utility
│   └── ui/                # shadcn/ui component library
├── pages/                 # Route-level page components
├── hooks/                 # Custom React hooks
├── lib/                   # Utility functions and configurations
└── main.tsx               # Application entry point
```

## ⚙️ Configuration

### Environment Variables

Create a `.env.local` file in the `front-end/` directory:

```env
# Backend API Configuration
VITE_BACKEND_URL=http://localhost:8000
VITE_WEBSOCKET_URL=ws://localhost:8000

# WebSocket Settings
VITE_WS_RECONNECT_ATTEMPTS=5
VITE_WS_RECONNECT_DELAY=1000
VITE_WS_CONNECTION_TIMEOUT=10000

# Development Settings
VITE_ENABLE_DEBUG_LOGS=true
```

### Configuration Testing

Use the `ConfigTest` component to verify your configuration during development:

```tsx
import { ConfigTest } from '@/components/test/ConfigTest';

// Add to any development page
<ConfigTest />
```

The ConfigTest component displays:
- Backend and WebSocket URLs
- Sample room WebSocket URL generation
- API endpoint construction
- Environment detection (dev/prod)
- Debug logging status
- Connection timeout settings

## 🛠️ Available Scripts

```bash
npm run dev          # Start development server on port 8080
npm run build        # Production build
npm run build:dev    # Development build with source maps
npm run lint         # Run ESLint
npm run preview      # Preview production build
npm run test         # Run tests in watch mode
npm run test:run     # Run tests once
```

## 🔌 WebSocket Integration

The frontend uses a centralized configuration system for WebSocket connections:

```typescript
import { getWebSocketUrl, config } from '@/lib/config';

// Get WebSocket URL for a specific room
const wsUrl = getWebSocketUrl('room-123');
// Result: ws://localhost:8000/ws/chat/room-123

// Access configuration values
console.log(config.reconnectAttempts); // 5
console.log(config.connectionTimeout); // 10000
```

### WebSocket Features
- Automatic reconnection with configurable attempts and delays
- Room-based URL generation
- Connection timeout handling
- Binary message support for voice data transmission
- Debug logging for development

## 🧪 Testing

### Test Framework
- **Vitest** for fast unit and integration testing
- **React Testing Library** for component testing
- **jsdom** for DOM simulation
- **Jest DOM** for additional matchers

### Running Tests
```bash
# Run tests in watch mode (development)
npm run test

# Run tests once (CI/production)
npm run test:run
```

### Test Structure
```
src/
├── components/
│   └── chat/
│       ├── __tests__/
│       │   └── ChatWindow.test.tsx    # Component tests
│       ├── ChatWindow.tsx
│       └── ...
└── test/
    └── setup.ts                       # Test configuration
```

### Writing Tests
Tests use Vitest with React Testing Library:

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import { ChatWindow } from '../ChatWindow';

describe('ChatWindow', () => {
  it('should display user notifications', async () => {
    render(<ChatWindow roomId="test-room" />);
    
    expect(screen.getByText(/1 user online/)).toBeInTheDocument();
  });
});
```

### Test Coverage
Current test coverage includes:
- **ChatWindow**: User join/leave notifications, user count display, WebSocket message handling, voice message transmission
- **Component Mocking**: WebSocket hooks, child components for isolated testing
- **Integration Tests**: Multi-user scenarios, message flow testing, voice message end-to-end flow
- **Voice Message Testing**: MediaRecorder API mocking, audio playback testing, binary WebSocket message handling

## 🧪 Development Tools

### Configuration Testing
The `ConfigTest` component helps verify:
- Environment variable loading
- URL generation for WebSocket connections
- API endpoint construction
- Development vs production settings

### Debug Logging
Enable debug logs in development:
```typescript
import { debugLog } from '@/lib/config';

debugLog('WebSocket connected to room:', roomId);
// Only logs in development or when VITE_ENABLE_DEBUG_LOGS=true
```

## 🎨 UI Components

Built with shadcn/ui and Tailwind CSS:
- Responsive design for mobile and desktop
- Accessible components with proper ARIA attributes
- Consistent styling with CSS custom properties
- Dark/light theme support (planned)

## 🎤 Voice Message Features

The application includes comprehensive voice message functionality:

### Voice Recording (InputBar)
- **MediaRecorder API Integration**: Records audio using WebM format with Opus codec
- **Real-time Recording Feedback**: Visual indicators and recording status display
- **Error Handling**: Comprehensive error messages for microphone access, browser support, and recording failures
- **Audio Quality Settings**: Optimized settings with echo cancellation and noise suppression
- **Recording Controls**: Start/stop recording with intuitive button states

### Voice Playback (MessageBubble)
- **Audio Player Controls**: Play/pause functionality with visual feedback
- **Progress Visualization**: Audio progress bar with current time and duration display
- **Automatic Audio Management**: Proper cleanup of audio URLs and event listeners
- **Error Handling**: Graceful handling of audio loading and playback errors
- **Message Status Display**: Visual status indicators with retry functionality for failed messages
- **Responsive Design**: Voice message bubbles adapt to current user vs. other user styling

### WebSocket Voice Transmission
- **Binary Data Support**: Efficient transmission of audio data via WebSocket binary messages
- **Dual Format Support**: Handles both binary WebSocket messages and JSON-encoded audio data
- **Message Status Tracking**: Visual indicators for sending, sent, delivered, failed, and read message states with retry functionality
- **Connection State Awareness**: Prevents voice message sending when disconnected

### Technical Implementation Details

#### Voice Recording Flow
1. **Permission Request**: Requests microphone access with error handling for denied/unavailable scenarios
2. **MediaRecorder Setup**: Configures WebM format with Opus codec, echo cancellation, and noise suppression
3. **Recording Management**: Handles start/stop recording with visual feedback and error states
4. **Audio Processing**: Converts recorded Blob to ArrayBuffer for WebSocket transmission

#### Voice Message Types
```typescript
interface VoiceMessage {
  id?: string;
  from: string;
  to: string;
  type: 'voice';
  audioData: ArrayBuffer;
  duration?: number;
  timestamp: string;
  status: "sending" | "sent" | "delivered" | "failed" | "read";
}

interface Message {
  id?: string;
  from: string;
  to: string;
  text?: string;
  lang: string;
  timestamp: string;
  status: "sending" | "sent" | "delivered" | "failed" | "read";
}
```

#### WebSocket Message Formats
- **Binary Messages**: Raw audio data transmitted as ArrayBuffer via WebSocket binary frames
- **JSON Voice Messages**: Voice metadata with hex-encoded audio data for backend compatibility
- **Message Types**: Supports 'voice', 'text', 'typing', 'user_join', 'user_leave', 'error' message types

### Chat Components
- **ChatWindow**: Main container managing WebSocket connection and message state with voice message support
- **MessageBubble**: Displays individual text and voice messages with playback controls, message status indicators, and retry functionality for failed messages
- **InputBar**: Handles text input and voice recording with MediaRecorder API integration
- **TypingIndicator**: Shows when other users are typing

### Message Delivery & Status Tracking

The application provides comprehensive message delivery tracking with visual feedback:

#### Message Status States
- **Sending**: Message is being transmitted to the server
- **Sent**: Message successfully received by server
- **Delivered**: Message delivered to recipient(s)
- **Failed**: Message transmission failed
- **Read**: Message has been read by recipient (future feature)

#### Retry Functionality
- Failed messages display a retry button alongside the error indicator
- Users can manually retry failed message transmission
- Retry functionality is available for both text and voice messages
- Visual feedback distinguishes between different failure states

#### Implementation Details
- Messages include optional `id` field for tracking and deduplication
- Status updates are handled through WebSocket message confirmations
- Optimistic UI updates provide immediate feedback while awaiting server confirmation
- Error states include user-friendly messaging and actionable retry options

## 🔗 Routing

Dynamic routing with React Router:
- `/` - Landing page for room creation/joining
- `/chat/:roomId` - Chat room interface
- `*` - 404 fallback for invalid routes

## 🚀 Deployment

### Development Build
```bash
npm run build:dev
```

### Production Build
```bash
npm run build
```

### Preview Production Build
```bash
npm run preview
```

## 🤝 Contributing

1. Follow the component architecture patterns in `reference-docs/frontend_guidelines.md`
2. Use TypeScript for all new components
3. Test configuration changes with the ConfigTest component
4. Ensure responsive design for mobile devices
5. Add proper accessibility attributes

## 📚 Documentation

- [Frontend Guidelines](../reference-docs/frontend_guidelines.md)
- [Product Requirements](../reference-docs/prd.md)
- [Implementation Plan](../reference-docs/Implementation_plan.md)