import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket

from app.services.connection_manager import ConnectionManager
from app.services.room_manager import RoomManager
from app.models import UserJoinMessage, UserLeaveMessage


class TestUserNotifications:
    """Test user join/leave notification functionality"""
    
    @pytest.fixture
    def room_manager(self):
        return RoomManager()

    @pytest.fixture
    def connection_manager(self, room_manager):
        return ConnectionManager(room_manager)
    
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
    async def test_user_join_notification_sent_to_existing_users(self, connection_manager, mock_websocket, mock_websocket2):
        """Test that join notifications are sent to existing users when a new user joins"""
        room_id = "test-room"
        user1_id = "user1"
        user2_id = "user2"
        
        # First user joins (no notification should be sent as no other users exist)
        connection1 = await connection_manager.connect(mock_websocket, room_id, user1_id)
        
        # Verify first user connected
        assert connection1.user_id == user1_id
        assert connection1.room_id == room_id
        
        # Reset mock to check for join notification
        mock_websocket.send_text.reset_mock()
        
        # Second user joins (should trigger join notification to first user)
        connection2 = await connection_manager.connect(mock_websocket2, room_id, user2_id)
        
        # Verify second user connected
        assert connection2.user_id == user2_id
        assert connection2.room_id == room_id
        
        # Verify join notification was sent to first user
        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        
        # Parse the JSON message
        import json
        message_data = json.loads(call_args)
        
        # Verify it's a user_join message
        assert message_data["type"] == "user_join"
        assert message_data["user_id"] == user2_id
        assert message_data["room_id"] == room_id
        assert "timestamp" in message_data
        
        # Verify no notification was sent to the joining user (user2)
        mock_websocket2.send_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_user_leave_notification_sent_to_remaining_users(self, connection_manager, mock_websocket, mock_websocket2):
        """Test that leave notifications are sent to remaining users when a user leaves"""
        room_id = "test-room"
        user1_id = "user1"
        user2_id = "user2"
        
        # Both users join
        await connection_manager.connect(mock_websocket, room_id, user1_id)
        await connection_manager.connect(mock_websocket2, room_id, user2_id)
        
        # Reset mocks to check for leave notification
        mock_websocket.send_text.reset_mock()
        mock_websocket2.send_text.reset_mock()
        
        # First user leaves (should trigger leave notification to second user)
        disconnected_connection = await connection_manager.disconnect(mock_websocket, broadcast_leave=True)
        
        # Verify user was disconnected
        assert disconnected_connection.user_id == user1_id
        
        # Verify leave notification was sent to remaining user (user2)
        mock_websocket2.send_text.assert_called_once()
        call_args = mock_websocket2.send_text.call_args[0][0]
        
        # Parse the JSON message
        import json
        message_data = json.loads(call_args)
        
        # Verify it's a user_leave message
        assert message_data["type"] == "user_leave"
        assert message_data["user_id"] == user1_id
        assert message_data["room_id"] == room_id
        assert "timestamp" in message_data
        
        # Verify no notification was sent to the leaving user
        mock_websocket.send_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_no_leave_notification_when_room_becomes_empty(self, connection_manager, mock_websocket):
        """Test that no leave notification is sent when the last user leaves and room becomes empty"""
        room_id = "test-room"
        user_id = "user1"
        
        # Single user joins
        await connection_manager.connect(mock_websocket, room_id, user_id)
        
        # Reset mock to check for leave notification
        mock_websocket.send_text.reset_mock()
        
        # User leaves (no other users to notify)
        disconnected_connection = await connection_manager.disconnect(mock_websocket, broadcast_leave=True)
        
        # Verify user was disconnected
        assert disconnected_connection.user_id == user_id
        
        # Verify no leave notification was sent (no other users in room)
        mock_websocket.send_text.assert_not_called()
        
        # Verify room was cleaned up
        assert room_id not in connection_manager.rooms
    
    @pytest.mark.asyncio
    async def test_multiple_users_join_notifications(self, connection_manager):
        """Test join notifications with multiple users joining sequentially"""
        room_id = "test-room"
        websockets = []
        user_ids = ["user1", "user2", "user3"]
        
        # Create mock websockets
        for i in range(3):
            ws = MagicMock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            ws.send_bytes = AsyncMock()
            websockets.append(ws)
        
        # First user joins (no notifications)
        await connection_manager.connect(websockets[0], room_id, user_ids[0])
        websockets[0].send_text.assert_not_called()
        
        # Second user joins (notification to user1)
        websockets[0].send_text.reset_mock()
        await connection_manager.connect(websockets[1], room_id, user_ids[1])
        websockets[0].send_text.assert_called_once()
        websockets[1].send_text.assert_not_called()
        
        # Third user joins (notifications to user1 and user2)
        websockets[0].send_text.reset_mock()
        websockets[1].send_text.reset_mock()
        await connection_manager.connect(websockets[2], room_id, user_ids[2])
        
        # Both existing users should receive join notification
        websockets[0].send_text.assert_called_once()
        websockets[1].send_text.assert_called_once()
        websockets[2].send_text.assert_not_called()
        
        # Verify room has 3 connections
        assert connection_manager.get_room_connection_count(room_id) == 3
    
    @pytest.mark.asyncio
    async def test_user_join_leave_message_serialization(self):
        """Test that UserJoinMessage and UserLeaveMessage serialize correctly"""
        from app.models import serialize_message
        import json
        
        # Test UserJoinMessage serialization
        join_msg = UserJoinMessage(user_id="test_user", room_id="test-room")
        serialized_join = serialize_message(join_msg)
        
        assert serialized_join["type"] == "user_join"
        assert serialized_join["user_id"] == "test_user"
        assert serialized_join["room_id"] == "test-room"
        assert "timestamp" in serialized_join
        
        # Verify it can be JSON serialized
        json_str = json.dumps(serialized_join, default=str)
        assert json_str is not None
        
        # Test UserLeaveMessage serialization
        leave_msg = UserLeaveMessage(user_id="test_user", room_id="test-room")
        serialized_leave = serialize_message(leave_msg)
        
        assert serialized_leave["type"] == "user_leave"
        assert serialized_leave["user_id"] == "test_user"
        assert serialized_leave["room_id"] == "test-room"
        assert "timestamp" in serialized_leave
        
        # Verify it can be JSON serialized
        json_str = json.dumps(serialized_leave, default=str)
        assert json_str is not None
    
    @pytest.mark.asyncio
    async def test_no_leave_notification_during_cleanup(self, connection_manager, mock_websocket, mock_websocket2):
        """Test that leave notifications are not sent during connection cleanup (broadcast_leave=False)"""
        room_id = "test-room"
        user1_id = "user1"
        user2_id = "user2"
        
        # Both users join
        await connection_manager.connect(mock_websocket, room_id, user1_id)
        await connection_manager.connect(mock_websocket2, room_id, user2_id)
        
        # Reset mocks
        mock_websocket.send_text.reset_mock()
        mock_websocket2.send_text.reset_mock()
        
        # First user disconnects with broadcast_leave=False (cleanup scenario)
        disconnected_connection = await connection_manager.disconnect(mock_websocket, broadcast_leave=False)
        
        # Verify user was disconnected
        assert disconnected_connection.user_id == user1_id
        
        # Verify no leave notification was sent to remaining user
        mock_websocket2.send_text.assert_not_called()
        mock_websocket.send_text.assert_not_called()