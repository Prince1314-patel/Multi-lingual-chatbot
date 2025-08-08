#!/usr/bin/env python3
"""
Test script to verify translation functionality with two users
"""

import asyncio
import json
import websockets
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_translation_with_two_users():
    """Test translation functionality with two users"""
    print("🧪 Testing Translation with Two Users")
    print("=" * 50)
    
    # Test message in Spanish
    test_message = {
        "type": "text",
        "content": "Hola, ¿cómo estás?",
        "target_language": "en"
    }
    
    try:
        # Connect first user
        uri1 = "ws://localhost:8000/ws/chat/test_room?user_id=user1&display_name=User1&preferred_language=en"
        print(f"🔌 Connecting user1: {uri1}")
        
        async with websockets.connect(uri1) as websocket1:
            print("✅ User1 connected")
            
            # Wait for connection established message
            response1 = await websocket1.recv()
            print(f"📨 User1 received: {response1}")
            
            # Connect second user
            uri2 = "ws://localhost:8000/ws/chat/test_room?user_id=user2&display_name=User2&preferred_language=en"
            print(f"🔌 Connecting user2: {uri2}")
            
            async with websockets.connect(uri2) as websocket2:
                print("✅ User2 connected")
                
                # Wait for connection established message
                response2 = await websocket2.recv()
                print(f"📨 User2 received: {response2}")
                
                # Wait for user join messages
                try:
                    join_msg1 = await asyncio.wait_for(websocket1.recv(), timeout=2.0)
                    print(f"📨 User1 received join: {join_msg1}")
                except asyncio.TimeoutError:
                    print("⚠️  No join message received by user1")
                
                try:
                    join_msg2 = await asyncio.wait_for(websocket2.recv(), timeout=2.0)
                    print(f"📨 User2 received join: {join_msg2}")
                except asyncio.TimeoutError:
                    print("⚠️  No join message received by user2")
                
                # Send test message from user1
                print(f"📤 User1 sending test message: {test_message['content']}")
                await websocket1.send(json.dumps(test_message))
                
                # Wait for responses
                print("⏳ Waiting for responses...")
                responses = []
                
                # Collect responses from both users
                for i in range(5):  # Wait for up to 5 responses
                    try:
                        # Try to get response from user2 (the receiver)
                        response = await asyncio.wait_for(websocket2.recv(), timeout=3.0)
                        responses.append(("user2", response))
                        print(f"📨 User2 received response {i+1}: {response}")
                    except asyncio.TimeoutError:
                        break
                
                # Check for translation in responses
                translation_found = False
                for user, response in responses:
                    try:
                        response_data = json.loads(response)
                        
                        if response_data.get("type") == "text":
                            print(f"✅ Text message received by {user}")
                            
                            # Check for translation
                            if "translated_content" in response_data:
                                print(f"✅ Translation found: {response_data['translated_content']}")
                                print(f"📊 Translation status: {response_data.get('translation_status', 'unknown')}")
                                translation_found = True
                            else:
                                print(f"⚠️  No translation found in {user}'s response")
                                
                        elif response_data.get("type") == "message_confirmation":
                            status = response_data.get("status", "unknown")
                            print(f"📊 Message confirmation status: {status}")
                            
                    except json.JSONDecodeError:
                        print(f"⚠️  Non-JSON response from {user}: {response}")
                
                if not translation_found:
                    print("❌ No translation found in any response")
                    return False
                
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    
    return True

async def main():
    """Main test function"""
    print("🚀 Translation Test with Two Users")
    print("=" * 50)
    
    success = await test_translation_with_two_users()
    
    if success:
        print("\n🎉 Translation test with two users completed!")
    else:
        print("\n❌ Translation test with two users failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 