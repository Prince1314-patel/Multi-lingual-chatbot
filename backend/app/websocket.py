import json
import logging
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.routing import APIRouter

from .services import ConnectionManager, RoomManager, MessageHandler
from .models import validate_room_id, generate_user_id

logger = logging.getLogger(__name__)

# Create router for WebSocket endpoints
websocket_router = APIRouter()

# Global service instances (will be initialized in main.py)
connection_manager: Optional[ConnectionManager] = None
room_manager: Optional[RoomManager] = None
message_handler: Optional[MessageHandler] = None


def init_websocket_services():
    """Initialize WebSocket services - called from main.py"""
    global connection_manager, room_manager, message_handler
    
    connection_manager = ConnectionManager()
    room_manager = RoomManager(cleanup_timeout_minutes=30)
    message_handler = MessageHandler(connection_manager, room_manager)
    
    logger.info("WebSocket services initialized")


def get_services():
    """Dependency to get WebSocket services"""
    if not all([connection_manager, room_manager, message_handler]):
        raise HTTPException(status_code=500, detail="WebSocket services not initialized")
    
    return connection_manager, room_manager, message_handler


@websocket_router.websocket("/ws/chat/{room_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    room_id: str,
    user_id: Optional[str] = None
):
    """
    WebSocket endpoint for chat rooms
    
    Args:
        websocket: WebSocket connection
        room_id: The chat room ID to join
        user_id: Optional user ID (will generate if not provided)
    """
    # Get services
    conn_mgr, room_mgr, msg_handler = get_services()
    
    # Validate room ID
    if not validate_room_id(room_id):
        logger.warning(f"Invalid room ID attempted: {room_id}")
        await websocket.close(code=4000, reason="Invalid room ID format")
        return
    
    # Generate user ID if not provided
    if not user_id:
        user_id = generate_user_id()
    
    connection = None
    
    try:
        # Accept WebSocket connection and join room
        connection = await conn_mgr.connect(websocket, room_id, user_id)
        
        # Get or create room
        room = room_mgr.get_or_create_room(room_id)
        
        logger.info(f"User {user_id} connected to room {room_id}")
        
        # Send welcome message with connection info
        welcome_message = {
            "type": "connection_established",
            "user_id": user_id,
            "room_id": room_id,
            "room_info": {
                "connection_count": room.get_connection_count(),
                "created_at": room.created_at.isoformat()
            }
        }
        
        await websocket.send_text(json.dumps(welcome_message))
        
        # Main message handling loop
        while True:
            try:
                # Receive message from WebSocket (can be text or binary)
                message = await websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "text" in message:
                        # Handle text message (JSON)
                        try:
                            message_data = json.loads(message["text"])
                            success = await msg_handler.handle_message(websocket, message_data)
                            
                            if not success:
                                logger.warning(f"Failed to handle text message from {user_id}")
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON from {user_id}: {e}")
                            await conn_mgr.send_error(
                                websocket, "INVALID_JSON", "Message must be valid JSON"
                            )
                            
                    elif "bytes" in message:
                        # Handle binary message (voice data)
                        binary_data = message["bytes"]
                        success = await msg_handler.handle_binary_message(websocket, binary_data)
                        
                        if not success:
                            logger.warning(f"Failed to handle binary message from {user_id}")
                    
                    else:
                        logger.warning(f"Received message with no text or bytes from {user_id}")
                        await conn_mgr.send_error(
                            websocket, "INVALID_MESSAGE", "Message must contain text or binary data"
                        )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user_id}")
                break
            
            except Exception as e:
                logger.error(f"Error handling message from {user_id}: {e}")
                await conn_mgr.send_error(
                    websocket, "MESSAGE_ERROR", "Failed to process message"
                )
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed during handshake for room {room_id}")
    
    except Exception as e:
        logger.error(f"Error in WebSocket endpoint for room {room_id}: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass  # Connection might already be closed
    
    finally:
        # Clean up connection
        if connection:
            try:
                # Handle user disconnect cleanup
                await msg_handler.handle_user_disconnect(connection)
                
                # Disconnect from connection manager
                await conn_mgr.disconnect(websocket)
                
                logger.info(f"Cleaned up connection for user {user_id} in room {room_id}")
                
            except Exception as e:
                logger.error(f"Error during connection cleanup for {user_id}: {e}")


@websocket_router.get("/ws/rooms/{room_id}/info")
async def get_room_info(room_id: str):
    """
    Get information about a specific room
    
    Args:
        room_id: The room ID to get info for
        
    Returns:
        Room information dictionary
    """
    # Get services
    conn_mgr, room_mgr, msg_handler = get_services()
    
    # Validate room ID
    if not validate_room_id(room_id):
        raise HTTPException(status_code=400, detail="Invalid room ID format")
    
    # Get room info
    room_info = room_mgr.get_detailed_room_info(room_id)
    
    if not room_info:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Add typing users info
    room_info['typing_users'] = list(msg_handler.get_typing_users(room_id))
    
    return room_info


@websocket_router.get("/ws/rooms")
async def list_active_rooms():
    """
    List all active rooms
    
    Returns:
        List of active room IDs and basic info
    """
    # Get services
    conn_mgr, room_mgr, msg_handler = get_services()
    
    active_rooms = room_mgr.get_active_rooms()
    
    rooms_info = []
    for room_id in active_rooms:
        room_info = room_mgr.get_detailed_room_info(room_id)
        if room_info:
            # Add minimal info for listing
            rooms_info.append({
                'room_id': room_id,
                'connection_count': room_info['connection_count'],
                'created_at': room_info['created_at'],
                'last_activity': room_info['last_activity']
            })
    
    return {
        'active_rooms': rooms_info,
        'total_count': len(rooms_info)
    }


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
    Health check endpoint for WebSocket services
    
    Returns:
        Health status of WebSocket services
    """
    try:
        # Get services
        conn_mgr, room_mgr, msg_handler = get_services()
        
        return {
            'status': 'healthy',
            'services': {
                'connection_manager': 'initialized',
                'room_manager': 'initialized', 
                'message_handler': 'initialized'
            },
            'stats': {
                'total_connections': conn_mgr.get_total_connections(),
                'total_rooms': len(room_mgr.rooms),
                'active_typing_timeouts': msg_handler.get_message_handler_stats()['active_typing_timeouts']
            }
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="WebSocket services unavailable")


# Cleanup function for graceful shutdown
async def cleanup_websocket_services():
    """Clean up WebSocket services on shutdown"""
    global connection_manager, room_manager, message_handler
    
    try:
        if message_handler:
            await message_handler.cleanup_all_typing_timeouts()
            logger.info("Cleaned up message handler")
        
        if room_manager:
            await room_manager.stop_cleanup_task()
            logger.info("Stopped room manager cleanup task")
        
        logger.info("WebSocket services cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during WebSocket services cleanup: {e}")
    
    finally:
        # Reset global variables
        connection_manager = None
        room_manager = None
        message_handler = None