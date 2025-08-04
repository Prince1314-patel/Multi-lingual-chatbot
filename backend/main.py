from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.websocket import websocket_router, init_websocket_services, cleanup_websocket_services

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application instance
app = FastAPI(
    title="WebSocket Chat Backend",
    description="Real-time chat backend with WebSocket support",
    version="1.0.0"
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include WebSocket router
app.include_router(websocket_router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    logger.info("Starting WebSocket Chat Backend...")
    init_websocket_services()
    logger.info("WebSocket services initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up services on application shutdown"""
    logger.info("Shutting down WebSocket Chat Backend...")
    await cleanup_websocket_services()
    logger.info("Shutdown complete")

@app.get("/")
async def root():
    """Root endpoint returning basic API information"""
    return {
        "message": "WebSocket Chat Backend API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "websocket": "/ws/chat/{room_id}",
            "room_info": "/ws/rooms/{room_id}/info",
            "active_rooms": "/ws/rooms",
            "stats": "/ws/stats",
            "websocket_health": "/ws/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    return {
        "status": "healthy",
        "service": "websocket-chat-backend"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )