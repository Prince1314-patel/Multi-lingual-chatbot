#!/usr/bin/env python3
"""
Simple voice message test
"""

import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def simple_voice_test():
    """Simple test for voice message functionality"""
    uri = "ws://localhost:8000/ws/chat/simplevoice123"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to WebSocket")
            
            # Wait for welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            logger.info(f"Connected as user: {welcome_data['user_id']}")
            
            # Send binary voice data
            voice_data = b"SIMPLE_VOICE_TEST_" + b"x" * 100
            await websocket.send(voice_data)
            logger.info(f"Sent voice data: {len(voice_data)} bytes")
            
            # Try to receive response (will timeout for single client, which is expected)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                if isinstance(response, bytes):
                    logger.info(f"✅ Received binary response: {len(response)} bytes")
                    if response == voice_data:
                        logger.info("✅ Voice data matches!")
                else:
                    logger.info(f"Received text response: {response}")
            except asyncio.TimeoutError:
                logger.info("✅ No response (expected for single client)")
            
            logger.info("Simple voice test completed successfully")
            
    except Exception as e:
        logger.error(f"Simple voice test failed: {e}")


if __name__ == "__main__":
    asyncio.run(simple_voice_test())