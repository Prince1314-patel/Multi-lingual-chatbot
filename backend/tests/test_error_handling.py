"""
Tests for comprehensive error handling and logging functionality
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import WebSocket, WebSocketDisconnect, HTTPException

from app.core.error_handler import ErrorHandler, ErrorCode, ChatLogger
from app.services.connection_manager import ConnectionManager
from app.services.message_handler import MessageHandler
from app.services.room_manager import RoomManager
from app.models import ConnectionInfo, TextMessage, VoiceMessage, ErrorMessage


class MockWebSocket:
    """Mock WebSocket for testing error handling"""
    
    def __init__(self, should_fail=False, fail_on_send=False):
        self.accept = AsyncMock()
        self.close = AsyncMock()
        self.send_text = AsyncMock()
        self.send_bytes = AsyncMock()
        self.messages_sent = []
        self.should_fail = should_fail
        self.fail_on_send = fail_on_send
        
        if fail_on_send:
            self.send_text.side_effect = Exception("Send failed")
            self.send_bytes.side_effect = Exception("Send failed")
    
    async def receive(self):
        if self.should_fail:
            raise WebSocketDisconnect()
        return {"type": "websocket.receive", "text": '{"type": "text", "content": "test"}'}


@pytest.fixture
def chat_logger():
    """Create a ChatLogger for testing"""
    return ChatLogger("test_logger")


@pytest.fixture
def error_handler(chat_logger):
    """Create an ErrorHandler for testing"""
    return ErrorHandler(chat_logger)


@pytest.fixture
def mock_connection():
    """Create a mock ConnectionInfo"""
    ws = MockWebSocket()
    return ConnectionInfo(
        websocket=ws,
        user_id="test_user_123",
        room_id="test_room_456"
    )


@pytest.fixture
def connection_manager():
    """Create a ConnectionManager for testing"""
    return ConnectionManager()


@pytest.fixture
def room_manager():
    """Create a RoomManager for testing"""
    return RoomManager()


@pytest.fixture
def message_handler(connection_manager, room_manager):
    """Create a MessageHandler for testing"""
    return MessageHandler(connection_manager, room_manager)


class TestChatLogger:
    """Test ChatLogger functionality"""
    
    def test_log_connection_event(self, chat_logger):
        """Test logging connection events"""
        with patch.object(chat_logger.logger, 'info') as mock_info:
            chat_logger.log_connection_event("established", "user123", "room456")
            mock_info.assert_called_once()
            args = mock_info.call_args[0][0]
            assert "Connection established" in args
            assert "user123" in args
            assert "room456" in args
    
    def test_log_message_event(self, chat_logger):
        """Test logging message events"""
        with patch.object(chat_logger.logger, 'info') as mock_info:
            chat_logger.log_message_event("sent", "user123", "room456", "text")
            mock_info.assert_called_once()
            args = mock_info.call_args[0][0]
            assert "Message sent" in args
            assert "user123" in args
            assert "room456" in args
            assert "text" in args
    
    def test_log_error_with_exception(self, chat_logger):
        """Test logging errors with exceptions"""
        test_exception = ValueError("Test error")
        with patch.object(chat_logger.logger, 'error') as mock_error:
            chat_logger.log_error(
                ErrorCode.INVALID_MESSAGE_FORMAT, 
                "Test error message", 
                "user123", 
                "room456", 
                test_exception
            )
            mock_error.assert_called_once()
            args = mock_error.call_args[0][0]
            assert "INVALID_MESSAGE_FORMAT" in args
            assert "Test error message" in args
            assert "user123" in args
            assert "room456" in args
    
    def test_log_performance(self, chat_logger):
        """Test logging performance metrics"""
        with patch.object(chat_logger.logger, 'info') as mock_info:
            chat_logger.log_performance("message_processing", 150.5, "user123", "room456")
            mock_info.assert_called_once()
            args = mock_info.call_args[0][0]
            assert "PERFORMANCE" in args
            assert "message_processing" in args
            assert "150.50ms" in args


class TestErrorHandler:
    """Test ErrorHandler functionality"""
    
    @pytest.mark.asyncio
    async def test_handle_websocket_error_success(self, error_handler):
        """Test successful WebSocket error handling"""
        ws = MockWebSocket()
        
        result = await error_handler.handle_websocket_error(
            ws, ErrorCode.INVALID_JSON, "Test error", "user123", "room456"
        )
        
        assert result is True
        ws.send_text.assert_called_once()
        
        # Verify error message format
        sent_data = ws.send_text.call_args[0][0]
        error_data = json.loads(sent_data)
        assert error_data["type"] == "error"
        assert error_data["error_code"] == "INVALID_JSON"
        assert error_data["message"] == "Test error"
    
    @pytest.mark.asyncio
    async def test_handle_websocket_error_send_fails(self, error_handler):
        """Test WebSocket error handling when send fails"""
        ws = MockWebSocket(fail_on_send=True)
        
        result = await error_handler.handle_websocket_error(
            ws, ErrorCode.INVALID_JSON, "Test error", "user123", "room456"
        )
        
        assert result is False
        ws.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_connection_cleanup_success(self, error_handler, mock_connection):
        """Test successful connection cleanup"""
        # Mock connection manager and message handler
        conn_mgr = Mock()
        conn_mgr.get_connection_info.return_value = mock_connection
        conn_mgr.disconnect = AsyncMock()
        
        msg_handler = Mock()
        msg_handler.handle_user_disconnect = AsyncMock()
        
        result = await error_handler.handle_connection_cleanup(
            mock_connection.websocket, "user123", "room456", conn_mgr, msg_handler
        )
        
        assert result is True
        msg_handler.handle_user_disconnect.assert_called_once_with(mock_connection)
        conn_mgr.disconnect.assert_called_once_with(mock_connection.websocket, broadcast_leave=True)
    
    @pytest.mark.asyncio
    async def test_handle_connection_cleanup_partial_failure(self, error_handler, mock_connection):
        """Test connection cleanup with partial failures"""
        # Mock connection manager and message handler
        conn_mgr = Mock()
        conn_mgr.get_connection_info.return_value = mock_connection
        conn_mgr.disconnect = AsyncMock(side_effect=Exception("Disconnect failed"))
        
        msg_handler = Mock()
        msg_handler.handle_user_disconnect = AsyncMock()
        
        result = await error_handler.handle_connection_cleanup(
            mock_connection.websocket, "user123", "room456", conn_mgr, msg_handler
        )
        
        assert result is False  # Should return False due to disconnect failure
        msg_handler.handle_user_disconnect.assert_called_once_with(mock_connection)
        conn_mgr.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_safe_websocket_close_success(self, error_handler):
        """Test successful WebSocket closure"""
        ws = MockWebSocket()
        
        result = await error_handler.safe_websocket_close(ws, 1000, "Normal closure")
        
        assert result is True
        ws.close.assert_called_once_with(code=1000, reason="Normal closure")
    
    @pytest.mark.asyncio
    async def test_safe_websocket_close_failure(self, error_handler):
        """Test WebSocket closure failure"""
        ws = MockWebSocket()
        ws.close.side_effect = Exception("Close failed")
        
        result = await error_handler.safe_websocket_close(ws, 1000, "Normal closure")
        
        assert result is False
        ws.close.assert_called_once()
    
    def test_handle_message_validation_error_json(self, error_handler):
        """Test message validation error handling for JSON errors"""
        error = ValueError("Invalid JSON format")
        
        error_code = error_handler.handle_message_validation_error(
            error, "user123", "room456"
        )
        
        assert error_code == ErrorCode.INVALID_JSON
    
    def test_handle_message_validation_error_empty(self, error_handler):
        """Test message validation error handling for empty content"""
        error = ValueError("Content cannot be empty")
        
        error_code = error_handler.handle_message_validation_error(
            error, "user123", "room456"
        )
        
        assert error_code == ErrorCode.EMPTY_MESSAGE
    
    def test_handle_message_validation_error_size(self, error_handler):
        """Test message validation error handling for size errors"""
        error = ValueError("Message too large")
        
        error_code = error_handler.handle_message_validation_error(
            error, "user123", "room456"
        )
        
        assert error_code == ErrorCode.MESSAGE_TOO_LARGE
    
    def test_handle_message_validation_error_generic(self, error_handler):
        """Test message validation error handling for generic errors"""
        error = ValueError("Unknown validation error")
        
        error_code = error_handler.handle_message_validation_error(
            error, "user123", "room456"
        )
        
        assert error_code == ErrorCode.VALIDATION_ERROR


class TestConnectionManagerErrorHandling:
    """Test enhanced error handling in ConnectionManager"""
    
    @pytest.mark.asyncio
    async def test_send_message_binary_too_large(self, connection_manager, mock_connection):
        """Test sending binary message that's too large"""
        # Add connection to manager
        connection_manager.connection_lookup[mock_connection.websocket] = mock_connection
        
        # Create oversized voice message
        large_audio_data = b"x" * (11 * 1024 * 1024)  # 11MB
        voice_message = VoiceMessage(
            user_id="user123",
            room_id="room456",
            audio_data=large_audio_data
        )
        
        result = await connection_manager.send_message(mock_connection.websocket, voice_message)
        
        assert result is False
        mock_connection.websocket.send_bytes.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_message_text_too_large(self, connection_manager, mock_connection):
        """Test sending text message that's too large"""
        # Add connection to manager
        connection_manager.connection_lookup[mock_connection.websocket] = mock_connection
        
        # Create text message with valid content first, then manually set large content
        text_message = TextMessage(
            user_id="user123",
            room_id="room456",
            content="valid content"
        )
        
        # Manually create a large serialized message to test size limit
        with patch('app.services.connection_manager.serialize_message') as mock_serialize:
            large_json = "x" * (2 * 1024 * 1024)  # 2MB JSON string
            mock_serialize.return_value = {"large": "data"}
            
            with patch('json.dumps') as mock_dumps:
                mock_dumps.return_value = large_json
                
                result = await connection_manager.send_message(mock_connection.websocket, text_message)
                
                assert result is False
                mock_connection.websocket.send_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_message_websocket_disconnect(self, connection_manager, mock_connection):
        """Test sending message when WebSocket disconnects"""
        # Add connection to manager
        connection_manager.connection_lookup[mock_connection.websocket] = mock_connection
        
        # Make send_text raise WebSocketDisconnect
        mock_connection.websocket.send_text.side_effect = WebSocketDisconnect()
        
        text_message = TextMessage(
            user_id="user123",
            room_id="room456",
            content="test message"
        )
        
        result = await connection_manager.send_message(mock_connection.websocket, text_message)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_broadcast_to_room_nonexistent_room(self, connection_manager):
        """Test broadcasting to a room that doesn't exist"""
        text_message = TextMessage(
            user_id="user123",
            room_id="nonexistent_room",
            content="test message"
        )
        
        result = await connection_manager.broadcast_to_room("nonexistent_room", text_message)
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_to_room_with_failed_connections(self):
        """Test broadcasting when some connections fail"""
        # Create a fresh connection manager for this test
        connection_manager = ConnectionManager()
        room_id = "test_room"
        
        # Create working connection
        ws1 = MockWebSocket()
        conn1 = ConnectionInfo(websocket=ws1, user_id="user1", room_id=room_id)
        
        # Create failing connection
        ws2 = MockWebSocket(fail_on_send=True)
        conn2 = ConnectionInfo(websocket=ws2, user_id="user2", room_id=room_id)
        
        # Manually set up connections to avoid logger issues
        from app.models import Room
        connection_manager.rooms[room_id] = Room(room_id=room_id)
        connection_manager.rooms[room_id].add_connection(conn1)
        connection_manager.rooms[room_id].add_connection(conn2)
        connection_manager.connection_lookup[ws1] = conn1
        connection_manager.connection_lookup[ws2] = conn2
        
        text_message = TextMessage(
            user_id="user1",
            room_id=room_id,
            content="test message"
        )
        
        result = await connection_manager.broadcast_to_room(room_id, text_message)
        
        # Should succeed for one connection, fail for the other
        assert result == 1
        
        # Failed connection should be cleaned up
        assert ws2 not in connection_manager.connection_lookup


class TestErrorRecovery:
    """Test error recovery scenarios"""
    
    @pytest.mark.asyncio
    async def test_message_handler_continues_after_error(self):
        """Test that message handler continues processing after an error"""
        # Create fresh instances to avoid mocking issues
        connection_manager = ConnectionManager()
        room_manager = RoomManager()
        message_handler = MessageHandler(connection_manager, room_manager)
        
        # Create mock connection
        ws = MockWebSocket()
        mock_connection = ConnectionInfo(
            websocket=ws,
            user_id="test_user_123",
            room_id="test_room_456"
        )
        
        # Set up connection in manager
        connection_manager.connection_lookup[ws] = mock_connection
        
        # First message causes error (invalid format)
        invalid_message_data = {"invalid": "format"}
        result1 = await message_handler.handle_message(ws, invalid_message_data)
        assert result1 is False
        
        # Second message should work - but we need to set up the room properly
        from app.models import Room
        room = Room(room_id="test_room_456")
        room.add_connection(mock_connection)
        room_manager.rooms["test_room_456"] = room
        connection_manager.rooms["test_room_456"] = room
        
        valid_message_data = {
            "type": "text",
            "user_id": "test_user_123",
            "room_id": "test_room_456",
            "content": "Hello world"
        }
        result2 = await message_handler.handle_message(ws, valid_message_data)
        assert result2 is True
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_multiple_failures(self):
        """Test that connections are properly cleaned up after multiple failures"""
        # Create a fresh connection manager for this test
        connection_manager = ConnectionManager()
        room_id = "test_room"
        
        # Create multiple failing connections
        failing_connections = []
        for i in range(3):
            ws = MockWebSocket(fail_on_send=True)
            # Manually set up the connection to avoid logger issues
            connection = ConnectionInfo(websocket=ws, user_id=f"user{i}", room_id=room_id)
            
            # Manually add to connection manager
            if room_id not in connection_manager.rooms:
                from app.models import Room
                connection_manager.rooms[room_id] = Room(room_id=room_id)
            
            connection_manager.rooms[room_id].add_connection(connection)
            connection_manager.connection_lookup[ws] = connection
            failing_connections.append(ws)
        
        # Try to broadcast - should clean up all failing connections
        text_message = TextMessage(
            user_id="sender",
            room_id=room_id,
            content="test message"
        )
        
        result = await connection_manager.broadcast_to_room(room_id, text_message)
        
        assert result == 0  # No successful sends
        
        # All failing connections should be cleaned up
        for ws in failing_connections:
            assert ws not in connection_manager.connection_lookup
        
        # Room should be empty and cleaned up
        assert room_id not in connection_manager.rooms


@pytest.mark.asyncio
async def test_error_code_enum_coverage():
    """Test that all error codes are properly defined"""
    # Verify all expected error codes exist
    expected_codes = [
        "CONNECTION_FAILED", "CONNECTION_NOT_FOUND", "CONNECTION_TIMEOUT",
        "INVALID_ROOM_ID", "ROOM_NOT_FOUND", "INVALID_MESSAGE_FORMAT",
        "INVALID_JSON", "MESSAGE_TOO_LARGE", "EMPTY_MESSAGE",
        "UNSUPPORTED_MESSAGE_TYPE", "MESSAGE_PROCESSING_ERROR",
        "EMPTY_VOICE_MESSAGE", "VOICE_MESSAGE_TOO_LARGE",
        "INTERNAL_SERVER_ERROR", "SERVICE_UNAVAILABLE"
    ]
    
    for code in expected_codes:
        assert hasattr(ErrorCode, code)
        assert isinstance(getattr(ErrorCode, code), ErrorCode)


def test_error_message_serialization():
    """Test that error messages can be properly serialized"""
    error_msg = ErrorMessage(
        error_code="TEST_ERROR",
        message="Test error message"
    )
    
    # Should be able to serialize to dict
    error_dict = error_msg.model_dump()
    assert error_dict["type"] == "error"
    assert error_dict["error_code"] == "TEST_ERROR"
    assert error_dict["message"] == "Test error message"
    assert "timestamp" in error_dict
    
    # Should be able to serialize to JSON
    json_str = json.dumps(error_dict, default=str)
    assert "TEST_ERROR" in json_str
    assert "Test error message" in json_str