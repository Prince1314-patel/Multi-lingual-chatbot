# To-Do List

This to-do list is organized by phases to guide the step-by-step development of the chat application.

---

## ✅ Phase 1: Core Chat with WebSocket & Room Links - COMPLETED

- [x] Initialize monorepo with React frontend and FastAPI backend.
- [x] Set up CI/CD pipelines (GitHub Actions).
- [x] Implement backend unique room ID generation and URL routing.
- [x] Develop WebSocket endpoint `/ws/chat/{roomID}` for room-based message broadcasting.
- [x] Build React chat UI with:
    - Message list
    - Text input box
    - Voice recording via MediaRecorder API
- [x] Connect frontend to WebSocket using room ID from URL.
- [x] Implement sending and receiving of text messages over WebSocket.
- [x] Implement sending and receiving of voice message blobs over WebSocket.
- [x] Write unit tests for WebSocket connection and message handling.
- [x] Conduct manual end-to-end testing with multiple users.

**Current Status**: ✅ **COMPLETED**
- Backend: FastAPI with comprehensive WebSocket implementation, connection management, rate limiting, and extensive test coverage
- Frontend: React application with full chat functionality, voice recording, message delivery confirmation, and comprehensive testing

---

## 🔄 Phase 2: Text Translation with Groq LLM - IN PROGRESS

- [ ] Integrate Groq Llama-3.3-70B-Versatile API on backend for text translation.
- [ ] Create AI services module (`backend/app/ai_services/`) for translation service.
- [ ] Extend WebSocket protocol to support message objects containing original and translated text.
- [ ] Implement asynchronous translation calls with retry and error handling.
- [ ] Add language selector UI for user preferred language.
- [ ] Enhance frontend to display dual-language messages side-by-side.
- [ ] Mock Groq API for automated tests covering translation workflow.
- [ ] Validate UI rendering and translation correctness manually.

**Current Status**: 🔄 **READY TO START**
- Backend infrastructure is ready for AI service integration
- Frontend is ready for dual-language message display
- Need to implement Groq API integration and translation pipeline

---

## 📅 Phase 3: Voice Transcription, Translation & Synthesis - PLANNED

- [ ] Integrate OpenAI Whisper or equivalent for ASR on backend.
- [ ] Chain whisper transcription to Groq translation API call.
- [ ] Integrate Coqui TTS for translated text synthesis to audio.
- [ ] Optionally add Chatterbox TTS integration for voice cloning capabilities.
- [ ] Expand WebSocket handling for binary audio frames and JSON messages.
- [ ] Add UI indicators showing transcription, translation, and synthesis progress.
- [ ] Implement playback controls for both original and synthesized voice messages.
- [ ] Write end-to-end tests simulating voice message flows with mocked AI services.
- [ ] Conduct latency and performance testing.

**Current Status**: 📅 **PLANNED**
- Voice message transmission is already implemented
- Need to add AI processing pipeline for transcription, translation, and synthesis

---

## 📅 Phase 4: Persistence, Scalability & History - PLANNED

- [ ] Set up MongoDB database for storing messages, sessions, and metadata.
- [ ] Configure AWS S3 bucket for audio file storage.
- [ ] Implement backend logic to save chat messages and audio references.
- [ ] Develop API endpoint to retrieve historical messages for room join or reload.
- [ ] Integrate Redis or similar pub/sub for multi-instance WebSocket scaling.
- [ ] Update frontend to load chat history on room entry with pagination or lazy loading support.
- [ ] Perform load testing for concurrent user scenarios and data volume.
- [ ] Verify data consistency and recovery on frontend.

**Current Status**: 📅 **PLANNED**
- Current implementation uses in-memory storage
- Need to add persistent storage and scaling capabilities

---

## 📅 Phase 5: Observability, Admin & Advanced Features - PLANNED

- [ ] Instrument backend with Prometheus for real-time metrics and error tracking.
- [ ] Develop REST APIs for serving metrics and usage data.
- [ ] Build React-based admin dashboard for monitoring message volume, languages, errors, etc.
- [ ] Implement role-based access control middleware in backend for admin features.
- [ ] Test RBAC and dashboard security.

**Current Status**: 📅 **PLANNED**
- Basic logging and error handling are implemented
- Need to add comprehensive monitoring and admin features

---

## 🚀 Immediate Next Steps (Phase 2 Priority)

### Backend Tasks
1. **Create AI Services Module**
   - [ ] Create `backend/app/ai_services/` directory
   - [ ] Implement `translation_service.py` with Groq API integration
   - [ ] Add configuration for Groq API key
   - [ ] Create translation message models

2. **Extend Message Handler**
   - [ ] Modify `message_handler.py` to process text messages through translation
   - [ ] Add translation status tracking
   - [ ] Implement retry logic for translation failures

3. **Update WebSocket Protocol**
   - [ ] Extend message models to include translated text
   - [ ] Update frontend message handling for dual-language display

### Frontend Tasks
1. **Language Selection**
   - [ ] Add language selector component
   - [ ] Store user language preference
   - [ ] Update message display for dual-language support

2. **Translation UI**
   - [ ] Modify message bubbles to show original and translated text
   - [ ] Add translation status indicators
   - [ ] Handle translation errors gracefully

### Testing Tasks
1. **AI Service Testing**
   - [ ] Create mocks for Groq API
   - [ ] Write integration tests for translation pipeline
   - [ ] Test error handling and retry logic

---

## 🔧 Infrastructure Requirements

### Environment Variables Needed
```env
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# OpenAI Configuration (for Phase 3)
OPENAI_API_KEY=your_openai_api_key_here

# TTS Configuration (for Phase 3)
COQUI_TTS_URL=http://localhost:5002
CHATTERBOX_TTS_URL=http://localhost:5003
```

### Dependencies to Add
```bash
# Backend (Phase 2)
pip install groq openai

# Backend (Phase 3)
pip install openai-whisper coqui-tts

# Backend (Phase 4)
pip install motor redis boto3
```

---

## 📊 Current Project Health

- **Backend**: ✅ Fully functional with comprehensive WebSocket implementation
- **Frontend**: ✅ Fully functional with complete chat UI and voice recording
- **Testing**: ✅ Extensive test coverage for both frontend and backend
- **Documentation**: ✅ Comprehensive documentation and implementation guides
- **Next Phase**: 🔄 Ready to begin Phase 2 (Text Translation with Groq LLM)

---

This structured to-do list reflects the current development status and provides clear next steps for continuing the project development.