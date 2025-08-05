import asyncio
import logging
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from fastapi import WebSocket

from .connection_manager import ConnectionManager
from .room_manager import RoomManager
from .rate_limiter import RateLimiter
from ..models import (
    MessageType,
    TextMessage,
    VoiceMessage,
    TypingMessage,
    UserJoinMessage,
    UserLeaveMessage,
    MessageDeliveryConfirmation,
    ErrorMessage,
    deserialize_message,
    serialize_message
)

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles processing and routing of different message types"""
    
    def __init__(self, connection_manager: ConnectionManager, room_manager: RoomManager, 
                 rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize MessageHandler
        
        Args:
            connection_manager: ConnectionManager instance for handling connections
            room_manager: RoomManager instance for room operations
            rate_limiter: Optional RateLimiter instance for message rate limiting
        """
        self.connection_manager = connection_manager
        self.room_manager = room_manager
        self.rate_limiter = rate_limiter
        self.typing_timeouts: Dict[str, Dict[str, asyncio.Task]] = {}  # room_id -> user_id -> timeout_task
    
    async def handle_message(self, websocket: WebSocket, message_data: dict) -> bool:
        """
        Handle incoming message from WebSocket
        
        Args:
            websocket: The WebSocket connection
            message_data: Raw message data dictionary
            
        Returns:
            True if message was handled successfully, False otherwise
        """
        try:
            # Get connection info
            connection = self.connection_manager.get_connection_info(websocket)
            if not connection:
                await self.connection_manager.send_error(
                    websocket, "CONNECTION_NOT_FOUND", "Connection not found"
                )
                return False
            
            # Deserialize message
            try:
                message = deserialize_message(message_data)
            except (ValueError, KeyError) as e:
                await self.connection_manager.send_error(
                    websocket, "INVALID_MESSAGE_FORMAT", f"Invalid message format: {str(e)}"
                )
                return False
            
            # Validate message belongs to the connection's room
            if hasattr(message, 'room_id') and message.room_id != connection.room_id:
                await self.connection_manager.send_error(
                    websocket, "INVALID_ROOM", "Message room does not match connection room"
                )
                return False
            
            # Route message based on type
            if isinstance(message, TextMessage):
                return await self.handle_text_message(connection, message)
            elif isinstance(message, VoiceMessage):
                return await self.handle_voice_message(connection, message)
            elif isinstance(message, TypingMessage):
                return await self.handle_typing_message(connection, message)
            else:
                await self.connection_manager.send_error(
                    websocket, "UNSUPPORTED_MESSAGE_TYPE", f"Unsupported message type: {type(message).__name__}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.connection_manager.send_error(
                websocket, "MESSAGE_PROCESSING_ERROR", "Failed to process message"
            )
            return False
    
    async def handle_binary_message(self, websocket: WebSocket, binary_data: bytes) -> bool:
        """
        Handle incoming binary message (voice data) from WebSocket
        
        Args:
            websocket: The WebSocket connection
            binary_data: Raw binary audio data
            
        Returns:
            True if message was handled successfully, False otherwise
        """
        try:
            # Get connection info
            connection = self.connection_manager.get_connection_info(websocket)
            if not connection:
                await self.connection_manager.send_error(
                    websocket, "CONNECTION_NOT_FOUND", "Connection not found"
                )
                return False
            
            # Validate binary data
            if not binary_data:
                await self.connection_manager.send_error(
                    websocket, "EMPTY_BINARY_DATA", "Binary data cannot be empty"
                )
                return False
            
            # Validate audio data size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if len(binary_data) > max_size:
                await self.connection_manager.send_error(
                    websocket, "BINARY_DATA_TOO_LARGE", f"Binary data exceeds maximum size of {max_size} bytes"
                )
                return False
            
            # Create VoiceMessage with binary data
            voice_message = VoiceMessage(
                user_id=connection.user_id,
                room_id=connection.room_id,
                audio_data=binary_data,
                audio_format="webm"  # Default format, could be detected or specified
            )
            
            # Update connection activity
            connection.update_activity()
            
            # Broadcast to all users in the room with delivery confirmation
            sent_count = await self.connection_manager.broadcast_to_room(
                connection.room_id, voice_message, exclude_user=connection.user_id, send_confirmation=True
            )
            
            logger.info(f"Binary voice message from {connection.user_id} ({len(binary_data)} bytes) broadcasted to {sent_count} users in room {connection.room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling binary message: {e}")
            await self.connection_manager.send_error(
                websocket, "BINARY_MESSAGE_PROCESSING_ERROR", "Failed to process binary message"
            )
            return False
    
    async def handle_text_message(self, connection, message: TextMessage) -> bool:
        """
        Handle text message processing and broadcasting with rate limiting
        
        Args:
            connection: ConnectionInfo object
            message: TextMessage to process
            
        Returns:
            True if message was handled successfully
        """
        try:
            # Check rate limit if rate limiter is available
            if self.rate_limiter:
                allowed, wait_time = self.rate_limiter.check_message_rate_limit(
                    connection.user_id, 'text'
                )
                if not allowed:
                    await self.connection_manager.send_error(
                        connection.websocket, "RATE_LIMIT_EXCEEDED", 
                        f"Text message rate limit exceeded. Wait {wait_time:.1f} seconds."
                    )
                    return False
            
            # Update connection activity
            connection.update_activity()
            
            # Validate message content
            if not message.content or not message.content.strip():
                await self.connection_manager.send_error(
                    connection.websocket, "EMPTY_MESSAGE", "Message content cannot be empty"
                )
                return False
            
            # Set correct user_id and room_id from connection
            message.user_id = connection.user_id
            message.room_id = connection.room_id
            
            # Broadcast to all users in the room with delivery confirmation
            sent_count = await self.connection_manager.broadcast_to_room(
                connection.room_id, message, exclude_user=connection.user_id, send_confirmation=True
            )
            
            logger.info(f"Text message from {connection.user_id} broadcasted to {sent_count} users in room {connection.room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            return False
    
    async def handle_voice_message(self, connection, message: VoiceMessage) -> bool:
        """
        Handle voice message processing and broadcasting with rate limiting
        
        Args:
            connection: ConnectionInfo object
            message: VoiceMessage to process
            
        Returns:
            True if message was handled successfully
        """
        try:
            # Check rate limit if rate limiter is available
            if self.rate_limiter:
                allowed, wait_time = self.rate_limiter.check_message_rate_limit(
                    connection.user_id, 'voice'
                )
                if not allowed:
                    await self.connection_manager.send_error(
                        connection.websocket, "RATE_LIMIT_EXCEEDED", 
                        f"Voice message rate limit exceeded. Wait {wait_time:.1f} seconds."
                    )
                    return False
            
            # Update connection activity
            connection.update_activity()
            
            # Validate voice message
            if not message.audio_data:
                await self.connection_manager.send_error(
                    connection.websocket, "EMPTY_VOICE_MESSAGE", "Voice message must contain audio data"
                )
                return False
            
            # Validate audio data size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if len(message.audio_data) > max_size:
                await self.connection_manager.send_error(
                    connection.websocket, "VOICE_MESSAGE_TOO_LARGE", f"Voice message exceeds maximum size of {max_size} bytes"
                )
                return False
            
            # Validate duration if provided
            if message.duration is not None and (message.duration <= 0 or message.duration > 300):
                await self.connection_manager.send_error(
                    connection.websocket, "INVALID_DURATION", "Voice message duration must be between 0 and 300 seconds"
                )
                return False
            
            # Set correct user_id and room_id from connection
            message.user_id = connection.user_id
            message.room_id = connection.room_id
            
            # Broadcast to all users in the room with delivery confirmation
            sent_count = await self.connection_manager.broadcast_to_room(
                connection.room_id, message, exclude_user=connection.user_id, send_confirmation=True
            )
            
            logger.info(f"Voice message from {connection.user_id} broadcasted to {sent_count} users in room {connection.room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling voice message: {e}")
            return False
    
    async def handle_typing_message(self, connection, message: TypingMessage) -> bool:
        """
        Handle typing indicator message processing with rate limiting
        
        Args:
            connection: ConnectionInfo object
            message: TypingMessage to process
            
        Returns:
            True if message was handled successfully
        """
        try:
            # Check rate limit if rate limiter is available
            if self.rate_limiter:
                allowed, wait_time = self.rate_limiter.check_message_rate_limit(
                    connection.user_id, 'typing'
                )
                if not allowed:
                    # For typing messages, we silently drop them instead of sending error
                    # to avoid spamming the user with rate limit errors
                    logger.debug(f"Typing message rate limited for user {connection.user_id}")
                    return False
            
            # Update connection activity
            connection.update_activity()
            
            # Set correct user_id and room_id from connection
            message.user_id = connection.user_id
            message.room_id = connection.room_id
            
            # Get room
            room = self.room_manager.get_room(connection.room_id)
            if not room:
                logger.warning(f"Room {connection.room_id} not found for typing message")
                return False
            
            # Update typing status in connection
            connection.set_typing(message.is_typing)
            
            # Manage typing timeout
            await self._manage_typing_timeout(connection, message.is_typing)
            
            # Broadcast typing indicator to other users in the room (exclude sender)
            sent_count = await self.connection_manager.broadcast_to_room(
                connection.room_id, message, exclude_user=connection.user_id
            )
            
            logger.debug(f"Typing indicator from {connection.user_id} (typing: {message.is_typing}) broadcasted to {sent_count} users")
            return True
            
        except Exception as e:
            logger.error(f"Error handling typing message: {e}")
            return False
    
    async def _manage_typing_timeout(self, connection, is_typing: bool):
        """
        Manage typing indicator timeout for a user
        
        Args:
            connection: ConnectionInfo object
            is_typing: Whether user is currently typing
        """
        room_id = connection.room_id
        user_id = connection.user_id
        
        # Initialize room typing timeouts if needed
        if room_id not in self.typing_timeouts:
            self.typing_timeouts[room_id] = {}
        
        # Cancel existing timeout task if any
        if user_id in self.typing_timeouts[room_id]:
            self.typing_timeouts[room_id][user_id].cancel()
            del self.typing_timeouts[room_id][user_id]
        
        # Set new timeout if user is typing
        if is_typing:
            timeout_task = asyncio.create_task(
                self._typing_timeout_handler(connection, 3.0)  # 3 second timeout
            )
            self.typing_timeouts[room_id][user_id] = timeout_task
    
    async def _typing_timeout_handler(self, connection, timeout_seconds: float):
        """
        Handle typing indicator timeout
        
        Args:
            connection: ConnectionInfo object
            timeout_seconds: Timeout duration in seconds
        """
        try:
            await asyncio.sleep(timeout_seconds)
            
            # Check if user is still typing (might have been updated)
            if connection.is_typing:
                # Set typing to false
                connection.set_typing(False)
                
                # Send typing stopped message to other users
                typing_message = TypingMessage(
                    user_id=connection.user_id,
                    room_id=connection.room_id,
                    is_typing=False
                )
                
                await self.connection_manager.broadcast_to_room(
                    connection.room_id, typing_message, exclude_user=connection.user_id
                )
                
                logger.debug(f"Typing timeout for user {connection.user_id} in room {connection.room_id}")
            
            # Clean up timeout task
            room_id = connection.room_id
            user_id = connection.user_id
            if (room_id in self.typing_timeouts and 
                user_id in self.typing_timeouts[room_id]):
                del self.typing_timeouts[room_id][user_id]
                
        except asyncio.CancelledError:
            # Task was cancelled, which is normal
            pass
        except Exception as e:
            logger.error(f"Error in typing timeout handler: {e}")
    
    async def handle_user_disconnect(self, connection):
        """
        Handle cleanup when a user disconnects
        
        Args:
            connection: ConnectionInfo object of disconnected user
        """
        try:
            room_id = connection.room_id
            user_id = connection.user_id
            
            # Cancel any active typing timeout
            if (room_id in self.typing_timeouts and 
                user_id in self.typing_timeouts[room_id]):
                self.typing_timeouts[room_id][user_id].cancel()
                del self.typing_timeouts[room_id][user_id]
                
                # Clean up empty room entry
                if not self.typing_timeouts[room_id]:
                    del self.typing_timeouts[room_id]
            
            # If user was typing, send typing stopped message
            if connection.is_typing:
                typing_message = TypingMessage(
                    user_id=user_id,
                    room_id=room_id,
                    is_typing=False
                )
                
                await self.connection_manager.broadcast_to_room(
                    room_id, typing_message, exclude_user=user_id
                )
            
            logger.debug(f"Cleaned up typing state for disconnected user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling user disconnect cleanup: {e}")
    
    def get_typing_users(self, room_id: str) -> Set[str]:
        """
        Get set of users currently typing in a room
        
        Args:
            room_id: The room ID
            
        Returns:
            Set of user IDs currently typing
        """
        room = self.room_manager.get_room(room_id)
        if room:
            return room.get_typing_users()
        return set()
    
    def get_message_handler_stats(self) -> Dict:
        """
        Get statistics about the message handler
        
        Returns:
            Dictionary with message handler statistics
        """
        total_typing_timeouts = sum(len(room_timeouts) for room_timeouts in self.typing_timeouts.values())
        
        return {
            'active_typing_timeouts': total_typing_timeouts,
            'rooms_with_typing': len(self.typing_timeouts),
            'typing_timeout_seconds': 3.0
        }
    
    async def cleanup_all_typing_timeouts(self):
        """Clean up all active typing timeouts (useful for shutdown)"""
        for room_timeouts in self.typing_timeouts.values():
            for timeout_task in room_timeouts.values():
                timeout_task.cancel()
        
        self.typing_timeouts.clear()
        logger.info("Cleaned up all typing timeouts")