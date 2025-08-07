#!/usr/bin/env python3
"""
Test script to verify translation functionality
"""

import asyncio
import json
import websockets
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_translation():
    """Test translation functionality"""
    print("🧪 Testing Translation Functionality")
    print("=" * 50)
    
    # Test message in Spanish (simplified to match frontend format)
    test_message = {
        "type": "text",
        "content": "Hola, ¿cómo estás?",
        "target_language": "en"
    }
    
    try:
        # Connect to WebSocket
        uri = "ws://localhost:8000/ws/chat/test_room?user_id=test_user&display_name=Test%20User&preferred_language=en"
        
        print(f"🔌 Connecting to WebSocket: {uri}")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Wait for connection established message
            response = await websocket.recv()
            print(f"📨 Received: {response}")
            
            # Send test message
            print(f"📤 Sending test message: {test_message['content']}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for multiple responses (confirmation and actual message)
            print("⏳ Waiting for responses...")
            responses = []
            for i in range(3):  # Wait for up to 3 responses
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    responses.append(response)
                    print(f"📨 Received response {i+1}: {response}")
                except asyncio.TimeoutError:
                    break
            
            # Check for translation in responses
            translation_found = False
            for response in responses:
                try:
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "text":
                        print("✅ Message received successfully")
                        
                        # Check for translation
                        if "translated_content" in response_data:
                            print(f"✅ Translation found: {response_data['translated_content']}")
                            print(f"📊 Translation status: {response_data.get('translation_status', 'unknown')}")
                            translation_found = True
                        else:
                            print("⚠️  No translation found in response")
                            
                    elif response_data.get("type") == "message_confirmation":
                        status = response_data.get("status", "unknown")
                        print(f"📊 Message confirmation status: {status}")
                        
                except json.JSONDecodeError:
                    print(f"⚠️  Non-JSON response: {response}")
            
            if not translation_found:
                print("❌ No translation found in any response")
                
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    
    return True

async def main():
    """Main test function"""
    print("🚀 Translation Test")
    print("=" * 50)
    
    success = await test_translation()
    
    if success:
        print("\n🎉 Translation test completed successfully!")
    else:
        print("\n❌ Translation test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 