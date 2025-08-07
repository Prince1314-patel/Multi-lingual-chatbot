"""
AI Services Module

This module provides AI-powered services for the multilingual chat application.
It includes translation services, voice processing, and other AI functionalities.

The module is designed to be extensible, allowing easy addition of new AI services
while maintaining consistent error handling and configuration patterns.

Key Components:
- TranslationService: Handles text translation using Groq LLM
- BaseAIService: Abstract base class for AI services
- AIServiceConfig: Configuration management for AI services
"""

from .translation_service import TranslationService
from .base_service import BaseAIService
from .config import AIServiceConfig

__all__ = [
    "TranslationService",
    "BaseAIService", 
    "AIServiceConfig"
]
