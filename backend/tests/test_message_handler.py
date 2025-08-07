import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.message_handler import MessageHandler
from app.services.connection_manager import ConnectionManager
from app.services.room_manager import RoomManager
from app.models import (
    TextMessage, VoiceMessage, TypingMessage, ConnectionInfo, Room
)


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
    """Create a mock RoomManager"""
    return RoomManager()


@pytest.fixture
def connection_manager(room_manager):
    """Create a mock ConnectionManager"""
    from app.services.rate_limiter import RateLimiter, RateLimitConfig
    rate_limiter = RateLimiter(RateLimitConfig())
    return ConnectionManager(room_manager, rate_limiter)


@pytest.fixture
def message_handler(connection_manager, room_manager):
    """Create MessageHandler with mocked dependencies"""
    from app.services.rate_limiter import RateLimiter, RateLimitConfig
    rate_limiter = RateLimiter(RateLimitConfig())
    return MessageHandler(connection_manager, room_manager, rate_limiter)


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


@pytest.mark.asyncio
async def test_handle_text_message_success(message_handler, mock_connection):
    """Test successful text message handling"""
    # Create text message
    message = TextMessage(
        user_id="test_user_123",
        room_id="test-room-456",
        content="Hello world!"
    )
    
    # Mock connection manager methods
    message_handler.connection_manager.broadcast_to_room = AsyncMock(return_value=2)
    
    # Handle message
    result = await message_handler.handle_text_message(mock_connection, message)
    
    # Verify success
    assert result is True
    message_handler.connection_manager.broadcast_to_room.assert_called_once()
    
    # Verify message was updated with connection info
    assert message.user_id == mock_connection.user_id
    assert message.room_id == mock_connection.room_id


@pytest.mark.asyncio
async def test_handle_text_message_empty_content(message_handler, mock_connection):
    """Test text message with empty content"""
    # Create text message with valid content first, then modify it
    message = TextMessage(
        user_id="test_user_123",
        room_id="test-room-456",
        content="valid content"
    )
    
    # Manually set empty content to bypass Pydantic validation
    message.content = "   "  # Whitespace only
    
    # Mock connection manager methods
    message_handler.connection_manager.send_error = AsyncMock()
    
    # Handle message
    result = await message_handler.handle_text_message(mock_connection, message)
    
    # Verify failure
    assert result is False
    message_handler.connection_manager.send_error.assert_called_once_with(
        mock_connection.websocket, "EMPTY_MESSAGE", "Message content cannot be empty"
    )


@pytest.mark.asyncio
async def test_handle_voice_message_success(message_handler, mock_connection):
    """Test successful voice message handling"""
    # Create voice message with audio data
    audio_data = b"fake_audio_data_here"
    message = VoiceMessage(
        user_id="test_user_123",
        room_id="test-room-456",
        audio_data=audio_data,
        duration=5.0,
        audio_format="webm"
    )
    
    # Mock connection manager methods
    message_handler.connection_manager.broadcast_to_room = AsyncMock(return_value=2)
    
    # Handle message
    result = await message_handler.handle_voice_message(mock_connection, message)
    
    # Verify success
    assert result is True
    message_handler.connection_manager.broadcast_to_room.assert_called_once()
    
    # Verify message was updated with connection info
    assert message.user_id == mock_connection.user_id
    assert message.room_id == mock_connection.room_id


@pytest.mark.asyncio
async def test_handle_voice_message_no_audio_data(message_handler, mock_connection):
    """Test voice message without audio data"""
    # Create voice message without audio data
    message = VoiceMessage(
        user_id="test_user_123",
        room_id="test-room-456",
        audio_data=None
    )
    
    # Mock connection manager methods
    message_handler.connection_manager.send_error = AsyncMock()
    
    # Handle message
    result = await message_handler.handle_voice_message(mock_connection, message)
    
    # Verify failure
    assert result is False
    message_handler.connection_manager.send_error.assert_called_once_with(
        mock_connection.websocket, "EMPTY_VOICE_MESSAGE", "Voice message must contain audio data"
    )


@pytest.mark.asyncio
async def test_handle_voice_message_too_large(message_handler, mock_connection):
    """Test voice message that exceeds size limit"""
    # Create oversized audio data (11MB)
    audio_data = b"x" * (11 * 1024 * 1024)
    message = VoiceMessage(
        user_id="test_user_123",
        room_id="test-room-456",
        audio_data=audio_data
    )
    
    # Mock connection manager methods
    message_handler.connection_manager.send_error = AsyncMock()
    
    # Handle message
    result = await message_handler.handle_voice_message(mock_connection, message)
    
    # Verify failure
    assert result is False
    message_handler.connection_manager.send_error.assert_called_once()
    args = message_handler.connection_manager.send_error.call_args[0]
    assert args[1] == "VOICE_MESSAGE_TOO_LARGE"


@pytest.mark.asyncio
async def test_handle_voice_message_invalid_duration(message_handler, mock_connection):
    """Test voice message with invalid duration"""
    # Create voice message with valid duration first, then modify it
    message = VoiceMessage(
        user_id="test_user_123",
        room_id="test-room-456",
        audio_data=b"fake_audio",
        duration=250.0  # Valid duration
    )
    
    # Manually set invalid duration to bypass Pydantic validation
    message.duration = 400.0  # Exceeds 300 second limit
    
    # Mock connection manager methods
    message_handler.connection_manager.send_error = AsyncMock()
    
    # Handle message
    result = await message_handler.handle_voice_message(mock_connection, message)
    
    # Verify failure
    assert result is False
    message_handler.connection_manager.send_error.assert_called_once_with(
        mock_connection.websocket, "INVALID_DURATION", "Voice message duration must be between 0 and 300 seconds"
    )


@pytest.mark.asyncio
async def test_handle_typing_message_start_typing(message_handler, mock_connection):
    """Test handling typing start message"""
    # Create typing message
    message = TypingMessage(
        user_id="test_user_123",
        room_id="test-room-456",
        isTyping=True
    )
    
    # Mock dependencies
    message_handler.connection_manager.broadcast_to_room = AsyncMock(return_value=1)
    message_handler.room_manager.get_room = Mock(return_value=Room(room_id="test-room-456"))
    
    # Handle message
    result = await message_handler.handle_typing_message(mock_connection, message)
    
    # Verify success
    assert result is True
    assert mock_connection.is_typing is True
    
    # Verify broadcast was called with exclude_user
    message_handler.connection_manager.broadcast_to_room.assert_called_once()
    call_args = message_handler.connection_manager.broadcast_to_room.call_args
    assert call_args[1]['exclude_user'] == mock_connection.user_id


@pytest.mark.asyncio
async def test_handle_typing_message_stop_typing(message_handler, mock_connection):
    """Test handling typing stop message"""
    # Set initial typing state
    mock_connection.set_typing(True)
    
    # Create typing stop message
    message = TypingMessage(
        user_id="test_user_123",
        room_id="test-room-456",
        isTyping=False
    )
    
    # Mock dependencies
    message_handler.connection_manager.broadcast_to_room = AsyncMock(return_value=1)
    message_handler.room_manager.get_room = Mock(return_value=Room(room_id="test-room-456"))
    
    # Handle message
    result = await message_handler.handle_typing_message(mock_connection, message)
    
    # Verify success
    assert result is True
    assert mock_connection.is_typing is False


@pytest.mark.asyncio
async def test_typing_timeout_handler(message_handler, mock_connection):
    """Test typing timeout functionality"""
    # Set user as typing
    mock_connection.set_typing(True)
    
    # Mock broadcast method
    message_handler.connection_manager.broadcast_to_room = AsyncMock()
    
    # Start typing timeout with short duration for testing
    timeout_task = asyncio.create_task(
        message_handler._typing_timeout_handler(mock_connection, 0.1)
    )
    
    # Wait for timeout to complete
    await timeout_task
    
    # Verify typing was set to false
    assert mock_connection.is_typing is False
    
    # Verify broadcast was called to notify others
    message_handler.connection_manager.broadcast_to_room.assert_called_once()


@pytest.mark.asyncio
async def test_manage_typing_timeout_creates_task(message_handler, mock_connection):
    """Test that typing timeout management creates and manages tasks"""
    room_id = mock_connection.room_id
    user_id = mock_connection.user_id
    
    # Initially no timeouts
    assert room_id not in message_handler.typing_timeouts
    
    # Start typing timeout
    await message_handler._manage_typing_timeout(mock_connection, True)
    
    # Verify timeout task was created
    assert room_id in message_handler.typing_timeouts
    assert user_id in message_handler.typing_timeouts[room_id]
    
    task = message_handler.typing_timeouts[room_id][user_id]
    assert not task.done()
    
    # Stop typing (should remove timeout)
    await message_handler._manage_typing_timeout(mock_connection, False)
    
    # Verify timeout was removed
    assert user_id not in message_handler.typing_timeouts.get(room_id, {})


@pytest.mark.asyncio
async def test_handle_user_disconnect_cleanup(message_handler, mock_connection):
    """Test cleanup when user disconnects"""
    # Set up typing state
    mock_connection.set_typing(True)
    await message_handler._manage_typing_timeout(mock_connection, True)
    
    # Mock broadcast method
    message_handler.connection_manager.broadcast_to_room = AsyncMock()
    
    # Handle disconnect
    await message_handler.handle_user_disconnect(mock_connection)
    
    # Verify typing timeout was cancelled and cleaned up
    room_id = mock_connection.room_id
    user_id = mock_connection.user_id
    assert room_id not in message_handler.typing_timeouts or user_id not in message_handler.typing_timeouts.get(room_id, {})
    
    # Verify typing stop message was broadcast
    message_handler.connection_manager.broadcast_to_room.assert_called_once()


@pytest.mark.asyncio
async def test_handle_message_invalid_connection(message_handler):
    """Test handling message with invalid connection"""
    ws = MockWebSocket()
    message_data = {"type": "text", "content": "Hello"}
    
    # Mock connection manager to return None
    message_handler.connection_manager.get_connection_info = Mock(return_value=None)
    message_handler.connection_manager.send_error = AsyncMock()
    
    # Handle message
    result = await message_handler.handle_message(ws, message_data)
    
    # Verify failure
    assert result is False
    message_handler.connection_manager.send_error.assert_called_once_with(
        ws, "CONNECTION_NOT_FOUND", "Connection not found"
    )


@pytest.mark.asyncio
async def test_handle_message_invalid_format(message_handler, mock_connection):
    """Test handling message with invalid format"""
    ws = mock_connection.websocket
    message_data = {"invalid": "format"}
    
    # Mock connection manager
    message_handler.connection_manager.get_connection_info = Mock(return_value=mock_connection)
    message_handler.connection_manager.send_error = AsyncMock()
    
    # Handle message
    result = await message_handler.handle_message(ws, message_data)
    
    # Verify failure
    assert result is False
    message_handler.connection_manager.send_error.assert_called_once()
    args = message_handler.connection_manager.send_error.call_args[0]
    assert args[1] == "INVALID_MESSAGE_FORMAT"


@pytest.mark.asyncio
async def test_handle_message_room_mismatch(message_handler, mock_connection):
    """Test handling message with room mismatch"""
    ws = mock_connection.websocket
    message_data = {
        "type": "text",
        "user_id": "test_user_123",
        "room_id": "different-room",  # Different from connection room
        "content": "Hello"
    }
    
    # Mock connection manager
    message_handler.connection_manager.get_connection_info = Mock(return_value=mock_connection)
    message_handler.connection_manager.send_error = AsyncMock()
    
    # Handle message
    result = await message_handler.handle_message(ws, message_data)
    
    # Verify failure
    assert result is False
    message_handler.connection_manager.send_error.assert_called_once_with(
        ws, "INVALID_ROOM", "Message room does not match connection room"
    )


@pytest.mark.asyncio
async def test_handle_message_success_text(message_handler, mock_connection):
    """Test successful message handling for text message"""
    ws = mock_connection.websocket
    message_data = {
        "type": "text",
        "user_id": "test_user_123",
        "room_id": "test-room-456",
        "content": "Hello world!"
    }
    
    # Mock dependencies
    message_handler.connection_manager.get_connection_info = Mock(return_value=mock_connection)
    message_handler.connection_manager.broadcast_to_room = AsyncMock(return_value=2)
    
    # Handle message
    result = await message_handler.handle_message(ws, message_data)
    
    # Verify success
    assert result is True


def test_get_typing_users(message_handler):
    """Test getting typing users for a room"""
    room_id = "test-room-456"
    
    # Mock room with typing users
    mock_room = Mock()
    mock_room.get_typing_users.return_value = {"user1", "user2"}
    message_handler.room_manager.get_room = Mock(return_value=mock_room)
    
    # Get typing users
    typing_users = message_handler.get_typing_users(room_id)
    
    # Verify result
    assert typing_users == {"user1", "user2"}
    message_handler.room_manager.get_room.assert_called_once_with(room_id)


def test_get_typing_users_no_room(message_handler):
    """Test getting typing users for non-existent room"""
    room_id = "non-existent-room"
    
    # Mock room manager to return None
    message_handler.room_manager.get_room = Mock(return_value=None)
    
    # Get typing users
    typing_users = message_handler.get_typing_users(room_id)
    
    # Verify empty set
    assert typing_users == set()


def test_get_message_handler_stats(message_handler):
    """Test getting message handler statistics"""
    # Set up some typing timeouts
    message_handler.typing_timeouts = {
        "room1": {"user1": Mock(), "user2": Mock()},
        "room2": {"user3": Mock()}
    }
    
    # Get stats
    stats = message_handler.get_message_handler_stats()
    
    # Verify stats
    assert stats['active_typing_timeouts'] == 3
    assert stats['rooms_with_typing'] == 2
    assert stats['typing_timeout_seconds'] == 3.0


@pytest.mark.asyncio
async def test_cleanup_all_typing_timeouts(message_handler):
    """Test cleaning up all typing timeouts"""
    # Create mock timeout tasks
    task1 = Mock()
    task2 = Mock()
    task3 = Mock()
    
    message_handler.typing_timeouts = {
        "room1": {"user1": task1, "user2": task2},
        "room2": {"user3": task3}
    }
    
    # Cleanup all timeouts
    await message_handler.cleanup_all_typing_timeouts()
    
    # Verify all tasks were cancelled
    task1.cancel.assert_called_once()
    task2.cancel.assert_called_once()
    task3.cancel.assert_called_once()
    
    # Verify timeouts were cleared
    assert message_handler.typing_timeouts == {}