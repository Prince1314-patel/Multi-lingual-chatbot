# Backend Structure Documentation

## Overview
The backend is built with FastAPI and provides real-time multilingual chat functionality with WebSocket support, AI-powered translation, and comprehensive error handling.

## Core Components

### 1. WebSocket Management (`app/websocket.py`)
- **Purpose**: Main WebSocket endpoint and service initialization
- **Key Features**:
  - WebSocket connection handling with CORS support
  - Service initialization (translation, rate limiting, connection management)
  - Graceful shutdown handling
- **Recent Updates**:
  - Made `init_websocket_services()` async to properly initialize translation service
  - Added rate limiter startup/shutdown handling

### 2. Message Handler (`app/services/message_handler.py`)
- **Purpose**: Central message processing and routing logic
- **Key Features**:
  - Text message handling with translation orchestration
  - Voice message processing
  - Typing indicator management
  - Personalized message delivery
- **Recent Updates**:
  - **Translation Orchestration**: Messages requiring translation are processed asynchronously for each user
  - **Personalized Delivery**: Each user receives messages in their preferred language
  - **Typing Indicator Fixes**: Enhanced typing timeout handling to prevent interference with translation
  - **Translation Progress Tracking**: Added `translation_in_progress` set to prevent typing messages during translation
  - **Extended Timeout**: Increased typing timeout from 5 to 30 seconds
  - **Status Management**: Explicitly set message status to "delivered" for translated messages

### 3. Translation Service (`app/ai_services/translation_service.py`)
- **Purpose**: AI-powered text translation using Groq API
- **Key Features**:
  - Language detection and translation
  - Caching for performance
  - Comprehensive error handling
  - Detailed logging for debugging
- **Recent Updates**:
  - Enhanced logging with detailed translation flow tracking
  - Improved error handling and retry logic
  - Better performance monitoring with processing time tracking

### 4. Connection Manager (`app/services/connection_manager.py`)
- **Purpose**: WebSocket connection lifecycle management
- **Key Features**:
  - Connection tracking and cleanup
  - Message broadcasting
  - Rate limiting integration
- **Recent Updates**:
  - Improved message delivery confirmation
  - Enhanced error handling for disconnected users

### 5. Room Manager (`app/services/room_manager.py`)
- **Purpose**: Chat room management and user organization
- **Key Features**:
  - Room creation and management
  - User assignment to rooms
  - Connection tracking within rooms
- **Recent Updates**:
  - Enhanced room validation and cleanup

## Message Flow Architecture

### Translation Flow (Updated)
1. **Message Reception**: User sends text message
2. **Translation Detection**: System checks if translation is needed based on user language preferences
3. **Personalized Processing**: If translation needed:
   - Mark room as having translation in progress
   - Process translation for each user individually
   - Send translated message to users with different language preferences
   - Send original message to users with same language preference
4. **Status Management**: All messages explicitly set to "delivered" status
5. **Cleanup**: Remove room from translation progress tracking

### Typing Indicator Flow (Updated)
1. **Typing Start**: User begins typing → Set typing timeout (30 seconds)
2. **Message Sent**: User sends message → Cancel typing timeout immediately
3. **Translation Protection**: If translation in progress → Skip typing timeout messages
4. **Normal Timeout**: If no translation → Send typing stopped after 30 seconds

## Data Models

### Message Models (`app/models/message.py`)
- **TextMessage**: Enhanced with translation fields and status tracking
- **VoiceMessage**: Voice message handling with transcription
- **TypingMessage**: Typing indicator management
- **Recent Updates**:
  - Added `status` field with delivery tracking
  - Enhanced translation status fields
  - Improved validation patterns

### Connection Models (`app/models/connection.py`)
- **Connection**: WebSocket connection with user preferences
- **Room**: Chat room with user management
- **Recent Updates**:
  - Enhanced room ID validation (allows underscores and hyphens)
  - Improved user preference handling

## Error Handling

### Comprehensive Error Management
- **Connection Errors**: Graceful handling of WebSocket disconnections
- **Translation Errors**: Fallback to original message on translation failure
- **Rate Limiting**: Token bucket algorithm for message and connection limits
- **Logging**: Structured logging throughout all components

## Performance Optimizations

### Translation Optimizations
- **Caching**: Translation results cached to reduce API calls
- **Async Processing**: Non-blocking translation processing
- **Progress Tracking**: Prevents duplicate work and typing interference

### Connection Optimizations
- **Connection Pooling**: Efficient WebSocket connection management
- **Memory Management**: Automatic cleanup of disconnected users
- **Rate Limiting**: Prevents abuse and ensures fair usage

## Configuration

### Environment Variables
- `GROQ_API_KEY`: Required for translation service
- `LOG_LEVEL`: Logging verbosity control
- `RATE_LIMIT_MESSAGES`: Message rate limiting configuration
- `RATE_LIMIT_CONNECTIONS`: Connection rate limiting configuration

### Service Dependencies
- **Translation Service**: Requires valid Groq API key
- **Rate Limiter**: Automatic startup/shutdown handling
- **Connection Manager**: Integrated with room management

## Recent Bug Fixes

### Translation Issues (Resolved)
- **Duplicate Messages**: Fixed by removing redundant broadcast of original messages
- **Status Indicators**: Removed "Translating..." and "Translation failed" UI elements
- **Language Detection**: Fixed logic to compare sender's preferred language with receiver's preferred language

### Typing Indicator Issues (Resolved)
- **Interference with Translation**: Added translation progress tracking to prevent typing messages during translation
- **Premature Timeouts**: Increased timeout from 5 to 30 seconds
- **Race Conditions**: Enhanced cancellation logic when messages are sent

### Status Display Issues (Resolved)
- **Message Status**: Explicitly set status to "delivered" for all translated messages
- **Frontend Integration**: Updated frontend to properly read status from backend messages
- **Icon Display**: Messages now show correct delivery status icons

## Testing

### Test Coverage
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end message flow testing
- **Translation Tests**: Multi-language communication verification
- **Error Handling Tests**: Failure scenario validation

### Test Files Location
All test files are located in `backend/tests/` directory as per project guidelines.

## Deployment

### Development Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=. python main.py
```

### Production Considerations
- **Environment Variables**: Ensure all required API keys are set
- **Rate Limiting**: Configure appropriate limits for production load
- **Logging**: Set appropriate log levels for production monitoring
- **Error Monitoring**: Implement proper error tracking and alerting
