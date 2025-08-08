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
            
            # Wait for responses with deadline-driven approach
            print("⏳ Waiting for responses with 15-second deadline...")
            responses = []
            translation_found = False
            deadline = asyncio.get_event_loop().time() + 15.0  # 15-second overall deadline
            
            while asyncio.get_event_loop().time() < deadline and not translation_found:
                try:
                    # Calculate remaining time for this iteration
                    remaining_time = deadline - asyncio.get_event_loop().time()
                    if remaining_time <= 0:
                        break
                    
                    response = await asyncio.wait_for(websocket.recv(), timeout=remaining_time)
                    responses.append(response)
                    print(f"📨 Received response: {response}")
                    
                    # Check for translation in this response
                    try:
                        response_data = json.loads(response)
                        
                        if response_data.get("type") == "text":
                            print("✅ Message received successfully")
                            
                            # Check for translation
                            if "translated_content" in response_data:
                                print(f"✅ Translation found: {response_data['translated_content']}")
                                print(f"📊 Translation status: {response_data.get('translation_status', 'unknown')}")
                                translation_found = True
                                break  # Exit loop once translation is found
                            else:
                                print("⚠️  No translation found in this response, continuing...")
                                
                        elif response_data.get("type") == "message_confirmation":
                            status = response_data.get("status", "unknown")
                            print(f"📊 Message confirmation status: {status}")
                            
                    except json.JSONDecodeError:
                        print(f"⚠️  Non-JSON response: {response}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for next response")
                    break
            
            # Assert that translation was found
            assert translation_found, f"❌ No translation found within deadline. Received {len(responses)} responses but none contained translation."
                
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