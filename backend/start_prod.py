#!/usr/bin/env python3
"""
Production startup script for WebSocket Chat Backend
Configures production-specific settings and starts the server
"""
import os
import uvicorn
from app.config import settings

def main():
    """Start the production server with appropriate configuration"""
    
    # Production configuration
    prod_config = {
        "app": "main:app",
        "host": settings.host,
        "port": settings.port,
        "reload": False,  # Never reload in production
        "log_level": settings.log_level,
        "access_log": True,
        "use_colors": False,  # Better for log aggregation
        "workers": 1,  # Single worker for WebSocket support
        "loop": "uvloop",  # Use uvloop for better performance
        "http": "httptools"  # Use httptools for better performance
    }
    
    print(f"🚀 Starting WebSocket Chat Backend in PRODUCTION mode")
    print(f"📍 Server will be available at: http://{settings.host}:{settings.port}")
    print(f"📝 Log level: {prod_config['log_level']}")
    print(f"🌐 CORS origins: {settings.get_cors_origins()}")
    print(f"⚙️  Environment: {settings.environment}")
    print(f"👥 Workers: {prod_config['workers']}")
    print("=" * 60)
    
    # Start the server
    uvicorn.run(**prod_config)

if __name__ == "__main__":
    main()