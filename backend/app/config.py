"""
Configuration module for WebSocket Chat Backend
Handles environment variables and application settings
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    reload: bool = Field(default=True, env="RELOAD")
    log_level: str = Field(default="info", env="LOG_LEVEL")
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:8080", "http://127.0.0.1:8080"],
        env="CORS_ORIGINS"
  
   )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["*"], env="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # WebSocket Configuration
    websocket_timeout: int = Field(default=60, env="WEBSOCKET_TIMEOUT")
    max_connections_per_room: int = Field(default=50, env="MAX_CONNECTIONS_PER_ROOM")
    room_cleanup_interval: int = Field(default=300, env="ROOM_CLEANUP_INTERVAL")  # 5 minutes
    empty_room_timeout: int = Field(default=1800, env="EMPTY_ROOM_TIMEOUT")  # 30 minutes
    
    # Message Configuration
    max_message_size: int = Field(default=1024 * 1024, env="MAX_MESSAGE_SIZE")  # 1MB
    max_voice_message_size: int = Field(default=5 * 1024 * 1024, env="MAX_VOICE_MESSAGE_SIZE")  # 5MB
    typing_timeout: int = Field(default=3, env="TYPING_TIMEOUT")  # 3 seconds
    
    # Logging Configuration
    log_file: str = Field(default="backend.log", env="LOG_FILE")
    enable_file_logging: bool = Field(default=True, env="ENABLE_FILE_LOGGING")
    
    # Development/Production Settings
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() in ["development", "dev"]
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() in ["production", "prod"]
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins, handling string input from environment"""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins


# Global settings instance
settings = Settings()