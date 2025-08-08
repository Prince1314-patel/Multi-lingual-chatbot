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

### ✅ Backend Tasks - COMPLETED
- [x] Integrate Groq Llama-3.3-70B-Versatile API on backend for text translation.
- [x] Create AI services module (`backend/app/ai_services/`) for translation service.
- [x] Extend WebSocket protocol to support message objects containing original and translated text.
- [x] Implement asynchronous translation calls with retry and error handling.
- [x] Mock Groq API for automated tests covering translation workflow.
- [x] Add timezone utilities and migrate from deprecated `datetime.utcnow()` to IST timezone.

### 🔄 Frontend Tasks - IN PROGRESS
- [x] Add language selector UI for user preferred language.
- [x] Enhance frontend to display dual-language messages side-by-side.
- [x] Validate UI rendering and translation correctness manually.

**Current Status**: 🔄 **BACKEND COMPLETED, FRONTEND IN PROGRESS**
- Backend: ✅ Complete translation service with Groq API integration, 161 tests passing
- Frontend: ✅ Completed the frontend integration
- Timezone: ✅ Migrated to IST timezone throughout application

---

## 📅 Phase 3: Voice Transcription, Translation & Synthesis - PLANNED

- [ ] Integrate OpenAI Whisper or equivalent for ASR on backend.
- [ ] Chain whisper transcription to Groq translation API call.
- [ ] Integrate Chatterbox TTS for translated text synthesis to audio and voice cloning capabilities.
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

## 🚀 Immediate Next Steps (Phase 2.3 - Frontend Translation)

### Frontend Tasks
1. **Language Selection**
   - [ ] Add language selector component
   - [ ] Store user language preference
   - [ ] Update message display for dual-language support

2. **Translation UI**
   - [ ] Modify message bubbles to show original and translated text
   - [ ] Add translation status indicators
   - [ ] Handle translation errors gracefully

3. **WebSocket Integration**
   - [ ] Update frontend WebSocket handling for translation messages
   - [ ] Process translation status updates in real-time
   - [ ] Display translation progress indicators

### Testing Tasks
1. **Frontend Translation Testing**
   - [ ] Test language selector functionality
   - [ ] Validate dual-language message display
   - [ ] Test translation error handling in UI

---

## 🔧 Infrastructure Requirements

### Environment Variables Needed
```env
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# OpenAI Configuration (for Phase 3)
OPENAI_API_KEY=your_openai_api_key_here

# TTS Configuration (for Phase 3)
CHATTERBOX_TTS_URL=http://localhost:5003
```

### Dependencies Added
```bash
# Backend (Phase 2) - ✅ INSTALLED
pip install groq

# Backend (Phase 3)
pip install openai-whisper

# Backend (Phase 4)
pip install motor redis boto3
```

---

## 📊 Current Project Health

- **Backend**: ✅ Fully functional with comprehensive WebSocket implementation and translation service
- **Frontend**: ✅ Fully functional with complete chat UI and voice recording
- **Testing**: ✅ Extensive test coverage (161 tests passing) for both frontend and backend
- **Documentation**: ✅ Comprehensive documentation and implementation guides
- **Timezone**: ✅ Migrated to IST timezone throughout application
- **Translation Backend**: ✅ Complete Groq API integration with retry logic and error handling
- **Next Phase**: 🔄 Phase 2.3 - Frontend translation UI implementation

---

## 🎯 Recent Achievements

### ✅ Timezone Migration (Latest)
- Replaced deprecated `datetime.utcnow()` with IST timezone-aware datetime objects
- Created comprehensive timezone utilities for both backend and frontend
- Updated 15+ files across backend and frontend
- All 161 tests passing with new timezone implementation

### ✅ Phase 2 Backend Completion
- Complete AI services module with Groq API integration
- Translation service with retry logic and error handling
- Enhanced message models with translation fields
- Asynchronous translation processing
- Comprehensive test coverage for translation functionality

---

This structured to-do list reflects the current development status and provides clear next steps for continuing the project development.