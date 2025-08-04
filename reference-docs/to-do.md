# To-Do List

This to-do list is organized by phases to guide the step-by-step development of the chat application.

---

## Phase 1: Core Chat with WebSocket & Room Links

- [ ]  Initialize monorepo with React frontend and FastAPI backend.
- [ ]  Set up CI/CD pipelines (GitHub Actions).
- [ ]  Implement backend unique room ID generation and URL routing.
- [ ]  Develop WebSocket endpoint `/ws/chat/{roomID}` for room-based message broadcasting.
- [ ]  Build React chat UI with:
    - Message list
    - Text input box
    - Voice recording via MediaRecorder API
- [ ]  Connect frontend to WebSocket using room ID from URL.
- [ ]  Implement sending and receiving of text messages over WebSocket.
- [ ]  Implement sending and receiving of voice message blobs over WebSocket.
- [ ]  Write unit tests for WebSocket connection and message handling.
- [ ]  Conduct manual end-to-end testing with multiple users.

---

## Phase 2: Text Translation with Groq LLM

- [ ]  Integrate Groq Llama-3.3-70B-Versatile API on backend for text translation.
- [ ]  Extend WebSocket protocol to support message objects containing original and translated text.
- [ ]  Implement asynchronous translation calls with retry and error handling.
- [ ]  Add language selector UI for user preferred language.
- [ ]  Enhance frontend to display dual-language messages side-by-side.
- [ ]  Mock Groq API for automated tests covering translation workflow.
- [ ]  Validate UI rendering and translation correctness manually.

---

## Phase 3: Voice Transcription, Translation & Synthesis

- [ ]  Integrate OpenAI Whisper or equivalent for ASR on backend.
- [ ]  Chain whisper transcription to Groq translation API call.
- [ ]  Integrate Coqui TTS for translated text synthesis to audio.
- [ ]  Optionally add Chatterbox TTS integration for voice cloning capabilities.
- [ ]  Expand WebSocket handling for binary audio frames and JSON messages.
- [ ]  Add UI indicators showing transcription, translation, and synthesis progress.
- [ ]  Implement playback controls for both original and synthesized voice messages.
- [ ]  Write end-to-end tests simulating voice message flows with mocked AI services.
- [ ]  Conduct latency and performance testing.

---

## Phase 4: Persistence, Scalability & History

- [ ]  Set up MongoDB database for storing messages, sessions, and metadata.
- [ ]  Configure AWS S3 bucket for audio file storage.
- [ ]  Implement backend logic to save chat messages and audio references.
- [ ]  Develop API endpoint to retrieve historical messages for room join or reload.
- [ ]  Integrate Redis or similar pub/sub for multi-instance WebSocket scaling.
- [ ]  Update frontend to load chat history on room entry with pagination or lazy loading support.
- [ ]  Perform load testing for concurrent user scenarios and data volume.
- [ ]  Verify data consistency and recovery on frontend.

---

## Phase 5: Observability, Admin & Advanced Features

- [ ]  Instrument backend with Prometheus for real-time metrics and error tracking.
- [ ]  Develop REST APIs for serving metrics and usage data.
- [ ]  Build React-based admin dashboard for monitoring message volume, languages, errors, etc.
- [ ]  Implement role-based access control middleware in backend for admin features.
- [ ]  Test RBAC and dashboard security.

### Future Enhancements:

- [ ]  Add multi-user group chat features.
- [ ]  Integrate Elasticsearch for full-text search in chat history.
- [ ]  Implement offline message queueing and synchronization on reconnect.

---

This structured to-do list will help ensure organized progress through the application development lifecycle.