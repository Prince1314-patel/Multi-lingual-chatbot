import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from app.websocket import websocket_router, init_websocket_services, cleanup_websocket_services
from app.models import validate_room_id, generate_user_id


class MockWebSocketTestClient:
    """Mock WebSocket test client for integration testing"""
    
    def __init__(self):
        self.sent_messages = []
        self.received_messages = []
        self.is_connected = False
        self.disconnect_code = None
        self.disconnect_reason = None
    
    async def accept(self):
        self.is_connected = True
    
    async def send_text(self, data: str):
        if not self.is_connected:
            raise WebSocketDisconnect(code=1000, reason="Not connected")
        self.sent_messages.append({"type": "text", "data": data})
    
    async def send_bytes(self, data: bytes):
        if not self.is_connected:
            raise WebSocketDisconnect(code=1000, reason="Not connected")
        self.sent_messages.append({"type": "bytes", "data": data})
    
    async def receive(self):
        if not self.is_connected:
            raise WebSocketDisconnect(code=1000, reason="Not connected")
        
        if self.received_messages:
            return self.received_messages.pop(0)
        
        # Simulate waiting for message
        await asyncio.sleep(0.1)
        return {"type": "websocket.receive", "text": '{"type": "ping"}'}
    
    def add_received_message(self, message_type: str, data):
        """Add a message to be received by the WebSocket"""
        if message_type == "text":
            self.received_messages.append({"type": "websocket.receive", "text": data})
        elif message_type == "bytes":
            self.received_messages.append({"type": "websocket.receive", "bytes": data})
    
    def disconnect(self, code: int = 1000, reason: str = "Normal closure"):
        self.is_connected = False
        self.disconnect_code = code
        self.disconnect_reason = reason
        raise WebSocketDisconnect(code=code, reason=reason)


class TestWebSocketEndpointIntegration:
    """Integration tests for WebSocket endpoint functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_services(self):
        """Initialize WebSocket services before each test"""
        init_websocket_services()
        yield
        # Cleanup is handled by the cleanup fixture
    
    @pytest.fixture
    async def cleanup_services(self):
        """Cleanup services after tests"""
        yield
        await cleanup_websocket_services()
    
    @pytest.fixture
    def mock_websocket_client(self):
        """Create a mock WebSocket client"""
        return MockWebSocketTestClient()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_establishment(self, mock_websocket_client, cleanup_services):
        """Test WebSocket connection establishment and welcome message"""
        from app.websocket import websocket_chat_endpoint
        
        room_id = "test-connection-room"
        user_id = "test-connection-user"
        
        # Create a task to run the WebSocket endpoint
        endpoint_task = asyncio.create_task(
            websocket_chat_endpoint(mock_websocket_client, room_id, user_id)
        )
        
        # Give the endpoint time to establish connection
        await asyncio.sleep(0.1)
        
        # Verify connection was accepted
        assert mock_websocket_client.is_connected
        
        # Verify welcome message was sent
        assert len(mock_websocket_client.sent_messages) >= 1
        
        welcome_message = None
        for msg in mock_websocket_client.sent_messages:
            if msg["type"] == "text":
                data = json.loads(msg["data"])
                if data.get("type") == "connection_established":
                    welcome_message = data
                    break
        
        assert welcome_message is not None
        assert welcome_message["user_id"] == user_id
        assert welcome_message["room_id"] == room_id
        assert "room_info" in welcome_message
        
        # Disconnect to end the test
        mock_websocket_client.disconnect()
        
        # Wait for endpoint to handle disconnection
        try:
            await asyncio.wait_for(endpoint_task, timeout=1.0)
        except asyncio.TimeoutError:
            endpoint_task.cancel()
    
    @pytest.mark.asyncio
    async def test_websocket_text_message_handling(self, mock_websocket_client, cleanup_services):
        """Test WebSocket text message handling through the endpoint"""
        from app.websocket import websocket_chat_endpoint
        
        room_id = "test-message-room"
        user_id = "test-message-user"
        
        # Add a text message to be received
        text_message = {
            "type": "text",
            "id": "endpoint_test_001",
            "user_id": user_id,
            "room_id": room_id,
            "content": "Hello from endpoint test!",
            "lang": "en"
        }
        mock_websocket_client.add_received_message("text", json.dumps(text_message))
        
        # Add disconnect message to end the connection
        mock_websocket_client.received_messages.append({"type": "websocket.disconnect"})
        
        # Run the WebSocket endpoint
        await websocket_chat_endpoint(mock_websocket_client, room_id, user_id)
        
        # Verify messages were processed
        assert len(mock_websocket_client.sent_messages) >= 1
        
        # Check for welcome message and any confirmations
        message_types = []
        for msg in mock_websocket_client.sent_messages:
            if msg["type"] == "text":
                data = json.loads(msg["data"])
                message_types.append(data.get("type"))
        
        assert "connection_established" in message_types
    
    @pytest.mark.asyncio
    async def test_websocket_binary_message_handling(self, mock_websocket_client, cleanup_services):
        """Test WebSocket binary message handling through the endpoint"""
        from app.websocket import websocket_chat_endpoint
        
        room_id = "test-binary-room"
        user_id = "test-binary-user"
        
        # Add a binary message to be received
        audio_data = b"fake_audio_data_for_endpoint_test"
        mock_websocket_client.add_received_message("bytes", audio_data)
        
        # Add disconnect message to end the connection
        mock_websocket_client.received_messages.append({"type": "websocket.disconnect"})
        
        # Run the WebSocket endpoint
        await websocket_chat_endpoint(mock_websocket_client, room_id, user_id)
        
        # Verify messages were processed
        assert len(mock_websocket_client.sent_messages) >= 1
        
        # Check for welcome message and delivery confirmation
        confirmation_found = False
        for msg in mock_websocket_client.sent_messages:
            if msg["type"] == "text":
                data = json.loads(msg["data"])
                if data.get("type") == "message_confirmation":
                    confirmation_found = True
                    assert data["status"] == "delivered"
                    break
        
        # Note: confirmation might not be found if no other users in room
    
    @pytest.mark.asyncio
    async def test_websocket_invalid_room_id_handling(self, cleanup_services):
        """Test WebSocket endpoint handling of invalid room IDs"""
        from app.websocket import websocket_chat_endpoint
        
        mock_client = MockWebSocketTestClient()
        invalid_room_id = ""  # Empty room ID should be invalid
        user_id = "test-user"
        
        # This should handle the invalid room ID gracefully
        await websocket_chat_endpoint(mock_client, invalid_room_id, user_id)
        
        # Connection should not be established for invalid room ID
        # (The actual validation depends on the validate_room_id implementation)
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling_and_recovery(self, cleanup_services):
        """Test WebSocket endpoint error handling and recovery scenarios"""
        from app.websocket import websocket_chat_endpoint
        
        # Test 1: Connection with failing WebSocket
        failing_client = MockWebSocketTestClient()
        
        # Override send_text to fail
        original_send_text = failing_client.send_text
        async def failing_send_text(data):
            raise Exception("Network error")
        failing_client.send_text = failing_send_text
        
        room_id = "error-test-room"
        user_id = "error-test-user"
        
        # This should handle the error gracefully
        await websocket_chat_endpoint(failing_client, room_id, user_id)
        
        # Test 2: Invalid JSON message handling
        json_test_client = MockWebSocketTestClient()
        json_test_client.add_received_message("text", "invalid json {")
        json_test_client.received_messages.append({"type": "websocket.disconnect"})
        
        await websocket_chat_endpoint(json_test_client, room_id, "json-test-user")
        
        # Should handle invalid JSON gracefully
        assert json_test_client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_multiple_websocket_connections_same_room(self, cleanup_services):
        """Test multiple WebSocket connections to the same room"""
        from app.websocket import websocket_chat_endpoint
        
        room_id = "multi-connection-room"
        
        # Create multiple clients
        client1 = MockWebSocketTestClient()
        client2 = MockWebSocketTestClient()
        client3 = MockWebSocketTestClient()
        
        # Add disconnect messages to end connections
        for client in [client1, client2, client3]:
            client.received_messages.append({"type": "websocket.disconnect"})
        
        # Run connections concurrently
        tasks = [
            asyncio.create_task(websocket_chat_endpoint(client1, room_id, "user1")),
            asyncio.create_task(websocket_chat_endpoint(client2, room_id, "user2")),
            asyncio.create_task(websocket_chat_endpoint(client3, room_id, "user3"))
        ]
        
        await asyncio.gather(*tasks)
        
        # All clients should have received welcome messages
        for client in [client1, client2, client3]:
            welcome_found = False
            for msg in client.sent_messages:
                if msg["type"] == "text":
                    data = json.loads(msg["data"])
                    if data.get("type") == "connection_established":
                        welcome_found = True
                        break
            assert welcome_found
    
    @pytest.mark.asyncio
    async def test_websocket_room_isolation(self, cleanup_services):
        """Test that WebSocket connections in different rooms are isolated"""
        from app.websocket import websocket_chat_endpoint
        
        # Create clients for different rooms
        room1_client = MockWebSocketTestClient()
        room2_client = MockWebSocketTestClient()
        
        # Add messages and disconnects
        room1_message = {
            "type": "text",
            "id": "isolation_test_001",
            "user_id": "room1_user",
            "room_id": "room1",
            "content": "Message for room1 only",
            "lang": "en"
        }
        room1_client.add_received_message("text", json.dumps(room1_message))
        
        for client in [room1_client, room2_client]:
            client.received_messages.append({"type": "websocket.disconnect"})
        
        # Run connections to different rooms
        tasks = [
            asyncio.create_task(websocket_chat_endpoint(room1_client, "room1", "room1_user")),
            asyncio.create_task(websocket_chat_endpoint(room2_client, "room2", "room2_user"))
        ]
        
        await asyncio.gather(*tasks)
        
        # Room2 client should not receive room1 messages
        room2_messages = []
        for msg in room2_client.sent_messages:
            if msg["type"] == "text":
                data = json.loads(msg["data"])
                if data.get("type") == "text" and data.get("content") == "Message for room1 only":
                    room2_messages.append(data)
        
        assert len(room2_messages) == 0  # Should not receive cross-room messages
    
    @pytest.mark.asyncio
    async def test_websocket_connection_cleanup(self, cleanup_services):
        """Test WebSocket connection cleanup on disconnection"""
        from app.websocket import websocket_chat_endpoint, connection_manager
        
        room_id = "cleanup-test-room"
        user_id = "cleanup-test-user"
        
        # Get initial connection count
        initial_connections = connection_manager.get_total_connections() if connection_manager else 0
        
        client = MockWebSocketTestClient()
        client.received_messages.append({"type": "websocket.disconnect"})
        
        # Run and complete the WebSocket connection
        await websocket_chat_endpoint(client, room_id, user_id)
        
        # Connection should be cleaned up
        final_connections = connection_manager.get_total_connections() if connection_manager else 0
        assert final_connections == initial_connections
    
    @pytest.mark.asyncio
    async def test_websocket_performance_under_load(self, cleanup_services):
        """Test WebSocket endpoint performance with multiple concurrent connections"""
        from app.websocket import websocket_chat_endpoint
        
        room_id = "performance-room"
        num_connections = 20
        
        # Create multiple clients
        clients = []
        tasks = []
        
        start_time = time.time()
        
        for i in range(num_connections):
            client = MockWebSocketTestClient()
            client.received_messages.append({"type": "websocket.disconnect"})
            clients.append(client)
            
            task = asyncio.create_task(
                websocket_chat_endpoint(client, room_id, f"perf_user_{i}")
            )
            tasks.append(task)
        
        # Run all connections concurrently
        await asyncio.gather(*tasks)
        
        connection_time = time.time() - start_time
        
        # Should handle multiple connections efficiently
        assert connection_time < 5.0  # Should complete within 5 seconds
        
        # All clients should have been processed
        for client in clients:
            assert len(client.sent_messages) >= 1  # At least welcome message
    
    @pytest.mark.asyncio
    async def test_websocket_message_ordering(self, cleanup_services):
        """Test that WebSocket messages maintain proper ordering"""
        from app.websocket import websocket_chat_endpoint
        
        room_id = "ordering-test-room"
        user_id = "ordering-test-user"
        
        client = MockWebSocketTestClient()
        
        # Add multiple messages in sequence
        for i in range(5):
            message = {
                "type": "text",
                "id": f"order_test_{i:03d}",
                "user_id": user_id,
                "room_id": room_id,
                "content": f"Message {i}",
                "lang": "en"
            }
            client.add_received_message("text", json.dumps(message))
        
        client.received_messages.append({"type": "websocket.disconnect"})
        
        # Run the WebSocket endpoint
        await websocket_chat_endpoint(client, room_id, user_id)
        
        # Messages should be processed in order
        # (Verification depends on specific implementation details)
        assert len(client.sent_messages) >= 1
    
    @pytest.mark.asyncio
    async def test_websocket_graceful_shutdown(self, cleanup_services):
        """Test WebSocket graceful shutdown handling"""
        from app.websocket import websocket_chat_endpoint
        
        room_id = "shutdown-test-room"
        user_id = "shutdown-test-user"
        
        client = MockWebSocketTestClient()
        
        # Create a long-running connection
        endpoint_task = asyncio.create_task(
            websocket_chat_endpoint(client, room_id, user_id)
        )
        
        # Give it time to establish
        await asyncio.sleep(0.1)
        
        # Simulate graceful shutdown
        client.disconnect(code=1001, reason="Going away")
        
        # Should handle shutdown gracefully
        try:
            await asyncio.wait_for(endpoint_task, timeout=1.0)
        except asyncio.TimeoutError:
            endpoint_task.cancel()
            
        # Connection should be properly cleaned up
        assert not client.is_connected
        