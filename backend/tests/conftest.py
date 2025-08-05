import pytest
from app.services import ConnectionManager, RoomManager, MessageHandler
from app.services.rate_limiter import RateLimiter, RateLimitConfig

@pytest.fixture
def services():
    rate_limit_config = RateLimitConfig(
        text_messages_per_minute=60,
        voice_messages_per_minute=10,
        typing_messages_per_minute=120,
        max_connections_per_room=50,
        max_connections_per_ip=10
    )
    rate_limiter = RateLimiter(rate_limit_config)
    connection_manager = ConnectionManager(rate_limiter)
    room_manager = RoomManager()
    message_handler = MessageHandler(connection_manager, room_manager, rate_limiter)
    return connection_manager, room_manager, message_handler
