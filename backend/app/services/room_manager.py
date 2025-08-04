import asyncio
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import re
import secrets
import string

from ..models import Room, validate_room_id, generate_room_id

logger = logging.getLogger(__name__)


class RoomManager:
    """Manages chat room lifecycle, creation, validation, and cleanup"""
    
    def __init__(self, cleanup_timeout_minutes: int = 30):
        """
        Initialize RoomManager
        
        Args:
            cleanup_timeout_minutes: Minutes of inactivity before room cleanup
        """
        self.rooms: Dict[str, Room] = {}
        self.cleanup_timeout = timedelta(minutes=cleanup_timeout_minutes)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    def create_room(self, room_id: Optional[str] = None) -> Room:
        """
        Create a new chat room
        
        Args:
            room_id: Optional custom room ID, will generate one if not provided
            
        Returns:
            Room object for the created room
            
        Raises:
            ValueError: If room_id is invalid or already exists
        """
        if room_id is None:
            room_id = self._generate_unique_room_id()
        else:
            if not self.validate_room_id(room_id):
                raise ValueError(f"Invalid room ID format: {room_id}")
            
            if room_id in self.rooms:
                raise ValueError(f"Room {room_id} already exists")
        
        room = Room(room_id=room_id)
        self.rooms[room_id] = room
        
        logger.info(f"Created room {room_id}")
        return room
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """
        Get a room by ID
        
        Args:
            room_id: The room ID to look up
            
        Returns:
            Room object if found, None otherwise
        """
        return self.rooms.get(room_id)
    
    def get_or_create_room(self, room_id: str) -> Room:
        """
        Get an existing room or create it if it doesn't exist
        
        Args:
            room_id: The room ID
            
        Returns:
            Room object (existing or newly created)
            
        Raises:
            ValueError: If room_id format is invalid
        """
        if not self.validate_room_id(room_id):
            raise ValueError(f"Invalid room ID format: {room_id}")
        
        room = self.get_room(room_id)
        if room is None:
            room = self.create_room(room_id)
        
        return room
    
    def delete_room(self, room_id: str) -> bool:
        """
        Delete a room
        
        Args:
            room_id: The room ID to delete
            
        Returns:
            True if room was deleted, False if room didn't exist
        """
        room = self.rooms.pop(room_id, None)
        if room:
            logger.info(f"Deleted room {room_id}")
            return True
        return False
    
    def validate_room_id(self, room_id: str) -> bool:
        """
        Validate room ID format and security
        
        Args:
            room_id: The room ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not room_id:
            return False
        
        # Check length (6-32 characters)
        if len(room_id) < 6 or len(room_id) > 32:
            return False
        
        # Check for URL-safe characters only (alphanumeric, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9_-]+$', room_id):
            return False
        
        # Prevent common problematic patterns
        problematic_patterns = [
            r'^-+$',  # Only hyphens
            r'^_+$',  # Only underscores
            r'^\d+$',  # Only numbers (could conflict with other systems)
        ]
        
        for pattern in problematic_patterns:
            if re.match(pattern, room_id):
                return False
        
        return True
    
    def _generate_unique_room_id(self, max_attempts: int = 10) -> str:
        """
        Generate a unique room ID that doesn't conflict with existing rooms
        
        Args:
            max_attempts: Maximum attempts to generate unique ID
            
        Returns:
            Unique room ID
            
        Raises:
            RuntimeError: If unable to generate unique ID after max_attempts
        """
        for _ in range(max_attempts):
            room_id = self._generate_secure_room_id()
            if room_id not in self.rooms:
                return room_id
        
        raise RuntimeError(f"Unable to generate unique room ID after {max_attempts} attempts")
    
    def _generate_secure_room_id(self) -> str:
        """
        Generate a cryptographically secure room ID
        
        Returns:
            Secure room ID string
        """
        # Use a mix of letters and numbers for better readability
        alphabet = string.ascii_lowercase + string.digits
        # Generate 12 character ID for good collision resistance
        return ''.join(secrets.choice(alphabet) for _ in range(12))
    
    def get_active_rooms(self) -> List[str]:
        """
        Get list of active room IDs (rooms with connections)
        
        Returns:
            List of room IDs that have active connections
        """
        return [room_id for room_id, room in self.rooms.items() if not room.is_empty()]
    
    def get_inactive_rooms(self) -> List[str]:
        """
        Get list of inactive room IDs (rooms without connections)
        
        Returns:
            List of room IDs that have no active connections
        """
        return [room_id for room_id, room in self.rooms.items() if room.is_empty()]
    
    def get_rooms_for_cleanup(self) -> List[str]:
        """
        Get list of room IDs that are eligible for cleanup
        
        Returns:
            List of room IDs that should be cleaned up
        """
        cutoff_time = datetime.utcnow() - self.cleanup_timeout
        cleanup_rooms = []
        
        for room_id, room in self.rooms.items():
            if room.is_empty() and room.last_activity < cutoff_time:
                cleanup_rooms.append(room_id)
        
        return cleanup_rooms
    
    def cleanup_inactive_rooms(self) -> int:
        """
        Clean up rooms that have been inactive for too long
        
        Returns:
            Number of rooms cleaned up
        """
        rooms_to_cleanup = self.get_rooms_for_cleanup()
        
        for room_id in rooms_to_cleanup:
            self.delete_room(room_id)
        
        if rooms_to_cleanup:
            logger.info(f"Cleaned up {len(rooms_to_cleanup)} inactive rooms")
        
        return len(rooms_to_cleanup)
    
    async def start_cleanup_task(self, cleanup_interval_minutes: int = 10):
        """
        Start the automatic cleanup task
        
        Args:
            cleanup_interval_minutes: How often to run cleanup (in minutes)
        """
        if self._running:
            logger.warning("Cleanup task is already running")
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(
            self._cleanup_loop(cleanup_interval_minutes)
        )
        logger.info(f"Started room cleanup task (interval: {cleanup_interval_minutes} minutes)")
    
    async def stop_cleanup_task(self):
        """Stop the automatic cleanup task"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        logger.info("Stopped room cleanup task")
    
    async def _cleanup_loop(self, interval_minutes: int):
        """
        Background task that periodically cleans up inactive rooms
        
        Args:
            interval_minutes: Cleanup interval in minutes
        """
        interval_seconds = interval_minutes * 60
        
        while self._running:
            try:
                await asyncio.sleep(interval_seconds)
                if self._running:  # Check again after sleep
                    self.cleanup_inactive_rooms()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                # Continue running despite errors
    
    def get_room_stats(self) -> Dict:
        """
        Get overall room statistics
        
        Returns:
            Dictionary with room statistics
        """
        total_rooms = len(self.rooms)
        active_rooms = len(self.get_active_rooms())
        inactive_rooms = len(self.get_inactive_rooms())
        cleanup_eligible = len(self.get_rooms_for_cleanup())
        
        return {
            'total_rooms': total_rooms,
            'active_rooms': active_rooms,
            'inactive_rooms': inactive_rooms,
            'cleanup_eligible': cleanup_eligible,
            'cleanup_timeout_minutes': self.cleanup_timeout.total_seconds() / 60
        }
    
    def get_detailed_room_info(self, room_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific room
        
        Args:
            room_id: The room ID
            
        Returns:
            Dictionary with detailed room information, None if room doesn't exist
        """
        room = self.get_room(room_id)
        if not room:
            return None
        
        return {
            'room_id': room_id,
            'created_at': room.created_at.isoformat(),
            'last_activity': room.last_activity.isoformat(),
            'connection_count': room.get_connection_count(),
            'message_count': room.message_count,
            'is_empty': room.is_empty(),
            'typing_users': list(room.get_typing_users()),
            'time_since_last_activity': (datetime.utcnow() - room.last_activity).total_seconds(),
            'eligible_for_cleanup': room_id in self.get_rooms_for_cleanup()
        }