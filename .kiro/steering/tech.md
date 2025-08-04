# Technology Stack & Build System

## Frontend Stack

- **Framework**: React 18 with TypeScript and functional components + hooks
- **Build Tool**: Vite with SWC for fast builds and hot reload
- **Styling**: Tailwind CSS with shadcn/ui component library
- **State Management**: React Context API, React Query for server state
- **Routing**: React Router DOM with dynamic room routes (`/chat/:roomId`)
- **UI Components**: Radix UI primitives with custom styling
- **Audio**: MediaRecorder API for voice recording, native audio playback

## Backend Stack (Planned)

- **Framework**: FastAPI (Python) with async/await
- **WebSockets**: Native FastAPI WebSocket support
- **AI Services**: 
  - Groq Llama-3.3-70B-Versatile (translation)
  - OpenAI Whisper (speech-to-text)
  - Coqui TTS + Chatterbox TTS (text-to-speech)
- **Database**: MongoDB (messages), AWS S3 (audio files), Redis (scaling)
- **Server**: Uvicorn ASGI server

## Development Commands

```bash
# Frontend development
cd front-end
npm run dev          # Start dev server on port 8080
npm run build        # Production build
npm run build:dev    # Development build
npm run lint         # ESLint check
npm run preview      # Preview production build

# Package management
npm install          # Install dependencies
```

## Code Quality Tools

- **Linting**: ESLint with React hooks and TypeScript rules
- **Formatting**: Built-in Vite formatting
- **Type Checking**: TypeScript strict mode
- **Testing**: Jest + React Testing Library (planned)

## Key Dependencies

- **UI**: @radix-ui components, lucide-react icons, tailwindcss
- **Forms**: react-hook-form with zod validation
- **Data Fetching**: @tanstack/react-query
- **Utilities**: clsx, tailwind-merge, date-fns

## Build Configuration

- **Vite Config**: Path aliases (`@/` → `./src/`), development component tagging
- **Tailwind**: Custom color scheme with chat-specific variables, shadcn/ui integration
- **TypeScript**: Strict configuration with path mapping