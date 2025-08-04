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
    generate_user_id
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        # Dictionary mapping room_id -> Room objects
        self.rooms: Dict[str, Room] = {}
        # Dictionary mapping websocket -> ConnectionInfo for quick lookup
        self.connection_lookup: Dict[WebSocket, ConnectionInfo] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str, user_id: Optional[str] = None) -> ConnectionInfo:
        """
        Accept a WebSocket connection and add it to a room
        
        Args:
            websocket: The WebSocket connection
            room_id: The room to join
            user_id: Optional user ID, will generate one if not provided
            
        Returns:
            ConnectionInfo object for the new connection
        """
        await websocket.accept()
        
        # Generate user ID if not provided
        if not user_id:
            user_id = generate_user_id()
        
        # Create connection info
        connection = ConnectionInfo(
            websocket=websocket,
            user_id=user_id,
            room_id=room_id
        )
        
        # Create room if it doesn't exist
        if room_id not in self.rooms:
            self.rooms[room_id] = Room(room_id=room_id)
        
        # Add connection to room and lookup table
        self.rooms[room_id].add_connection(connection)
        self.connection_lookup[websocket] = connection
        
        logger.info(f"User {user_id} connected to room {room_id}")
        
        # Broadcast user join message to other users in the room
        join_message = UserJoinMessage(
            user_id=user_id,
            room_id=room_id
        )
        await self.broadcast_to_room(room_id, join_message, exclude_user=user_id)
        
        return connection
    
    async def disconnect(self, websocket: WebSocket, broadcast_leave: bool = True) -> Optional[ConnectionInfo]:
        """
        Handle WebSocket disconnection and cleanup
        
        Args:
            websocket: The WebSocket connection to disconnect
            broadcast_leave: Whether to broadcast leave message (False during cleanup)
            
        Returns:
            ConnectionInfo of the disconnected user, or None if not found
        """
        connection = self.connection_lookup.pop(websocket, None)
        if not connection:
            return None
        
        room_id = connection.room_id
        user_id = connection.user_id
        
        # Remove connection from room
        if room_id in self.rooms:
            self.rooms[room_id].remove_connection(user_id)
            
            # Broadcast user leave message to remaining users (if requested)
            if broadcast_leave and not self.rooms[room_id].is_empty():
                leave_message = UserLeaveMessage(
                    user_id=user_id,
                    room_id=room_id
                )
                await self.broadcast_to_room(room_id, leave_message)
            
            # Clean up empty room
            if self.rooms[room_id].is_empty():
                del self.rooms[room_id]
                logger.info(f"Room {room_id} deleted (empty)")
        
        logger.info(f"User {user_id} disconnected from room {room_id}")
        return connection
    
    async def send_message(self, websocket: WebSocket, message: MessageType) -> bool:
        """
        Send a message to a specific WebSocket connection
        
        Args:
            websocket: The target WebSocket connection
            message: The message to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            # Handle VoiceMessage with binary data specially
            if isinstance(message, VoiceMessage) and message.audio_data:
                # Send binary audio data directly
                await websocket.send_bytes(message.audio_data)
                return True
            else:
                # Send as JSON text message
                serialized = serialize_message(message)
                # Handle datetime serialization manually
                json_str = json.dumps(serialized, default=str)
                await websocket.send_text(json_str)
                return True
        except Exception as e:
            logger.error(f"Failed to send message to websocket: {e}")
            return False
    
    async def broadcast_to_room(self, room_id: str, message: MessageType, exclude_user: Optional[str] = None) -> int:
        """
        Broadcast a message to all connections in a room
        
        Args:
            room_id: The room to broadcast to
            message: The message to broadcast
            exclude_user: Optional user ID to exclude from broadcast
            
        Returns:
            Number of connections the message was successfully sent to
        """
        if room_id not in self.rooms:
            logger.warning(f"Attempted to broadcast to non-existent room: {room_id}")
            return 0
        
        room = self.rooms[room_id]
        connections = room.get_all_connections()
        successful_sends = 0
        failed_connections = []
        
        for user_id, connection in connections.items():
            # Skip excluded user
            if exclude_user and user_id == exclude_user:
                continue
            
            success = await self.send_message(connection.websocket, message)
            if success:
                successful_sends += 1
                connection.update_activity()
            else:
                # Mark connection for cleanup
                failed_connections.append(connection.websocket)
        
        # Clean up failed connections (don't broadcast leave messages during cleanup)
        for failed_ws in failed_connections:
            await self.disconnect(failed_ws, broadcast_leave=False)
        
        # Update room activity if message was sent successfully
        if successful_sends > 0:
            room.update_activity()
            if hasattr(message, 'type') and message.type in ['text', 'voice']:
                room.increment_message_count()
        
        logger.debug(f"Broadcasted message to {successful_sends} connections in room {room_id}")
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
        return self.rooms.get(room_id)
    
    def get_room_connection_count(self, room_id: str) -> int:
        """
        Get the number of active connections in a room
        
        Args:
            room_id: The room ID
            
        Returns:
            Number of active connections, 0 if room doesn't exist
        """
        room = self.rooms.get(room_id)
        return room.get_connection_count() if room else 0
    
    def get_active_rooms(self) -> List[str]:
        """
        Get list of active room IDs
        
        Returns:
            List of room IDs that have active connections
        """
        return [room_id for room_id, room in self.rooms.items() if not room.is_empty()]
    
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
        for room in self.rooms.values():
            room.cleanup_expired_typing()
    
    def get_room_stats(self, room_id: str) -> Optional[Dict]:
        """
        Get statistics for a specific room
        
        Args:
            room_id: The room ID
            
        Returns:
            Dictionary with room statistics, None if room doesn't exist
        """
        room = self.rooms.get(room_id)
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