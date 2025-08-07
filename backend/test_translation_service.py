#!/usr/bin/env python3
"""
Test script for Translation Service

This script tests the translation service functionality to ensure it's working
correctly with the Groq API. It performs basic translation tests and validates
the service configuration.

Usage:
    python test_translation_service.py
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.ai_services.config import ai_config
from app.ai_services.translation_service import TranslationService, TranslationRequest


async def test_translation_service():
    """Test the translation service functionality"""
    print("🧪 Testing Translation Service")
    print("=" * 50)
    
    # Check if GROQ_API_KEY is set
    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY environment variable is not set")
        print("Please set your Groq API key:")
        print("export GROQ_API_KEY=your_api_key_here")
        return False
    
    try:
        # Initialize translation service
        print("📦 Initializing translation service...")
        translation_service = TranslationService(ai_config)
        await translation_service.initialize()
        print("✅ Translation service initialized successfully")
        
        # Test supported languages
        print("\n🌍 Testing supported languages...")
        supported_languages = translation_service.get_supported_languages()
        print(f"✅ Found {len(supported_languages)} supported languages")
        
        # Test language detection
        print("\n🔍 Testing language detection...")
        test_texts = [
            "Hello, how are you?",
            "Hola, ¿cómo estás?",
            "Bonjour, comment allez-vous?",
            "Hallo, wie geht es dir?",
            "Ciao, come stai?"
        ]
        
        for text in test_texts:
            detected_lang = await translation_service.detect_language(text)
            print(f"  '{text[:20]}...' -> {detected_lang}")
        
        # Test translation
        print("\n🔄 Testing translation...")
        test_request = TranslationRequest(
            text="Hello, how are you today?",
            source_language="en",
            target_language="es",
            user_id="test_user",
            room_id="test_room",
            message_id="test_message_1",
            timestamp=datetime.utcnow()
        )
        
        result = await translation_service.translate_text(test_request)
        print(f"✅ Translation successful:")
        print(f"  Original: {result.original_text}")
        print(f"  Translated: {result.translated_text}")
        print(f"  Source: {result.source_language}")
        print(f"  Target: {result.target_language}")
        print(f"  Processing time: {result.processing_time:.2f}s")
        
        # Test batch translation
        print("\n📦 Testing batch translation...")
        batch_requests = [
            TranslationRequest(
                text="Good morning",
                source_language="en",
                target_language="fr",
                user_id="test_user",
                room_id="test_room",
                message_id="test_message_2",
                timestamp=datetime.utcnow()
            ),
            TranslationRequest(
                text="Good afternoon",
                source_language="en",
                target_language="de",
                user_id="test_user",
                room_id="test_room",
                message_id="test_message_3",
                timestamp=datetime.utcnow()
            )
        ]
        
        batch_results = await translation_service.translate_batch(batch_requests)
        print(f"✅ Batch translation completed: {len(batch_results)} results")
        for i, result in enumerate(batch_results):
            print(f"  {i+1}. {result.original_text} -> {result.translated_text}")
        
        # Test service statistics
        print("\n📊 Testing service statistics...")
        stats = translation_service.get_stats()
        print(f"✅ Service statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Test cache functionality
        print("\n💾 Testing cache functionality...")
        cache_stats = translation_service.get_cache_stats()
        print(f"✅ Cache statistics:")
        for key, value in cache_stats.items():
            print(f"  {key}: {value}")
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        await translation_service.cleanup()
        print("✅ Translation service cleaned up successfully")
        
        print("\n🎉 All tests passed! Translation service is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main function to run the translation service test"""
    print("🚀 Starting Translation Service Test")
    print("=" * 50)
    
    success = await test_translation_service()
    
    if success:
        print("\n✅ Translation service test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Translation service test failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
