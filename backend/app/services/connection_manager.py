from typing import Dict, List, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging
from datetime import datetime

from ..models import (
    ConnectionInfo,
    Room,
    MessageType,
    VoiceMessage,
    serialize_message,
    deserialize_message,
    ErrorMessage,
    UserJoinMessage,
    UserLeaveMessage,
    MessageDeliveryConfirmation,
    generate_user_id
)
from ..core import ErrorCode, ChatLogger, get_chat_logger
from .rate_limiter import RateLimiter
from .room_manager import RoomManager

logger = get_chat_logger()


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self, room_manager: RoomManager, rate_limiter: Optional[RateLimiter] = None):
        self.room_manager = room_manager
        # Dictionary mapping websocket -> ConnectionInfo for quick lookup
        self.connection_lookup: Dict[WebSocket, ConnectionInfo] = {}
        # Rate limiter for connection and message limits
        self.rate_limiter = rate_limiter
    
    async def connect(self, websocket: WebSocket, room_id: str, user_id: Optional[str] = None, 
                     ip_address: Optional[str] = None, display_name: Optional[str] = None,
                     preferred_language: Optional[str] = None) -> ConnectionInfo:
        """
        Accept a WebSocket connection and add it to a room with rate limiting
        
        Args:
            websocket: The WebSocket connection
            room_id: The room to join
            user_id: Optional user ID, will generate one if not provided
            ip_address: Optional IP address for rate limiting
            display_name: Optional display name for the user
            preferred_language: Optional preferred language for translation
            
        Returns:
            ConnectionInfo object for the new connection
            
        Raises:
            ConnectionError: If connection limits are exceeded
        """
        # Check connection limits if rate limiter is available
        if self.rate_limiter:
            allowed, reason = self.rate_limiter.check_connection_limit(room_id, ip_address)
            if not allowed:
                logger.log_error(
                    ErrorCode.CONNECTION_LIMIT_EXCEEDED,
                    f"Connection limit exceeded: {reason}",
                    user_id, room_id
                )
                await websocket.close(code=4008, reason=reason)
                raise ConnectionError(reason)
        
        await websocket.accept()
        
        # Generate user ID if not provided
        if not user_id:
            user_id = generate_user_id()
        
        # Create connection info with user preferences
        connection = ConnectionInfo(
            websocket=websocket,
            user_id=user_id,
            room_id=room_id,
            display_name=display_name,
            preferred_language=preferred_language
        )
        
        # Create room if it doesn't exist
        room = self.room_manager.get_or_create_room(room_id)
        
        # Add connection to room and lookup table
        room.add_connection(connection)
        self.connection_lookup[websocket] = connection
        
        # Add to rate limiter tracking
        if self.rate_limiter:
            self.rate_limiter.add_connection(room_id, user_id, ip_address)
        
        logger.log_connection_event("established", user_id, room_id)
        
        

        # Broadcast user join message to other users in the room
        join_message = UserJoinMessage(
            user_id=user_id,
            room_id=room_id,
            display_name=connection.get_display_name()
        )
        await self.broadcast_to_room(room_id, join_message, exclude_user=user_id)
        
        return connection
    
    async def disconnect(self, websocket: WebSocket, broadcast_leave: bool = True, 
                        ip_address: Optional[str] = None) -> Optional[ConnectionInfo]:
        """
        Handle WebSocket disconnection and cleanup
        
        Args:
            websocket: The WebSocket connection to disconnect
            broadcast_leave: Whether to broadcast leave message (False during cleanup)
            ip_address: Optional IP address for rate limiter cleanup
            
        Returns:
            ConnectionInfo of the disconnected user, or None if not found
        """
        connection = self.connection_lookup.pop(websocket, None)
        if not connection:
            return None
        
        room_id = connection.room_id
        user_id = connection.user_id
        
        # Remove from rate limiter tracking
        if self.rate_limiter:
            self.rate_limiter.remove_connection(room_id, user_id, ip_address)
        
        # Remove connection from room
        room = self.room_manager.get_room(room_id)
        if room:
            room.remove_connection(user_id)
            
            # Broadcast user leave message to remaining users (if requested)
            if broadcast_leave and not room.is_empty():
                leave_message = UserLeaveMessage(
                    user_id=user_id,
                    room_id=room_id,
                    display_name=connection.get_display_name()
                )
                await self.broadcast_to_room(room_id, leave_message)
            
            # Clean up empty room
            if room.is_empty():
                self.room_manager.delete_room(room_id)
                logger.log_connection_event("room_deleted", None, room_id, {"reason": "empty"})
        
        logger.log_connection_event("disconnected", user_id, room_id)
        return connection
    
    async def send_message(self, websocket: WebSocket, message: MessageType) -> bool:
        """
        Send a message to a specific WebSocket connection with enhanced error handling
        
        Args:
            websocket: The target WebSocket connection
            message: The message to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        connection = self.get_connection_info(websocket)
        user_id = connection.user_id if connection else "unknown"
        room_id = connection.room_id if connection else "unknown"
        
        try:
            # Handle VoiceMessage with binary data specially
            if isinstance(message, VoiceMessage) and message.audio_data:
                # Validate binary data size before sending
                if len(message.audio_data) > 10 * 1024 * 1024:  # 10MB limit
                    logger.log_error(
                        ErrorCode.BINARY_DATA_TOO_LARGE,
                        f"Binary data too large: {len(message.audio_data)} bytes",
                        user_id, room_id
                    )
                    return False
                
                # Send binary audio data directly
                await websocket.send_bytes(message.audio_data)
                logger.log_message_event("binary_sent", user_id, room_id, "voice", {
                    "size_bytes": len(message.audio_data)
                })
                return True
            else:
                # Send as JSON text message
                try:
                    serialized = serialize_message(message)
                    # Use proper JSON encoder for datetime objects
                    def json_encoder(obj):
                        if isinstance(obj, datetime):
                            return obj.isoformat()
                        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
                    
                    json_str = json.dumps(serialized, default=json_encoder)
                    
                    # Check message size
                    if len(json_str) > 1024 * 1024:  # 1MB limit for text messages
                        logger.log_error(
                            ErrorCode.MESSAGE_TOO_LARGE,
                            f"Text message too large: {len(json_str)} bytes",
                            user_id, room_id
                        )
                        return False
                    
                    await websocket.send_text(json_str)
                    logger.log_message_event("text_sent", user_id, room_id, message.type if hasattr(message, 'type') else "unknown")
                    return True
                    
                except (TypeError, ValueError) as e:
                    logger.log_error(
                        ErrorCode.INVALID_MESSAGE_FORMAT,
                        f"Failed to serialize message: {str(e)}",
                        user_id, room_id, e
                    )
                    return False
                    
        except WebSocketDisconnect:
            logger.log_connection_event("disconnected_during_send", user_id, room_id)
            return False
        except Exception as e:
            logger.log_error(
                ErrorCode.MESSAGE_PROCESSING_ERROR,
                f"Failed to send message: {str(e)}",
                user_id, room_id, e
            )
            return False
    
    async def broadcast_to_room(self, room_id: str, message: MessageType, exclude_user: Optional[str] = None, send_confirmation: bool = False) -> int:
        """
        Broadcast a message to all connections in a room with enhanced error handling
        
        Args:
            room_id: The room to broadcast to
            message: The message to broadcast
            exclude_user: Optional user ID to exclude from broadcast
            send_confirmation: Whether to send delivery confirmation back to sender
            
        Returns:
            Number of connections the message was successfully sent to
        """
        room = self.room_manager.get_room(room_id)
        if not room:
            logger.log_error(
                ErrorCode.ROOM_NOT_FOUND,
                f"Attempted to broadcast to non-existent room: {room_id}",
                room_id=room_id
            )
            return 0
        
        room = self.room_manager.get_room(room_id)
        connections = room.get_all_connections()
        successful_sends = 0
        failed_connections = []
        
        # Log broadcast attempt
        message_type = message.type if hasattr(message, 'type') else "unknown"
        logger.log_message_event("broadcast_started", exclude_user, room_id, message_type, {
            "target_connections": len(connections),
            "excluded_user": exclude_user
        })
        
        for user_id, connection in connections.items():
            # Skip excluded user
            if exclude_user and user_id == exclude_user:
                continue
            
            try:
                success = await self.send_message(connection.websocket, message)
                if success:
                    successful_sends += 1
                    connection.update_activity()
                else:
                    # Mark connection for cleanup
                    failed_connections.append(connection.websocket)
                    logger.log_warning(
                        f"Failed to send message to user {user_id}",
                        user_id, room_id
                    )
            except Exception as e:
                logger.log_error(
                    ErrorCode.MESSAGE_PROCESSING_ERROR,
                    f"Error broadcasting to user {user_id}: {str(e)}",
                    user_id, room_id, e
                )
                failed_connections.append(connection.websocket)
        
        # Send delivery confirmation back to sender if requested and message has ID
        if send_confirmation and hasattr(message, 'id') and hasattr(message, 'user_id') and exclude_user:
            sender_connection = None
            for user_id, connection in connections.items():
                if user_id == exclude_user:
                    sender_connection = connection
                    break
            
            if sender_connection:
                confirmation_status = "delivered" if successful_sends > 0 else "failed"
                confirmation = MessageDeliveryConfirmation(
                    message_id=message.id,
                    status=confirmation_status,
                    user_id=message.user_id,
                    room_id=room_id
                )
                try:
                    await self.send_message(sender_connection.websocket, confirmation)
                except Exception as e:
                    logger.log_error(
                        ErrorCode.MESSAGE_PROCESSING_ERROR,
                        f"Failed to send delivery confirmation: {str(e)}",
                        exclude_user, room_id, e
                    )
        
        # Clean up failed connections (don't broadcast leave messages during cleanup)
        cleanup_count = 0
        for failed_ws in failed_connections:
            try:
                await self.disconnect(failed_ws, broadcast_leave=False)
                cleanup_count += 1
            except Exception as e:
                logger.log_error(
                    ErrorCode.CONNECTION_FAILED,
                    f"Failed to cleanup failed connection: {str(e)}",
                    room_id=room_id, exception=e
                )
        
        # Update room activity and increment message count for text/voice messages
        try:
            room.update_activity()
            if hasattr(message, 'type') and message.type in ['text', 'voice']:
                room.increment_message_count()
        except Exception as e:
            logger.log_error(
                ErrorCode.INTERNAL_SERVER_ERROR,
                f"Failed to update room activity: {str(e)}",
                room_id=room_id, exception=e
            )
        
        # Log broadcast completion
        logger.log_message_event("broadcast_completed", exclude_user, room_id, message_type, {
            "successful_sends": successful_sends,
            "failed_connections": len(failed_connections),
            "cleaned_up_connections": cleanup_count
        })
        
        return successful_sends
    
    async def send_error(self, websocket: WebSocket, error_code: str, error_message: str) -> bool:
        """
        Send an error message to a specific connection
        
        Args:
            websocket: The target WebSocket connection
            error_code: Error code identifier
            error_message: Human-readable error message
            
        Returns:
            True if error was sent successfully, False otherwise
        """
        error_msg = ErrorMessage(
            error_code=error_code,
            message=error_message
        )
        return await self.send_message(websocket, error_msg)
    
    def get_connection_info(self, websocket: WebSocket) -> Optional[ConnectionInfo]:
        """
        Get connection info for a WebSocket
        
        Args:
            websocket: The WebSocket connection
            
        Returns:
            ConnectionInfo if found, None otherwise
        """
        return self.connection_lookup.get(websocket)
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """
        Get room by ID
        
        Args:
            room_id: The room ID
            
        Returns:
            Room object if found, None otherwise
        """
        return self.room_manager.get_room(room_id)
    
    def get_room_connection_count(self, room_id: str) -> int:
        """
        Get the number of active connections in a room
        
        Args:
            room_id: The room ID
            
        Returns:
            Number of active connections, 0 if room doesn't exist
        """
        room = self.room_manager.get_room(room_id)
        return room.get_connection_count() if room else 0
    
    def get_active_rooms(self) -> List[str]:
        """
        Get list of active room IDs
        
        Returns:
            List of room IDs that have active connections
        """
        return self.room_manager.get_active_rooms()
    
    def get_total_connections(self) -> int:
        """
        Get total number of active connections across all rooms
        
        Returns:
            Total number of active connections
        """
        return len(self.connection_lookup)
    
    async def cleanup_expired_typing(self):
        """
        Clean up expired typing indicators across all rooms
        """
        for room in self.room_manager.rooms.values():
            room.cleanup_expired_typing()
    
    def get_room_stats(self, room_id: str) -> Optional[Dict]:
        """
        Get statistics for a specific room
        
        Args:
            room_id: The room ID
            
        Returns:
            Dictionary with room statistics, None if room doesn't exist
        """
        room = self.room_manager.get_room(room_id)
        if not room:
            return None
        
        return {
            'room_id': room_id,
            'connection_count': room.get_connection_count(),
            'message_count': room.message_count,
            'created_at': room.created_at.isoformat(),
            'last_activity': room.last_activity.isoformat(),
            'typing_users': list(room.get_typing_users())
        }