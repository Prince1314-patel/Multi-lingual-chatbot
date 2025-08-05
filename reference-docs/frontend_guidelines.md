# Frontend Guidelines

This document outlines best practices, architectural decisions, and coding standards for developing the frontend of the AI-Powered Multilingual Voice & Text Communication Agent.

---

## Technology Stack

- **Framework:** React (with hooks and functional components)  
- **Styling:** CSS Modules or styled-components for scoped styling  
- **State Management:** React Context API or Redux Toolkit for global state  
- **Networking:** Native WebSocket API for real-time communication  
- **Build Tool:** Vite or Create React App (CRA) for fast builds and hot reload  
- **Testing:** Vitest with React Testing Library and jsdom  

---

## Architecture & Component Structure

- **Single-Page Application (SPA):**  
  Use React Router for route management, with a dynamic route for chat rooms (e.g., `/chat/:roomID`).

- **Component Breakdown:**  
  - **App:** Root component managing routing and context providers.  
  - **RoomJoin:** Component to enter or generate a chat room link.  
  - **ChatWindow:** Displays messages and controls message sending with voice message support.  
  - **MessageBubble:** Renders individual text and voice messages with integrated audio playback controls.  
  - **InputBar:** Text input box and voice recording with MediaRecorder API integration.  
  - **TypingIndicator:** Shows when other users are typing.  
  - **LanguageSelector:** Allows users to choose preferred language(s).  
  - **ProgressIndicator:** Shows transcription/translation/TTS progress.  
  - **ConfigTest:** Development component for testing and displaying configuration values.  

- **Hooks:**  
  - Custom hooks for WebSocket connection and message handling (e.g., `useWebSocket`) with binary message support.  
  - Built-in MediaRecorder API integration within InputBar component for voice recording.  

---

## Coding Standards & Best Practices

- **Functional Components:** Prefer React functional components with hooks.  
- **Reusable Components:** Build components to be reusable, composable, and unit testable.  
- **Type Safety:** Use TypeScript for typesafety wherever possible.  
- **Accessibility:**  
  - Use semantic HTML elements.  
  - Keyboard navigable UI controls.  
  - Proper ARIA attributes for dynamic content and audio controls.  
- **State Management:**  
  - Use Context or Redux to store global states such as user language preference and WebSocket connection status.  
  - Local component state only for transient UI state.  
- **Error Handling:** Gracefully handle network errors or API failures with user-friendly messages and retry options.  
- **Performance:**  
  - Virtualize long message lists with libraries like `react-window`.  
  - Debounce rapid input events if applicable.  
  - Lazy load translation or audio playback components.  

---

## User Experience (UX)

- **Onboarding:**  
  - Show language selection dropdown at first room join.  
  - Provide clear instructions for voice message recording and playback.

- **Messaging:**  
  - Show timestamps for messages.  
  - Distinguish between original and translated messages visually (different bubbles or colors).  
  - Support inline playback and pause of voice messages.  
  - Show live status ("Transcribing...", "Translating...", "Synthesizing...") in the UI.

- **Mobile Responsiveness:**  
  - Ensure chat UI is responsive and touch-friendly.  
  - Optimize for both portrait and landscape views.

---

## WebSocket Integration

- Maintain a single WebSocket connection per chat room session with binary message support.  
- Use JSON message format with clear types (e.g., text, voice, typing, user_join, user_leave, error).  
- Support binary WebSocket messages for efficient voice data transmission.  
- Manage reconnection logic and show connection status to users.  
- Handle both JSON-encoded audio data and binary audio data formats.  

---

## Audio Recording & Playback

- **MediaRecorder API**: Capture voice messages in WebM format with Opus codec for optimal compression and quality
- **Recording Feedback**: Visual indicators including recording status, animated recording indicator, and error messages
- **Audio Quality**: Configure MediaRecorder with echo cancellation, noise suppression, and 44.1kHz sample rate
- **Playback Controls**: Integrated audio player with play/pause, progress bar, and time display
- **Error Handling**: Comprehensive error handling for microphone permissions, browser support, and audio failures
- **Binary WebSocket Support**: Efficient transmission of audio data via WebSocket binary messages
- **Audio Management**: Proper cleanup of audio URLs and event listeners to prevent memory leaks  

---

## Internationalization (i18n)

- Use libraries like `react-i18next` or equivalent.  
- Dynamically update UI text based on user language selection.  
- Properly format timestamps and dates per locale.

---

## Configuration Management

- **Environment Variables:** Use Vite's `VITE_` prefixed environment variables for configuration.
- **Configuration Module:** Centralized configuration in `src/lib/config.ts` with validation and fallbacks.
- **Development Testing:** Use the `ConfigTest` component to verify configuration values during development.
- **WebSocket URLs:** Dynamic URL generation for room-specific WebSocket connections.
- **Debug Logging:** Configurable debug logging with automatic enablement in development mode.

### Configuration Testing

The `ConfigTest` component (`src/components/test/ConfigTest.tsx`) provides a visual interface for developers to:
- Verify environment variable loading
- Test WebSocket URL generation
- Check API endpoint construction
- Validate configuration values
- Debug connection settings

To use the ConfigTest component during development:
```tsx
import { ConfigTest } from '@/components/test/ConfigTest';

// Add to any development page or component
<ConfigTest />
```

## Testing Guidelines

### Test Framework Setup
- **Vitest:** Fast unit testing framework with native ES modules support
- **React Testing Library:** Component testing with user-centric approach
- **jsdom:** DOM simulation for browser environment testing
- **Jest DOM:** Additional matchers for DOM assertions

### Testing Structure
```
src/
├── components/
│   └── chat/
│       ├── __tests__/
│       │   └── ChatWindow.test.tsx    # Component tests
│       └── ChatWindow.tsx
└── test/
    └── setup.ts                       # Global test configuration
```

### Testing Best Practices
- **Component Testing:** Write unit tests for components and hooks using React Testing Library
- **Integration Testing:** Perform integration tests simulating full chat flows with WebSocket mocking
- **Mocking Strategy:** Use Vitest mocks for WebSocket connections, AI service calls, and child components
- **User-Centric Testing:** Test user interactions and behaviors rather than implementation details
- **Accessibility Testing:** Include accessibility checks in component tests
- **Configuration Testing:** Use the ConfigTest component to verify configuration during development

### Current Test Coverage
- **ChatWindow Component:** Comprehensive tests for user notifications, join/leave events, user count display
- **WebSocket Integration:** Mocked WebSocket behavior for testing message handling
- **Multi-user Scenarios:** Tests for multiple users joining and leaving chat rooms

### Running Tests
```bash
npm run test        # Watch mode for development
npm run test:run    # Single run for CI/production
```

---

## Code Review & Collaboration

- Write clear, descriptive commit messages.  
- Use Pull Requests for code review with checklist for standards compliance.  
- Document components and hooks with comments and usage instructions.  

---

Following these guidelines will help build a robust, maintainable, and user-friendly frontend for the multilingual voice and text chat application.

