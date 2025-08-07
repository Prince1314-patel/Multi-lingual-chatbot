#!/usr/bin/env python3
"""
Simple test to check if basic message processing is working
"""

import asyncio
import json
import websockets
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_simple_message():
    """Test basic message functionality"""
    print("🧪 Testing Basic Message Functionality")
    print("=" * 50)
    
    # Simple test message
    test_message = {
        "type": "text",
        "content": "Hello, this is a test message"
    }
    
    try:
        # Connect to WebSocket
        uri = "ws://localhost:8000/ws/chat/test_room?user_id=test_user&display_name=Test%20User"
        
        print(f"🔌 Connecting to WebSocket: {uri}")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Wait for connection established message
            response = await websocket.recv()
            print(f"📨 Received: {response}")
            
            # Send test message
            print(f"📤 Sending test message: {test_message['content']}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for responses
            print("⏳ Waiting for responses...")
            responses = []
            for i in range(3):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    responses.append(response)
                    print(f"📨 Received response {i+1}: {response}")
                except asyncio.TimeoutError:
                    break
            
            # Check responses
            for response in responses:
                try:
                    response_data = json.loads(response)
                    print(f"📊 Response type: {response_data.get('type')}")
                    if response_data.get("type") == "text":
                        print("✅ Text message received successfully")
                    elif response_data.get("type") == "message_confirmation":
                        status = response_data.get("status", "unknown")
                        print(f"📊 Message confirmation status: {status}")
                        
                except json.JSONDecodeError:
                    print(f"⚠️  Non-JSON response: {response}")
                
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    
    return True

async def main():
    """Main test function"""
    print("🚀 Simple Message Test")
    print("=" * 50)
    
    success = await test_simple_message()
    
    if success:
        print("\n🎉 Simple message test completed!")
    else:
        print("\n❌ Simple message test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 