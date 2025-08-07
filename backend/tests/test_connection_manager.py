import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from fastapi import WebSocket

from app.services.connection_manager import ConnectionManager
from app.services.room_manager import RoomManager
from app.models import TextMessage, TypingMessage, ErrorMessage


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.accept = AsyncMock()
        self.close = AsyncMock()
        self.messages_sent = []
    
    async def send_text(self, data: str):
        self.messages_sent.append(data)


@pytest.fixture
def room_manager():
    """Create a mock RoomManager for testing"""
    return RoomManager()


@pytest.fixture
def connection_manager(room_manager):
    """Create a fresh ConnectionManager for each test"""
    from app.services.rate_limiter import RateLimiter, RateLimitConfig
    rate_limiter = RateLimiter(RateLimitConfig())
    return ConnectionManager(room_manager, rate_limiter)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing"""
    return MockWebSocket()


@pytest.mark.asyncio
async def test_connect_new_user(connection_manager, mock_websocket):
    """Test connecting a new user to a room"""
    room_id = "test-room-123"
    
    # Connect user
    connection = await connection_manager.connect(mock_websocket, room_id)
    
    # Verify connection was created
    assert connection.room_id == room_id
    assert connection.user_id.startswith("user_")
    assert connection.websocket == mock_websocket
    
    # Verify room was created
    assert room_id in connection_manager.room_manager.rooms
    room = connection_manager.get_room(room_id)
    assert room.get_connection_count() == 1
    
    # Verify WebSocket was accepted
    mock_websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_connect_multiple_users(connection_manager):
    """Test connecting multiple users to the same room"""
    room_id = "test-room-123"
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    # Connect first user
    conn1 = await connection_manager.connect(ws1, room_id, "user1")
    
    # Connect second user
    conn2 = await connection_manager.connect(ws2, room_id, "user2")
    
    # Verify both connections exist
    room = connection_manager.get_room(room_id)
    assert room.get_connection_count() == 2
    assert room.get_connection("user1") == conn1
    assert room.get_connection("user2") == conn2


@pytest.mark.asyncio
async def test_disconnect_user(connection_manager):
    """Test disconnecting a user"""
    room_id = "test-room-123"
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    # Connect two users
    await connection_manager.connect(ws1, room_id, "user1")
    await connection_manager.connect(ws2, room_id, "user2")
    
    # Disconnect first user
    disconnected = await connection_manager.disconnect(ws1)
    
    # Verify disconnection
    assert disconnected.user_id == "user1"
    room = connection_manager.get_room(room_id)
    assert room.get_connection_count() == 1
    assert room.get_connection("user1") is None
    assert room.get_connection("user2") is not None


@pytest.mark.asyncio
async def test_disconnect_last_user_deletes_room(connection_manager):
    """Test that disconnecting the last user deletes the room"""
    room_id = "test-room-123"
    ws = MockWebSocket()
    
    # Connect user
    await connection_manager.connect(ws, room_id, "user1")
    assert room_id in connection_manager.room_manager.rooms
    
    # Disconnect user
    await connection_manager.disconnect(ws)
    
    # Verify room was deleted
    assert room_id not in connection_manager.room_manager.rooms


@pytest.mark.asyncio
async def test_send_message(connection_manager):
    """Test sending a message to a specific connection"""
    room_id = "test-room-123"
    ws = MockWebSocket()
    
    # Connect user
    await connection_manager.connect(ws, room_id, "user1")
    
    # Send message
    message = TextMessage(user_id="user1", room_id=room_id, content="Hello!")
    success = await connection_manager.send_message(ws, message)
    
    # Verify message was sent
    assert success is True
    assert len(ws.messages_sent) == 1


@pytest.mark.asyncio
async def test_broadcast_to_room(connection_manager):
    """Test broadcasting a message to all users in a room"""
    room_id = "test-room-123"
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()
    
    # Connect users to same room
    await connection_manager.connect(ws1, room_id, "user1")
    await connection_manager.connect(ws2, room_id, "user2")
    
    # Connect user to different room
    await connection_manager.connect(ws3, "other-room-456", "user3")
    
    # Broadcast message to test_room_123
    message = TextMessage(user_id="user1", room_id=room_id, content="Hello everyone!")
    sent_count = await connection_manager.broadcast_to_room(room_id, message)
    
    # Verify message was sent to users in the room
    assert sent_count == 2
    assert len(ws1.messages_sent) >= 1
    assert len(ws2.messages_sent) >= 1
    assert len(ws3.messages_sent) == 0  # Different room


@pytest.mark.asyncio
async def test_broadcast_exclude_user(connection_manager):
    """Test broadcasting with user exclusion"""
    room_id = "test-room-123"
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    # Connect users
    await connection_manager.connect(ws1, room_id, "user1")
    await connection_manager.connect(ws2, room_id, "user2")
    
    # Broadcast excluding user1
    message = TextMessage(user_id="user1", room_id=room_id, content="Hello!")
    sent_count = await connection_manager.broadcast_to_room(room_id, message, exclude_user="user1")
    
    # Verify only user2 received the broadcast
    assert sent_count == 1


@pytest.mark.asyncio
async def test_send_error(connection_manager):
    """Test sending error messages"""
    room_id = "test-room-123"
    ws = MockWebSocket()
    
    # Connect user
    await connection_manager.connect(ws, room_id, "user1")
    
    # Send error
    success = await connection_manager.send_error(ws, "INVALID_MESSAGE", "Message format is invalid")
    
    # Verify error was sent
    assert success is True
    assert len(ws.messages_sent) == 1


def test_get_connection_info(connection_manager):
    """Test getting connection info"""
    # Test with non-existent connection
    ws = MockWebSocket()
    assert connection_manager.get_connection_info(ws) is None


def test_get_room_stats(connection_manager):
    """Test getting room statistics"""
    # Test with non-existent room
    stats = connection_manager.get_room_stats("non-existent-room")
    assert stats is None


@pytest.mark.asyncio
async def test_get_room_stats_with_data(connection_manager):
    """Test getting room statistics with actual data"""
    room_id = "test-room-123"
    ws = MockWebSocket()
    
    # Connect user
    await connection_manager.connect(ws, room_id, "user1")
    
    # Get stats
    stats = connection_manager.get_room_stats(room_id)
    
    # Verify stats
    assert stats is not None
    assert stats['room_id'] == room_id
    assert stats['connection_count'] == 1
    assert stats['message_count'] == 0
    assert 'created_at' in stats
    assert 'last_activity' in stats


def test_get_active_rooms(connection_manager):
    """Test getting list of active rooms"""
    # Initially no rooms
    assert connection_manager.get_active_rooms() == []


def test_get_total_connections(connection_manager):
    """Test getting total connection count"""
    # Initially no connections
    assert connection_manager.get_total_connections() == 0


@pytest.mark.asyncio
async def test_get_total_connections_with_data(connection_manager):
    """Test getting total connection count with actual connections"""
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    # Connect users to different rooms
    await connection_manager.connect(ws1, "test-room-1", "user1")
    await connection_manager.connect(ws2, "test-room-2", "user2")
    
    # Verify total count
    assert connection_manager.get_total_connections() == 2
    assert len(connection_manager.get_active_rooms()) == 2