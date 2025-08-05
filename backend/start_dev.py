#!/usr/bin/env python3
"""
Development startup script for WebSocket Chat Backend
Configures development-specific settings and starts the server
"""
import os
import uvicorn
from app.config import settings

def main():
    """Start the development server with appropriate configuration"""
    
    # Override settings for development
    dev_config = {
        "app": "main:app",
        "host": settings.host,
        "port": settings.port,
        "reload": True,
        "log_level": "debug" if settings.debug else "info",
        "access_log": True,
        "use_colors": True,
        "reload_dirs": ["app"],
        "reload_excludes": ["*.log", "*.pyc", "__pycache__"]
    }
    
    print(f"🚀 Starting WebSocket Chat Backend in DEVELOPMENT mode")
    print(f"📍 Server will be available at: http://{settings.host}:{settings.port}")
    print(f"🔄 Auto-reload: {'enabled' if dev_config['reload'] else 'disabled'}")
    print(f"📝 Log level: {dev_config['log_level']}")
    print(f"🌐 CORS origins: {settings.get_cors_origins()}")
    print(f"⚙️  Environment: {settings.environment}")
    print("=" * 60)
    
    # Start the server
    uvicorn.run(**dev_config)

if __name__ == "__main__":
    main()