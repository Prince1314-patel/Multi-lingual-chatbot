import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.room_manager import RoomManager
from app.models import Room


@pytest.fixture
def room_manager():
    """Create a fresh RoomManager for each test"""
    return RoomManager(cleanup_timeout_minutes=30)


def test_create_room_with_generated_id(room_manager):
    """Test creating a room with auto-generated ID"""
    room = room_manager.create_room()
    
    assert room.room_id is not None
    assert len(room.room_id) == 12
    assert room.room_id in room_manager.rooms
    assert room_manager.get_room(room.room_id) == room


def test_create_room_with_custom_id(room_manager):
    """Test creating a room with custom ID"""
    custom_id = "my-custom-room-123"
    room = room_manager.create_room(custom_id)
    
    assert room.room_id == custom_id
    assert room_manager.get_room(custom_id) == room


def test_create_room_duplicate_id_fails(room_manager):
    """Test that creating a room with duplicate ID fails"""
    room_id = "test-room-123"
    room_manager.create_room(room_id)
    
    with pytest.raises(ValueError, match="already exists"):
        room_manager.create_room(room_id)


def test_create_room_invalid_id_fails(room_manager):
    """Test that creating a room with invalid ID fails"""
    invalid_ids = [
        "",  # Empty
        "ab",  # Too short
        "a" * 33,  # Too long
        "room with spaces",  # Spaces
        "room@invalid",  # Special characters
        "---",  # Only hyphens
        "___",  # Only underscores
        "12345",  # Only numbers (too short anyway)
    ]
    
    for invalid_id in invalid_ids:
        with pytest.raises(ValueError, match="Invalid room ID format"):
            room_manager.create_room(invalid_id)


def test_validate_room_id(room_manager):
    """Test room ID validation logic"""
    # Valid IDs
    valid_ids = [
        "room123",
        "my-room-456",
        "test_room_789",
        "Room-With-Mixed_Case123",
        "a1b2c3d4e5f6",  # 12 chars
        "abcdef" * 5 + "ab",  # 32 chars (max length)
    ]
    
    for valid_id in valid_ids:
        assert room_manager.validate_room_id(valid_id), f"Should be valid: {valid_id}"
    
    # Invalid IDs
    invalid_ids = [
        "",  # Empty
        "short",  # Too short (5 chars)
        "a" * 33,  # Too long
        "room with spaces",  # Spaces
        "room@invalid",  # Special characters
        "room.invalid",  # Dots
        "room/invalid",  # Slashes
        "---",  # Only hyphens
        "___",  # Only underscores
        "123456",  # Only numbers
    ]
    
    for invalid_id in invalid_ids:
        assert not room_manager.validate_room_id(invalid_id), f"Should be invalid: {invalid_id}"


def test_get_room(room_manager):
    """Test getting rooms by ID"""
    # Non-existent room
    assert room_manager.get_room("non-existent") is None
    
    # Existing room
    room_id = "test-room-123"
    created_room = room_manager.create_room(room_id)
    retrieved_room = room_manager.get_room(room_id)
    
    assert retrieved_room == created_room


def test_get_or_create_room(room_manager):
    """Test get or create room functionality"""
    room_id = "test-room-123"
    
    # First call should create the room
    room1 = room_manager.get_or_create_room(room_id)
    assert room1.room_id == room_id
    assert room_id in room_manager.rooms
    
    # Second call should return existing room
    room2 = room_manager.get_or_create_room(room_id)
    assert room2 == room1


def test_get_or_create_room_invalid_id_fails(room_manager):
    """Test that get_or_create with invalid ID fails"""
    with pytest.raises(ValueError, match="Invalid room ID format"):
        room_manager.get_or_create_room("invalid id with spaces")


def test_delete_room(room_manager):
    """Test deleting rooms"""
    room_id = "test-room-123"
    room_manager.create_room(room_id)
    
    # Room should exist
    assert room_manager.get_room(room_id) is not None
    
    # Delete should succeed
    assert room_manager.delete_room(room_id) is True
    assert room_manager.get_room(room_id) is None
    
    # Delete non-existent room should return False
    assert room_manager.delete_room(room_id) is False


def test_get_active_and_inactive_rooms(room_manager):
    """Test getting active and inactive room lists"""
    # Create rooms
    room1 = room_manager.create_room("room123")
    room2 = room_manager.create_room("room456")
    room3 = room_manager.create_room("room789")
    
    # Initially all rooms are inactive (empty)
    assert len(room_manager.get_active_rooms()) == 0
    assert len(room_manager.get_inactive_rooms()) == 3
    
    # Mock some rooms as having connections
    room1.connections = {'user1': 'mock_connection'}
    room2.connections = {'user2': 'mock_connection'}
    
    # Now we should have 2 active, 1 inactive
    active_rooms = room_manager.get_active_rooms()
    inactive_rooms = room_manager.get_inactive_rooms()
    
    assert len(active_rooms) == 2
    assert len(inactive_rooms) == 1
    assert "room123" in active_rooms
    assert "room456" in active_rooms
    assert "room789" in inactive_rooms


def test_get_rooms_for_cleanup(room_manager):
    """Test getting rooms eligible for cleanup"""
    # Create rooms with different activity times
    room1 = room_manager.create_room("room123")
    room2 = room_manager.create_room("room456")
    room3 = room_manager.create_room("room789")
    
    # Set different last activity times
    old_time = datetime.utcnow() - timedelta(hours=2)  # 2 hours ago
    recent_time = datetime.utcnow() - timedelta(minutes=5)  # 5 minutes ago
    
    room1.last_activity = old_time  # Eligible for cleanup
    room2.last_activity = recent_time  # Not eligible
    room3.last_activity = old_time  # Eligible for cleanup
    
    # Mock room2 as having connections (should not be eligible even if old)
    room2.connections = {'user1': 'mock_connection'}
    
    cleanup_rooms = room_manager.get_rooms_for_cleanup()
    
    # Only room1 and room3 should be eligible (empty and old)
    assert len(cleanup_rooms) == 2
    assert "room123" in cleanup_rooms
    assert "room789" in cleanup_rooms
    assert "room456" not in cleanup_rooms


def test_cleanup_inactive_rooms(room_manager):
    """Test cleaning up inactive rooms"""
    # Create rooms
    room1 = room_manager.create_room("room123")
    room2 = room_manager.create_room("room456")
    
    # Set old activity time
    old_time = datetime.utcnow() - timedelta(hours=2)
    room1.last_activity = old_time
    room2.last_activity = old_time
    
    # Mock room2 as having connections
    room2.connections = {'user1': 'mock_connection'}
    
    # Run cleanup
    cleaned_count = room_manager.cleanup_inactive_rooms()
    
    # Only room1 should be cleaned up
    assert cleaned_count == 1
    assert room_manager.get_room("room123") is None
    assert room_manager.get_room("room456") is not None


@pytest.mark.asyncio
async def test_cleanup_task_lifecycle(room_manager):
    """Test starting and stopping the cleanup task"""
    # Start cleanup task
    await room_manager.start_cleanup_task(cleanup_interval_minutes=1)
    assert room_manager._running is True
    assert room_manager._cleanup_task is not None
    
    # Stop cleanup task
    await room_manager.stop_cleanup_task()
    assert room_manager._running is False
    assert room_manager._cleanup_task is None


@pytest.mark.asyncio
async def test_cleanup_task_already_running_warning(room_manager):
    """Test that starting cleanup task when already running shows warning"""
    await room_manager.start_cleanup_task(cleanup_interval_minutes=1)
    
    # Try to start again - should not create new task
    original_task = room_manager._cleanup_task
    await room_manager.start_cleanup_task(cleanup_interval_minutes=1)
    assert room_manager._cleanup_task == original_task
    
    await room_manager.stop_cleanup_task()


def test_get_room_stats(room_manager):
    """Test getting room statistics"""
    # Initially no rooms
    stats = room_manager.get_room_stats()
    assert stats['total_rooms'] == 0
    assert stats['active_rooms'] == 0
    assert stats['inactive_rooms'] == 0
    assert stats['cleanup_eligible'] == 0
    assert stats['cleanup_timeout_minutes'] == 30
    
    # Create some rooms
    room1 = room_manager.create_room("room123")
    room2 = room_manager.create_room("room456")
    
    # Mock one as active
    room1.connections = {'user1': 'mock_connection'}
    
    # Set one as eligible for cleanup
    room2.last_activity = datetime.utcnow() - timedelta(hours=2)
    
    stats = room_manager.get_room_stats()
    assert stats['total_rooms'] == 2
    assert stats['active_rooms'] == 1
    assert stats['inactive_rooms'] == 1
    assert stats['cleanup_eligible'] == 1


def test_get_detailed_room_info(room_manager):
    """Test getting detailed room information"""
    # Non-existent room
    assert room_manager.get_detailed_room_info("non-existent") is None
    
    # Create room
    room_id = "test-room-123"
    room = room_manager.create_room(room_id)
    
    # Get detailed info
    info = room_manager.get_detailed_room_info(room_id)
    
    assert info is not None
    assert info['room_id'] == room_id
    assert 'created_at' in info
    assert 'last_activity' in info
    assert info['connection_count'] == 0
    assert info['message_count'] == 0
    assert info['is_empty'] is True
    assert info['typing_users'] == []
    assert 'time_since_last_activity' in info
    assert 'eligible_for_cleanup' in info


def test_generate_unique_room_id_collision_handling(room_manager):
    """Test that room ID generation handles collisions"""
    # Mock the secure ID generator to return predictable values
    with patch.object(room_manager, '_generate_secure_room_id') as mock_gen:
        mock_gen.side_effect = ['collision', 'collision', 'unique123']
        
        # Create a room with the collision ID
        room_manager.create_room('collision')
        
        # Generate new room should skip collision and use unique123
        room = room_manager.create_room()
        assert room.room_id == 'unique123'


def test_generate_unique_room_id_max_attempts_exceeded():
    """Test that room ID generation fails after max attempts"""
    room_manager = RoomManager()
    
    with patch.object(room_manager, '_generate_secure_room_id') as mock_gen:
        mock_gen.return_value = 'collision'
        
        # Create a room with the collision ID
        room_manager.create_room('collision')
        
        # Try to generate new room should fail after max attempts
        with pytest.raises(RuntimeError, match="Unable to generate unique room ID"):
            room_manager._generate_unique_room_id(max_attempts=3)


def test_secure_room_id_generation(room_manager):
    """Test that secure room ID generation produces valid IDs"""
    for _ in range(100):  # Test multiple generations
        room_id = room_manager._generate_secure_room_id()
        assert len(room_id) == 12
        assert room_manager.validate_room_id(room_id)
        # Should only contain lowercase letters and digits
        assert all(c.islower() or c.isdigit() for c in room_id)