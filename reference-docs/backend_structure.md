# Backend Structure Guidelines

This document specifies the architecture, core modules, and best practices for building the backend of the AI-Powered Multilingual Voice & Text Communication Agent, focusing on maintainability, scalability, and real-time performance.

---

## Technology Choices

- **Framework:** FastAPI (Python, async)
- **Real-time Communication:** WebSockets (FastAPI native support)
- **AI/ML Integration:** Groq API (translation), OpenAI Whisper (ASR),Chatterbox TTS (speech synthesis)
- **Persistence:** MongoDB (messages, metadata), AWS S3 (audio blobs), Redis (scaling pub/sub, optional)
- **Other:** Uvicorn (ASGI server), Pydantic (validation), pytest (testing)

---

## Project Directory Structure

```
backend/
│
├── app/
│   ├── main.py                # FastAPI application entrypoint
│   ├── websocket.py           # WebSocket endpoints, room management
│   ├── api/                   # RESTful endpoints (history, admin, health)
│   ├── ai_services/           # Groq, Whisper, Coqui, Chatterbox integrations
│   ├── models/                # Pydantic and MongoDB schemas
│   ├── storage/               # MongoDB, S3, Redis interfaces/utilities
│   ├── utils/                 # Utility/helper functions
│   └── config.py              # Configuration variables and secrets loading
│
├── requirements.txt
├── Dockerfile
└── tests/
```

---

## Core Modules

### 1. **WebSocket Room Handling**
- Endpoint: `/ws/chat/{room_id}`  
- Manages all incoming connections; maintains active connections per room in memory or via Redis for scalability.
- Handles JSON (text, control, status) and binary (audio) messages.
- Broadcasts messages only to clients in the same room.
- Each connection can store user context (language preference, display name).

### 2. **Message Processing**
- Text messages:  
  - On receive: broadcast original, then trigger translation pipeline (Groq API), send translated result as a follow-up event.
- Audio messages:  
  - On receive: send to ASR (Whisper), get transcript, pipeline to translation (Groq), TTS synthesis (Coqui or Chatterbox), then send back TTS audio (binary frame).
- All steps are asynchronous with progress events for the client ("Transcribing", "Translating", etc).

### 3. **AI Service Integrations (`ai_services/`)**
- **Translation:** Wrapper for Groq text generation API, expose `translate(text, src_lang, tgt_lang)`.
- **ASR:** Whisper integration for audio to text.
- **TTS:** Wrappers for Coqui and Chatterbox APIs/servers, selective use based on context.
- Caching/failover logic for service downtime.

### 4. **Persistence Layer (`storage/`)**
- **MongoDB**: Store chat messages, room metadata (room_id, participants, timestamps).
- **AWS S3**: Save audio blobs, reference URLs in message records.
- **Redis (optional)**: Manage distributed WebSocket room state for high availability.

### 5. **RESTful APIs (`api/`)**
- `/history/{room_id}`: Fetch chat history for a given room (with pagination).
- `/health`: Liveness/readiness probes.
- `/admin/*`: Metrics and statistics endpoints (secured if enabled).

### 6. **Configuration and Utilities**
- `config.py`: Centralized config (env vars, keys, service URLs).
- Logging and error-handling utilities for observability.

---

## Coding Best Practices

- All core logic is `async` for high concurrency.
- Use Pydantic for all request/response and internal message models.
- Graceful error handling and user-friendly error events down the WebSocket.
- Modular, testable functions with unit/integration test coverage.
- Sensitive secrets loaded from environment variables; never hard-code tokens.

---

## Scalability and Extensibility

- In-memory structures support small scale; plug Redis for distributed systems.
- Each component (message processor, AI integrations, storage) is pluggable/replaceable.
- WebSocket broadcast logic allows group chat via room_id (with minimal changes).

---

## Security & Compliance

- Generate unguessable UUIDs for room_id.
- Sanitize and validate all incoming WebSocket and REST requests.
- Secure all admin and sensitive endpoints.

---

## Deployment

- Use Uvicorn ASGI server for production.
- Dockerize the backend for consistency and scalability.
- Recommend horizontal scaling with load balancer (sticky sessions or Redis pub/sub).

---

## Observability

- Integrate logging for message/process flows.
- Use Prometheus metrics for key events (message counts, errors, AI API latency).
- Provide `/health` endpoint for liveness checks.

---
