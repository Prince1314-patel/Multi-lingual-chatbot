import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from app.services.connection_manager import ConnectionManager
from app.services.message_handler import MessageHandler
from app.services.room_manager import RoomManager
from app.models import (
    TextMessage,
    VoiceMessage,
    TypingMessage,
    ConnectionInfo,
    Room,
    serialize_message
)


class TestFinalComprehensiveIntegration:
    """Final comprehensive integration tests covering all requirements:
    - Complete text message flow (Requirements: 2.1, 2.2)
    - Multi-user chat room testing scenarios (Requirements: 2.1, 2.2)
    - Voice message end-to-end integration tests (Requirements: 3.1, 3.2)
    - Connection recovery and error handling tests (Requirements: 2.5)
    """
    
    @pytest.fixture
    def services(self):
        """Create integrated service instances"""
        from app.services.rate_limiter import RateLimiter, RateLimitConfig
        rate_limiter = RateLimiter(RateLimitConfig())
        room_manager = RoomManager()
        connection_manager = ConnectionManager(rate_limiter)
        message_handler = MessageHandler(connection_manager, room_manager, rate_limiter)
        return connection_manager, room_manager, message_handler
    
    @pytest.fixture
    def mock_websocket_factory(self):
        """Factory to create multiple mock WebSockets"""
        def create_websocket():
            websocket = MagicMock(spec=WebSocket)
            websocket.accept = AsyncMock()
            websocket.send_text = AsyncMock()
            websocket.send_bytes = AsyncMock()
            websocket.receive = AsyncMock()
            return websocket
        return create_websocket

    @pytest.mark.asyncio
    async def test_complete_text_message_flow_integration(self, services):
        """Test complete text message flow from sender to receiver with delivery confirmation
        Requirements: 2.1, 2.2"""
        connection_manager, room_manager, message_handler = services
        room_id = "integration-text-room"
        
        # Create mock websockets for sender and receiver
        sender_ws = MagicMock(spec=WebSocket)
        sender_ws.accept = AsyncMock()
        sender_ws.send_text = AsyncMock()
        
        receiver_ws = MagicMock(spec=WebSocket)
        receiver_ws.accept = AsyncMock()
        receiver_ws.send_text = AsyncMock()
        
        # Step 1: Connect both users to the room
        sender_connection = await connection_manager.connect(sender_ws, room_id, "sender_user")
        receiver_connection = await connection_manager.connect(receiver_ws, room_id, "receiver_user")
        
        # Verify connections established
        assert sender_connection.user_id == "sender_user"
        assert receiver_connection.user_id == "receiver_user"
        assert connection_manager.get_room_connection_count(room_id) == 2
        
        # Step 2: Create and send text message
        text_message = TextMessage(
            id="test_msg_001",
            user_id="sender_user",
            room_id=room_id,
            content="Hello, this is a test message!"
        )
        
        # Reset mocks to track message handling
        sender_ws.send_text.reset_mock()
        receiver_ws.send_text.reset_mock()
        
        # Step 3: Handle the message through the message handler
        result = await message_handler.handle_text_message(sender_connection, text_message)
        
        # Verify message was processed successfully
        assert result is True
        
        # Step 4: Verify message was sent to receiver
        receiver_ws.send_text.assert_called_once()
        receiver_call_args = receiver_ws.send_text.call_args[0][0]
        receiver_message = json.loads(receiver_call_args)
        
        assert receiver_message["type"] == "text"
        assert receiver_message["id"] == "test_msg_001"
        assert receiver_message["user_id"] == "sender_user"
        assert receiver_message["content"] == "Hello, this is a test message!"
        assert "timestamp" in receiver_message
        
        # Step 5: Verify delivery confirmation was sent to sender
        sender_ws.send_text.assert_called_once()
        sender_call_args = sender_ws.send_text.call_args[0][0]
        confirmation_message = json.loads(sender_call_args)
        
        assert confirmation_message["type"] == "message_confirmation"
        assert confirmation_message["message_id"] == "test_msg_001"
        assert confirmation_message["status"] == "delivered"
        assert confirmation_message["user_id"] == "sender_user"
        assert confirmation_message["room_id"] == room_id  
  
    @pytest.mark.asyncio
    async def test_multi_user_chat_room_scenarios_integration(self, services, mock_websocket_factory):
        """Test multi-user chat room scenarios with concurrent users
        Requirements: 2.1, 2.2"""
        connection_manager, room_manager, message_handler = services
        room_id = "multi-user-room"
        
        # Create 5 users for comprehensive testing
        users = []
        websockets = []
        connections = []
        
        for i in range(5):
            ws = mock_websocket_factory()
            user_id = f"user_{i}"
            websockets.append(ws)
            
            # Connect user to room
            connection = await connection_manager.connect(ws, room_id, user_id)
            connections.append(connection)
            users.append(user_id)
        
        # Verify all users connected
        assert connection_manager.get_room_connection_count(room_id) == 5
        
        # Test 1: Broadcast message from user_0 to all others
        sender_connection = connections[0]
        sender_ws = websockets[0]
        
        # Reset all mocks
        for ws in websockets:
            ws.send_text.reset_mock()
        
        # Send message from user_0
        broadcast_message = TextMessage(
            id="broadcast_msg_001",
            user_id="user_0",
            room_id=room_id,
            content="Hello everyone!"
        )
        
        result = await message_handler.handle_text_message(sender_connection, broadcast_message)
        assert result is True
        
        # Verify message sent to all other users (not sender)
        for i, ws in enumerate(websockets):
            if i == 0:  # Sender should only receive confirmation
                ws.send_text.assert_called_once()
                call_args = ws.send_text.call_args[0][0]
                message = json.loads(call_args)
                assert message["type"] == "message_confirmation"
            else:  # Receivers should get the message
                ws.send_text.assert_called_once()
                call_args = ws.send_text.call_args[0][0]
                message = json.loads(call_args)
                assert message["type"] == "text"
                assert message["content"] == "Hello everyone!"
                assert message["user_id"] == "user_0"
        
        # Test 2: Concurrent messages from multiple users
        # Reset mocks
        for ws in websockets:
            ws.send_text.reset_mock()
        
        # Send messages concurrently from users 1, 2, 3
        concurrent_tasks = []
        for i in range(1, 4):
            message = TextMessage(
                id=f"concurrent_msg_{i}",
                user_id=f"user_{i}",
                room_id=room_id,
                content=f"Concurrent message from user {i}"
            )
            task = asyncio.create_task(
                message_handler.handle_text_message(connections[i], message)
            )
            concurrent_tasks.append(task)
        
        # Wait for all concurrent messages to complete
        results = await asyncio.gather(*concurrent_tasks)
        assert all(results)  # All messages should be processed successfully
        
        # Verify each user received messages from others
        for i, ws in enumerate(websockets):
            if i in [1, 2, 3]:  # Senders should receive confirmations + messages from others
                assert ws.send_text.call_count >= 1
            else:  # Non-senders should receive all 3 messages
                assert ws.send_text.call_count == 3
        
        # Test 3: User disconnection and reconnection
        # Disconnect user_2
        disconnected_connection = await connection_manager.disconnect(websockets[2], broadcast_leave=True)
        assert disconnected_connection.user_id == "user_2"
        assert connection_manager.get_room_connection_count(room_id) == 4
        
        # Reconnect user_2
        new_ws = mock_websocket_factory()
        new_connection = await connection_manager.connect(new_ws, room_id, "user_2_reconnected")
        assert connection_manager.get_room_connection_count(room_id) == 5

    @pytest.mark.asyncio
    async def test_voice_message_end_to_end_integration(self, services):
        """Test complete voice message flow including binary data transmission
        Requirements: 3.1, 3.2"""
        connection_manager, room_manager, message_handler = services
        room_id = "voice-integration-room"
        
        # Create mock websockets for sender and receiver
        sender_ws = MagicMock(spec=WebSocket)
        sender_ws.accept = AsyncMock()
        sender_ws.send_text = AsyncMock()
        sender_ws.send_bytes = AsyncMock()
        
        receiver_ws = MagicMock(spec=WebSocket)
        receiver_ws.accept = AsyncMock()
        receiver_ws.send_text = AsyncMock()
        receiver_ws.send_bytes = AsyncMock()
        
        # Connect both users
        sender_connection = await connection_manager.connect(sender_ws, room_id, "voice_sender")
        receiver_connection = await connection_manager.connect(receiver_ws, room_id, "voice_receiver")
        
        # Reset mocks to track voice message handling
        sender_ws.send_text.reset_mock()
        sender_ws.send_bytes.reset_mock()
        receiver_ws.send_text.reset_mock()
        receiver_ws.send_bytes.reset_mock()
        
        # Step 1: Test binary voice data handling
        audio_data = b"fake_audio_data_for_integration_test_12345"
        
        # Handle binary message (simulating voice recording)
        result = await message_handler.handle_binary_message(sender_ws, audio_data)
        assert result is True
        
        # Verify binary data was sent to receiver
        receiver_ws.send_bytes.assert_called_once_with(audio_data)
        
        # Verify delivery confirmation sent to sender
        sender_ws.send_text.assert_called_once()
        confirmation_call = sender_ws.send_text.call_args[0][0]
        confirmation = json.loads(confirmation_call)
        
        assert confirmation["type"] == "message_confirmation"
        assert confirmation["status"] == "delivered"
        assert confirmation["user_id"] == "voice_sender"
        assert confirmation["room_id"] == room_id
        
        # Step 2: Test voice message object creation and transmission
        sender_ws.send_text.reset_mock()
        receiver_ws.send_bytes.reset_mock()
        
        voice_message = VoiceMessage(
            id="voice_msg_001",
            user_id="voice_sender",
            room_id=room_id,
            audio_data=audio_data,
            duration=5.5,
            audio_format="webm"
        )
        
        result = await message_handler.handle_voice_message(sender_connection, voice_message)
        assert result is True
        
        # Verify voice message was broadcast as binary data
        receiver_ws.send_bytes.assert_called_once_with(audio_data)
        
        # Step 3: Test large voice message handling
        large_audio_data = b"x" * (5 * 1024 * 1024)  # 5MB audio file
        
        sender_ws.send_text.reset_mock()
        receiver_ws.send_bytes.reset_mock()
        
        result = await message_handler.handle_binary_message(sender_ws, large_audio_data)
        assert result is True  # Should handle large files within limits
        
        # Verify large file was transmitted
        receiver_ws.send_bytes.assert_called_once_with(large_audio_data)
        
        # Step 4: Test voice message size limits
        oversized_audio_data = b"x" * (15 * 1024 * 1024)  # 15MB - exceeds limit
        
        sender_ws.send_text.reset_mock()
        receiver_ws.send_bytes.reset_mock()
        
        result = await message_handler.handle_binary_message(sender_ws, oversized_audio_data)
        assert result is False  # Should reject oversized files
        
        # Verify error message sent to sender
        sender_ws.send_text.assert_called_once()
        error_call = sender_ws.send_text.call_args[0][0]
        error_message = json.loads(error_call)
        
        assert error_message["type"] == "error"
        assert "BINARY_DATA_TOO_LARGE" in error_message["error_code"] 
   
    @pytest.mark.asyncio
    async def test_connection_recovery_and_error_handling_integration(self, services):
        """Test connection recovery scenarios and comprehensive error handling
        Requirements: 2.5"""
        connection_manager, room_manager, message_handler = services
        room_id = "recovery-test-room"
        
        # Test 1: WebSocket disconnection during message sending
        sender_ws = MagicMock(spec=WebSocket)
        sender_ws.accept = AsyncMock()
        sender_ws.send_text = AsyncMock(side_effect=WebSocketDisconnect(code=1001, reason="Going away"))
        
        receiver_ws = MagicMock(spec=WebSocket)
        receiver_ws.accept = AsyncMock()
        receiver_ws.send_text = AsyncMock()
        
        # Connect users
        sender_connection = await connection_manager.connect(sender_ws, room_id, "unstable_sender")
        receiver_connection = await connection_manager.connect(receiver_ws, room_id, "stable_receiver")
        
        # Reset mocks
        sender_ws.send_text.reset_mock()
        receiver_ws.send_text.reset_mock()
        
        # Try to send message from unstable sender
        text_message = TextMessage(
            id="recovery_msg_001",
            user_id="unstable_sender",
            room_id=room_id,
            content="This message should handle disconnection gracefully"
        )
        
        # Message handling should not crash even if sender disconnects
        result = await message_handler.handle_text_message(sender_connection, text_message)
        assert result is True  # Handler should complete successfully
        
        # Receiver should still get the message
        receiver_ws.send_text.assert_called_once()
        
        # Test 2: Network failure simulation
        failing_ws = MagicMock(spec=WebSocket)
        failing_ws.accept = AsyncMock()
        failing_ws.send_text = AsyncMock(side_effect=Exception("Network error"))
        failing_ws.send_bytes = AsyncMock(side_effect=Exception("Network error"))
        
        # Connect failing user
        failing_connection = await connection_manager.connect(failing_ws, room_id, "failing_user")
        
        # Reset receiver mock
        receiver_ws.send_text.reset_mock()
        
        # Send message that should trigger cleanup of failed connection
        recovery_message = TextMessage(
            id="recovery_msg_002",
            user_id="stable_receiver",
            room_id=room_id,
            content="Testing connection cleanup"
        )
        
        result = await message_handler.handle_text_message(receiver_connection, recovery_message)
        assert result is True
        
        # Test 3: Room cleanup after all users disconnect
        initial_room_count = len(connection_manager.get_active_rooms())
        
        # Disconnect all users
        await connection_manager.disconnect(receiver_ws, broadcast_leave=True)
        await connection_manager.disconnect(failing_ws, broadcast_leave=False)  # Already failed
        
        # Room should be cleaned up
        final_room_count = len(connection_manager.get_active_rooms())
        assert final_room_count <= initial_room_count
        assert connection_manager.get_room_connection_count(room_id) == 0
        
        # Test 4: Reconnection after disconnection
        new_ws = MagicMock(spec=WebSocket)
        new_ws.accept = AsyncMock()
        new_ws.send_text = AsyncMock()
        
        # Reconnect user to same room
        reconnected_connection = await connection_manager.connect(new_ws, room_id, "reconnected_user")
        assert reconnected_connection.user_id == "reconnected_user"
        assert connection_manager.get_room_connection_count(room_id) == 1
        
        # Test 5: Invalid message format handling
        invalid_message_data = {"invalid": "format", "missing": "required_fields"}
        
        new_ws.send_text.reset_mock()
        
        # This should trigger error handling
        result = await message_handler.handle_message(new_ws, invalid_message_data)
        assert result is False
        
        # Error message should be sent
        new_ws.send_text.assert_called_once()
        error_call = new_ws.send_text.call_args[0][0]
        error_message = json.loads(error_call)
        assert error_message["type"] == "error"

    @pytest.mark.asyncio
    async def test_typing_indicators_integration_basic(self, services):
        """Test basic typing indicators functionality
        Requirements: 2.1, 2.2"""
        connection_manager, room_manager, message_handler = services
        room_id = "typing-integration-room"
        
        # Create multiple users
        user1_ws = MagicMock(spec=WebSocket)
        user1_ws.accept = AsyncMock()
        user1_ws.send_text = AsyncMock()
        
        user2_ws = MagicMock(spec=WebSocket)
        user2_ws.accept = AsyncMock()
        user2_ws.send_text = AsyncMock()
        
        # Connect users
        user1_conn = await connection_manager.connect(user1_ws, room_id, "typing_user1")
        user2_conn = await connection_manager.connect(user2_ws, room_id, "typing_user2")
        
        # Reset mocks
        user1_ws.send_text.reset_mock()
        user2_ws.send_text.reset_mock()
        
        # Test: User starts typing
        typing_message = TypingMessage(
            user_id="typing_user1",
            room_id=room_id,
            is_typing=True
        )
        
        # Create room first to avoid the "room not found" issue
        room = room_manager.get_or_create_room(room_id)
        assert room is not None
        
        result = await message_handler.handle_typing_message(user1_conn, typing_message)
        assert result is True
        
        # Other user should receive typing indicator
        user2_ws.send_text.assert_called_once()
        call_args = user2_ws.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == "typing"
        assert message["user_id"] == "typing_user1"
        assert message["is_typing"] is True
        
        # Sender should not receive their own typing indicator
        user1_ws.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_room_isolation_and_cross_room_security_integration(self, services):
        """Test that messages are properly isolated between rooms"""
        connection_manager, room_manager, message_handler = services
        
        # Create users in different rooms
        room1_user_ws = MagicMock(spec=WebSocket)
        room1_user_ws.accept = AsyncMock()
        room1_user_ws.send_text = AsyncMock()
        
        room2_user_ws = MagicMock(spec=WebSocket)
        room2_user_ws.accept = AsyncMock()
        room2_user_ws.send_text = AsyncMock()
        
        # Connect users to different rooms
        room1_conn = await connection_manager.connect(room1_user_ws, "test-room-1", "user_in_room1")
        room2_conn = await connection_manager.connect(room2_user_ws, "test-room-2", "user_in_room2")
        
        # Reset mocks
        room1_user_ws.send_text.reset_mock()
        room2_user_ws.send_text.reset_mock()
        
        # Send message in room1
        room1_message = TextMessage(
            id="isolation_test_001",
            user_id="user_in_room1",
            room_id="test-room-1",
            content="This message should only be in room1"
        )
        
        result = await message_handler.handle_text_message(room1_conn, room1_message)
        assert result is True
        
        # User in room1 should receive confirmation
        room1_user_ws.send_text.assert_called_once()
        
        # User in room2 should NOT receive the message
        room2_user_ws.send_text.assert_not_called()
        
        # Verify room statistics are independent
        room1_stats = connection_manager.get_room_stats("test-room-1")
        room2_stats = connection_manager.get_room_stats("test-room-2")
        
        assert room1_stats["connection_count"] == 1
        assert room2_stats["connection_count"] == 1
        # Note: message_count might be 0 if only confirmations are sent, not actual messages to other users

    @pytest.mark.asyncio
    async def test_performance_under_load_integration(self, services, mock_websocket_factory):
        """Test system performance with multiple concurrent operations"""
        connection_manager, room_manager, message_handler = services
        room_id = "performance-test-room"
        
        # Create 10 concurrent users
        connections = []
        websockets = []
        
        start_time = time.time()
        
        # Connect users concurrently
        connect_tasks = []
        for i in range(10):
            ws = mock_websocket_factory()
            websockets.append(ws)
            task = asyncio.create_task(
                connection_manager.connect(ws, room_id, f"perf_user_{i}")
            )
            connect_tasks.append(task)
        connections = await asyncio.gather(*connect_tasks)
        connection_time = time.time() - start_time
        
        # Verify all connections established quickly
        assert len(connections) == 10
        assert connection_time < 1.0  # Should cn 1 second
        assert connection_manager.get_room_connection_count(room_id) == 10
        
        # Send messages concurrently from all users
        message_start_time = time.time()
        message_tasks = []
        
        for i, connection in enumerate(connections):
            message = TextMessage(
                id=f"perf_msg_{i}",
                user_id=f"perf_user_{i}",
                room_id=room_id,
                content=f"Performance test message {i}"
            )
            task = asyncio.create_task(
                message_handler.handle_text_message(connection, message)
            )
            message_tasks.append(task)
        
        results = await asyncio.gather(*message_tasks)
        message_time = time.time() - message_start_time
        
        # Verify all messages processed successfully and quickly
        assert all(results)
        assert message_time < 2.0  # Should process within 2 seconds
        
        # Verify room statistics
        room_stats = connection_manager.get_room_stats(room_id)
        assert room_stats["connection_count"] == 10    
        
    @pytest.mark.asyncio
    async def test_message_ordering_and_consistency_integration(self, services):
        """Test message ordering and consistency in high-throughput scenarios"""
        connection_manager, room_manager, message_handler = services
        room_id = "ordering-test-room"
        
        # Create sender and receiver
        sender_ws = MagicMock(spec=WebSocket)
        sender_ws.accept = AsyncMock()
        sender_ws.send_text = AsyncMock()
        
        receiver_ws = MagicMock(spec=WebSocket)
        receiver_ws.accept = AsyncMock()
        receiver_ws.send_text = AsyncMock()
        
        sender_conn = await connection_manager.connect(sender_ws, room_id, "sender")
        receiver_conn = await connection_manager.connect(receiver_ws, room_id, "receiver")
        
        # Reset mocks
        sender_ws.send_text.reset_mock()
        receiver_ws.send_text.reset_mock()
        
        # Send multiple messages in rapid succession
        message_tasks = []
        for i in range(20):
            message = TextMessage(
                id=f"order_msg_{i:03d}",
                user_id="sender",
                room_id=room_id,
                content=f"Message {i}"
            )
            task = asyncio.create_task(
                message_handler.handle_text_message(sender_conn, message)
            )
            message_tasks.append(task)
        
        # Wait for all messages to be processed
        results = await asyncio.gather(*message_tasks)
        assert all(results)
        
        # Verify all messages were sent
        assert receiver_ws.send_text.call_count == 20
        assert sender_ws.send_text.call_count == 20  # Confirmations
        
        # Verify message content consistency
        received_messages = []
        for call in receiver_ws.send_text.call_args_list:
            message_data = json.loads(call[0][0])
            if message_data["type"] == "text":
                received_messages.append(message_data)
        
        assert len(received_messages) == 20
        
        # Verify all messages have correct structure
        for msg in received_messages:
            assert msg["type"] == "text"
            assert msg["user_id"] == "sender"
            assert msg["room_id"] == room_id
            assert "content" in msg
            assert "timestamp" in msg

    @pytest.mark.asyncio
    async def test_concurrent_room_operations_integration(self, services, mock_websocket_factory):
        """Test concurrent operations across multiple rooms"""
        connection_manager, room_manager, message_handler = services
        
        # Create multiple rooms with users
        rooms = ["room-a", "room-b", "room-c"]
        room_connections = {}
        
        # Set up users in each room
        for room_id in rooms:
            connections = []
            for i in range(3):  # 3 users per room
                ws = mock_websocket_factory()
                user_id = f"{room_id}_user_{i}"
                conn = await connection_manager.connect(ws, room_id, user_id)
                connections.append((ws, conn))
            room_connections[room_id] = connections
        
        # Verify all rooms are set up correctly
        for room_id in rooms:
            assert connection_manager.get_room_connection_count(room_id) == 3
        
        # Send concurrent messages across all rooms
        all_tasks = []
        for room_id in rooms:
            connections = room_connections[room_id]
            for i, (ws, conn) in enumerate(connections):
                # Reset mock
                ws.send_text.reset_mock()
                
                # Create message
                message = TextMessage(
                    id=f"{room_id}_msg_{i}",
                    user_id=conn.user_id,
                    room_id=room_id,
                    content=f"Message from {conn.user_id}"
                )
                
                # Add to concurrent tasks
                task = asyncio.create_task(
                    message_handler.handle_text_message(conn, message)
                )
                all_tasks.append(task)
        
        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*all_tasks)
        execution_time = time.time() - start_time
        
        # Verify all messages processed successfully
        assert all(results)
        assert execution_time < 3.0  # Should complete within 3 seconds
        
        # Verify room isolation - each room should have received only its own messages
        for room_id in rooms:
            connections = room_connections[room_id]
            for ws, conn in connections:
                # Each user should receive messages from other users in the same room
                # Plus their own confirmation
                expected_calls = 3  # 2 messages from others + 1 confirmation for own message
                assert ws.send_text.call_count == expected_calls

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios_integration(self, services):
        """Test various error scenarios and recovery mechanisms"""
        connection_manager, room_manager, message_handler = services
        room_id = "error-recovery-room"
        
        # Test 1: Connection with valid room ID
        valid_ws = MagicMock(spec=WebSocket)
        valid_ws.accept = AsyncMock()
        valid_ws.send_text = AsyncMock()
        
        # This should work as the connection manager handles room creation
        connection = await connection_manager.connect(valid_ws, "test-room-123", "test_user")
        assert connection.user_id == "test_user"
        
        # Test 2: Message with missing required fields
        incomplete_message_data = {
            "type": "text",
            "content": "Missing user_id and room_id"
        }
        
        valid_ws.send_text.reset_mock()
        result = await message_handler.handle_message(valid_ws, incomplete_message_data)
        assert result is False
        
        # Error should be sent to user
        valid_ws.send_text.assert_called_once()
        
        # Test 3: Binary message with empty data
        empty_binary_result = await message_handler.handle_binary_message(valid_ws, b"")
        assert empty_binary_result is False
        
        # Test 4: Connection cleanup after errors
        initial_connections = connection_manager.get_total_connections()
        
        # Simulate connection failure during cleanup
        failing_ws = MagicMock(spec=WebSocket)
        failing_ws.accept = AsyncMock()
        failing_ws.send_text = AsyncMock(side_effect=Exception("Connection failed"))
        
        failing_connection = await connection_manager.connect(failing_ws, room_id, "failing_user")
        
        # Disconnect should handle the failure gracefully
        result = await connection_manager.disconnect(failing_ws, broadcast_leave=True)
        assert result is not None  # Should return the connection info even if broadcast fails

    @pytest.mark.asyncio
    async def test_comprehensive_end_to_end_integration(self, services, mock_websocket_factory):
        """Test comprehensive end-to-end integration covering all major features"""
        connection_manager, room_manager, message_handler = services
        room_id = "comprehensive-test-room"
        
        # Create multiple users
        users = []
        for i in range(4):
            ws = mock_websocket_factory()
            user_id = f"comprehensive_user_{i}"
            conn = await connection_manager.connect(ws, room_id, user_id)
            users.append((ws, conn, user_id))
        
        # Verify all users connected
        assert connection_manager.get_room_connection_count(room_id) == 4
        
        # Test 1: Text message flow
        sender_ws, sender_conn, sender_id = users[0]
        sender_ws.send_text.reset_mock()
        
        # Reset all other users' mocks
        for ws, _, _ in users[1:]:
            ws.send_text.reset_mock()
        
        text_message = TextMessage(
            id="comprehensive_text_001",
            user_id=sender_id,
            room_id=room_id,
            content="Comprehensive test message"
        )
        
        result = await message_handler.handle_text_message(sender_conn, text_message)
        assert result is True
        
        # Verify sender received confirmation
        sender_ws.send_text.assert_called_once()
        
        # Verify other users received the message
        for ws, _, _ in users[1:]:
            ws.send_text.assert_called_once()
        
        # Test 2: Voice message flow
        voice_sender_ws, voice_sender_conn, voice_sender_id = users[1]
        voice_sender_ws.send_text.reset_mock()
        voice_sender_ws.send_bytes.reset_mock()
        
        # Reset other users' mocks
        for ws, _, _ in users:
            if ws != voice_sender_ws:
                ws.send_bytes.reset_mock()
        
        audio_data = b"comprehensive_test_audio_data"
        result = await message_handler.handle_binary_message(voice_sender_ws, audio_data)
        assert result is True
        
        # Verify voice sender received confirmation
        voice_sender_ws.send_text.assert_called_once()
        
        # Verify other users received the audio data
        for ws, _, _ in users:
            if ws != voice_sender_ws:
                ws.send_bytes.assert_called_once_with(audio_data)
        
        # Test 3: User disconnection
        disconnect_ws, disconnect_conn, disconnect_id = users[2]
        result = await connection_manager.disconnect(disconnect_ws, broadcast_leave=True)
        assert result.user_id == disconnect_id
        assert connection_manager.get_room_connection_count(room_id) == 3
        
        # Test 4: Performance under concurrent load
        remaining_users = users[:2] + users[3:]  # Skip disconnected user
        
        # Send concurrent messages
        concurrent_tasks = []
        for ws, conn, user_id in remaining_users:
            ws.send_text.reset_mock()
            message = TextMessage(
                id=f"concurrent_{user_id}",
                user_id=user_id,
                room_id=room_id,
                content=f"Concurrent message from {user_id}"
            )
            task = asyncio.create_task(
                message_handler.handle_text_message(conn, message)
            )
            concurrent_tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks)
        execution_time = time.time() - start_time
        
        # Verify all concurrent messages processed successfully
        assert all(results)
        assert execution_time < 1.0  # Should be fast
        
        # Verify final room state
        room_stats = connection_manager.get_room_stats(room_id)
        assert room_stats["connection_count"] == 3  # One user disconnected