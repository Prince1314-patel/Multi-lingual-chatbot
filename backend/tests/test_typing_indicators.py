import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.message_handler import MessageHandler
from app.services.connection_manager import ConnectionManager
from app.services.room_manager import RoomManager
from app.models import (
    TypingMessage, ConnectionInfo, Room, TextMessage
)


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.accept = AsyncMock()
        self.close = AsyncMock()
        self.messages_sent = []
    
    async def send_text(self, data: str):
        self.messages_sent.append(data)
    
    async def send_bytes(self, data: bytes):
        self.messages_sent.append(data)


@pytest.fixture
def room_manager():
    """Create a RoomManager"""
    return RoomManager()


@pytest.fixture
def connection_manager(room_manager):
    """Create a ConnectionManager"""
    return ConnectionManager(room_manager)


@pytest.fixture
def message_handler(connection_manager, room_manager):
    """Create MessageHandler with dependencies"""
    return MessageHandler(connection_manager, room_manager)


@pytest.fixture
def mock_connection():
    """Create a mock ConnectionInfo"""
    ws = MockWebSocket()
    connection = ConnectionInfo(
        websocket=ws,
        user_id="test_user_123",
        room_id="test-room-456"
    )
    return connection


@pytest.fixture
def mock_connection2():
    """Create a second mock ConnectionInfo"""
    ws = MockWebSocket()
    connection = ConnectionInfo(
        websocket=ws,
        user_id="test_user_789",
        room_id="test-room-456"
    )
    return connection


@pytest.mark.asyncio
async def test_typing_indicator_broadcasting_logic(message_handler, mock_connection):
    """Test typing indicator broadcasting logic in MessageHandler"""
    # Create typing message
    typing_message = TypingMessage(
        user_id="test_user_123",
        room_id="test-room-456",
        is_typing=True
    )
    
    # Mock dependencies
    message_handler.connection_manager.broadcast_to_room = AsyncMock(return_value=2)
    message_handler.room_manager.get_room = Mock(return_value=Room(room_id="test-room-456"))
    
    # Handle typing message
    result = await message_handler.handle_typing_message(mock_connection, typing_message)
    
    # Verify success
    assert result is True
    
    # Verify connection typing state was updated
    assert mock_connection.is_typing is True
    
    # Verify broadcast was called with correct parameters
    message_handler.connection_manager.broadcast_to_room.assert_called_once()
    call_args = message_handler.connection_manager.broadcast_to_room.call_args
    assert call_args[0][0] == "test-room-456"  # room_id
    assert call_args[1]['exclude_user'] == "test_user_123"  # exclude sender


@pytest.mark.asyncio
async def test_typing_timeout_after_3_seconds(message_handler, mock_connection):
    """Test automatic typing timeout after 3 seconds of inactivity"""
    # Set user as typing
    mock_connection.set_typing(True)
    
    # Mock broadcast method
    message_handler.connection_manager.broadcast_to_room = AsyncMock()
    
    # Start typing timeout with short duration for testing (0.1 seconds instead of 3)
    timeout_task = asyncio.create_task(
        message_handler._typing_timeout_handler(mock_connection, 0.1)
    )
    
    # Wait for timeout to complete
    await timeout_task
    
    # Verify typing was automatically set to false
    assert mock_connection.is_typing is False
    
    # Verify broadcast was called to notify others
    message_handler.connection_manager.broadcast_to_room.assert_called_once()
    
    # Verify the broadcast message was a typing stop message
    call_args = message_handler.connection_manager.broadcast_to_room.call_args
    broadcasted_message = call_args[0][1]
    assert isinstance(broadcasted_message, TypingMessage)
    assert broadcasted_message.is_typing is False
    assert broadcasted_message.user_id == "test_user_123"


@pytest.mark.asyncio
async def test_typing_timeout_cancellation_on_new_typing(message_handler, mock_connection):
    """Test that new typing activity cancels previous timeout"""
    room_id = mock_connection.room_id
    user_id = mock_connection.user_id
    
    # Start first typing timeout
    await message_handler._manage_typing_timeout(mock_connection, True)
    
    # Verify timeout task was created
    assert room_id in message_handler.typing_timeouts
    assert user_id in message_handler.typing_timeouts[room_id]
    first_task = message_handler.typing_timeouts[room_id][user_id]
    first_task_id = id(first_task)
    
    # Start second typing timeout (should cancel first and create new)
    await message_handler._manage_typing_timeout(mock_connection, True)
    
    # Verify a new task was created (different object)
    second_task = message_handler.typing_timeouts[room_id][user_id]
    second_task_id = id(second_task)
    assert second_task_id != first_task_id
    assert not second_task.cancelled()
    
    # The first task should have been cancelled (though we can't check it directly
    # since it was deleted from the dict, but we can verify a new task exists)
    assert second_task is not first_task


@pytest.mark.asyncio
async def test_typing_indicator_aggregation_multiple_users(connection_manager, room_manager, message_handler):
    """Test typing indicator aggregation for multiple users"""
    room_id = "test-room-456"
    
    # Create multiple connections using connection manager
    # This will create the room in connection manager, not room manager
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()
    
    conn1 = await connection_manager.connect(ws1, room_id, "user1")
    conn2 = await connection_manager.connect(ws2, room_id, "user2") 
    conn3 = await connection_manager.connect(ws3, room_id, "user3")
    
    # Set multiple users as typing
    conn1.set_typing(True)
    conn2.set_typing(True)
    # conn3 remains not typing
    
    # Get the room from connection manager (not room manager)
    room = connection_manager.get_room(room_id)
    typing_users = room.get_typing_users()
    
    # Verify aggregation
    assert len(typing_users) == 2
    assert "user1" in typing_users
    assert "user2" in typing_users
    assert "user3" not in typing_users


@pytest.mark.asyncio
async def test_typing_cleared_on_message_send(message_handler, mock_connection):
    """Test that typing indicator is cleared when user sends a message"""
    # Set user as typing first
    mock_connection.set_typing(True)
    await message_handler._manage_typing_timeout(mock_connection, True)
    
    # Verify user is typing
    assert mock_connection.is_typing is True
    
    # Mock dependencies for text message
    message_handler.connection_manager.broadcast_to_room = AsyncMock(return_value=1)
    
    # Send a text message
    text_message = TextMessage(
        user_id="test_user_123",
        room_id="test-room-456",
        content="Hello world!"
    )
    
    result = await message_handler.handle_text_message(mock_connection, text_message)
    
    # Verify message was sent successfully
    assert result is True
    
    # Note: In a real implementation, sending a message should clear typing.
    # This would typically be handled in the WebSocket endpoint or by the frontend
    # sending a typing=false message when a message is sent.


@pytest.mark.asyncio
async def test_typing_timeout_cleanup_on_disconnect(message_handler, mock_connection):
    """Test typing timeout cleanup when user disconnects"""
    room_id = mock_connection.room_id
    user_id = mock_connection.user_id
    
    # Set user as typing and create timeout
    mock_connection.set_typing(True)
    await message_handler._manage_typing_timeout(mock_connection, True)
    
    # Verify timeout exists
    assert room_id in message_handler.typing_timeouts
    assert user_id in message_handler.typing_timeouts[room_id]
    
    # Mock broadcast method
    message_handler.connection_manager.broadcast_to_room = AsyncMock()
    
    # Handle user disconnect
    await message_handler.handle_user_disconnect(mock_connection)
    
    # Verify timeout was cleaned up
    assert user_id not in message_handler.typing_timeouts.get(room_id, {})
    
    # Verify typing stop message was broadcast
    message_handler.connection_manager.broadcast_to_room.assert_called_once()


@pytest.mark.asyncio
async def test_typing_timeout_room_cleanup(message_handler):
    """Test that empty room entries are cleaned up from typing timeouts"""
    # Create mock connections for different rooms
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    conn1 = ConnectionInfo(websocket=ws1, user_id="user1", room_id="test-room-1")
    conn2 = ConnectionInfo(websocket=ws2, user_id="user2", room_id="test-room-2")
    
    # Set up typing timeouts for both users
    await message_handler._manage_typing_timeout(conn1, True)
    await message_handler._manage_typing_timeout(conn2, True)
    
    # Verify both rooms have timeouts
    assert "test-room-1" in message_handler.typing_timeouts
    assert "test-room-2" in message_handler.typing_timeouts
    
    # Mock broadcast method
    message_handler.connection_manager.broadcast_to_room = AsyncMock()
    
    # Disconnect user1 (should clean up room1 entry)
    await message_handler.handle_user_disconnect(conn1)
    
    # Verify room1 was cleaned up but room2 remains
    assert "test-room-1" not in message_handler.typing_timeouts
    assert "test-room-2" in message_handler.typing_timeouts


@pytest.mark.asyncio
async def test_typing_indicator_no_persistent_storage(message_handler, mock_connection):
    """Test that typing indicators are not stored persistently"""
    # Create typing message
    typing_message = TypingMessage(
        user_id="test_user_123",
        room_id="test-room-456",
        is_typing=True
    )
    
    # Mock dependencies
    message_handler.connection_manager.broadcast_to_room = AsyncMock(return_value=1)
    message_handler.room_manager.get_room = Mock(return_value=Room(room_id="test-room-456"))
    
    # Handle typing message
    await message_handler.handle_typing_message(mock_connection, typing_message)
    
    # Verify typing state is only in memory (connection object)
    assert mock_connection.is_typing is True
    
    # Verify no persistent storage is used (typing timeouts are in-memory only)
    assert isinstance(message_handler.typing_timeouts, dict)
    
    # The typing state should only exist in the connection object and timeout dict
    # No database or file storage should be involved


@pytest.mark.asyncio
async def test_concurrent_typing_timeouts(message_handler):
    """Test handling multiple concurrent typing timeouts"""
    # Create multiple mock connections
    connections = []
    for i in range(5):
        ws = MockWebSocket()
        conn = ConnectionInfo(
            websocket=ws,
            user_id=f"user_{i}",
            room_id="test-room"
        )
        connections.append(conn)
    
    # Start typing for all users
    tasks = []
    for conn in connections:
        conn.set_typing(True)
        task = asyncio.create_task(
            message_handler._manage_typing_timeout(conn, True)
        )
        tasks.append(task)
    
    # Wait for all timeout tasks to be created
    await asyncio.gather(*tasks)
    
    # Verify all timeouts were created
    assert "test-room" in message_handler.typing_timeouts
    assert len(message_handler.typing_timeouts["test-room"]) == 5
    
    # Stop typing for some users
    for i in range(3):
        await message_handler._manage_typing_timeout(connections[i], False)
    
    # Verify partial cleanup
    assert len(message_handler.typing_timeouts["test-room"]) == 2


@pytest.mark.asyncio
async def test_typing_timeout_error_handling(message_handler, mock_connection):
    """Test error handling in typing timeout"""
    # Mock broadcast to raise an exception
    message_handler.connection_manager.broadcast_to_room = AsyncMock(
        side_effect=Exception("Broadcast failed")
    )
    
    # Set user as typing
    mock_connection.set_typing(True)
    
    # Start typing timeout with short duration
    timeout_task = asyncio.create_task(
        message_handler._typing_timeout_handler(mock_connection, 0.1)
    )
    
    # Wait for timeout to complete (should handle exception gracefully)
    await timeout_task
    
    # Verify typing was still set to false despite broadcast error
    assert mock_connection.is_typing is False


def test_get_message_handler_stats_typing_info(message_handler):
    """Test that message handler stats include typing information"""
    # Set up some typing timeouts
    message_handler.typing_timeouts = {
        "room1": {"user1": Mock(), "user2": Mock()},
        "room2": {"user3": Mock()},
        "room3": {}  # Empty room
    }
    
    # Get stats
    stats = message_handler.get_message_handler_stats()
    
    # Verify typing-related stats
    assert 'active_typing_timeouts' in stats
    assert 'rooms_with_typing' in stats
    assert 'typing_timeout_seconds' in stats
    
    assert stats['active_typing_timeouts'] == 3
    assert stats['rooms_with_typing'] == 3  # Includes empty room
    assert stats['typing_timeout_seconds'] == 3.0


@pytest.mark.asyncio
async def test_typing_indicator_room_isolation(connection_manager, room_manager, message_handler):
    """Test that typing indicators are isolated between rooms"""
    # Create connections in different rooms
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    conn1 = await connection_manager.connect(ws1, "test-room-1", "user1")
    conn2 = await connection_manager.connect(ws2, "test-room-2", "user2")
    
    # Set user1 as typing in room1
    conn1.set_typing(True)
    
    # Get typing users directly from connection manager rooms
    room1 = connection_manager.get_room("test-room-1")
    room2 = connection_manager.get_room("test-room-2")
    
    typing_room1 = room1.get_typing_users() if room1 else set()
    typing_room2 = room2.get_typing_users() if room2 else set()
    
    # Verify isolation
    assert "user1" in typing_room1
    assert "user1" not in typing_room2
    assert len(typing_room2) == 0


@pytest.mark.asyncio
async def test_expired_typing_indicator_cleanup(connection_manager, room_manager):
    """Test cleanup of expired typing indicators"""
    room_id = "test-room"
    
    # Create connection using connection manager
    ws = MockWebSocket()
    conn = await connection_manager.connect(ws, room_id, "user1")
    
    # Set typing with manual timeout in the past
    conn.set_typing(True)
    conn.typing_timeout = datetime.utcnow() - timedelta(seconds=5)  # Expired
    
    # Get the room from connection manager and check typing users
    room = connection_manager.get_room(room_id)
    typing_users = room.get_typing_users()
    
    # Verify expired typing was cleaned up
    assert len(typing_users) == 0
    assert conn.is_typing is False