#!/usr/bin/env python3
"""
Simple WebSocket client test script for testing the chat endpoint
"""

import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_websocket_connection():
    """Test basic WebSocket connection and messaging"""
    uri = "ws://localhost:8000/ws/chat/testroom123"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            logger.info(f"Received welcome: {welcome_data}")
            
            # Send a text message
            text_message = {
                "type": "text",
                "content": "Hello from test client!",
                "user_id": "test_user",
                "room_id": "testroom123"
            }
            
            await websocket.send(json.dumps(text_message))
            logger.info("Sent text message")
            
            # Send typing indicator
            typing_message = {
                "type": "typing",
                "is_typing": True,
                "user_id": "test_user",
                "room_id": "testroom123"
            }
            
            await websocket.send(json.dumps(typing_message))
            logger.info("Sent typing indicator")
            
            # Wait for any responses
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                response_data = json.loads(response)
                logger.info(f"Received response: {response_data}")
            except asyncio.TimeoutError:
                logger.info("No response received (expected for single client)")
            
            logger.info("WebSocket test completed successfully")
            
    except Exception as e:
        logger.error(f"WebSocket test failed: {e}")


async def test_multiple_clients():
    """Test multiple clients in the same room"""
    room_id = "testroommulti"
    
    async def client_handler(client_id: str):
        uri = f"ws://localhost:8000/ws/chat/{room_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"Client {client_id} connected")
                
                # Wait for welcome message
                welcome = await websocket.recv()
                logger.info(f"Client {client_id} received welcome")
                
                # Send a message
                message = {
                    "type": "text",
                    "content": f"Hello from {client_id}!",
                    "user_id": client_id,
                    "room_id": room_id
                }
                
                await websocket.send(json.dumps(message))
                logger.info(f"Client {client_id} sent message")
                
                # Listen for messages for a short time
                try:
                    for _ in range(3):
                        response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        response_data = json.loads(response)
                        logger.info(f"Client {client_id} received: {response_data.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    pass
                
                logger.info(f"Client {client_id} finished")
                
        except Exception as e:
            logger.error(f"Client {client_id} error: {e}")
    
    # Run multiple clients concurrently
    await asyncio.gather(
        client_handler("client1"),
        client_handler("client2"),
        client_handler("client3")
    )


if __name__ == "__main__":
    print("Testing WebSocket endpoint...")
    print("Make sure the backend server is running on localhost:8000")
    print()
    
    # Test single client
    print("=== Testing single client ===")
    asyncio.run(test_websocket_connection())
    
    print()
    
    # Test multiple clients
    print("=== Testing multiple clients ===")
    asyncio.run(test_multiple_clients())
    
    print()
    print("WebSocket tests completed!")