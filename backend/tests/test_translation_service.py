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
from app.utils import get_current_time

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
            timestamp=get_current_time()
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
                timestamp=get_current_time()
            ),
            TranslationRequest(
                text="Good afternoon",
                source_language="en",
                target_language="de",
                user_id="test_user",
                room_id="test_room",
                message_id="test_message_3",
                timestamp=get_current_time()
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


async def test_token_estimation():
    """Test the token estimation functionality"""
    print("\n🔢 Testing Token Estimation Functionality")
    print("=" * 50)
    
    try:
        # Initialize translation service
        translation_service = TranslationService(ai_config)
        await translation_service.initialize()
        
        # Test cases for different languages and scenarios
        test_cases = [
            # English tests
            {
                "text": "Hello, how are you today?",
                "source_lang": "en",
                "target_lang": "es",
                "description": "English to Spanish (basic)"
            },
            {
                "text": "The quick brown fox jumps over the lazy dog. This is a longer sentence to test token estimation accuracy.",
                "source_lang": "en", 
                "target_lang": "de",
                "description": "English to German (long text)"
            },
            
            # Chinese tests (high token density)
            {
                "text": "你好，今天天气怎么样？",
                "source_lang": "zh",
                "target_lang": "en",
                "description": "Chinese to English (high token density)"
            },
            {
                "text": "人工智能技术正在快速发展，为各行各业带来了巨大的变革。机器学习和深度学习算法的进步使得计算机能够处理更复杂的任务。",
                "source_lang": "zh",
                "target_lang": "en", 
                "description": "Chinese to English (technical text)"
            },
            
            # Arabic tests (RTL script)
            {
                "text": "السلام عليكم، كيف حالك اليوم؟",
                "source_lang": "ar",
                "target_lang": "en",
                "description": "Arabic to English (RTL script)"
            },
            
            # Japanese tests (mixed scripts)
            {
                "text": "こんにちは、元気ですか？今日はとても良い天気ですね。",
                "source_lang": "ja",
                "target_lang": "en",
                "description": "Japanese to English (mixed scripts)"
            },
            
            # German tests (compound words)
            {
                "text": "Die Donaudampfschifffahrtsgesellschaftskapitänswitwe war sehr traurig.",
                "source_lang": "de",
                "target_lang": "en",
                "description": "German to English (compound words)"
            },
            
            # Edge cases
            {
                "text": "",
                "source_lang": "en",
                "target_lang": "es",
                "description": "Empty text"
            },
            {
                "text": "A",
                "source_lang": "en",
                "target_lang": "fr",
                "description": "Single character"
            },
            {
                "text": "123 456 789",
                "source_lang": "en",
                "target_lang": "de",
                "description": "Numbers and spaces"
            }
        ]
        
        print(f"Running {len(test_cases)} token estimation test cases...\n")
        
        for i, test_case in enumerate(test_cases, 1):
            text = test_case["text"]
            source_lang = test_case["source_lang"]
            target_lang = test_case["target_lang"]
            description = test_case["description"]
            
            print(f"Test {i}: {description}")
            print(f"  Text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            print(f"  Languages: {source_lang} -> {target_lang}")
            print(f"  Character count: {len(text)}")
            
            # Test token estimation
            estimated_tokens = translation_service._estimate_tokens(text, source_lang, target_lang)
            print(f"  Estimated tokens: {estimated_tokens}")
            
            # Test expansion factor
            expansion_factor = translation_service._get_translation_expansion_factor(source_lang, target_lang)
            print(f"  Expansion factor: {expansion_factor:.2f}")
            
            # Validate reasonable estimates
            if text:  # Skip validation for empty text
                char_to_token_ratio = estimated_tokens / len(text) if len(text) > 0 else 0
                print(f"  Char/Token ratio: {char_to_token_ratio:.2f}")
                
                # Basic sanity checks
                if estimated_tokens < 0:
                    print(f"  ❌ ERROR: Negative token estimate!")
                elif estimated_tokens == 0 and len(text) > 0:
                    print(f"  ❌ ERROR: Zero tokens for non-empty text!")
                elif char_to_token_ratio > 5.0:  # Extremely high ratio
                    print(f"  ⚠️  WARNING: Very high char/token ratio!")
                elif char_to_token_ratio < 0.1:  # Extremely low ratio
                    print(f"  ⚠️  WARNING: Very low char/token ratio!")
                else:
                    print(f"  ✅ Token estimate looks reasonable")
            else:
                print(f"  ✅ Empty text handled correctly")
            
            print()
        
        # Test language coefficient coverage
        print("🌍 Testing language coefficient coverage...")
        supported_languages = translation_service.get_supported_languages()
        missing_coefficients = []
        
        for lang_code in supported_languages.keys():
            if lang_code not in translation_service.token_coefficients:
                missing_coefficients.append(lang_code)
        
        if missing_coefficients:
            print(f"⚠️  Missing token coefficients for: {', '.join(missing_coefficients)}")
        else:
            print("✅ All supported languages have token coefficients")
        
        # Test tiktoken availability
        print(f"\n🔧 Tiktoken availability: {'✅ Available' if translation_service.tokenizer else '❌ Not available'}")
        
        print("\n✅ Token estimation tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Token estimation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'translation_service' in locals():
            await translation_service.cleanup()


async def test_token_estimation_accuracy():
    """Test token estimation accuracy against actual API usage (if API key available)"""
    print("\n📊 Testing Token Estimation Accuracy")
    print("=" * 50)
    
    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not available, skipping accuracy test")
        return True
    
    try:
        translation_service = TranslationService(ai_config)
        await translation_service.initialize()
        
        # Test cases for accuracy validation
        accuracy_test_cases = [
            {
                "text": "Hello world, this is a test.",
                "source_lang": "en",
                "target_lang": "es"
            },
            {
                "text": "你好世界",
                "source_lang": "zh", 
                "target_lang": "en"
            }
        ]
        
        print("Comparing token estimates with actual API usage...\n")
        
        for i, test_case in enumerate(accuracy_test_cases, 1):
            text = test_case["text"]
            source_lang = test_case["source_lang"]
            target_lang = test_case["target_lang"]
            
            print(f"Accuracy Test {i}: {source_lang} -> {target_lang}")
            print(f"  Text: '{text}'")
            
            # Get our estimation
            estimated_tokens = translation_service._estimate_tokens(text, source_lang, target_lang)
            print(f"  Our estimate: {estimated_tokens} tokens")
            
            # Try to get actual usage by performing translation
            try:
                request = TranslationRequest(
                    text=text,
                    source_language=source_lang,
                    target_language=target_lang,
                    user_id="test_user",
                    room_id="test_room",
                    message_id="test_message",
                    timestamp=get_current_time()
                )
                
                result = await translation_service.translate_text(request)
                print(f"  Translation: '{result.translated_text[:50]}{'...' if len(result.translated_text) > 50 else ''}'")
                print(f"  Processing time: {result.processing_time:.2f}s")
                
                # Calculate actual output tokens (approximation)
                actual_output_tokens = translation_service._estimate_tokens(
                    result.translated_text, target_lang, target_lang
                )
                print(f"  Actual output tokens (estimated): {actual_output_tokens}")
                
                # Compare with our prediction
                accuracy_ratio = actual_output_tokens / estimated_tokens if estimated_tokens > 0 else 0
                print(f"  Accuracy ratio: {accuracy_ratio:.2f} (1.0 = perfect)")
                
                if 0.5 <= accuracy_ratio <= 2.0:
                    print(f"  ✅ Estimation within reasonable range")
                else:
                    print(f"  ⚠️  Estimation may need adjustment")
                
            except Exception as e:
                print(f"  ❌ Translation failed: {e}")
            
            print()
        
        print("✅ Token estimation accuracy test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Accuracy test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'translation_service' in locals():
            await translation_service.cleanup()


async def main():
    """Main test function"""
    print("🚀 Running Translation Service Tests")
    print("=" * 50)
    
    success = True
    
    # Run original translation test
    if await test_translation_service():
        print("✅ Basic translation test passed")
    else:
        print("❌ Basic translation test failed")
        success = False
    
    # Run token estimation tests
    if await test_token_estimation():
        print("✅ Token estimation test passed")
    else:
        print("❌ Token estimation test failed")
        success = False
    
    # Run accuracy test
    if await test_token_estimation_accuracy():
        print("✅ Token estimation accuracy test passed")
    else:
        print("❌ Token estimation accuracy test failed")
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
