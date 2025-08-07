from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
import sys
import traceback

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from app.utils import get_current_time_iso

from app.websocket import websocket_router, init_websocket_services, cleanup_websocket_services
from app.core import get_chat_logger, ErrorCode
from app.config import settings

# Configure enhanced logging based on settings
log_handlers = [logging.StreamHandler(sys.stdout)]
if settings.enable_file_logging:
    log_handlers.append(logging.FileHandler(settings.log_file))

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = get_chat_logger()

# Create FastAPI application instance with enhanced error handling
app = FastAPI(
    title="WebSocket Chat Backend",
    description="Real-time chat backend with WebSocket support",
    version="1.0.0"
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.log_error(
        ErrorCode.INTERNAL_SERVER_ERROR,
        f"Unhandled exception in {request.method} {request.url}: {str(exc)}",
        exception=exc
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": get_current_time_iso()
        }
    )

# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Enhanced HTTP exception handler"""
    logger.log_error(
        ErrorCode.INTERNAL_SERVER_ERROR,
        f"HTTP exception in {request.method} {request.url}: {exc.status_code} - {exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP {exc.status_code}",
            "message": exc.detail,
            "timestamp": get_current_time_iso()
        }
    )

# Configure CORS for frontend integration using settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Include WebSocket router
app.include_router(websocket_router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup with error handling"""
    try:
        logger.log_message_event("startup_initiated", None, None, "system")
        await init_websocket_services()
        logger.log_message_event("startup_completed", None, None, "system")
    except Exception as e:
        logger.log_error(
            ErrorCode.SERVICE_UNAVAILABLE,
            f"Failed to initialize WebSocket services: {str(e)}",
            exception=e
        )
        # Re-raise to prevent the application from starting in a broken state
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up services on application shutdown with error handling"""
    try:
        logger.log_message_event("shutdown_initiated", None, None, "system")
        await cleanup_websocket_services()
        logger.log_message_event("shutdown_completed", None, None, "system")
    except Exception as e:
        logger.log_error(
            ErrorCode.INTERNAL_SERVER_ERROR,
            f"Error during shutdown: {str(e)}",
            exception=e
        )
        # Don't re-raise during shutdown to allow graceful termination

@app.get("/")
async def root():
    """Root endpoint returning basic API information with error handling"""
    try:
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
    except Exception as e:
        logger.log_error(
            ErrorCode.INTERNAL_SERVER_ERROR,
            f"Error in root endpoint: {str(e)}",
            exception=e
        )
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers with error handling"""
    try:
        return {
            "status": "healthy",
            "service": "websocket-chat-backend",
            "timestamp": get_current_time_iso()
        }
    except Exception as e:
        logger.log_error(
            ErrorCode.INTERNAL_SERVER_ERROR,
            f"Error in health check: {str(e)}",
            exception=e
        )
        raise HTTPException(status_code=503, detail="Service unavailable")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level
    )