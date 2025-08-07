import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket

from app.services.message_handler import MessageHandler
from app.services.connection_manager import ConnectionManager
from app.services.room_manager import RoomManager
from app.models import VoiceMessage, ConnectionInfo


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing"""
    websocket = MagicMock(spec=WebSocket)
    websocket.send_text = AsyncMock()
    websocket.send_bytes = AsyncMock()
    return websocket


@pytest.fixture
def room_manager():
    """Create a RoomManager instance for testing"""
    return RoomManager()


@pytest.fixture
def connection_manager(room_manager):
    """Create a ConnectionManager instance for testing"""
    return ConnectionManager(room_manager)


@pytest.fixture
def message_handler(connection_manager, room_manager):
    """Create a MessageHandler instance for testing"""
    return MessageHandler(connection_manager, room_manager)


@pytest.fixture
def sample_connection(mock_websocket):
    """Create a sample connection for testing"""
    return ConnectionInfo(
        websocket=mock_websocket,
        user_id="test_user",
        room_id="test-room"
    )


@pytest.mark.asyncio
async def test_handle_binary_message_success(message_handler, connection_manager, mock_websocket, sample_connection):
    """Test successful binary message handling"""
    # Setup
    binary_data = b"fake_audio_data_12345"
    connection_manager.connection_lookup[mock_websocket] = sample_connection
    connection_manager.room_manager.rooms["test-room"] = MagicMock()
    connection_manager.room_manager.rooms["test-room"].get_all_connections.return_value = {
        "test_user": sample_connection
    }
    connection_manager.room_manager.rooms["test-room"].update_activity = MagicMock()
    connection_manager.room_manager.rooms["test-room"].increment_message_count = MagicMock()
    
    # Mock broadcast_to_room to return success
    connection_manager.broadcast_to_room = AsyncMock(return_value=1)
    
    # Execute
    result = await message_handler.handle_binary_message(mock_websocket, binary_data)
    
    # Verify
    assert result is True
    connection_manager.broadcast_to_room.assert_called_once()
    
    # Check that the broadcasted message is a VoiceMessage with correct data
    call_args = connection_manager.broadcast_to_room.call_args
    broadcasted_message = call_args[0][1]  # Second argument is the message
    
    assert isinstance(broadcasted_message, VoiceMessage)
    assert broadcasted_message.audio_data == binary_data
    assert broadcasted_message.user_id == "test_user"
    assert broadcasted_message.room_id == "test-room"
    assert broadcasted_message.audio_format == "webm"


@pytest.mark.asyncio
async def test_handle_binary_message_empty_data(message_handler, connection_manager, mock_websocket, sample_connection):
    """Test binary message handling with empty data"""
    # Setup
    binary_data = b""
    connection_manager.connection_lookup[mock_websocket] = sample_connection
    connection_manager.send_error = AsyncMock()
    
    # Execute
    result = await message_handler.handle_binary_message(mock_websocket, binary_data)
    
    # Verify
    assert result is False
    connection_manager.send_error.assert_called_once_with(
        mock_websocket, "EMPTY_BINARY_DATA", "Binary data cannot be empty"
    )


@pytest.mark.asyncio
async def test_handle_binary_message_too_large(message_handler, connection_manager, mock_websocket, sample_connection):
    """Test binary message handling with data too large"""
    # Setup
    binary_data = b"x" * (11 * 1024 * 1024)  # 11MB - exceeds 10MB limit
    connection_manager.connection_lookup[mock_websocket] = sample_connection
    connection_manager.send_error = AsyncMock()
    
    # Execute
    result = await message_handler.handle_binary_message(mock_websocket, binary_data)
    
    # Verify
    assert result is False
    connection_manager.send_error.assert_called_once_with(
        mock_websocket, "BINARY_DATA_TOO_LARGE", f"Binary data exceeds maximum size of {10 * 1024 * 1024} bytes"
    )


@pytest.mark.asyncio
async def test_handle_binary_message_no_connection(message_handler, connection_manager, mock_websocket):
    """Test binary message handling when connection not found"""
    # Setup
    binary_data = b"fake_audio_data"
    connection_manager.send_error = AsyncMock()
    
    # Execute
    result = await message_handler.handle_binary_message(mock_websocket, binary_data)
    
    # Verify
    assert result is False
    connection_manager.send_error.assert_called_once_with(
        mock_websocket, "CONNECTION_NOT_FOUND", "Connection not found"
    )


@pytest.mark.asyncio
async def test_send_voice_message_as_binary(connection_manager, mock_websocket):
    """Test that VoiceMessage with audio_data is sent as binary"""
    # Setup
    audio_data = b"test_audio_data_123"
    voice_message = VoiceMessage(
        user_id="test_user",
        room_id="test-room",
        audio_data=audio_data,
        audio_format="webm"
    )
    
    # Execute
    result = await connection_manager.send_message(mock_websocket, voice_message)
    
    # Verify
    assert result is True
    mock_websocket.send_bytes.assert_called_once_with(audio_data)
    mock_websocket.send_text.assert_not_called()


@pytest.mark.asyncio
async def test_send_voice_message_without_audio_data(connection_manager, mock_websocket):
    """Test that VoiceMessage without audio_data is sent as JSON"""
    # Setup
    voice_message = VoiceMessage(
        user_id="test_user",
        room_id="test-room",
        audio_data=None,
        audio_format="webm"
    )
    
    # Execute
    result = await connection_manager.send_message(mock_websocket, voice_message)
    
    # Verify
    assert result is True
    mock_websocket.send_text.assert_called_once()
    mock_websocket.send_bytes.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_voice_message_to_room(connection_manager, room_manager):
    """Test broadcasting voice message to multiple users in room"""
    # Setup
    room_id = "test-room"
    audio_data = b"broadcast_audio_test"
    
    # Create mock websockets and connections
    ws1 = MagicMock(spec=WebSocket)
    ws1.send_bytes = AsyncMock()
    ws2 = MagicMock(spec=WebSocket)
    ws2.send_bytes = AsyncMock()
    
    conn1 = ConnectionInfo(websocket=ws1, user_id="user1", room_id=room_id)
    conn2 = ConnectionInfo(websocket=ws2, user_id="user2", room_id=room_id)
    
    # Setup room with connections
    room = room_manager.get_or_create_room(room_id)
    room.add_connection(conn1)
    room.add_connection(conn2)
    
    connection_manager.room_manager.rooms[room_id] = room
    connection_manager.connection_lookup[ws1] = conn1
    connection_manager.connection_lookup[ws2] = conn2
    
    # Create voice message
    voice_message = VoiceMessage(
        user_id="sender",
        room_id=room_id,
        audio_data=audio_data,
        audio_format="webm"
    )
    
    # Execute
    sent_count = await connection_manager.broadcast_to_room(room_id, voice_message)
    
    # Verify
    assert sent_count == 2
    ws1.send_bytes.assert_called_once_with(audio_data)
    ws2.send_bytes.assert_called_once_with(audio_data)


@pytest.mark.asyncio
async def test_voice_message_size_validation():
    """Test voice message size validation in model"""
    # Test valid size
    audio_data = b"x" * 1024  # 1KB
    voice_message = VoiceMessage(
        user_id="test_user",
        room_id="test-room",
        audio_data=audio_data
    )
    assert voice_message.audio_data == audio_data
    
    # Test large size (should still create the object, validation happens in handler)
    large_audio_data = b"x" * (5 * 1024 * 1024)  # 5MB
    large_voice_message = VoiceMessage(
        user_id="test_user",
        room_id="test-room",
        audio_data=large_audio_data
    )
    assert large_voice_message.audio_data == large_audio_data


@pytest.mark.asyncio
async def test_voice_message_format_validation():
    """Test voice message format validation"""
    # Test valid formats
    valid_formats = ["webm", "mp3", "wav", "ogg"]
    
    for format_type in valid_formats:
        voice_message = VoiceMessage(
            user_id="test_user",
            room_id="test-room",
            audio_format=format_type
        )
        assert voice_message.audio_format == format_type
    
    # Test invalid format should raise validation error
    with pytest.raises(ValueError):
        VoiceMessage(
            user_id="test_user",
            room_id="test-room",
            audio_format="invalid_format"
        )


@pytest.mark.asyncio
async def test_voice_message_duration_validation():
    """Test voice message duration validation"""
    # Test valid duration
    voice_message = VoiceMessage(
        user_id="test_user",
        room_id="test-room",
        duration=30.5
    )
    assert voice_message.duration == 30.5
    
    # Test maximum duration
    voice_message = VoiceMessage(
        user_id="test_user",
        room_id="test-room",
        duration=300.0
    )
    assert voice_message.duration == 300.0
    
    # Test invalid duration (negative)
    with pytest.raises(ValueError):
        VoiceMessage(
            user_id="test_user",
            room_id="test-room",
            duration=-1.0
        )
    
    # Test invalid duration (too long)
    with pytest.raises(ValueError):
        VoiceMessage(
            user_id="test_user",
            room_id="test-room",
            duration=301.0
        )