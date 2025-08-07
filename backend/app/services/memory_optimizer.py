"""
Memory optimization service for WebSocket connections
Monitors and optimizes memory usage across the application
"""
import asyncio
import gc
import psutil
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import timedelta, datetime
import logging
import weakref

from ..utils import get_current_time

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Memory usage statistics"""
    total_memory_mb: float
    used_memory_mb: float
    available_memory_mb: float
    memory_percent: float
    process_memory_mb: float
    process_memory_percent: float
    timestamp: datetime


@dataclass
class MemoryThresholds:
    """Memory usage thresholds for optimization"""
    warning_threshold_percent: float = 80.0
    critical_threshold_percent: float = 90.0
    cleanup_threshold_percent: float = 85.0
    max_process_memory_mb: float = 1024.0  # 1GB
    gc_threshold_percent: float = 75.0


class MemoryOptimizer:
    """Memory optimizer for WebSocket application"""
    
    def __init__(self, thresholds: Optional[MemoryThresholds] = None):
        """
        Initialize memory optimizer
        
        Args:
            thresholds: Memory thresholds configuration
        """
        self.thresholds = thresholds or MemoryThresholds()
        self.stats_history: List[MemoryStats] = []
        self.max_history_size = 100
        
        # Weak references to services for cleanup
        self._connection_manager_ref: Optional[weakref.ReferenceType] = None
        self._room_manager_ref: Optional[weakref.ReferenceType] = None
        self._message_handler_ref: Optional[weakref.ReferenceType] = None
        self._rate_limiter_ref: Optional[weakref.ReferenceType] = None
        
        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Optimization counters
        self.optimization_stats = {
            'gc_collections': 0,
            'connection_cleanups': 0,
            'room_cleanups': 0,
            'memory_warnings': 0,
            'memory_critical_events': 0
        }
    
    def register_services(self, connection_manager=None, room_manager=None, 
                         message_handler=None, rate_limiter=None):
        """
        Register services for memory optimization
        
        Args:
            connection_manager: ConnectionManager instance
            room_manager: RoomManager instance
            message_handler: MessageHandler instance
            rate_limiter: RateLimiter instance
        """
        if connection_manager:
            self._connection_manager_ref = weakref.ref(connection_manager)
        if room_manager:
            self._room_manager_ref = weakref.ref(room_manager)
        if message_handler:
            self._message_handler_ref = weakref.ref(message_handler)
        if rate_limiter:
            self._rate_limiter_ref = weakref.ref(rate_limiter)
        
        logger.info("Services registered with memory optimizer")
    
    async def start_monitoring(self, interval_seconds: int = 30):
        """
        Start memory monitoring
        
        Args:
            interval_seconds: Monitoring interval in seconds
        """
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info(f"Memory monitoring started (interval: {interval_seconds}s)")
    
    async def stop_monitoring(self):
        """Stop memory monitoring"""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        logger.info("Memory monitoring stopped")
    
    def get_current_memory_stats(self) -> MemoryStats:
        """Get current memory usage statistics"""
        # System memory
        memory = psutil.virtual_memory()
        
        # Process memory
        process = psutil.Process()
        process_memory = process.memory_info()
        
        return MemoryStats(
            total_memory_mb=memory.total / (1024 * 1024),
            used_memory_mb=memory.used / (1024 * 1024),
            available_memory_mb=memory.available / (1024 * 1024),
            memory_percent=memory.percent,
            process_memory_mb=process_memory.rss / (1024 * 1024),
            process_memory_percent=(process_memory.rss / memory.total) * 100,
            timestamp=get_current_time()
        )
    
    async def _monitoring_loop(self, interval_seconds: int):
        """Background monitoring loop"""
        while self._running:
            try:
                await asyncio.sleep(interval_seconds)
                if self._running:
                    await self._check_memory_usage()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {e}")
    
    async def _check_memory_usage(self):
        """Check memory usage and trigger optimizations if needed"""
        stats = self.get_current_memory_stats()
        
        # Store stats history
        self.stats_history.append(stats)
        if len(self.stats_history) > self.max_history_size:
            self.stats_history.pop(0)
        
        # Check thresholds
        if stats.memory_percent >= self.thresholds.critical_threshold_percent:
            logger.critical(f"Critical memory usage: {stats.memory_percent:.1f}%")
            self.optimization_stats['memory_critical_events'] += 1
            await self._emergency_cleanup()
            
        elif stats.memory_percent >= self.thresholds.cleanup_threshold_percent:
            logger.warning(f"High memory usage: {stats.memory_percent:.1f}%, triggering cleanup")
            self.optimization_stats['memory_warnings'] += 1
            await self._optimize_memory()
            
        elif stats.memory_percent >= self.thresholds.gc_threshold_percent:
            logger.info(f"Memory usage: {stats.memory_percent:.1f}%, triggering garbage collection")
            await self._trigger_garbage_collection()
        
        # Check process memory
        if stats.process_memory_mb >= self.thresholds.max_process_memory_mb:
            logger.warning(f"Process memory usage high: {stats.process_memory_mb:.1f}MB")
            await self._optimize_process_memory()
    
    async def _optimize_memory(self):
        """Perform memory optimization"""
        logger.info("Starting memory optimization")
        
        # Clean up connections
        await self._cleanup_stale_connections()
        
        # Clean up rooms
        await self._cleanup_empty_rooms()
        
        # Clean up rate limiter
        await self._cleanup_rate_limiter()
        
        # Trigger garbage collection
        await self._trigger_garbage_collection()
        
        logger.info("Memory optimization completed")
    
    async def _emergency_cleanup(self):
        """Emergency cleanup for critical memory situations"""
        logger.critical("Starting emergency memory cleanup")
        
        # Aggressive connection cleanup
        await self._cleanup_stale_connections(aggressive=True)
        
        # Force room cleanup
        await self._cleanup_empty_rooms(force=True)
        
        # Clear rate limiter caches
        await self._cleanup_rate_limiter(aggressive=True)
        
        # Force garbage collection multiple times
        for _ in range(3):
            await self._trigger_garbage_collection()
            await asyncio.sleep(0.1)
        
        logger.critical("Emergency memory cleanup completed")
    
    async def _cleanup_stale_connections(self, aggressive: bool = False):
        """Clean up stale connections"""
        connection_manager = self._get_connection_manager()
        if not connection_manager:
            return
        
        try:
            # Get stale connections (connections with no recent activity)
            cutoff_minutes = 5 if aggressive else 15
            cutoff_time = get_current_time() - timedelta(minutes=cutoff_minutes)
            
            stale_connections = []
            for websocket, connection in connection_manager.connection_lookup.items():
                if connection.last_activity < cutoff_time:
                    stale_connections.append(websocket)
            
            # Disconnect stale connections
            cleanup_count = 0
            for websocket in stale_connections:
                try:
                    await connection_manager.disconnect(websocket, broadcast_leave=False)
                    cleanup_count += 1
                except Exception as e:
                    logger.error(f"Error cleaning up stale connection: {e}")
            
            if cleanup_count > 0:
                logger.info(f"Cleaned up {cleanup_count} stale connections")
                self.optimization_stats['connection_cleanups'] += cleanup_count
                
        except Exception as e:
            logger.error(f"Error in connection cleanup: {e}")
    
    async def _cleanup_empty_rooms(self, force: bool = False):
        """Clean up empty rooms"""
        room_manager = self._get_room_manager()
        if not room_manager:
            return
        
        try:
            # Force cleanup or use normal timeout
            if force:
                # Clean up all empty rooms immediately
                empty_rooms = room_manager.get_inactive_rooms()
                for room_id in empty_rooms:
                    room_manager.delete_room(room_id)
                
                if empty_rooms:
                    logger.info(f"Force cleaned up {len(empty_rooms)} empty rooms")
                    self.optimization_stats['room_cleanups'] += len(empty_rooms)
            else:
                # Use normal cleanup
                cleaned_count = room_manager.cleanup_inactive_rooms()
                if cleaned_count > 0:
                    self.optimization_stats['room_cleanups'] += cleaned_count
                    
        except Exception as e:
            logger.error(f"Error in room cleanup: {e}")
    
    async def _cleanup_rate_limiter(self, aggressive: bool = False):
        """Clean up rate limiter caches"""
        rate_limiter = self._get_rate_limiter()
        if not rate_limiter:
            return
        
        try:
            if aggressive:
                # Clear all rate limiter caches
                rate_limiter.user_buckets.clear()
                rate_limiter.last_activity.clear()
                logger.info("Aggressively cleaned up rate limiter caches")
            else:
                # Use normal cleanup
                rate_limiter._cleanup_inactive_entries()
                
        except Exception as e:
            logger.error(f"Error in rate limiter cleanup: {e}")
    
    async def _trigger_garbage_collection(self):
        """Trigger garbage collection"""
        try:
            # Run garbage collection in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            collected = await loop.run_in_executor(None, gc.collect)
            
            self.optimization_stats['gc_collections'] += 1
            logger.debug(f"Garbage collection completed, collected {collected} objects")
            
        except Exception as e:
            logger.error(f"Error in garbage collection: {e}")
    
    async def _optimize_process_memory(self):
        """Optimize process-specific memory usage"""
        try:
            # Clear message handler typing timeouts
            message_handler = self._get_message_handler()
            if message_handler:
                await message_handler.cleanup_all_typing_timeouts()
            
            # Trigger garbage collection
            await self._trigger_garbage_collection()
            
            logger.info("Process memory optimization completed")
            
        except Exception as e:
            logger.error(f"Error in process memory optimization: {e}")
    
    def _get_connection_manager(self):
        """Get connection manager from weak reference"""
        if self._connection_manager_ref:
            return self._connection_manager_ref()
        return None
    
    def _get_room_manager(self):
        """Get room manager from weak reference"""
        if self._room_manager_ref:
            return self._room_manager_ref()
        return None
    
    def _get_message_handler(self):
        """Get message handler from weak reference"""
        if self._message_handler_ref:
            return self._message_handler_ref()
        return None
    
    def _get_rate_limiter(self):
        """Get rate limiter from weak reference"""
        if self._rate_limiter_ref:
            return self._rate_limiter_ref()
        return None
    
    def get_memory_report(self) -> Dict:
        """Get comprehensive memory report"""
        current_stats = self.get_current_memory_stats()
        
        # Calculate trends if we have history
        trend_data = {}
        if len(self.stats_history) >= 2:
            recent_stats = self.stats_history[-5:]  # Last 5 measurements
            avg_memory = sum(s.memory_percent for s in recent_stats) / len(recent_stats)
            avg_process = sum(s.process_memory_mb for s in recent_stats) / len(recent_stats)
            
            trend_data = {
                'avg_memory_percent_recent': avg_memory,
                'avg_process_memory_mb_recent': avg_process,
                'memory_trend': 'increasing' if current_stats.memory_percent > avg_memory else 'stable'
            }
        
        return {
            'current_stats': {
                'total_memory_mb': current_stats.total_memory_mb,
                'used_memory_mb': current_stats.used_memory_mb,
                'available_memory_mb': current_stats.available_memory_mb,
                'memory_percent': current_stats.memory_percent,
                'process_memory_mb': current_stats.process_memory_mb,
                'process_memory_percent': current_stats.process_memory_percent
            },
            'thresholds': {
                'warning_threshold': self.thresholds.warning_threshold_percent,
                'critical_threshold': self.thresholds.critical_threshold_percent,
                'cleanup_threshold': self.thresholds.cleanup_threshold_percent,
                'max_process_memory_mb': self.thresholds.max_process_memory_mb
            },
            'optimization_stats': self.optimization_stats.copy(),
            'trend_data': trend_data,
            'status': self._get_memory_status(current_stats),
            'recommendations': self._get_recommendations(current_stats)
        }
    
    def _get_memory_status(self, stats: MemoryStats) -> str:
        """Get memory status based on current stats"""
        if stats.memory_percent >= self.thresholds.critical_threshold_percent:
            return 'critical'
        elif stats.memory_percent >= self.thresholds.cleanup_threshold_percent:
            return 'high'
        elif stats.memory_percent >= self.thresholds.warning_threshold_percent:
            return 'warning'
        else:
            return 'normal'
    
    def _get_recommendations(self, stats: MemoryStats) -> List[str]:
        """Get memory optimization recommendations"""
        recommendations = []
        
        if stats.memory_percent >= self.thresholds.critical_threshold_percent:
            recommendations.append("Critical memory usage - consider restarting the service")
            recommendations.append("Implement connection limits immediately")
            
        elif stats.memory_percent >= self.thresholds.cleanup_threshold_percent:
            recommendations.append("High memory usage - increase cleanup frequency")
            recommendations.append("Consider reducing connection limits")
            
        elif stats.memory_percent >= self.thresholds.warning_threshold_percent:
            recommendations.append("Monitor memory usage closely")
            
        if stats.process_memory_mb >= self.thresholds.max_process_memory_mb:
            recommendations.append("Process memory usage is high - check for memory leaks")
            
        if not recommendations:
            recommendations.append("Memory usage is within normal limits")
            
        return recommendations