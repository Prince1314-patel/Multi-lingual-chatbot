# WebSocket Chat Backend Startup Guide

This document explains how to start and configure the WebSocket Chat Backend.

## Quick Start

### Development Mode
```bash
# Using the startup script (recommended)
./start.sh dev

# Or directly with Python
python start_dev.py

# Or with the original main.py
python main.py
```

### Production Mode
```bash
# Using the startup script (recommended)
./start.sh prod

# Or directly with Python
python start_prod.py
```

## Startup Scripts

### Shell Script (`start.sh`)
The main startup script provides a convenient way to start the server with proper environment setup.

**Usage:**
```bash
./start.sh [dev|prod] [options]
```

**Options:**
- `--install` - Install/update dependencies before starting
- `--no-venv` - Skip virtual environment activation
- `--help` - Show help message

**Examples:**
```bash
# Start in development mode with dependency installation
./start.sh dev --install

# Start in production mode without virtual environment
./start.sh prod --no-venv

# Install dependencies and start in development mode
./start.sh --install
```

### Python Scripts

#### Development (`start_dev.py`)
- Enables auto-reload for code changes
- Uses debug log level
- Includes development-specific optimizations
- Watches `app/` directory for changes

#### Production (`start_prod.py`)
- Disables auto-reload for stability
- Uses optimized event loop (uvloop)
- Single worker process for WebSocket support
- Production-ready logging configuration

## Configuration

### Environment Variables

The backend supports configuration through environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host address |
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `info` | Logging level (debug, info, warning, error) |
| `ENVIRONMENT` | `development` | Environment mode |
| `DEBUG` | `false` | Enable debug mode |
| `RELOAD` | `true` | Enable auto-reload (dev only) |

#### CORS Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `http://localhost:8080,http://127.0.0.1:8080` | Allowed origins (comma-separated) |
| `CORS_ALLOW_CREDENTIALS` | `true` | Allow credentials in CORS |
| `CORS_ALLOW_METHODS` | `*` | Allowed HTTP methods |
| `CORS_ALLOW_HEADERS` | `*` | Allowed HTTP headers |

#### WebSocket Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `WEBSOCKET_TIMEOUT` | `60` | WebSocket connection timeout (seconds) |
| `MAX_CONNECTIONS_PER_ROOM` | `50` | Maximum connections per room |
| `ROOM_CLEANUP_INTERVAL` | `300` | Room cleanup interval (seconds) |
| `EMPTY_ROOM_TIMEOUT` | `1800` | Empty room timeout (seconds) |

#### Message Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_MESSAGE_SIZE` | `1048576` | Maximum text message size (bytes) |
| `MAX_VOICE_MESSAGE_SIZE` | `5242880` | Maximum voice message size (bytes) |
| `TYPING_TIMEOUT` | `3` | Typing indicator timeout (seconds) |

### Configuration File

Create a `.env` file in the backend directory to set environment variables:

```bash
# Copy the example file
cp .env.example .env

# Edit the configuration
nano .env
```

Example `.env` file:
```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
DEBUG=true

# CORS Configuration
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://localhost:3000

# WebSocket Configuration
MAX_CONNECTIONS_PER_ROOM=100
WEBSOCKET_TIMEOUT=120

# Logging
LOG_LEVEL=debug
ENABLE_FILE_LOGGING=true
LOG_FILE=backend.log
```

## Health Checks

The backend provides health check endpoints:

- **Health Check**: `GET /health`
  - Returns server health status
  - Used by load balancers and monitoring

- **API Info**: `GET /`
  - Returns API information and available endpoints
  - Useful for service discovery

## Logging

The backend uses structured logging with the following features:

- **File Logging**: Logs are written to `backend.log` by default
- **Console Logging**: Real-time logs in the terminal
- **Structured Format**: Consistent log format with timestamps
- **Error Tracking**: Detailed error logging with stack traces
- **Performance Logging**: Request timing and performance metrics

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Find process using port 8000
   lsof -i :8000
   
   # Kill the process
   kill -9 <PID>
   
   # Or use a different port
   PORT=8001 ./start.sh dev
   ```

2. **Virtual Environment Issues**
   ```bash
   # Recreate virtual environment
   rm -rf venv
   python3 -m venv venv
   ./start.sh dev --install
   ```

3. **Dependency Issues**
   ```bash
   # Reinstall dependencies
   ./start.sh dev --install
   
   # Or manually
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **CORS Issues**
   ```bash
   # Add your frontend URL to CORS_ORIGINS
   export CORS_ORIGINS="http://localhost:8080,http://localhost:3000"
   ./start.sh dev
   ```

### Debug Mode

Enable debug mode for detailed logging:

```bash
DEBUG=true LOG_LEVEL=debug ./start.sh dev
```

### Performance Monitoring

Monitor server performance:

```bash
# Check server status
curl http://localhost:8000/health

# View real-time logs
tail -f backend.log

# Monitor WebSocket connections
curl http://localhost:8000/ws/stats
```

## Integration with Frontend

The backend is configured to work with the React frontend:

- **Default CORS**: Allows `http://localhost:8080` (Vite dev server)
- **WebSocket Endpoint**: `/ws/chat/{room_id}`
- **Health Check**: Frontend can check `/health` for backend availability

### Frontend Configuration

Update your frontend to connect to the backend:

```typescript
// WebSocket connection
const wsUrl = `ws://localhost:8000/ws/chat/${roomId}`;

// Health check
const healthCheck = await fetch('http://localhost:8000/health');
```

## Production Deployment

For production deployment:

1. **Set Environment Variables**:
   ```bash
   export ENVIRONMENT=production
   export DEBUG=false
   export LOG_LEVEL=info
   export HOST=0.0.0.0
   export PORT=8000
   ```

2. **Start Production Server**:
   ```bash
   ./start.sh prod
   ```

3. **Use Process Manager** (recommended):
   ```bash
   # With PM2
   pm2 start start_prod.py --name websocket-chat

   # With systemd
   sudo systemctl start websocket-chat
   ```

4. **Configure Reverse Proxy** (nginx example):
   ```nginx
   location /ws/ {
       proxy_pass http://localhost:8000;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header Host $host;
   }
   ```