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
- **ChatWindow**: User join/leave notifications, user count display, WebSocket message handling
- **Component Mocking**: WebSocket hooks, child components for isolated testing
- **Integration Tests**: Multi-user scenarios, message flow testing

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

### Chat Components
- **ChatWindow**: Main container managing WebSocket connection and message state
- **MessageBubble**: Displays individual messages with translation support
- **InputBar**: Handles text input and voice recording with typing indicators
- **TypingIndicator**: Shows when other users are typing

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