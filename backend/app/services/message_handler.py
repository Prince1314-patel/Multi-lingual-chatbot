import asyncio
import logging
from typing import Dict, Optional, Set
from datetime import timedelta
from fastapi import WebSocket

from ..utils import get_current_time

from .connection_manager import ConnectionManager
from .room_manager import RoomManager
from .rate_limiter import RateLimiter
from ..models import (
    MessageType,
    TextMessage,
    VoiceMessage,
    TypingMessage,
    UserJoinMessage,
    UserLeaveMessage,
    MessageDeliveryConfirmation,
    ErrorMessage,
    TranslationRequest,
    TranslationResult,
    deserialize_message,
    serialize_message
)
from ..ai_services.translation_service import TranslationService

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles processing and routing of different message types"""
    
    def __init__(self, connection_manager: ConnectionManager, room_manager: RoomManager, 
                 rate_limiter: Optional[RateLimiter] = None,
                 translation_service: Optional[TranslationService] = None):
        """
        Initialize MessageHandler
        
        Args:
            connection_manager: ConnectionManager instance for handling connections
            room_manager: RoomManager instance for room operations
            rate_limiter: Optional RateLimiter instance for message rate limiting
            translation_service: Optional TranslationService instance for text translation
        """
        self.connection_manager = connection_manager
        self.room_manager = room_manager
        self.rate_limiter = rate_limiter
        self.translation_service = translation_service
        
        # Typing indicator management
        self.typing_timeouts: Dict[str, Dict[str, asyncio.Task]] = {}
        
        # Translation progress tracking
        self.translation_in_progress: Set[str] = set()  # Track rooms with active translations
    
    async def handle_message(self, websocket: WebSocket, message_data: dict) -> bool:
        """
        Handle incoming message from WebSocket
        
        Args:
            websocket: The WebSocket connection
            message_data: Raw message data dictionary
            
        Returns:
            True if message was handled successfully, False otherwise
        """
        try:
            # Get connection info
            connection = self.connection_manager.get_connection_info(websocket)
            if not connection:
                await self.connection_manager.send_error(
                    websocket, "CONNECTION_NOT_FOUND", "Connection not found"
                )
                return False
            
            # --- START: CORRECTED LOGIC ---
            # Enrich message data with trusted connection data BEFORE deserialization
            # This ensures Pydantic validation passes with required fields
            message_data['user_id'] = connection.user_id
            # Only set room_id if not already provided (for validation purposes)
            if 'room_id' not in message_data:
                message_data['room_id'] = connection.room_id
            # Always generate server-side timestamp to ensure consistency (as datetime object)
            message_data['timestamp'] = get_current_time()
            # Add display name from connection
            message_data['display_name'] = connection.get_display_name()
            # --- END: CORRECTED LOGIC ---

            # Deserialize message (now with all required fields)
            try:
                message = deserialize_message(message_data)
            except (ValueError, KeyError) as e:
                await self.connection_manager.send_error(
                    websocket, "INVALID_MESSAGE_FORMAT", f"Invalid message format: {str(e)}"
                )
                return False
            
            # Validate message belongs to the connection's room (now works for all types)
            if hasattr(message, 'room_id') and message.room_id != connection.room_id:
                await self.connection_manager.send_error(
                    websocket, "INVALID_ROOM", "Message room does not match connection room"
                )
                return False
            
            # Route message based on type
            if isinstance(message, TextMessage):
                return await self.handle_text_message(connection, message)
            elif isinstance(message, VoiceMessage):
                return await self.handle_voice_message(connection, message)
            elif isinstance(message, TypingMessage):
                return await self.handle_typing_message(connection, message)
            else:
                await self.connection_manager.send_error(
                    websocket, "UNSUPPORTED_MESSAGE_TYPE", f"Unsupported message type: {type(message).__name__}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.connection_manager.send_error(
                websocket, "MESSAGE_PROCESSING_ERROR", "Failed to process message"
            )
            return False
    
    async def handle_binary_message(self, websocket: WebSocket, binary_data: bytes) -> bool:
        """
        Handle incoming binary message (voice data) from WebSocket
        
        Args:
            websocket: The WebSocket connection
            binary_data: Raw binary audio data
            
        Returns:
            True if message was handled successfully, False otherwise
        """
        try:
            # Get connection info
            connection = self.connection_manager.get_connection_info(websocket)
            if not connection:
                await self.connection_manager.send_error(
                    websocket, "CONNECTION_NOT_FOUND", "Connection not found"
                )
                return False
            
            # Validate binary data
            if not binary_data:
                await self.connection_manager.send_error(
                    websocket, "EMPTY_BINARY_DATA", "Binary data cannot be empty"
                )
                return False
            
            # Validate audio data size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if len(binary_data) > max_size:
                await self.connection_manager.send_error(
                    websocket, "BINARY_DATA_TOO_LARGE", f"Binary data exceeds maximum size of {max_size} bytes"
                )
                return False
            
            # Create VoiceMessage with binary data and server-side timestamp
            voice_message = VoiceMessage(
                user_id=connection.user_id,
                room_id=connection.room_id,
                display_name=connection.get_display_name(),
                audio_data=binary_data,
                audio_format="webm",  # Default format, could be detected or specified
                timestamp=get_current_time()  # Server-side timestamp
            )
            
            # Update connection activity
            connection.update_activity()
            
            # Broadcast to all users in the room with delivery confirmation
            sent_count = await self.connection_manager.broadcast_to_room(
                connection.room_id, voice_message, exclude_user=connection.user_id, send_confirmation=True
            )
            
            logger.info(f"Binary voice message from {connection.user_id} ({len(binary_data)} bytes) broadcasted to {sent_count} users in room {connection.room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling binary message: {e}")
            await self.connection_manager.send_error(
                websocket, "BINARY_MESSAGE_PROCESSING_ERROR", "Failed to process binary message"
            )
            return False
    
    async def handle_text_message(self, connection, message: TextMessage) -> bool:
        """
        Handle text message processing and broadcasting with translation support
        
        Args:
            connection: ConnectionInfo object
            message: TextMessage to process
            
        Returns:
            True if message was handled successfully
        """
        try:
            # Check rate limit if rate limiter is available
            if self.rate_limiter:
                allowed, wait_time = self.rate_limiter.check_message_rate_limit(
                    connection.user_id, 'text'
                )
                if not allowed:
                    await self.connection_manager.send_error(
                        connection.websocket, "RATE_LIMIT_EXCEEDED", 
                        f"Text message rate limit exceeded. Wait {wait_time:.1f} seconds."
                    )
                    return False
            
            # Update connection activity
            connection.update_activity()
            
            # Set typing to false when user sends a message (this will prevent typing timeout)
            connection.set_typing(False)
            
            # Cancel any existing typing timeout for this user
            room_id = connection.room_id
            user_id = connection.user_id
            if (room_id in self.typing_timeouts and 
                user_id in self.typing_timeouts[room_id]):
                self.typing_timeouts[room_id][user_id].cancel()
                del self.typing_timeouts[room_id][user_id]
            
            # Validate message content
            if not message.content or not message.content.strip():
                await self.connection_manager.send_error(
                    connection.websocket, "EMPTY_MESSAGE", "Message content cannot be empty"
                )
                return False
            
            # Set target language based on user preferences if not already set
            if not message.target_language and connection.preferred_language:
                message.target_language = connection.preferred_language
            
            # Handle translation if translation service is available
            if self.translation_service and self.translation_service.enabled:
                # Get all users in the room to determine translation needs
                room = self.room_manager.get_room(connection.room_id)
                if room:
                    connections = room.get_all_connections()
                    
                    # Check if any users need translation (different preferred language than sender)
                    needs_translation = False
                    sender_preferred_lang = connection.preferred_language
                    
                    for user_id, user_connection in connections.items():
                        if user_id != connection.user_id:  # Skip sender
                            if (user_connection.preferred_language and 
                                sender_preferred_lang and
                                user_connection.preferred_language != sender_preferred_lang):
                                needs_translation = True
                                logger.info(f"🔄 Translation needed: sender prefers {sender_preferred_lang}, user {user_id} prefers {user_connection.preferred_language}")
                                break
                    
                    if needs_translation:
                        # Don't broadcast original message immediately when translation is needed
                        # Instead, process translation and send personalized messages to each user
                        logger.info(f"🔄 Translation needed, processing personalized messages for each user")
                        
                        # Mark translation as in progress for this room
                        self.translation_in_progress.add(connection.room_id)
                        
                        # Process translation asynchronously for each user
                        asyncio.create_task(self._process_translation_for_all_users(connection, message))
                        
                        logger.info(f"Text message from {connection.user_id} - translation processing started for room {connection.room_id}")
                        return True
                    else:
                        logger.info(f"⏭️  No translation needed: all users have same preferred language or no preferences")
            
            # No translation needed, broadcast immediately
            sent_count = await self.connection_manager.broadcast_to_room(
                connection.room_id, message, exclude_user=connection.user_id, send_confirmation=True
            )
            
            logger.info(f"Text message from {connection.user_id} broadcasted to {sent_count} users in room {connection.room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            return False
    
    async def handle_voice_message(self, connection, message: VoiceMessage) -> bool:
        """
        Handle voice message processing and broadcasting with rate limiting
        
        Args:
            connection: ConnectionInfo object
            message: VoiceMessage to process
            
        Returns:
            True if message was handled successfully
        """
        try:
            # Check rate limit if rate limiter is available
            if self.rate_limiter:
                allowed, wait_time = self.rate_limiter.check_message_rate_limit(
                    connection.user_id, 'voice'
                )
                if not allowed:
                    await self.connection_manager.send_error(
                        connection.websocket, "RATE_LIMIT_EXCEEDED", 
                        f"Voice message rate limit exceeded. Wait {wait_time:.1f} seconds."
                    )
                    return False
            
            # Update connection activity
            connection.update_activity()
            
            # Validate voice message
            if not message.audio_data:
                await self.connection_manager.send_error(
                    connection.websocket, "EMPTY_VOICE_MESSAGE", "Voice message must contain audio data"
                )
                return False
            
            # Validate audio data size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if len(message.audio_data) > max_size:
                await self.connection_manager.send_error(
                    connection.websocket, "VOICE_MESSAGE_TOO_LARGE", f"Voice message exceeds maximum size of {max_size} bytes"
                )
                return False
            
            # Validate duration if provided
            if message.duration is not None and (message.duration <= 0 or message.duration > 300):
                await self.connection_manager.send_error(
                    connection.websocket, "INVALID_DURATION", "Voice message duration must be between 0 and 300 seconds"
                )
                return False
            
            # Broadcast to all users in the room with delivery confirmation
            sent_count = await self.connection_manager.broadcast_to_room(
                connection.room_id, message, exclude_user=connection.user_id, send_confirmation=True
            )
            
            logger.info(f"Voice message from {connection.user_id} broadcasted to {sent_count} users in room {connection.room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling voice message: {e}")
            return False
    
    async def handle_typing_message(self, connection, message: TypingMessage) -> bool:
        """
        Handle typing indicator message processing with rate limiting
        
        Args:
            connection: ConnectionInfo object
            message: TypingMessage to process
            
        Returns:
            True if message was handled successfully
        """
        try:
            # Check rate limit if rate limiter is available
            if self.rate_limiter:
                allowed, wait_time = self.rate_limiter.check_message_rate_limit(
                    connection.user_id, 'typing'
                )
                if not allowed:
                    # For typing messages, we silently drop them instead of sending error
                    # to avoid spamming the user with rate limit errors
                    logger.debug(f"Typing message rate limited for user {connection.user_id}")
                    return False
            
            # Update connection activity
            connection.update_activity()
            
            # Get room
            room = self.room_manager.get_room(connection.room_id)
            if not room:
                logger.warning(f"Room {connection.room_id} not found for typing message")
                return False
            
            # Update typing status in connection
            connection.set_typing(message.isTyping)
            
            # Manage typing timeout
            await self._manage_typing_timeout(connection, message.isTyping)
            
            # Broadcast typing indicator to other users in the room (exclude sender)
            sent_count = await self.connection_manager.broadcast_to_room(
                connection.room_id, message, exclude_user=connection.user_id
            )
            
            logger.debug(f"Typing indicator from {connection.user_id} (typing: {message.isTyping}) broadcasted to {sent_count} users")
            return True
            
        except Exception as e:
            logger.error(f"Error handling typing message: {e}")
            return False
    
    async def _manage_typing_timeout(self, connection, is_typing: bool):
        """
        Manage typing indicator timeout for a user
        
        Args:
            connection: ConnectionInfo object
            is_typing: Whether user is currently typing
        """
        room_id = connection.room_id
        user_id = connection.user_id
        
        # Initialize room typing timeouts if needed
        if room_id not in self.typing_timeouts:
            self.typing_timeouts[room_id] = {}
        
        # Cancel existing timeout task if any
        if user_id in self.typing_timeouts[room_id]:
            self.typing_timeouts[room_id][user_id].cancel()
            del self.typing_timeouts[room_id][user_id]
        
        # Set new timeout if user is typing
        if is_typing:
            timeout_task = asyncio.create_task(
                self._typing_timeout_handler(connection, 30.0)  # Increased to 30 seconds to avoid interference with translation
            )
            self.typing_timeouts[room_id][user_id] = timeout_task
    
    async def _typing_timeout_handler(self, connection, timeout_seconds: float):
        """
        Handle typing indicator timeout
        
        Args:
            connection: ConnectionInfo object
            timeout_seconds: Timeout duration in seconds
        """
        try:
            await asyncio.sleep(timeout_seconds)
            
            # Check if user is still typing (might have been updated)
            if connection.is_typing:
                # Set typing to false
                connection.set_typing(False)
                
                # Don't send typing stopped message if translation is in progress
                if connection.room_id in self.translation_in_progress:
                    logger.debug(f"Skipping typing timeout message for user {connection.user_id} - translation in progress")
                else:
                    # Send typing stopped message to other users
                    typing_message = TypingMessage(
                        user_id=connection.user_id,
                        room_id=connection.room_id,
                        isTyping=False
                    )
                    
                    await self.connection_manager.broadcast_to_room(
                        connection.room_id, typing_message, exclude_user=connection.user_id
                    )
                    
                    logger.debug(f"Typing timeout for user {connection.user_id} in room {connection.room_id}")
            else:
                # User is not typing, just clean up without sending message
                logger.debug(f"Typing timeout cleanup for user {connection.user_id} in room {connection.room_id} (not typing)")
            
            # Clean up timeout task
            room_id = connection.room_id
            user_id = connection.user_id
            if (room_id in self.typing_timeouts and 
                user_id in self.typing_timeouts[room_id]):
                del self.typing_timeouts[room_id][user_id]
                
        except asyncio.CancelledError:
            # Task was cancelled, which is normal
            pass
        except Exception as e:
            logger.error(f"Error in typing timeout handler: {e}")
    
    async def handle_user_disconnect(self, connection):
        """
        Handle cleanup when a user disconnects
        
        Args:
            connection: ConnectionInfo object of disconnected user
        """
        try:
            room_id = connection.room_id
            user_id = connection.user_id
            
            # Cancel any active typing timeout
            if (room_id in self.typing_timeouts and 
                user_id in self.typing_timeouts[room_id]):
                self.typing_timeouts[room_id][user_id].cancel()
                del self.typing_timeouts[room_id][user_id]
                
                # Clean up empty room entry
                if not self.typing_timeouts[room_id]:
                    del self.typing_timeouts[room_id]
            
            # If user was typing, send typing stopped message
            if connection.is_typing:
                typing_message = TypingMessage(
                    user_id=user_id,
                    room_id=room_id,
                    isTyping=False
                )
                
                await self.connection_manager.broadcast_to_room(
                    room_id, typing_message, exclude_user=user_id
                )
            
            logger.debug(f"Cleaned up typing state for disconnected user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling user disconnect cleanup: {e}")
    
    def get_typing_users(self, room_id: str) -> Set[str]:
        """
        Get set of users currently typing in a room
        
        Args:
            room_id: The room ID
            
        Returns:
            Set of user IDs currently typing
        """
        room = self.room_manager.get_room(room_id)
        if room:
            return room.get_typing_users()
        return set()
    
    def get_message_handler_stats(self) -> Dict:
        """
        Get statistics about the message handler
        
        Returns:
            Dictionary with message handler statistics
        """
        total_typing_timeouts = sum(len(room_timeouts) for room_timeouts in self.typing_timeouts.values())
        
        return {
            'active_typing_timeouts': total_typing_timeouts,
            'rooms_with_typing': len(self.typing_timeouts),
            'typing_timeout_seconds': 3.0
        }
    
    async def cleanup_all_typing_timeouts(self):
        """Clean up all active typing timeouts (useful for shutdown)"""
        for room_timeouts in self.typing_timeouts.values():
            for timeout_task in room_timeouts.values():
                timeout_task.cancel()
        
        self.typing_timeouts.clear()
        logger.info("Cleaned up all typing timeouts")
    
    async def _process_translation_for_all_users(self, connection, message: TextMessage) -> None:
        """
        Process translation for a text message for each user based on their preferred language.
        
        This method handles the translation of text messages for each user individually,
        translating to their preferred language and sending personalized messages.
        
        Args:
            connection: ConnectionInfo object of the sender
            message: TextMessage to translate
        """
        try:
            logger.info(f"🔄 Starting translation for all users for message {message.id} from {connection.user_id}")
            logger.info(f"📝 Original message: '{message.content}' (lang: {message.lang})")
            
            # Get all users in the room
            room = self.room_manager.get_room(connection.room_id)
            if not room:
                logger.error(f"Room {connection.room_id} not found for translation")
                return
            
            connections = room.get_all_connections()
            
            # Process translation for each user
            for user_id, user_connection in connections.items():
                if user_id == connection.user_id:
                    continue  # Skip sender
                
                # Check if this user needs translation (different preferred language than sender)
                sender_preferred_lang = connection.preferred_language
                if (user_connection.preferred_language and 
                    sender_preferred_lang and
                    user_connection.preferred_language != sender_preferred_lang):
                    
                    logger.info(f"🔄 Translating for user {user_id} to {user_connection.preferred_language}")
                    logger.info(f"📝 Sender ({connection.user_id}) prefers: {sender_preferred_lang}")
                    logger.info(f"📝 Receiver ({user_id}) prefers: {user_connection.preferred_language}")
                    
                    try:
                        # Create translation request for this specific user
                        translation_request = TranslationRequest(
                            text=message.content,
                            source_language=None,  # Let the service detect the language automatically
                            target_language=user_connection.preferred_language,
                            user_id=connection.user_id,
                            room_id=connection.room_id,
                            message_id=message.id,
                            timestamp=get_current_time()
                        )
                        
                        # Perform translation
                        translation_result = await self.translation_service.translate_text(translation_request)
                        
                        logger.info(f"✅ Translation completed for user {user_id}!")
                        logger.info(f"📝 Original: '{translation_result.original_text}' ({translation_result.source_language})")
                        logger.info(f"🔄 Translated: '{translation_result.translated_text}' ({translation_result.target_language})")
                        
                        # Create personalized message for this user
                        personalized_message = TextMessage(
                            id=message.id,
                            user_id=message.user_id,
                            room_id=message.room_id,
                            display_name=message.display_name,
                            timestamp=message.timestamp,
                            content=message.content,
                            lang=message.lang,
                            translated_content=translation_result.translated_text,
                            target_language=user_connection.preferred_language,
                            translation_status="completed",
                            translation_error=None,
                            status="delivered"
                        )
                        
                        # Send personalized message to this specific user
                        await self.connection_manager.send_message(user_connection.websocket, personalized_message)
                        
                        logger.info(f"📤 Personalized translation sent to user {user_id}")
                        
                    except Exception as e:
                        logger.error(f"❌ Translation failed for user {user_id}: {e}")
                        
                        # Send error message to this user
                        error_message = TextMessage(
                            id=message.id,
                            user_id=message.user_id,
                            room_id=message.room_id,
                            display_name=message.display_name,
                            timestamp=message.timestamp,
                            content=message.content,
                            lang=message.lang,
                            translated_content=None,
                            target_language=user_connection.preferred_language,
                            translation_status="failed",
                            translation_error=str(e),
                            status="delivered"
                        )
                        
                        await self.connection_manager.send_message(user_connection.websocket, error_message)
                
                else:
                    logger.info(f"⏭️  No translation needed for user {user_id} (same language or no preference)")
                    logger.info(f"📝 Sender prefers: {sender_preferred_lang}, User prefers: {user_connection.preferred_language}")
                    
                    # Send original message to users who have same language or no preference
                    original_message = TextMessage(
                        id=message.id,
                        user_id=message.user_id,
                        room_id=message.room_id,
                        display_name=message.display_name,
                        timestamp=message.timestamp,
                        content=message.content,
                        lang=message.lang,
                        translated_content=None,
                        target_language=None,
                        translation_status=None,
                        translation_error=None,
                        status="delivered"
                    )
                    
                    await self.connection_manager.send_message(user_connection.websocket, original_message)
                    logger.info(f"📤 Original message sent to user {user_id} (no translation needed)")
            
            logger.info(f"📤 Translation processing completed for message {message.id}")
            
            # Remove room from translation in progress
            if connection.room_id in self.translation_in_progress:
                self.translation_in_progress.remove(connection.room_id)
                logger.debug(f"Removed room {connection.room_id} from translation in progress")
            
        except Exception as e:
            logger.error(f"❌ Error in translation processing for all users: {e}")
            logger.error(f"📝 Failed message content: '{message.content}'")
            
            # Remove room from translation in progress even on error
            if connection.room_id in self.translation_in_progress:
                self.translation_in_progress.remove(connection.room_id)
                logger.debug(f"Removed room {connection.room_id} from translation in progress (error)")