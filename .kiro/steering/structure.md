# Project Structure & Organization

## Repository Layout

```
├── front-end/                 # React frontend application
├── reference-docs/            # Project documentation and specifications
└── .kiro/                     # Kiro AI assistant configuration
```

## Frontend Structure (`front-end/`)

```
front-end/
├── src/
│   ├── components/
│   │   ├── chat/              # Chat-specific components
│   │   │   ├── ChatWindow.tsx     # Main chat interface
│   │   │   ├── MessageBubble.tsx  # Individual message display
│   │   │   ├── InputBar.tsx       # Message input with voice recording
│   │   │   └── TypingIndicator.tsx # Typing status indicator
│   │   └── ui/                # shadcn/ui component library
│   ├── pages/                 # Route-level page components
│   │   ├── Index.tsx          # Landing page
│   │   ├── Chat.tsx           # Chat room page
│   │   └── NotFound.tsx       # 404 page
│   ├── hooks/                 # Custom React hooks
│   ├── lib/                   # Utility functions and configurations
│   └── main.tsx               # Application entry point
├── public/                    # Static assets
└── package.json               # Dependencies and scripts
```

## Backend Structure (Planned)

```
backend/
├── app/
│   ├── main.py                # FastAPI application entry
│   ├── websocket.py           # WebSocket room management
│   ├── api/                   # REST endpoints
│   ├── ai_services/           # AI service integrations
│   ├── models/                # Pydantic schemas
│   ├── storage/               # Database interfaces
│   └── config.py              # Configuration management
└── tests/                     # Backend tests
```

## Component Architecture Patterns

### Chat Components
- **ChatWindow**: Main container managing WebSocket connection and message state
- **MessageBubble**: Displays individual messages with translation support
- **InputBar**: Handles text input and voice recording with typing indicators
- **TypingIndicator**: Shows when other users are typing

### Routing Pattern
- `/` - Landing page for room creation/joining
- `/chat/:roomId` - Dynamic chat room interface
- `*` - 404 fallback for invalid routes

## File Naming Conventions

- **Components**: PascalCase with `.tsx` extension
- **Pages**: PascalCase with `.tsx` extension  
- **Hooks**: camelCase starting with `use` prefix
- **Utilities**: camelCase with `.ts` extension
- **Types**: PascalCase interfaces/types in component files or separate `.types.ts`

## Import Patterns

- Use `@/` path alias for src imports
- Group imports: external libraries, internal components, types
- Prefer named exports over default exports for utilities

## State Management

- **Local State**: useState for component-specific state
- **WebSocket State**: useRef for connection management
- **Global State**: React Context for user preferences, connection status
- **Server State**: React Query for API data fetching (future backend integration)

## Documentation Location

- **Product Requirements**: `reference-docs/prd.md`
- **Implementation Plan**: `reference-docs/Implementation_plan.md`
- **Architecture Guidelines**: `reference-docs/backend_structure.md`, `reference-docs/frontend_guidelines.md`
- **Current Tasks**: `reference-docs/to-do.md`