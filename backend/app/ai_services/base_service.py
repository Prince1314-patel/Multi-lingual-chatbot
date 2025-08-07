"""
Base AI Service

This module provides the foundation for all AI services in the application.
It defines the BaseAIService abstract class that provides common functionality
for error handling, retry logic, logging, and service lifecycle management.

All AI services should inherit from this base class to ensure consistent
behavior and proper error handling across the application.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic
from datetime import datetime, timedelta
from functools import wraps

from .config import AIServiceConfig

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AIServiceError(Exception):
    """
    Base exception for AI service errors.
    
    This exception is raised when AI service operations fail due to
    API errors, configuration issues, or other service-related problems.
    
    Attributes:
        service_name: Name of the AI service that raised the error
        operation: The operation that failed
        details: Additional error details
        retryable: Whether the error is retryable
    """
    
    def __init__(self, service_name: str, operation: str, details: str, 
                 retryable: bool = False):
        """
        Initialize AIServiceError.
        
        Args:
            service_name: Name of the AI service
            operation: The operation that failed
            details: Additional error details
            retryable: Whether the error is retryable
        """
        self.service_name = service_name
        self.operation = operation
        self.details = details
        self.retryable = retryable
        super().__init__(f"{service_name} {operation} failed: {details}")


class AIServiceTimeoutError(AIServiceError):
    """Exception raised when AI service operations timeout."""
    
    def __init__(self, service_name: str, operation: str, timeout: float):
        """
        Initialize AIServiceTimeoutError.
        
        Args:
            service_name: Name of the AI service
            operation: The operation that timed out
            timeout: The timeout value that was exceeded
        """
        super().__init__(
            service_name, operation, 
            f"Operation timed out after {timeout} seconds",
            retryable=True
        )


class AIServiceRateLimitError(AIServiceError):
    """Exception raised when AI service rate limits are exceeded."""
    
    def __init__(self, service_name: str, operation: str, retry_after: Optional[int] = None):
        """
        Initialize AIServiceRateLimitError.
        
        Args:
            service_name: Name of the AI service
            operation: The operation that hit rate limit
            retry_after: Seconds to wait before retrying
        """
        details = "Rate limit exceeded"
        if retry_after:
            details += f", retry after {retry_after} seconds"
        
        super().__init__(service_name, operation, details, retryable=True)
        self.retry_after = retry_after


def retry_on_error(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator to retry operations on retryable errors.
    
    This decorator implements exponential backoff retry logic for
    operations that may fail due to temporary issues like network
    problems or rate limits.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except AIServiceError as e:
                    last_exception = e
                    
                    if not e.retryable or attempt == max_retries:
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = base_delay * (2 ** attempt)
                    
                    # Add jitter to prevent thundering herd
                    jitter = delay * 0.1 * (asyncio.get_event_loop().time() % 1)
                    delay += jitter
                    
                    logger.warning(
                        f"Retryable error in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}): "
                        f"{e.details}. Retrying in {delay:.2f}s"
                    )
                    
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    # Non-retryable error
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise
            
            # If we get here, all retries failed
            raise last_exception
            
        return wrapper
    return decorator


class BaseAIService(ABC, Generic[T]):
    """
    Abstract base class for AI services.
    
    This class provides common functionality for all AI services including
    configuration management, error handling, retry logic, and service
    lifecycle management. All AI services should inherit from this class.
    
    Attributes:
        config: AI service configuration
        service_name: Name of the AI service
        enabled: Whether the service is enabled
        stats: Service usage statistics
    """
    
    def __init__(self, config: AIServiceConfig, service_name: str):
        """
        Initialize BaseAIService.
        
        Args:
            config: AI service configuration
            service_name: Name of the AI service
        """
        self.config = config
        self.service_name = service_name
        self.enabled = True
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_latency": 0.0,
            "last_request_time": None
        }
        
        logger.info(f"Initialized {service_name} AI service")
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the AI service.
        
        This method should be implemented by subclasses to perform any
        necessary initialization such as API client setup, connection
        establishment, or resource allocation.
        
        Raises:
            AIServiceError: If initialization fails
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up the AI service.
        
        This method should be implemented by subclasses to perform any
        necessary cleanup such as closing connections, releasing resources,
        or saving state.
        """
        pass
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the AI service.
        
        This method should be implemented by subclasses to verify that
        the service is functioning correctly. The default implementation
        returns True if the service is enabled.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        return self.enabled
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get service usage statistics.
        
        Returns:
            Dictionary containing service statistics
        """
        stats = self.stats.copy()
        if stats["total_requests"] > 0:
            stats["success_rate"] = stats["successful_requests"] / stats["total_requests"]
            stats["avg_latency"] = stats["total_latency"] / stats["total_requests"]
        else:
            stats["success_rate"] = 0.0
            stats["avg_latency"] = 0.0
        
        return stats
    
    def _update_stats(self, success: bool, latency: float) -> None:
        """
        Update service statistics.
        
        Args:
            success: Whether the operation was successful
            latency: Operation latency in seconds
        """
        self.stats["total_requests"] += 1
        self.stats["total_latency"] += latency
        self.stats["last_request_time"] = datetime.utcnow()
        
        if success:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1
    
    def _log_operation(self, operation: str, **kwargs) -> None:
        """
        Log an operation for debugging and monitoring.
        
        Args:
            operation: Name of the operation
            **kwargs: Additional logging context
        """
        logger.debug(
            f"{self.service_name} {operation}",
            extra={
                "service": self.service_name,
                "operation": operation,
                **kwargs
            }
        )
    
    def _handle_api_error(self, error: Exception, operation: str) -> AIServiceError:
        """
        Convert API errors to AIServiceError.
        
        Args:
            error: The original API error
            operation: The operation that failed
            
        Returns:
            Appropriate AIServiceError instance
        """
        error_str = str(error).lower()
        
        if "timeout" in error_str or "timed out" in error_str:
            return AIServiceTimeoutError(self.service_name, operation, self.config.groq_timeout)
        elif "rate limit" in error_str or "429" in error_str:
            return AIServiceRateLimitError(self.service_name, operation)
        else:
            return AIServiceError(
                self.service_name, operation, str(error),
                retryable="retry" in error_str or "temporary" in error_str
            )
