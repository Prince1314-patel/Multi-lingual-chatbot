import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket

from app.services.connection_manager import ConnectionManager
from app.services.message_handler import MessageHandler
from app.services.room_manager import RoomManager
from app.models import (
    TextMessage,
    VoiceMessage,
    MessageDeliveryConfirmation,
    ConnectionInfo,
    Room
)


@pytest.fixture
def room_manager():
    return RoomManager()


@pytest.fixture
def connection_manager(room_manager):
    return ConnectionManager(room_manager)


@pytest.fixture
def message_handler(connection_manager, room_manager):
    return MessageHandler(connection_manager, room_manager)


@pytest.fixture
def mock_websocket():
    websocket = MagicMock(spec=WebSocket)
    websocket.send_text = AsyncMock()
    websocket.send_bytes = AsyncMock()
    return websocket


@pytest.fixture
def mock_connection(mock_websocket):
    connection = ConnectionInfo(
        websocket=mock_websocket,
        user_id="test_user",
        room_id="test-room"
    )
    return connection


@pytest.fixture
def mock_room():
    return Room(room_id="test-room")


@pytest.mark.asyncio
async def test_text_message_delivery_confirmation(
    connection_manager, message_handler, mock_websocket, mock_connection, mock_room
):
    """Test that text messages generate delivery confirmations"""
    # Setup
    connection_manager.rooms["test-room"] = mock_room
    connection_manager.connection_lookup[mock_websocket] = mock_connection
    mock_room.add_connection(mock_connection)
    
    # Create a second user to receive the message
    mock_websocket2 = MagicMock(spec=WebSocket)
    mock_websocket2.send_text = AsyncMock()
    mock_connection2 = ConnectionInfo(
        websocket=mock_websocket2,
        user_id="test_user2",
        room_id="test-room"
    )
    connection_manager.connection_lookup[mock_websocket2] = mock_connection2
    mock_room.add_connection(mock_connection2)
    
    # Create text message
    text_message = TextMessage(
        id="test_msg_123",
        user_id="test_user",
        room_id="test-room",
        content="Hello, world!"
    )
    
    # Handle the message
    result = await message_handler.handle_text_message(mock_connection, text_message)
    
    # Verify message was handled successfully
    assert result is True
    
    # Verify message was sent to the recipient
    mock_websocket2.send_text.assert_called_once()
    
    # Verify delivery confirmation was sent back to sender
    mock_websocket.send_text.assert_called_once()
    
    # Parse the confirmation message
    confirmation_call = mock_websocket.send_text.call_args[0][0]
    import json
    confirmation_data = json.loads(confirmation_call)
    
    assert confirmation_data["type"] == "message_confirmation"
    assert confirmation_data["message_id"] == "test_msg_123"
    assert confirmation_data["status"] == "delivered"
    assert confirmation_data["user_id"] == "test_user"
    assert confirmation_data["room_id"] == "test-room"


@pytest.mark.asyncio
async def test_voice_message_delivery_confirmation(
    connection_manager, message_handler, mock_websocket, mock_connection, mock_room
):
    """Test that voice messages generate delivery confirmations"""
    # Setup
    connection_manager.rooms["test-room"] = mock_room
    connection_manager.connection_lookup[mock_websocket] = mock_connection
    mock_room.add_connection(mock_connection)
    
    # Create a second user to receive the message
    mock_websocket2 = MagicMock(spec=WebSocket)
    mock_websocket2.send_text = AsyncMock()
    mock_connection2 = ConnectionInfo(
        websocket=mock_websocket2,
        user_id="test_user2",
        room_id="test-room"
    )
    connection_manager.connection_lookup[mock_websocket2] = mock_connection2
    mock_room.add_connection(mock_connection2)
    
    # Create voice message
    audio_data = b"fake_audio_data"
    voice_message = VoiceMessage(
        id="test_voice_123",
        user_id="test_user",
        room_id="test-room",
        audio_data=audio_data,
        duration=5.0
    )
    
    # Handle the message
    result = await message_handler.handle_voice_message(mock_connection, voice_message)
    
    # Verify message was handled successfully
    assert result is True
    
    # Verify message was sent to the recipient
    mock_websocket2.send_bytes.assert_called_once_with(audio_data)
    
    # Verify delivery confirmation was sent back to sender
    mock_websocket.send_text.assert_called_once()
    
    # Parse the confirmation message
    confirmation_call = mock_websocket.send_text.call_args[0][0]
    import json
    confirmation_data = json.loads(confirmation_call)
    
    assert confirmation_data["type"] == "message_confirmation"
    assert confirmation_data["message_id"] == "test_voice_123"
    assert confirmation_data["status"] == "delivered"
    assert confirmation_data["user_id"] == "test_user"
    assert confirmation_data["room_id"] == "test-room"


@pytest.mark.asyncio
async def test_failed_delivery_confirmation(
    connection_manager, message_handler, mock_websocket, mock_connection, mock_room
):
    """Test that failed message delivery generates failed confirmation"""
    # Setup
    connection_manager.rooms["test-room"] = mock_room
    connection_manager.connection_lookup[mock_websocket] = mock_connection
    mock_room.add_connection(mock_connection)
    
    # Create a second user with failing websocket
    mock_websocket2 = MagicMock(spec=WebSocket)
    mock_websocket2.send_text = AsyncMock(side_effect=Exception("Connection failed"))
    mock_connection2 = ConnectionInfo(
        websocket=mock_websocket2,
        user_id="test_user2",
        room_id="test-room"
    )
    connection_manager.connection_lookup[mock_websocket2] = mock_connection2
    mock_room.add_connection(mock_connection2)
    
    # Create text message
    text_message = TextMessage(
        id="test_msg_456",
        user_id="test_user",
        room_id="test-room",
        content="Hello, world!"
    )
    
    # Handle the message
    result = await message_handler.handle_text_message(mock_connection, text_message)
    
    # Verify message was handled successfully (handler doesn't fail on broadcast errors)
    assert result is True
    
    # Verify delivery confirmation was sent back to sender with failed status
    mock_websocket.send_text.assert_called_once()
    
    # Parse the confirmation message
    confirmation_call = mock_websocket.send_text.call_args[0][0]
    import json
    confirmation_data = json.loads(confirmation_call)
    
    assert confirmation_data["type"] == "message_confirmation"
    assert confirmation_data["message_id"] == "test_msg_456"
    assert confirmation_data["status"] == "failed"
    assert confirmation_data["user_id"] == "test_user"
    assert confirmation_data["room_id"] == "test-room"


@pytest.mark.asyncio
async def test_message_delivery_confirmation_serialization():
    """Test that MessageDeliveryConfirmation serializes correctly"""
    confirmation = MessageDeliveryConfirmation(
        message_id="test_123",
        status="delivered",
        user_id="user_123",
        room_id="room_123"
    )
    
    # Test serialization
    from app.models import serialize_message
    serialized = serialize_message(confirmation)
    
    assert serialized["type"] == "message_confirmation"
    assert serialized["message_id"] == "test_123"
    assert serialized["status"] == "delivered"
    assert serialized["user_id"] == "user_123"
    assert serialized["room_id"] == "room_123"
    assert "timestamp" in serialized


@pytest.mark.asyncio
async def test_message_delivery_confirmation_deserialization():
    """Test that MessageDeliveryConfirmation deserializes correctly"""
    data = {
        "type": "message_confirmation",
        "message_id": "test_123",
        "status": "delivered",
        "user_id": "user_123",
        "room_id": "room_123",
        "timestamp": "2023-01-01T00:00:00"
    }
    
    # Test deserialization
    from app.models import deserialize_message
    message = deserialize_message(data)
    
    assert isinstance(message, MessageDeliveryConfirmation)
    assert message.message_id == "test_123"
    assert message.status == "delivered"
    assert message.user_id == "user_123"
    assert message.room_id == "room_123"