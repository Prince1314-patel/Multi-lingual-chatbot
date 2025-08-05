import json
import logging
import time
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.routing import APIRouter

from .services import ConnectionManager, RoomManager, MessageHandler
from .services.rate_limiter import RateLimiter, RateLimitConfig
from .services.memory_optimizer import MemoryOptimizer
from .models import validate_room_id, generate_user_id
from .core import ErrorHandler, ErrorCode, ChatLogger, get_error_handler, get_chat_logger

logger = get_chat_logger()

# Create router for WebSocket endpoints
websocket_router = APIRouter()

# Global service instances (will be initialized in main.py)
connection_manager: Optional[ConnectionManager] = None
room_manager: Optional[RoomManager] = None
message_handler: Optional[MessageHandler] = None
rate_limiter: Optional[RateLimiter] = None
memory_optimizer: Optional[MemoryOptimizer] = None


def init_websocket_services():
    """Initialize WebSocket services - called from main.py"""
    global connection_manager, room_manager, message_handler, rate_limiter, memory_optimizer
    
    # Initialize rate limiter with configuration
    rate_limit_config = RateLimitConfig(
        text_messages_per_minute=60,
        voice_messages_per_minute=10,
        typing_messages_per_minute=120,
        max_connections_per_room=50,
        max_connections_per_ip=10
    )
    rate_limiter = RateLimiter(rate_limit_config)
    
    # Initialize services with rate limiter
    connection_manager = ConnectionManager(rate_limiter)
    room_manager = RoomManager(cleanup_timeout_minutes=30)
    message_handler = MessageHandler(connection_manager, room_manager, rate_limiter)
    
    # Initialize memory optimizer
    memory_optimizer = MemoryOptimizer()
    memory_optimizer.register_services(
        connection_manager=connection_manager,
        room_manager=room_manager,
        message_handler=message_handler,
        rate_limiter=rate_limiter
    )
    
    logger.log_message_event("services_initialized", None, None, "system")


def get_services():
    """Dependency to get WebSocket services"""
    if not all([connection_manager, room_manager, message_handler]):
        raise HTTPException(status_code=500, detail="WebSocket services not initialized")
    
    return connection_manager, room_manager, message_handler

def get_all_services():
    """Get all services including performance optimization services"""
    if not all([connection_manager, room_manager, message_handler, rate_limiter, memory_optimizer]):
        raise HTTPException(status_code=500, detail="WebSocket services not initialized")
    
    return connection_manager, room_manager, message_handler, rate_limiter, memory_optimizer


def get_client_ip(websocket: WebSocket) -> Optional[str]:
    """Extract client IP address from WebSocket connection"""
    try:
        # Try to get real IP from headers (for proxy setups)
        if hasattr(websocket, 'headers'):
            forwarded_for = websocket.headers.get('x-forwarded-for')
            if forwarded_for:
                return forwarded_for.split(',')[0].strip()
            
            real_ip = websocket.headers.get('x-real-ip')
            if real_ip:
                return real_ip.strip()
        
        # Fallback to client address
        if hasattr(websocket, 'client') and websocket.client:
            return websocket.client.host
        
        return None
    except Exception as e:
        logger.error(f"Error extracting client IP: {e}")
        return None

@websocket_router.websocket("/ws/chat/{room_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    room_id: str,
    user_id: Optional[str] = None
):
    """
    WebSocket endpoint for chat rooms with comprehensive error handling
    
    Args:
        websocket: WebSocket connection
        room_id: The chat room ID to join
        user_id: Optional user ID (will generate if not provided)
    """
    error_handler = get_error_handler()
    start_time = time.time()
    
    # Get services with error handling
    try:
        conn_mgr, room_mgr, msg_handler = get_services()
    except Exception as e:
        logger.log_error(
            ErrorCode.SERVICE_UNAVAILABLE,
            f"WebSocket services not available: {str(e)}",
            exception=e
        )
        await error_handler.safe_websocket_close(
            websocket, code=1011, reason="Service unavailable"
        )
        return
    
    # Validate room ID with enhanced error handling
    if not validate_room_id(room_id):
        await error_handler.handle_websocket_error(
            websocket, ErrorCode.INVALID_ROOM_ID, 
            f"Invalid room ID format: {room_id}"
        )
        await error_handler.safe_websocket_close(
            websocket, code=4000, reason="Invalid room ID format"
        )
        return
    
    # Generate user ID if not provided
    if not user_id:
        user_id = generate_user_id()
    
    # Get client IP for rate limiting
    client_ip = get_client_ip(websocket)
    
    connection = None
    
    try:
        # Accept WebSocket connection and join room with timeout handling
        # Get or create room with error handling
        room = room_mgr.get_or_create_room(room_id)
        try:
            connection = await conn_mgr.connect(websocket, room_id, user_id, client_ip)
            logger.log_connection_event("established", user_id, room_id, {
                "connection_time_ms": (time.time() - start_time) * 1000,
                "client_ip": client_ip
            })
        except ConnectionError as e:
            # Connection limit exceeded
            await error_handler.handle_websocket_error(
                websocket, ErrorCode.CONNECTION_LIMIT_EXCEEDED,
                str(e), user_id, room_id
            )
            return
        except Exception as e:
            await error_handler.handle_websocket_error(
                websocket, ErrorCode.ROOM_NOT_FOUND,
                f"Failed to create or access room: {str(e)}",
                user_id, room_id, e
            )
            return
        
        # Send welcome message with error handling
        try:
            welcome_message = {
                "type": "connection_established",
                "user_id": user_id,
                "room_id": room_id,
                "room_info": {
                    "connection_count": room.get_connection_count(),
                    "created_at": room.created_at.isoformat()
                }
            }
            
            await websocket.send_text(json.dumps(welcome_message, default=str))
            logger.log_connection_event("welcome_sent", user_id, room_id)
            
        except Exception as e:
            logger.log_error(
                ErrorCode.MESSAGE_PROCESSING_ERROR,
                f"Failed to send welcome message: {str(e)}",
                user_id, room_id, e
            )
            # Continue anyway, connection is established
        
        # Main message handling loop with comprehensive error handling
        while True:
            try:
                # Receive message from WebSocket with timeout
                message_start_time = time.time()
                message = await websocket.receive()
                
                if message.get("type") == "websocket.disconnect":
                    logger.log_connection_event("disconnected", user_id, room_id)
                    break
                
            except WebSocketDisconnect:
                logger.log_connection_event("disconnected", user_id, room_id)
                break
            
            except Exception as e:
                await error_handler.handle_websocket_error(
                    websocket, ErrorCode.MESSAGE_PROCESSING_ERROR,
                    f"Unexpected error in message loop: {str(e)}",
                    user_id, room_id, e
                )
                # Continue the loop unless it's a critical error
                if "critical" in str(e).lower():
                    break
    
    except WebSocketDisconnect:
        logger.log_connection_event("disconnected_during_handshake", user_id, room_id)
    
    except Exception as e:
        logger.log_error(
            ErrorCode.INTERNAL_SERVER_ERROR,
            f"Critical error in WebSocket endpoint: {str(e)}",
            user_id, room_id, e
        )
        await error_handler.safe_websocket_close(
            websocket, code=1011, reason="Internal server error"
        )
    
    finally:
        # Comprehensive connection cleanup with error handling
        if connection:
            try:
                await msg_handler.handle_user_disconnect(connection)
                await conn_mgr.disconnect(websocket, broadcast_leave=True, ip_address=client_ip)
                logger.log_connection_event("cleanup_completed", user_id, room_id)
            except Exception as e:
                logger.log_error(
                    ErrorCode.CONNECTION_FAILED,
                    f"Error during connection cleanup: {str(e)}",
                    user_id, room_id, e
                )


@websocket_router.get("/ws/rooms/{room_id}/info")
async def get_room_info(room_id: str):
    """
    Get information about a specific room with comprehensive error handling
    
    Args:
        room_id: The room ID to get info for
        
    Returns:
        Room information dictionary
    """
    try:
        # Get services with error handling
        conn_mgr, room_mgr, msg_handler = get_services()
        
        # Validate room ID
        if not validate_room_id(room_id):
            logger.log_error(
                ErrorCode.INVALID_ROOM_ID,
                f"Invalid room ID format in info request: {room_id}"
            )
            raise HTTPException(status_code=400, detail="Invalid room ID format")
        
        # Get room info with error handling
        try:
            room_info = room_mgr.get_detailed_room_info(room_id)
        except Exception as e:
            logger.log_error(
                ErrorCode.INTERNAL_SERVER_ERROR,
                f"Failed to get room info: {str(e)}",
                room_id=room_id,
                exception=e
            )
            raise HTTPException(status_code=500, detail="Failed to retrieve room information")
        
        if not room_info:
            logger.log_warning(f"Room not found in info request", room_id=room_id)
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Add typing users info with error handling
        try:
            room_info['typing_users'] = list(msg_handler.get_typing_users(room_id))
        except Exception as e:
            logger.log_error(
                ErrorCode.MESSAGE_PROCESSING_ERROR,
                f"Failed to get typing users: {str(e)}",
                room_id=room_id,
                exception=e
            )
            # Continue without typing users info
            room_info['typing_users'] = []
        
        logger.log_message_event("room_info_retrieved", None, room_id, "info_request")
        return room_info
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.log_error(
            ErrorCode.INTERNAL_SERVER_ERROR,
            f"Unexpected error in room info endpoint: {str(e)}",
            room_id=room_id,
            exception=e
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@websocket_router.get("/ws/rooms")
async def list_active_rooms():
    """
    List all active rooms with comprehensive error handling
    
    Returns:
        List of active room IDs and basic info
    """
    try:
        # Get services with error handling
        conn_mgr, room_mgr, msg_handler = get_services()
        
        # Get active rooms with error handling
        try:
            active_rooms = room_mgr.get_active_rooms()
        except Exception as e:
            logger.log_error(
                ErrorCode.INTERNAL_SERVER_ERROR,
                f"Failed to get active rooms: {str(e)}",
                exception=e
            )
            raise HTTPException(status_code=500, detail="Failed to retrieve active rooms")
        
        rooms_info = []
        failed_rooms = []
        
        for room_id in active_rooms:
            try:
                room_info = room_mgr.get_detailed_room_info(room_id)
                if room_info:
                    # Add minimal info for listing
                    rooms_info.append({
                        'room_id': room_id,
                        'connection_count': room_info['connection_count'],
                        'created_at': room_info['created_at'],
                        'last_activity': room_info['last_activity']
                    })
                else:
                    failed_rooms.append(room_id)
            except Exception as e:
                logger.log_error(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    f"Failed to get info for room {room_id}: {str(e)}",
                    room_id=room_id,
                    exception=e
                )
                failed_rooms.append(room_id)
        
        if failed_rooms:
            logger.log_warning(
                f"Failed to get info for {len(failed_rooms)} rooms: {failed_rooms}"
            )
        
        result = {
            'active_rooms': rooms_info,
            'total_count': len(rooms_info)
        }
        
        if failed_rooms:
            result['failed_rooms'] = failed_rooms
        
        logger.log_message_event("rooms_listed", None, None, "list_request", {
            "total_rooms": len(rooms_info),
            "failed_rooms": len(failed_rooms)
        })
        
        return result
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.log_error(
            ErrorCode.INTERNAL_SERVER_ERROR,
            f"Unexpected error in list rooms endpoint: {str(e)}",
            exception=e
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@websocket_router.get("/ws/stats")
async def get_websocket_stats():
    """
    Get WebSocket service statistics
    
    Returns:
        Statistics about connections, rooms, and message handling
    """
    # Get services
    conn_mgr, room_mgr, msg_handler = get_services()
    
    return {
        'connections': {
            'total_connections': conn_mgr.get_total_connections(),
            'active_rooms': len(conn_mgr.get_active_rooms())
        },
        'rooms': room_mgr.get_room_stats(),
        'message_handler': msg_handler.get_message_handler_stats()
    }


# Health check endpoint for WebSocket service
@websocket_router.get("/ws/health")
async def websocket_health_check():
    """
    Health check endpoint for WebSocket services with comprehensive error handling
    
    Returns:
        Health status of WebSocket services
    """
    health_status = {
        'status': 'unknown',
        'services': {},
        'stats': {},
        'errors': []
    }
    
    try:
        # Get services with individual error handling
        try:
            conn_mgr, room_mgr, msg_handler = get_services()
            health_status['services']['service_initialization'] = 'healthy'
        except Exception as e:
            logger.log_error(
                ErrorCode.SERVICE_UNAVAILABLE,
                f"Services not available during health check: {str(e)}",
                exception=e
            )
            health_status['services']['service_initialization'] = 'unhealthy'
            health_status['errors'].append(f"Service initialization failed: {str(e)}")
            raise HTTPException(status_code=503, detail="WebSocket services unavailable")
        
        # Check connection manager health
        try:
            total_connections = conn_mgr.get_total_connections()
            active_rooms = len(conn_mgr.get_active_rooms())
            health_status['services']['connection_manager'] = 'healthy'
            health_status['stats']['total_connections'] = total_connections
            health_status['stats']['active_rooms'] = active_rooms
        except Exception as e:
            logger.log_error(
                ErrorCode.INTERNAL_SERVER_ERROR,
                f"Connection manager health check failed: {str(e)}",
                exception=e
            )
            health_status['services']['connection_manager'] = 'unhealthy'
            health_status['errors'].append(f"Connection manager error: {str(e)}")
        
        # Check room manager health
        try:
            room_stats = room_mgr.get_room_stats()
            health_status['services']['room_manager'] = 'healthy'
            health_status['stats']['room_stats'] = room_stats
        except Exception as e:
            logger.log_error(
                ErrorCode.INTERNAL_SERVER_ERROR,
                f"Room manager health check failed: {str(e)}",
                exception=e
            )
            health_status['services']['room_manager'] = 'unhealthy'
            health_status['errors'].append(f"Room manager error: {str(e)}")
        
        # Check message handler health
        try:
            msg_stats = msg_handler.get_message_handler_stats()
            health_status['services']['message_handler'] = 'healthy'
            health_status['stats']['message_handler'] = msg_stats
        except Exception as e:
            logger.log_error(
                ErrorCode.INTERNAL_SERVER_ERROR,
                f"Message handler health check failed: {str(e)}",
                exception=e
            )
            health_status['services']['message_handler'] = 'unhealthy'
            health_status['errors'].append(f"Message handler error: {str(e)}")
        
        # Determine overall health status
        unhealthy_services = [k for k, v in health_status['services'].items() if v == 'unhealthy']
        
        if not unhealthy_services:
            health_status['status'] = 'healthy'
        elif len(unhealthy_services) < len(health_status['services']):
            health_status['status'] = 'degraded'
        else:
            health_status['status'] = 'unhealthy'
        
        # Add timestamp
        health_status['timestamp'] = time.time()
        
        # Log health check result
        logger.log_message_event(
            "health_check_completed", None, None, "health_check",
            {"status": health_status['status'], "errors": len(health_status['errors'])}
        )
        
        # Return appropriate HTTP status
        if health_status['status'] == 'healthy':
            return health_status
        elif health_status['status'] == 'degraded':
            return health_status  # Still return 200 for degraded
        else:
            raise HTTPException(status_code=503, detail=health_status)
    
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.log_error(
            ErrorCode.INTERNAL_SERVER_ERROR,
            f"Critical error in health check: {str(e)}",
            exception=e
        )
        health_status['status'] = 'critical_error'
        health_status['errors'].append(f"Critical health check error: {str(e)}")
        raise HTTPException(status_code=503, detail=health_status)


# Cleanup function for graceful shutdown
async def cleanup_websocket_services():
    """Clean up WebSocket services on shutdown"""
    global connection_manager, room_manager, message_handler
    
    try:
        if message_handler:
            await message_handler.cleanup_all_typing_timeouts()
            logger.log_message_event("cleanup_completed", None, None, "message_handler")
        
        if room_manager:
            await room_manager.stop_cleanup_task()
            logger.log_message_event("cleanup_task_stopped", None, None, "room_manager")
        
        logger.log_message_event("cleanup_completed", None, None, "websocket_services")
        
    except Exception as e:
        logger.error(f"Error during WebSocket services cleanup: {e}")
    
    finally:
        # Reset global variables
        connection_manager = None
        room_manager = None
        message_handler = None