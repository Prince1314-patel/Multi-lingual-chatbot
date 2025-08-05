import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket

from app.services.connection_manager import ConnectionManager
from app.services.message_handler import MessageHandler
from app.services.room_manager import RoomManager


class TestIntegrationUserNotifications:
    """Integration tests for user join/leave notifications across all services"""
    
    @pytest.fixture
    def services(self):
        """Create integrated service instances"""
        room_manager = RoomManager()
        connection_manager = ConnectionManager(room_manager)
        message_handler = MessageHandler(connection_manager, room_manager)
        return connection_manager, room_manager, message_handler
    
    @pytest.fixture
    def mock_websocket(self):
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.send_bytes = AsyncMock()
        return websocket
    
    @pytest.fixture
    def mock_websocket2(self):
        websocket = MagicMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.send_bytes = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_complete_user_join_leave_flow(self, services, mock_websocket, mock_websocket2):
        """Test complete flow of users joining and leaving with proper notifications"""
        connection_manager, room_manager, message_handler = services
        room_id = "integration-test-room"
        user1_id = "integration_user1"
        user2_id = "integration_user2"
        
        # Step 1: First user joins
        connection1 = await connection_manager.connect(mock_websocket, room_id, user1_id)
        
        # Verify room was created and user connected
        assert connection1.user_id == user1_id
        assert connection1.room_id == room_id
        assert connection_manager.get_room_connection_count(room_id) == 1
        
        # Verify room exists in connection manager
        room = connection_manager.get_room(room_id)
        assert room is not None
        assert room.get_connection_count() == 1
        
        # Step 2: Second user joins (should trigger join notification)
        mock_websocket.send_text.reset_mock()
        connection2 = await connection_manager.connect(mock_websocket2, room_id, user2_id)
        
        # Verify second user connected
        assert connection2.user_id == user2_id
        assert connection2.room_id == room_id
        assert connection_manager.get_room_connection_count(room_id) == 2
        
        # Verify join notification was sent to first user
        mock_websocket.send_text.assert_called_once()
        join_call_args = mock_websocket.send_text.call_args[0][0]
        join_message = json.loads(join_call_args)
        
        assert join_message["type"] == "user_join"
        assert join_message["user_id"] == user2_id
        assert join_message["room_id"] == room_id
        
        # Step 3: First user leaves (should trigger leave notification)
        mock_websocket.send_text.reset_mock()
        mock_websocket2.send_text.reset_mock()
        
        disconnected = await connection_manager.disconnect(mock_websocket, broadcast_leave=True)
        
        # Verify user was disconnected
        assert disconnected.user_id == user1_id
        assert connection_manager.get_room_connection_count(room_id) == 1
        
        # Verify leave notification was sent to remaining user
        mock_websocket2.send_text.assert_called_once()
        leave_call_args = mock_websocket2.send_text.call_args[0][0]
        leave_message = json.loads(leave_call_args)
        
        assert leave_message["type"] == "user_leave"
        assert leave_message["user_id"] == user1_id
        assert leave_message["room_id"] == room_id
        
        # Step 4: Last user leaves (room should be cleaned up)
        await connection_manager.disconnect(mock_websocket2, broadcast_leave=True)
        
        # Verify room was cleaned up
        assert connection_manager.get_room_connection_count(room_id) == 0
        assert room_id not in connection_manager.rooms
    
    @pytest.mark.asyncio
    async def test_room_stats_with_user_notifications(self, services, mock_websocket, mock_websocket2):
        """Test that room statistics are properly updated with user join/leave events"""
        connection_manager, room_manager, message_handler = services
        room_id = "stats-test-room"
        user1_id = "stats_user1"
        user2_id = "stats_user2"
        
        # Initial state - no room exists
        assert connection_manager.get_room_stats(room_id) is None
        
        # First user joins
        await connection_manager.connect(mock_websocket, room_id, user1_id)
        
        # Check room stats after first user
        stats = connection_manager.get_room_stats(room_id)
        assert stats is not None
        assert stats['connection_count'] == 1
        assert stats['room_id'] == room_id
        
        # Second user joins
        await connection_manager.connect(mock_websocket2, room_id, user2_id)
        
        # Check room stats after second user
        stats = connection_manager.get_room_stats(room_id)
        assert stats['connection_count'] == 2
        
        # First user leaves
        await connection_manager.disconnect(mock_websocket, broadcast_leave=True)
        
        # Check room stats after user leaves
        stats = connection_manager.get_room_stats(room_id)
        assert stats['connection_count'] == 1
        
        # Last user leaves
        await connection_manager.disconnect(mock_websocket2, broadcast_leave=True)
        
        # Room should be cleaned up
        assert connection_manager.get_room_stats(room_id) is None
    
    @pytest.mark.asyncio
    async def test_multiple_rooms_user_notifications(self, services):
        """Test user notifications work correctly across multiple rooms"""
        connection_manager, room_manager, message_handler = services
        
        # Create websockets for different rooms
        room1_ws1 = MagicMock(spec=WebSocket)
        room1_ws1.accept = AsyncMock()
        room1_ws1.send_text = AsyncMock()
        
        room1_ws2 = MagicMock(spec=WebSocket)
        room1_ws2.accept = AsyncMock()
        room1_ws2.send_text = AsyncMock()
        
        room2_ws1 = MagicMock(spec=WebSocket)
        room2_ws1.accept = AsyncMock()
        room2_ws1.send_text = AsyncMock()
        
        # Users join different rooms
        await connection_manager.connect(room1_ws1, "test-room-1", "user1")
        await connection_manager.connect(room2_ws1, "test-room-2", "user2")
        
        # Reset mocks
        room1_ws1.send_text.reset_mock()
        room2_ws1.send_text.reset_mock()
        
        # Another user joins room1 (should only notify users in room1)
        await connection_manager.connect(room1_ws2, "test-room-1", "user3")
        
        # Verify notification only sent to room1 users
        room1_ws1.send_text.assert_called_once()  # user1 in room1 gets notification
        room2_ws1.send_text.assert_not_called()   # user2 in room2 gets no notification
        
        # Verify room stats are independent
        assert connection_manager.get_room_connection_count("test-room-1") == 2
        assert connection_manager.get_room_connection_count("test-room-2") == 1
    
    @pytest.mark.asyncio
    async def test_user_notification_message_format(self, services, mock_websocket, mock_websocket2):
        """Test that user notification messages have the correct format for frontend consumption"""
        connection_manager, room_manager, message_handler = services
        room_id = "format-test-room"
        user1_id = "format_user1"
        user2_id = "format_user2"
        
        # First user joins
        await connection_manager.connect(mock_websocket, room_id, user1_id)
        
        # Second user joins
        mock_websocket.send_text.reset_mock()
        await connection_manager.connect(mock_websocket2, room_id, user2_id)
        
        # Verify join message format
        join_call_args = mock_websocket.send_text.call_args[0][0]
        join_message = json.loads(join_call_args)
        
        # Check required fields for frontend
        required_fields = ["type", "user_id", "room_id", "timestamp"]
        for field in required_fields:
            assert field in join_message, f"Missing required field: {field}"
        
        assert join_message["type"] == "user_join"
        assert isinstance(join_message["timestamp"], str)
        
        # Test leave message format
        mock_websocket2.send_text.reset_mock()
        await connection_manager.disconnect(mock_websocket, broadcast_leave=True)
        
        # Verify leave message format
        leave_call_args = mock_websocket2.send_text.call_args[0][0]
        leave_message = json.loads(leave_call_args)
        
        # Check required fields for frontend
        for field in required_fields:
            assert field in leave_message, f"Missing required field: {field}"
        
        assert leave_message["type"] == "user_leave"
        assert isinstance(leave_message["timestamp"], str)
    
    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self, services):
        """Test user notifications work correctly with concurrent join/leave operations"""
        connection_manager, room_manager, message_handler = services
        room_id = "concurrent-test-room"
        
        # Create multiple websockets
        websockets = []
        user_ids = []
        
        for i in range(5):
            ws = MagicMock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            websockets.append(ws)
            user_ids.append(f"concurrent_user{i}")
        
        # Simulate concurrent joins
        join_tasks = []
        for i, (ws, user_id) in enumerate(zip(websockets, user_ids)):
            task = asyncio.create_task(
                connection_manager.connect(ws, room_id, user_id)
            )
            join_tasks.append(task)
        
        # Wait for all joins to complete
        connections = await asyncio.gather(*join_tasks)
        
        # Verify all users connected
        assert len(connections) == 5
        assert connection_manager.get_room_connection_count(room_id) == 5
        
        # Verify each user (except the first) received join notifications for users who joined after them
        for i, ws in enumerate(websockets):
            if i == 0:
                # First user should have received 4 join notifications (for users 1-4)
                assert ws.send_text.call_count == 4
            elif i == 1:
                # Second user should have received 3 join notifications (for users 2-4)
                assert ws.send_text.call_count == 3
            # And so on...
        
        # Test concurrent disconnections
        disconnect_tasks = []
        for ws in websockets[:3]:  # Disconnect first 3 users
            task = asyncio.create_task(
                connection_manager.disconnect(ws, broadcast_leave=True)
            )
            disconnect_tasks.append(task)
        
        # Wait for disconnections
        await asyncio.gather(*disconnect_tasks)
        
        # Verify remaining users
        assert connection_manager.get_room_connection_count(room_id) == 2