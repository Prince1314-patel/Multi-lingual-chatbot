# Frontend Guidelines

## Overview
The frontend is built with React, TypeScript, and Tailwind CSS, providing a modern, responsive chat interface with real-time multilingual communication capabilities.

## Core Components

### 1. Chat Window (`src/components/chat/ChatWindow.tsx`)
- **Purpose**: Main chat interface and WebSocket message handling
- **Key Features**:
  - Real-time message reception and display
  - WebSocket connection management
  - Message status tracking
  - Typing indicator handling
- **Recent Updates**:
  - **Status Parsing**: Updated to read `status` field from backend messages instead of hardcoding
  - **Message Echo**: Enhanced to use backend-provided status for own messages
  - **Translation Integration**: Proper handling of translated content from backend

### 2. Message Bubble (`src/components/chat/MessageBubble.tsx`)
- **Purpose**: Individual message rendering with translation support
- **Key Features**:
  - Conditional content display (original vs translated)
  - Status icon display
  - User-specific message styling
- **Recent Updates**:
  - **Translation Display**: Shows only translated content for other users when available
  - **Status Indicators**: Removed "Translating..." and "Translation failed" UI elements
  - **Clean Interface**: Simplified message display without redundant information

### 3. Input Bar (`src/components/chat/InputBar.tsx`)
- **Purpose**: Message input and sending functionality
- **Key Features**:
  - Text input with send button
  - Voice message support
  - Typing indicator management
- **Recent Updates**:
  - Enhanced typing indicator coordination with backend
  - Improved message sending flow

### 4. User Onboarding (`src/components/onboarding/UserOnboarding.tsx`)
- **Purpose**: User setup and language preference selection
- **Key Features**:
  - Language preference selection
  - Display name configuration
  - Room joining functionality
- **Recent Updates**:
  - Improved language preference handling
  - Enhanced user experience flow

## Message Flow Architecture

### Translation Display Flow (Updated)
1. **Message Reception**: WebSocket receives message from backend
2. **Content Analysis**: Check if `translated_content` is available and `translation_status` is 'completed'
3. **Display Logic**:
   - **Current User**: Always show original text
   - **Other Users**: Show translated content if available, otherwise show original
4. **Status Display**: Show appropriate delivery status icon based on backend status

### Status Management Flow (Updated)
1. **Backend Status**: Receive `status` field from backend messages
2. **Status Parsing**: Parse status as "sending" | "sent" | "delivered" | "failed" | "read"
3. **Icon Display**: Show appropriate icon based on status
4. **Own Messages**: Update echoed messages with backend-provided status

## Data Models

### Message Interface
```typescript
interface Message {
  id: string;
  from: string;
  text: string;
  timestamp: string;
  status: "sending" | "sent" | "delivered" | "failed" | "read";
  translated_content?: string;
  translation_status?: "pending" | "processing" | "completed" | "failed";
  translation_error?: string;
  target_language?: string;
}
```

### WebSocket Message Types
- **Text Messages**: Regular chat messages with translation support
- **Voice Messages**: Audio messages with transcription
- **Typing Messages**: Real-time typing indicators
- **Status Messages**: Connection and delivery status updates

## Translation Integration

### Translation Display Logic
```typescript
// For other users' messages
{isCurrentUser ? (
  <p className="text-sm">{regularMessage.text}</p>
) : (
  <p className="text-sm">
    {regularMessage.translated_content && regularMessage.translation_status === 'completed'
      ? regularMessage.translated_content
      : regularMessage.text}
  </p>
)}
```

### Translation Status Handling
- **Completed**: Display translated content
- **Failed/Pending**: Display original content
- **No Translation**: Display original content

## Status Icon System

### Status Icons
- **Sending**: Clock icon (⏰)
- **Sent**: Single checkmark (✓)
- **Delivered**: Double checkmark (✓✓)
- **Failed**: Error icon (❌)
- **Read**: Blue double checkmark (✓✓)

### Status Flow
1. **Message Sent**: Initially "sending"
2. **Backend Confirmation**: Updated to "delivered" by backend
3. **Frontend Display**: Shows appropriate icon based on status

## WebSocket Integration

### Connection Management
- **Automatic Reconnection**: Handles connection drops gracefully
- **Error Handling**: Displays connection status to users
- **Message Queuing**: Handles message sending during reconnection

### Message Handling
```typescript
const handleWebSocketMessage = (data: any) => {
  const message: Message = {
    // ... other fields
    status: (typeof data.status === 'string' ? data.status as "sending" | "sent" | "delivered" | "failed" | "read" : 'sent'),
    // ... translation fields
  };
};
```

## UI/UX Enhancements

### Translation Experience
- **Seamless Display**: Users see only translated content without UI clutter
- **No Status Indicators**: Removed "Translating..." messages for cleaner experience
- **Immediate Display**: Translated messages appear directly without intermediate states

### Message Status Experience
- **Accurate Icons**: Status icons reflect actual message delivery state
- **Consistent Display**: All messages show appropriate delivery status
- **Real-time Updates**: Status updates happen immediately upon backend confirmation

## Error Handling

### Connection Errors
- **Reconnection Logic**: Automatic retry with exponential backoff
- **User Feedback**: Clear status messages for connection issues
- **Graceful Degradation**: Continue functioning with limited features

### Translation Errors
- **Fallback Display**: Show original message if translation fails
- **No Error UI**: Don't display translation errors to users
- **Silent Recovery**: Continue normal chat flow

## Performance Optimizations

### Message Rendering
- **Virtual Scrolling**: Efficient rendering of large message lists
- **Memoization**: Prevent unnecessary re-renders
- **Lazy Loading**: Load older messages on demand

### WebSocket Optimization
- **Message Batching**: Group multiple messages when possible
- **Connection Pooling**: Efficient WebSocket connection management
- **Memory Management**: Clean up disconnected users and old messages

## Recent Bug Fixes

### Translation Display Issues (Resolved)
- **Duplicate Messages**: Fixed by showing only translated content for other users
- **Status Indicators**: Removed "Translating..." and "Translation failed" UI elements
- **Clean Interface**: Users now see only the translated message without original text

### Status Icon Issues (Resolved)
- **Incorrect Icons**: Fixed by reading status from backend instead of hardcoding
- **Own Messages**: Updated to use backend-provided status for echoed messages
- **Delivery Confirmation**: Messages now show correct delivery status icons

### Typing Indicator Issues (Resolved)
- **Interference**: Backend now prevents typing messages during translation
- **Clean Display**: No more typing indicators interfering with translated messages
- **Proper Timing**: Typing indicators work correctly with translation flow

## Testing

### Component Testing
- **Unit Tests**: Individual component testing with React Testing Library
- **Integration Tests**: End-to-end message flow testing
- **Translation Tests**: Multi-language display verification

### Test Files Location
All test files are located in `src/components/chat/__tests__/` directory.

## Development Setup

### Prerequisites
- Node.js 18+ and npm/yarn
- Backend server running on configured port

### Installation
```bash
cd front-end
npm install
npm run dev
```

### Environment Configuration
- **WebSocket URL**: Configure backend WebSocket endpoint
- **Translation Support**: Ensure backend translation service is running
- **CORS**: Backend must allow frontend origin

## Build and Deployment

### Development Build
```bash
npm run build
npm run preview
```

### Production Considerations
- **Environment Variables**: Configure production WebSocket endpoints
- **Error Monitoring**: Implement proper error tracking
- **Performance Monitoring**: Track message delivery and translation success rates

