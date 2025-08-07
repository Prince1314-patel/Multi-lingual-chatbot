#!/usr/bin/env python3
"""
Integration test script for testing voice message transmission via WebSocket
"""

import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_voice_message_transmission():
    """Test binary voice message transmission"""
    uri = "ws://localhost:8000/ws/chat/voicetest123"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket for voice test")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            logger.info(f"Received welcome: {welcome_data}")
            
            # Send a text message first
            text_message = {
                "type": "text",
                "content": "About to send voice message",
                "user_id": "voice_test_user",
                "room_id": "voicetest123"
            }
            
            await websocket.send(json.dumps(text_message))
            logger.info("Sent text message")
            
            # Wait for text message echo
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                response_data = json.loads(response)
                logger.info(f"Received text response: {response_data.get('content', 'N/A')}")
            except asyncio.TimeoutError:
                logger.info("No text response received")
            
            # Send binary voice data
            fake_audio_data = b"FAKE_AUDIO_DATA_" + b"x" * 1000  # 1KB of fake audio
            await websocket.send(fake_audio_data)
            logger.info(f"Sent binary voice data ({len(fake_audio_data)} bytes)")
            
            # Wait for binary response
            try:
                binary_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                if isinstance(binary_response, bytes):
                    logger.info(f"Received binary response ({len(binary_response)} bytes)")
                    # Verify it's the same data
                    if binary_response == fake_audio_data:
                        logger.info("✅ Binary data matches sent data!")
                    else:
                        logger.warning("❌ Binary data doesn't match sent data")
                else:
                    logger.info(f"Received non-binary response: {binary_response}")
            except asyncio.TimeoutError:
                logger.info("No binary response received (expected for single client)")
            
            logger.info("Voice message test completed successfully")
            
    except Exception as e:
        logger.error(f"Voice message test failed: {e}")


async def test_multiple_clients_voice():
    """Test voice message broadcasting between multiple clients"""
    room_id = "voicemulti123"
    
    async def voice_client_handler(client_id: str, should_send_voice: bool = False):
        uri = f"ws://localhost:8000/ws/chat/{room_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"Voice client {client_id} connected")
                
                # Wait for welcome message
                welcome = await websocket.recv()
                logger.info(f"Voice client {client_id} received welcome")
                
                if should_send_voice:
                    # Send voice message
                    voice_data = f"VOICE_FROM_{client_id}_".encode() + b"x" * 500
                    await websocket.send(voice_data)
                    logger.info(f"Voice client {client_id} sent voice data ({len(voice_data)} bytes)")
                
                # Listen for messages
                try:
                    for _ in range(3):
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        if isinstance(response, bytes):
                            logger.info(f"Voice client {client_id} received binary data ({len(response)} bytes)")
                        else:
                            response_data = json.loads(response)
                            logger.info(f"Voice client {client_id} received: {response_data.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    pass
                
                logger.info(f"Voice client {client_id} finished")
                
        except Exception as e:
            logger.error(f"Voice client {client_id} error: {e}")
    
    # Run multiple clients - one sends voice, others receive
    await asyncio.gather(
        voice_client_handler("voice_sender", should_send_voice=True),
        voice_client_handler("voice_receiver1"),
        voice_client_handler("voice_receiver2")
    )


async def test_large_voice_message():
    """Test handling of large voice messages"""
    uri = "ws://localhost:8000/ws/chat/largetest123"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected for large voice message test")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            logger.info("Received welcome for large test")
            
            # Send large voice data (5MB)
            large_voice_data = b"LARGE_VOICE_" + b"x" * (5 * 1024 * 1024)
            await websocket.send(large_voice_data)
            logger.info(f"Sent large voice data ({len(large_voice_data)} bytes)")
            
            # Wait for response or error
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                if isinstance(response, bytes):
                    logger.info(f"Received large binary response ({len(response)} bytes)")
                else:
                    response_data = json.loads(response)
                    if response_data.get('type') == 'error':
                        logger.info(f"Received expected error: {response_data.get('message')}")
                    else:
                        logger.info(f"Received response: {response_data}")
            except asyncio.TimeoutError:
                logger.info("No response to large voice message")
            
    except Exception as e:
        logger.error(f"Large voice message test failed: {e}")


async def test_invalid_voice_data():
    """Test handling of invalid voice data"""
    uri = "ws://localhost:8000/ws/chat/invalidtest123"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected for invalid voice data test")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            logger.info("Received welcome for invalid test")
            
            # Send empty binary data
            await websocket.send(b"")
            logger.info("Sent empty binary data")
            
            # Wait for error response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                response_data = json.loads(response)
                if response_data.get('type') == 'error':
                    logger.info(f"✅ Received expected error for empty data: {response_data.get('message')}")
                else:
                    logger.warning(f"❌ Expected error but got: {response_data}")
            except asyncio.TimeoutError:
                logger.warning("❌ No error response received for empty data")
            
    except Exception as e:
        logger.error(f"Invalid voice data test failed: {e}")


if __name__ == "__main__":
    print("Testing voice message WebSocket functionality...")
    print("Make sure the backend server is running on localhost:8000")
    print()
    
    # Test single client voice transmission
    print("=== Testing single client voice transmission ===")
    asyncio.run(test_voice_message_transmission())
    
    print()
    
    # Test multiple clients voice broadcasting
    print("=== Testing multiple clients voice broadcasting ===")
    asyncio.run(test_multiple_clients_voice())
    
    print()
    
    # Test large voice message handling
    print("=== Testing large voice message handling ===")
    asyncio.run(test_large_voice_message())
    
    print()
    
    # Test invalid voice data handling
    print("=== Testing invalid voice data handling ===")
    asyncio.run(test_invalid_voice_data())
    
    print()
    print("Voice message WebSocket tests completed!")