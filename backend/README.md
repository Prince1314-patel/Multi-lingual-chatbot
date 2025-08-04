# WebSocket Chat Backend

FastAPI-based backend for real-time chat with WebSocket support.

## Setup

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the development server:
```bash
python3 main.py
```

Or use the startup script:
```bash
./start.sh
```

The server will start on `http://localhost:8000`

## API Endpoints

- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint
- `WS /ws/chat/{room_id}` - WebSocket endpoint for chat rooms (to be implemented)

## Project Structure

```
backend/
├── app/
│   ├── models/          # Pydantic data models
│   └── services/        # Business logic services
├── tests/               # Test files
├── main.py             # FastAPI application entry point
├── requirements.txt    # Python dependencies
└── README.md          # This file
```