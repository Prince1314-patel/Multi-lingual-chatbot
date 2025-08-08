# AI-Powered Multilingual Voice & Text Communication Agent

A Progressive Web Application (PWA) that enables real-time multilingual communication through shareable chat room links. Users can exchange text and voice messages with automatic transcription, translation, and speech synthesis - no authentication required.

## 🚀 Features

- **Room-based Chat**: Unique, shareable links for instant room access
- **Real-time Messaging**: WebSocket-powered text and voice communication with delivery confirmation
- **Message Status Tracking**: Visual indicators for message delivery states with retry functionality
- **AI-powered Translation**: ✅ Groq Llama-3.3-70B-Versatile for multilingual text translation
- **Personalized Translation**: Each user receives messages in their preferred language
- **Clean Translation Display**: Shows only translated content without UI clutter
- **Voice Processing**: OpenAI Whisper (ASR), Coqui TTS, and Chatterbox TTS for voice cloning
- **IST Timezone Support**: ✅ Complete timezone migration with IST timezone-aware datetime handling
- **Progressive Web App**: Mobile-responsive, installable, offline-capable

## 🏗️ Architecture

### Frontend
- **React 18** with TypeScript and functional components
- **Vite** for fast builds and hot reload
- **Tailwind CSS** with shadcn/ui component library
- **WebSocket** for real-time communication

### Backend
- **FastAPI** (Python) with async/await
- **WebSocket** rooms for real-time messaging
- **AI Services**: ✅ Groq API integration, OpenAI Whisper (planned), Coqui TTS (planned)
- **Database**: MongoDB (planned), AWS S3 (planned), Redis (planned)
- **Timezone**: ✅ IST timezone-aware datetime handling throughout

## 📁 Project Structure

```
├── front-end/                 # React frontend application
│   ├── src/
│   │   ├── components/chat/   # Chat UI components
│   │   ├── lib/              # Utilities including timezone.ts
│   │   └── hooks/            # WebSocket and other hooks
├── backend/                   # FastAPI backend
│   ├── app/
│   │   ├── ai_services/      # ✅ AI services module (translation)
│   │   ├── services/         # WebSocket and message handling
│   │   ├── models/           # Data models with translation support
│   │   └── utils/            # ✅ Timezone utilities
│   └── tests/                # Comprehensive test suite (161 tests)
├── reference-docs/            # Project documentation and specifications
└── .kiro/                     # Kiro AI assistant configuration
```

## 🛠️ Development Setup

### Prerequisites

- **Node.js** (v18 or higher)
- **Python** (v3.9 or higher)
- **npm** or **yarn**

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd front-end
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables (optional):
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your backend URLs
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

5. Open your browser to `http://localhost:8080`

6. Test configuration (development):
   - Import and use the `ConfigTest` component to verify your setup
   - Check WebSocket URLs and API endpoints are correctly configured

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   ```bash
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

6. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 🔧 Available Scripts

### Frontend Commands

```bash
npm run dev          # Start development server
npm run build        # Production build
npm run build:dev    # Development build
npm run lint         # Run ESLint
npm run preview      # Preview production build
npm run test         # Run tests in watch mode
npm run test:run     # Run tests once
```

### Backend Commands

```bash
python -m uvicorn main:app --reload    # Start development server
python -m pytest tests/ -v             # Run all tests (161 tests)
python -m pytest tests/unit/           # Run unit tests only
python -m pytest tests/integration/    # Run integration tests only
python -m pytest --cov                 # Run with coverage report
```

## 🌐 Environment Variables

### Backend Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# API Keys
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
MONGODB_URL=mongodb://localhost:27017/multilingual_chat
REDIS_URL=redis://localhost:6379

# AWS Configuration (for S3 audio storage)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_S3_BUCKET=your_s3_bucket_name
AWS_REGION=us-east-1

# TTS Configuration
COQUI_TTS_URL=http://localhost:5002
CHATTERBOX_TTS_URL=http://localhost:5003

# Application Settings
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:8080,http://localhost:3000
```

## 🧪 Testing

### Frontend Testing
```bash
cd front-end
npm run test        # Run Vitest tests in watch mode
npm run test:run    # Run tests once
```

**Test Framework**: Vitest + React Testing Library + jsdom
**Current Coverage**: ChatWindow component with user notifications, WebSocket integration, multi-user scenarios

### Configuration Testing
Use the built-in ConfigTest component during development:
```tsx
import { ConfigTest } from '@/components/test/ConfigTest';
// Displays all configuration values and WebSocket URLs
```

### Backend Testing
```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -v              # Run all tests (161 tests)
python -m pytest tests/unit/            # Run unit tests only
python -m pytest tests/integration/     # Run integration tests only
python -m pytest --cov                  # Run with coverage report
```

**Test Results**: ✅ 161/161 tests passing
**Coverage**: Comprehensive coverage including WebSocket, translation service, and error handling

## 📋 Development Phases

### ✅ Phase 1: Core Chat with WebSocket & Room Links
- [x] React frontend with chat UI
- [x] WebSocket connection management
- [x] FastAPI backend with room-based WebSocket routing
- [x] Text and voice message transmission
- [x] Message delivery confirmation and retry functionality

### ✅ Phase 2: Text Translation with Groq LLM
- [x] ✅ Groq API integration for text translation
- [x] ✅ AI services module with translation service
- [x] ✅ Asynchronous translation with retry logic
- [x] ✅ Enhanced message models with translation fields
- [x] ✅ Timezone migration to IST throughout application
- [x] ✅ Personalized translation delivery for each user
- [x] ✅ Clean translation display without UI clutter
- [x] ✅ Fixed typing indicator interference
- [x] ✅ Fixed message status icons and delivery confirmation

### 📅 Phase 3: Voice Transcription, Translation & Synthesis
- [ ] OpenAI Whisper integration (ASR)
- [ ] Coqui TTS integration
- [ ] Chatterbox TTS for voice cloning
- [ ] Voice message processing pipeline

### 📅 Phase 4: Persistence, Scalability & History
- [ ] MongoDB integration
- [ ] AWS S3 for audio storage
- [ ] Redis for scaling
- [ ] Chat history retrieval

### 📅 Phase 5: Observability & Admin Features
- [ ] Prometheus metrics
- [ ] Admin dashboard
- [ ] Role-based access control

## 🎯 Recent Achievements

### ✅ Translation System (August 7, 2025)
- **Fixed duplicate message display**: Users now see only translated content
- **Fixed language detection logic**: Correctly compares user language preferences
- **Fixed translation status display**: Removed UI clutter for cleaner experience
- **Fixed typing indicator interference**: Prevents typing messages during translation
- **Fixed message status icons**: Messages show correct delivery status
- **Enhanced translation orchestration**: Personalized delivery for each user
- **Improved error handling**: Better fallback mechanisms for translation failures

### ✅ Technical Improvements
- **Enhanced logging**: Detailed translation flow tracking with timing
- **Performance optimization**: Reduced API calls and improved caching
- **Better error recovery**: Graceful handling of connection and translation issues
- **Improved user experience**: Clean interface without redundant information

### ✅ Timezone Migration (Previous)
- Replaced deprecated `datetime.utcnow()` with IST timezone-aware datetime objects
- Created comprehensive timezone utilities for both backend and frontend
- Updated 15+ files across backend and frontend
- All 161 tests passing with new timezone implementation

## 🔧 Key Features

### Translation System
- **Personalized Delivery**: Each user receives messages in their preferred language
- **Clean Display**: Shows only translated content without original text clutter
- **Status Management**: Proper delivery status icons for all messages
- **Error Handling**: Graceful fallback to original content on translation failure

### Real-time Communication
- **WebSocket-based**: Instant message delivery with connection management
- **Typing Indicators**: Real-time typing status with interference prevention
- **Message Status**: Visual indicators for sending, delivered, and failed states
- **Connection Recovery**: Automatic reconnection with message queuing

### User Experience
- **Language Selection**: Easy language preference setup during onboarding
- **Mobile Responsive**: Works seamlessly on all device sizes
- **Progressive Web App**: Installable and offline-capable
- **No Authentication**: Instant room access via shareable links

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Documentation

- [Product Requirements Document](reference-docs/prd.md)
- [Implementation Plan](reference-docs/Implementation_plan.md)
- [Backend Structure Guidelines](reference-docs/backend_structure.md)
- [Frontend Guidelines](reference-docs/frontend_guidelines.md)
- [Changelog](reference-docs/CHANGELOG.md)
- [Current To-Do List](reference-docs/to-do.md)

## 🆘 Support

For questions and support, please refer to the documentation in the `reference-docs/` directory or open an issue in the repository.