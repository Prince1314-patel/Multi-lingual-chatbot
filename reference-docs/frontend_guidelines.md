# Frontend Guidelines

This document outlines best practices, architectural decisions, and coding standards for developing the frontend of the AI-Powered Multilingual Voice & Text Communication Agent.

---

## Technology Stack

- **Framework:** React (with hooks and functional components)  
- **Styling:** CSS Modules or styled-components for scoped styling  
- **State Management:** React Context API or Redux Toolkit for global state  
- **Networking:** Native WebSocket API for real-time communication  
- **Build Tool:** Vite or Create React App (CRA) for fast builds and hot reload  
- **Testing:** Jest with React Testing Library  

---

## Architecture & Component Structure

- **Single-Page Application (SPA):**  
  Use React Router for route management, with a dynamic route for chat rooms (e.g., `/chat/:roomID`).

- **Component Breakdown:**  
  - **App:** Root component managing routing and context providers.  
  - **RoomJoin:** Component to enter or generate a chat room link.  
  - **ChatWindow:** Displays messages and controls message sending.  
  - **MessageList:** Renders a scrollable list of messages (text + audio).  
  - **MessageInput:** Text input box and voice record button.  
  - **AudioPlayer:** For playing back received and synthesized voice messages.  
  - **LanguageSelector:** Allows users to choose preferred language(s).  
  - **ProgressIndicator:** Shows transcription/translation/TTS progress.  
  - **ConfigTest:** Development component for testing and displaying configuration values.  

- **Hooks:**  
  - Custom hooks for WebSocket connection and message handling (e.g., `useWebSocket`).  
  - Hooks for media recording (`useMediaRecorder`).  

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

- Maintain a single WebSocket connection per chat room session.  
- Use JSON message format with clear types (e.g., text, audio, progress, error).  
- Manage reconnection logic and show connection status to users.  

---

## Audio Recording & Playback

- Use MediaRecorder API to capture voice messages in WAV or OGG format.  
- Provide visual feedback when recording (e.g., timer or waveform).  
- Support playback of received audio seamlessly within the chat window.  

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

- Write unit tests for components and hooks.  
- Perform integration tests simulating full chat flows.  
- Use mocks for WebSocket and AI service calls during tests.  
- Test accessibility and mobile responsiveness manually or with automated tools.
- Use the ConfigTest component to verify configuration during development and debugging.

---

## Code Review & Collaboration

- Write clear, descriptive commit messages.  
- Use Pull Requests for code review with checklist for standards compliance.  
- Document components and hooks with comments and usage instructions.  

---

Following these guidelines will help build a robust, maintainable, and user-friendly frontend for the multilingual voice and text chat application.

