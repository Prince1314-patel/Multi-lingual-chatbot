"""
Rate limiting service for WebSocket connections and messages
Implements token bucket algorithm for rate limiting
"""
import asyncio
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting"""
    capacity: int  # Maximum tokens
    tokens: float  # Current tokens
    refill_rate: float  # Tokens per second
    last_refill: float = field(default_factory=time.time)
    
    def refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens, return True if successful"""
        self.refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time to wait before tokens are available"""
        self.refill()
        if self.tokens >= tokens:
            return 0.0
        needed_tokens = tokens - self.tokens
        return needed_tokens / self.refill_rate


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    # Message rate limits (messages per minute)
    text_messages_per_minute: int = 60
    voice_messages_per_minute: int = 10
    typing_messages_per_minute: int = 120
    
    # Connection limits
    max_connections_per_room: int = 50
    max_connections_per_ip: int = 10
    
    # Burst limits (short-term)
    text_burst_limit: int = 10  # messages in 10 seconds
    voice_burst_limit: int = 3   # messages in 10 seconds
    
    # Memory optimization
    cleanup_interval_seconds: int = 300  # 5 minutes
    max_inactive_time_seconds: int = 3600  # 1 hour


class RateLimiter:
    """Rate limiter for WebSocket connections and messages"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimitConfig()
        
        # User-based rate limiting (user_id -> message_type -> TokenBucket)
        self.user_buckets: Dict[str, Dict[str, TokenBucket]] = {}
        
        # IP-based connection limiting (ip -> connection_count)
        self.ip_connections: Dict[str, int] = {}
        
        # Room-based connection limiting (room_id -> connection_count)
        self.room_connections: Dict[str, int] = {}
        
        # Last activity tracking for cleanup
        self.last_activity: Dict[str, float] = {}
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the rate limiter and cleanup task"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Rate limiter started")
    
    async def stop(self):
        """Stop the rate limiter and cleanup task"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        logger.info("Rate limiter stopped")
    
    def check_connection_limit(self, room_id: str, ip_address: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check if a new connection is allowed
        
        Args:
            room_id: Room ID to check
            ip_address: IP address of the connection (optional)
            
        Returns:
            Tuple of (allowed, reason)
        """
        # Check room connection limit
        room_count = self.room_connections.get(room_id, 0)
        if room_count >= self.config.max_connections_per_room:
            return False, f"Room connection limit exceeded ({self.config.max_connections_per_room})"
        
        # Check IP connection limit if IP is provided
        if ip_address:
            ip_count = self.ip_connections.get(ip_address, 0)
            if ip_count >= self.config.max_connections_per_ip:
                return False, f"IP connection limit exceeded ({self.config.max_connections_per_ip})"
        
        return True, "Connection allowed"
    
    def add_connection(self, room_id: str, user_id: str, ip_address: Optional[str] = None):
        """
        Add a new connection to tracking
        
        Args:
            room_id: Room ID
            user_id: User ID
            ip_address: IP address (optional)
        """
        # Increment room connection count
        self.room_connections[room_id] = self.room_connections.get(room_id, 0) + 1
        
        # Increment IP connection count if provided
        if ip_address:
            self.ip_connections[ip_address] = self.ip_connections.get(ip_address, 0) + 1
        
        # Update activity
        self.last_activity[user_id] = time.time()
        
        logger.debug(f"Added connection: room={room_id}, user={user_id}, ip={ip_address}")
    
    def remove_connection(self, room_id: str, user_id: str, ip_address: Optional[str] = None):
        """
        Remove a connection from tracking
        
        Args:
            room_id: Room ID
            user_id: User ID
            ip_address: IP address (optional)
        """
        # Decrement room connection count
        if room_id in self.room_connections:
            self.room_connections[room_id] = max(0, self.room_connections[room_id] - 1)
            if self.room_connections[room_id] == 0:
                del self.room_connections[room_id]
        
        # Decrement IP connection count if provided
        if ip_address and ip_address in self.ip_connections:
            self.ip_connections[ip_address] = max(0, self.ip_connections[ip_address] - 1)
            if self.ip_connections[ip_address] == 0:
                del self.ip_connections[ip_address]
        
        # Clean up user buckets
        if user_id in self.user_buckets:
            del self.user_buckets[user_id]
        
        # Clean up activity tracking
        if user_id in self.last_activity:
            del self.last_activity[user_id]
        
        logger.debug(f"Removed connection: room={room_id}, user={user_id}, ip={ip_address}")
    
    def check_message_rate_limit(self, user_id: str, message_type: str) -> Tuple[bool, float]:
        """
        Check if a message is allowed based on rate limits
        
        Args:
            user_id: User ID sending the message
            message_type: Type of message ('text', 'voice', 'typing')
            
        Returns:
            Tuple of (allowed, wait_time_seconds)
        """
        # Update activity
        self.last_activity[user_id] = time.time()
        
        # Get or create user buckets
        if user_id not in self.user_buckets:
            self.user_buckets[user_id] = {}
        
        user_buckets = self.user_buckets[user_id]
        
        # Get or create bucket for message type
        if message_type not in user_buckets:
            bucket = self._create_bucket_for_message_type(message_type)
            user_buckets[message_type] = bucket
        else:
            bucket = user_buckets[message_type]
        
        # Check if message is allowed
        if bucket.consume():
            return True, 0.0
        else:
            wait_time = bucket.get_wait_time()
            return False, wait_time
    
    def _create_bucket_for_message_type(self, message_type: str) -> TokenBucket:
        """Create a token bucket for a specific message type"""
        if message_type == 'text':
            return TokenBucket(
                capacity=self.config.text_burst_limit,
                tokens=self.config.text_burst_limit,
                refill_rate=self.config.text_messages_per_minute / 60.0
            )
        elif message_type == 'voice':
            return TokenBucket(
                capacity=self.config.voice_burst_limit,
                tokens=self.config.voice_burst_limit,
                refill_rate=self.config.voice_messages_per_minute / 60.0
            )
        elif message_type == 'typing':
            return TokenBucket(
                capacity=20,  # Allow burst of typing indicators
                tokens=20,
                refill_rate=self.config.typing_messages_per_minute / 60.0
            )
        else:
            # Default bucket for unknown message types
            return TokenBucket(
                capacity=10,
                tokens=10,
                refill_rate=1.0  # 1 message per second
            )
    
    async def _cleanup_loop(self):
        """Background cleanup task to remove inactive entries"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                if self._running:
                    self._cleanup_inactive_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rate limiter cleanup loop: {e}")
    
    def _cleanup_inactive_entries(self):
        """Clean up inactive user buckets and activity tracking"""
        current_time = time.time()
        inactive_threshold = current_time - self.config.max_inactive_time_seconds
        
        # Find inactive users
        inactive_users = [
            user_id for user_id, last_time in self.last_activity.items()
            if last_time < inactive_threshold
        ]
        
        # Clean up inactive users
        for user_id in inactive_users:
            if user_id in self.user_buckets:
                del self.user_buckets[user_id]
            if user_id in self.last_activity:
                del self.last_activity[user_id]
        
        if inactive_users:
            logger.info(f"Cleaned up {len(inactive_users)} inactive rate limit entries")
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        return {
            'active_users': len(self.user_buckets),
            'room_connections': dict(self.room_connections),
            'ip_connections': dict(self.ip_connections),
            'total_room_connections': sum(self.room_connections.values()),
            'total_ip_connections': sum(self.ip_connections.values()),
            'config': {
                'max_connections_per_room': self.config.max_connections_per_room,
                'max_connections_per_ip': self.config.max_connections_per_ip,
                'text_messages_per_minute': self.config.text_messages_per_minute,
                'voice_messages_per_minute': self.config.voice_messages_per_minute,
                'typing_messages_per_minute': self.config.typing_messages_per_minute
            }
        }
    
    def get_user_rate_limit_status(self, user_id: str) -> Dict:
        """Get rate limit status for a specific user"""
        if user_id not in self.user_buckets:
            return {'status': 'no_limits_active'}
        
        user_buckets = self.user_buckets[user_id]
        status = {}
        
        for message_type, bucket in user_buckets.items():
            bucket.refill()  # Update tokens
            status[message_type] = {
                'tokens_available': int(bucket.tokens),
                'capacity': bucket.capacity,
                'refill_rate': bucket.refill_rate,
                'wait_time_for_next': bucket.get_wait_time()
            }
        
        return status