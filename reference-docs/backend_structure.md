# Backend Structure Guidelines

This document specifies the architecture, core modules, and best practices for building the backend of the AI-Powered Multilingual Voice & Text Communication Agent, focusing on maintainability, scalability, and real-time performance.

---

## Technology Choices

- **Framework:** FastAPI (Python, async)
- **Real-time Communication:** WebSockets (FastAPI native support)
- **AI/ML Integration:** ✅ Groq API (translation), OpenAI Whisper (ASR - planned), Chatterbox TTS (speech synthesis - planned)
- **Persistence:** MongoDB (messages, metadata - planned), AWS S3 (audio blobs - planned), Redis (scaling pub/sub - planned)
- **Other:** Uvicorn (ASGI server), Pydantic (validation), pytest (testing), IST timezone handling

---

## Project Directory Structure

```
backend/
│
├── app/
│   ├── main.py                # FastAPI application entrypoint
│   ├── websocket.py           # WebSocket endpoints, room management
│   ├── api/                   # RESTful endpoints (history, admin, health)
│   ├── ai_services/           # ✅ Groq, Whisper, Coqui, Chatterbox integrations
│   │   ├── __init__.py        # AI services module initialization
│   │   ├── config.py          # AI service configuration
│   │   ├── base_service.py    # Base AI service class
│   │   └── translation_service.py # ✅ Groq translation service
│   ├── models/                # Pydantic and MongoDB schemas
│   ├── services/              # WebSocket and message handling services
│   │   ├── connection_manager.py # Connection management
│   │   ├── message_handler.py # Message processing with translation
│   │   ├── room_manager.py    # Room lifecycle management
│   │   ├── rate_limiter.py    # Rate limiting
│   │   └── memory_optimizer.py # Memory optimization
│   ├── utils/                 # ✅ Utility/helper functions including timezone
│   │   ├── __init__.py        # Utils module initialization
│   │   └── timezone.py        # ✅ IST timezone utilities
│   └── config.py              # Configuration variables and secrets loading
│
├── requirements.txt
├── Dockerfile
└── tests/                     # ✅ Comprehensive test suite (161 tests)
```

---

## Core Modules

### 1. **WebSocket Room Handling** ✅
- Endpoint: `/ws/chat/{room_id}`  
- Manages all incoming connections; maintains active connections per room in memory or via Redis for scalability.
- Handles JSON (text, control, status) and binary (audio) messages.
- Broadcasts messages only to clients in the same room.
- Each connection can store user context (language preference, display name).

### 2. **Message Processing** ✅
- Text messages:  
  - ✅ On receive: broadcast original, then trigger translation pipeline (Groq API), send translated result as a follow-up event.
- Audio messages:  
  - On receive: send to ASR (Whisper - planned), get transcript, pipeline to translation (Groq), TTS synthesis (Coqui or Chatterbox - planned), then send back TTS audio (binary frame).
- All steps are asynchronous with progress events for the client ("Transcribing", "Translating", etc).

### 3. **AI Service Integrations (`ai_services/`)** ✅
- ✅ **Translation:** Wrapper for Groq text generation API, expose `translate(text, src_lang, tgt_lang)`.
- **ASR:** Whisper integration for audio to text (planned).
- **TTS:** Wrappers for Coqui and Chatterbox APIs/servers, selective use based on context (planned).
- ✅ Caching/failover logic for service downtime.

### 4. **Persistence Layer (`storage/`)** 📅
- **MongoDB**: Store chat messages, room metadata (room_id, participants, timestamps) (planned).
- **AWS S3**: Save audio blobs, reference URLs in message records (planned).
- **Redis (optional)**: Manage distributed WebSocket room state for high availability (planned).

### 5. **RESTful APIs (`api/`)** ✅
- `/history/{room_id}`: Fetch chat history for a given room (with pagination).
- `/health`: Liveness/readiness probes.
- `/admin/*`: Metrics and statistics endpoints (secured if enabled).

### 6. **Configuration and Utilities** ✅
- `config.py`: Centralized config (env vars, keys, service URLs).
- ✅ Logging and error-handling utilities for observability.
- ✅ IST timezone utilities for consistent datetime handling.

---

## Coding Best Practices

- ✅ All core logic is `async` for high concurrency.
- ✅ Use Pydantic for all request/response and internal message models.
- ✅ Graceful error handling and user-friendly error events down the WebSocket.
- ✅ Modular, testable functions with unit/integration test coverage (161 tests passing).
- ✅ Sensitive secrets loaded from environment variables; never hard-code tokens.
- ✅ Timezone-aware datetime handling throughout the application.

---

## Scalability and Extensibility

- ✅ In-memory structures support small scale; plug Redis for distributed systems.
- ✅ Each component (message processor, AI integrations, storage) is pluggable/replaceable.
- ✅ WebSocket broadcast logic allows group chat via room_id (with minimal changes).

---

## Security & Compliance

- ✅ Generate unguessable UUIDs for room_id.
- ✅ Sanitize and validate all incoming WebSocket and REST requests.
- ✅ Secure all admin and sensitive endpoints.

---

## ✅ Recent Implementations

### AI Services Module
- Complete translation service with Groq API integration
- Retry logic and error handling for API failures
- Comprehensive test coverage for translation functionality
- Base service class for extensible AI service architecture

### Timezone Migration
- Replaced deprecated `datetime.utcnow()` with IST timezone-aware datetime objects
- Created comprehensive timezone utilities for both backend and frontend
- Updated 15+ files across backend and frontend
- All 161 tests passing with new timezone implementation

### Message Processing Enhancement
- Enhanced message models with translation fields
- Asynchronous translation processing
- Translation status tracking and error handling
- Real-time translation progress updates

---

## 🚀 Next Steps

### Phase 2.3: Frontend Translation UI
- Language selector component
- Dual-language message display
- Translation status indicators
- Translation error handling in UI

### Phase 3: Voice Processing Pipeline
- OpenAI Whisper integration for ASR
- Coqui TTS integration for speech synthesis
- Voice message processing pipeline
- Real-time transcription and translation indicators
