"""
Enhanced error handling and logging utilities for WebSocket chat backend
"""

import logging
import traceback
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import json

from ..models import ErrorMessage


class ErrorCode(Enum):
    """Standardized error codes for the WebSocket chat system"""
    
    # Connection errors
    CONNECTION_FAILED = "CONNECTION_FAILED"
    CONNECTION_NOT_FOUND = "CONNECTION_NOT_FOUND"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    CONNECTION_LIMIT_EXCEEDED = "CONNECTION_LIMIT_EXCEEDED"
    
    # Room errors
    INVALID_ROOM_ID = "INVALID_ROOM_ID"
    ROOM_NOT_FOUND = "ROOM_NOT_FOUND"
    ROOM_FULL = "ROOM_FULL"
    
    # Message errors
    INVALID_MESSAGE_FORMAT = "INVALID_MESSAGE_FORMAT"
    INVALID_JSON = "INVALID_JSON"
    MESSAGE_TOO_LARGE = "MESSAGE_TOO_LARGE"
    EMPTY_MESSAGE = "EMPTY_MESSAGE"
    UNSUPPORTED_MESSAGE_TYPE = "UNSUPPORTED_MESSAGE_TYPE"
    MESSAGE_PROCESSING_ERROR = "MESSAGE_PROCESSING_ERROR"
    
    # Voice message errors
    EMPTY_VOICE_MESSAGE = "EMPTY_VOICE_MESSAGE"
    VOICE_MESSAGE_TOO_LARGE = "VOICE_MESSAGE_TOO_LARGE"
    INVALID_AUDIO_FORMAT = "INVALID_AUDIO_FORMAT"
    INVALID_DURATION = "INVALID_DURATION"
    
    # Binary data errors
    EMPTY_BINARY_DATA = "EMPTY_BINARY_DATA"
    BINARY_DATA_TOO_LARGE = "BINARY_DATA_TOO_LARGE"
    BINARY_MESSAGE_PROCESSING_ERROR = "BINARY_MESSAGE_PROCESSING_ERROR"
    
    # System errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    
    # Validation errors
    INVALID_USER_ID = "INVALID_USER_ID"
    INVALID_ROOM = "INVALID_ROOM"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class ChatLogger:
    """Enhanced logging utility for WebSocket chat system"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure logger with appropriate formatting"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_connection_event(self, event: str, user_id: str, room_id: str, 
                           details: Optional[Dict[str, Any]] = None):
        """Log connection-related events"""
        message = f"Connection {event}: user={user_id}, room={room_id}"
        if details:
            message += f", details={details}"
        self.logger.info(message)
    
    def log_message_event(self, event: str, user_id: str, room_id: str, 
                         message_type: str, details: Optional[Dict[str, Any]] = None):
        """Log message-related events"""
        message = f"Message {event}: user={user_id}, room={room_id}, type={message_type}"
        if details:
            message += f", details={details}"
        self.logger.info(message)
    
    def log_error(self, error_code: ErrorCode, message: str, user_id: Optional[str] = None,
                  room_id: Optional[str] = None, exception: Optional[Exception] = None):
        """Log errors with standardized format"""
        error_msg = f"ERROR [{error_code.value}]: {message}"
        if user_id:
            error_msg += f", user={user_id}"
        if room_id:
            error_msg += f", room={room_id}"
        
        if exception:
            error_msg += f", exception={str(exception)}"
            self.logger.error(error_msg, exc_info=True)
        else:
            self.logger.error(error_msg)
    
    def log_warning(self, message: str, user_id: Optional[str] = None,
                   room_id: Optional[str] = None):
        """Log warnings with context"""
        warning_msg = f"WARNING: {message}"
        if user_id:
            warning_msg += f", user={user_id}"
        if room_id:
            warning_msg += f", room={room_id}"
        self.logger.warning(warning_msg)
    
    def log_performance(self, operation: str, duration_ms: float, 
                       user_id: Optional[str] = None, room_id: Optional[str] = None):
        """Log performance metrics"""
        perf_msg = f"PERFORMANCE: {operation} took {duration_ms:.2f}ms"
        if user_id:
            perf_msg += f", user={user_id}"
        if room_id:
            perf_msg += f", room={room_id}"
        self.logger.info(perf_msg)


class ErrorHandler:
    """Centralized error handling for WebSocket operations"""
    
    def __init__(self, logger: ChatLogger):
        self.logger = logger
    
    async def handle_websocket_error(self, websocket: WebSocket, error_code: ErrorCode, 
                                   message: str, user_id: Optional[str] = None,
                                   room_id: Optional[str] = None, 
                                   exception: Optional[Exception] = None) -> bool:
        """
        Handle WebSocket errors by logging and sending error response
        
        Args:
            websocket: The WebSocket connection
            error_code: Standardized error code
            message: Human-readable error message
            user_id: Optional user ID for context
            room_id: Optional room ID for context
            exception: Optional exception that caused the error
            
        Returns:
            True if error response was sent successfully, False otherwise
        """
        # Log the error
        self.logger.log_error(error_code, message, user_id, room_id, exception)
        
        # Try to send error response to client
        try:
            error_msg = ErrorMessage(
                error_code=error_code.value,
                message=message
            )
            
            error_data = error_msg.model_dump()
            await websocket.send_text(json.dumps(error_data, default=str))
            return True
            
        except Exception as send_error:
            self.logger.log_error(
                ErrorCode.MESSAGE_PROCESSING_ERROR,
                f"Failed to send error response: {str(send_error)}",
                user_id, room_id, send_error
            )
            return False
    
    
    
    def handle_message_validation_error(self, error: Exception, user_id: str, 
                                      room_id: str) -> ErrorCode:
        """
        Determine appropriate error code for message validation errors
        
        Args:
            error: The validation error
            user_id: User ID for context
            room_id: Room ID for context
            
        Returns:
            Appropriate ErrorCode for the validation error
        """
        error_str = str(error).lower()
        
        if "json" in error_str:
            return ErrorCode.INVALID_JSON
        elif "empty" in error_str or "content" in error_str:
            return ErrorCode.EMPTY_MESSAGE
        elif "size" in error_str or "large" in error_str:
            return ErrorCode.MESSAGE_TOO_LARGE
        elif "format" in error_str:
            return ErrorCode.INVALID_MESSAGE_FORMAT
        else:
            return ErrorCode.VALIDATION_ERROR
    
    async def safe_websocket_close(self, websocket: WebSocket, code: int = 1000, 
                                 reason: str = "Normal closure") -> bool:
        """
        Safely close a WebSocket connection with error handling
        
        Args:
            websocket: The WebSocket connection to close
            code: WebSocket close code
            reason: Reason for closure
            
        Returns:
            True if closed successfully, False otherwise
        """
        try:
            await websocket.close(code=code, reason=reason)
            return True
        except Exception as e:
            self.logger.log_error(
                ErrorCode.CONNECTION_FAILED,
                f"Failed to close WebSocket connection: {str(e)}",
                exception=e
            )
            return False


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None
_chat_logger: Optional[ChatLogger] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    global _error_handler, _chat_logger
    
    if _error_handler is None:
        _chat_logger = ChatLogger("websocket_chat")
        _error_handler = ErrorHandler(_chat_logger)
    
    return _error_handler


def get_chat_logger() -> ChatLogger:
    """Get the global chat logger instance"""
    global _chat_logger
    
    if _chat_logger is None:
        _chat_logger = ChatLogger("websocket_chat")
    
    return _chat_logger