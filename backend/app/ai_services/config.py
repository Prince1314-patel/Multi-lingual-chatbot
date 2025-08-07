"""
AI Service Configuration

This module manages configuration settings for AI services used in the application.
It provides centralized configuration management for API keys, timeouts, retry logic,
and other AI service parameters.

The configuration is designed to be environment-aware and supports both development
and production settings with appropriate defaults and validation.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()


class AIServiceConfig(BaseSettings):
    """
    Configuration settings for AI services.
    
    This class manages all AI service-related configuration including API keys,
    timeouts, retry settings, and model parameters. It uses Pydantic for
    validation and environment variable support.
    
    Attributes:
        groq_api_key: API key for Groq services
        groq_model: Default model to use for Groq API calls
        groq_timeout: Timeout for Groq API requests in seconds
        groq_max_retries: Maximum number of retries for failed requests
        groq_base_url: Base URL for Groq API (for custom endpoints)
        translation_enabled: Whether translation service is enabled
        translation_cache_ttl: Time-to-live for translation cache in seconds
    """
    
    # Groq API Configuration
    groq_api_key: str = Field(
        default=os.getenv("GROQ_API_KEY", ""),
        description="API key for Groq services"
    )
    
    groq_model: str = Field(
        default="llama3-70b-8192",
        description="Default model to use for Groq API calls"
    )
    
    groq_timeout: float = Field(
        default=30.0,
        description="Timeout for Groq API requests in seconds"
    )
    
    groq_max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests"
    )
    
    groq_base_url: Optional[str] = Field(
        default=None,
        description="Base URL for Groq API (for custom endpoints)"
    )
    
    # Translation Service Configuration
    translation_enabled: bool = Field(
        default=True,  # Enabled by default when API key is available
        description="Whether translation service is enabled"
    )
    
    translation_cache_ttl: int = Field(
        default=3600,  # 1 hour
        description="Time-to-live for translation cache in seconds"
    )
    
    # Performance Configuration
    max_concurrent_translations: int = Field(
        default=10,
        description="Maximum number of concurrent translation requests"
    )
    
    translation_batch_size: int = Field(
        default=5,
        description="Batch size for processing multiple translations"
    )
    
    @validator("groq_api_key")
    def validate_groq_api_key(cls, v: str, values: dict) -> str:
        """
        Validate that Groq API key is provided when translation is enabled.
        
        Args:
            v: The API key value to validate
            values: Dictionary containing other field values
            
        Returns:
            The validated API key
            
        Raises:
            ValueError: If API key is missing when translation is enabled
        """
        translation_enabled = values.get("translation_enabled", False)
        if not v and translation_enabled:
            raise ValueError("GROQ_API_KEY is required when translation is enabled")
        return v
    
    @validator("groq_timeout")
    def validate_timeout(cls, v: float) -> float:
        """
        Validate timeout value is within reasonable bounds.
        
        Args:
            v: The timeout value to validate
            
        Returns:
            The validated timeout value
            
        Raises:
            ValueError: If timeout is outside valid range
        """
        if v < 1.0 or v > 300.0:
            raise ValueError("Timeout must be between 1.0 and 300.0 seconds")
        return v
    
    @validator("groq_max_retries")
    def validate_max_retries(cls, v: int) -> int:
        """
        Validate retry count is within reasonable bounds.
        
        Args:
            v: The retry count to validate
            
        Returns:
            The validated retry count
            
        Raises:
            ValueError: If retry count is outside valid range
        """
        if v < 0 or v > 10:
            raise ValueError("Max retries must be between 0 and 10")
        return v
    
    class Config:
        """Pydantic configuration for environment variable support."""
        env_prefix = "AI_"
        case_sensitive = False


# Global configuration instance
ai_config = AIServiceConfig()
