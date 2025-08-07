#!/usr/bin/env python3
"""
Basic test script for Translation Service Structure

This script tests the translation service structure and configuration
without requiring the Groq API key. It validates the code structure
and configuration setup.

Usage:
    python3 test_translation_service_basic.py
"""

import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test that all modules can be imported correctly"""
    print("🧪 Testing Module Imports")
    print("=" * 50)
    
    try:
        # Test AI services imports
        from app.ai_services.config import ai_config
        print("✅ AI services config imported successfully")
        
        from app.ai_services.base_service import BaseAIService, AIServiceError
        print("✅ Base AI service imported successfully")
        
        from app.ai_services.translation_service import TranslationService, TranslationRequest, TranslationResult
        print("✅ Translation service imported successfully")
        
        # Test models imports
        from app.models import TextMessage, TranslationRequest as ModelTranslationRequest
        print("✅ Message models imported successfully")
        
        # Test services imports
        from app.services.message_handler import MessageHandler
        print("✅ Message handler imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration():
    """Test configuration setup"""
    print("\n⚙️ Testing Configuration")
    print("=" * 50)
    
    try:
        from app.ai_services.config import ai_config
        
        print(f"✅ Configuration loaded successfully")
        print(f"  Translation enabled: {ai_config.translation_enabled}")
        print(f"  Groq model: {ai_config.groq_model}")
        print(f"  Groq timeout: {ai_config.groq_timeout}")
        print(f"  Max retries: {ai_config.groq_max_retries}")
        print(f"  Cache TTL: {ai_config.translation_cache_ttl}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_message_models():
    """Test message models with translation support"""
    print("\n📝 Testing Message Models")
    print("=" * 50)
    
    try:
        from app.models import TextMessage
        
        # Test creating a text message with translation fields
        message = TextMessage(
            user_id="test_user",
            room_id="test_room",
            content="Hello, how are you?",
            lang="en",
            target_language="es",
            translation_status="pending"
        )
        
        print("✅ Text message with translation fields created successfully")
        print(f"  Content: {message.content}")
        print(f"  Language: {message.lang}")
        print(f"  Target language: {message.target_language}")
        print(f"  Translation status: {message.translation_status}")
        
        # Test serialization
        message_dict = message.model_dump()
        print("✅ Message serialization successful")
        print(f"  Serialized keys: {list(message_dict.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Message models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_translation_models():
    """Test translation request and result models"""
    print("\n🔄 Testing Translation Models")
    print("=" * 50)
    
    try:
        from app.ai_services.translation_service import TranslationRequest, TranslationResult
        
        # Test translation request
        request = TranslationRequest(
            text="Hello, how are you?",
            source_language="en",
            target_language="es",
            user_id="test_user",
            room_id="test_room",
            message_id="test_message_1",
            timestamp=datetime.utcnow()
        )
        
        print("✅ Translation request created successfully")
        print(f"  Text: {request.text}")
        print(f"  Source: {request.source_language}")
        print(f"  Target: {request.target_language}")
        
        # Test translation result
        result = TranslationResult(
            original_text="Hello, how are you?",
            translated_text="Hola, ¿cómo estás?",
            source_language="en",
            target_language="es",
            confidence=0.95,
            processing_time=1.5,
            timestamp=datetime.utcnow()
        )
        
        print("✅ Translation result created successfully")
        print(f"  Original: {result.original_text}")
        print(f"  Translated: {result.translated_text}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Processing time: {result.processing_time}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Translation models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_structure():
    """Test service structure without initialization"""
    print("\n🏗️ Testing Service Structure")
    print("=" * 50)
    
    try:
        from app.ai_services.config import ai_config
        from app.ai_services.translation_service import TranslationService
        
        # Test service creation (without initialization)
        service = TranslationService(ai_config)
        
        print("✅ Translation service created successfully")
        print(f"  Service name: {service.service_name}")
        print(f"  Enabled: {service.enabled}")
        print(f"  Supported languages: {len(service.supported_languages)}")
        
        # Test supported languages
        languages = service.get_supported_languages()
        print("✅ Supported languages retrieved successfully")
        print(f"  Total languages: {len(languages)}")
        print(f"  Sample languages: {list(languages.items())[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run all basic tests"""
    print("🚀 Starting Basic Translation Service Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration,
        test_message_models,
        test_translation_models,
        test_service_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("📊 Test Results")
    print("=" * 50)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All basic tests passed! Translation service structure is correct.")
        print("\n📋 Next Steps:")
        print("1. Set your GROQ_API_KEY environment variable:")
        print("   export GROQ_API_KEY=your_api_key_here")
        print("2. Run the full test: python3 test_translation_service.py")
        return True
    else:
        print(f"\n❌ {total - passed} test(s) failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
