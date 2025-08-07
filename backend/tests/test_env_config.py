#!/usr/bin/env python3
"""
Test script to verify environment configuration and translation service setup.
Run this script to check if your .env file is properly configured.
"""

import os
import sys
from dotenv import load_dotenv

def test_env_loading():
    """Test if environment variables are loaded correctly"""
    print("🔧 Testing Environment Configuration")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check if GROQ_API_KEY is set
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        print(f"✅ GROQ_API_KEY is set: {groq_api_key[:10]}...")
    else:
        print("❌ GROQ_API_KEY is not set")
        print("   Please create a .env file with your Groq API key")
        return False
    
    # Check other important variables
    translation_enabled = os.getenv("TRANSLATION_ENABLED", "true").lower() == "true"
    print(f"✅ TRANSLATION_ENABLED: {translation_enabled}")
    
    groq_model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    print(f"✅ GROQ_MODEL: {groq_model}")
    
    return True

def test_ai_config():
    """Test AI service configuration"""
    print("\n🤖 Testing AI Service Configuration")
    print("=" * 50)
    
    try:
        from app.ai_services.config import ai_config
        
        print(f"✅ AI Config loaded successfully")
        print(f"   Groq API Key available: {bool(ai_config.groq_api_key)}")
        print(f"   Translation enabled: {ai_config.translation_enabled}")
        print(f"   Groq model: {ai_config.groq_model}")
        print(f"   Groq timeout: {ai_config.groq_timeout}s")
        print(f"   Groq max retries: {ai_config.groq_max_retries}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to load AI config: {e}")
        return False

def test_translation_service():
    """Test translation service initialization"""
    print("\n🌐 Testing Translation Service")
    print("=" * 50)
    
    try:
        from app.ai_services.translation_service import TranslationService
        from app.ai_services.config import ai_config
        
        # Try to initialize translation service
        service = TranslationService(ai_config)
        print(f"✅ Translation service created successfully")
        
        # Check if service is enabled
        if service.enabled:
            print(f"✅ Translation service is enabled")
        else:
            print(f"⚠️  Translation service is disabled")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize translation service: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Environment and Configuration Test")
    print("=" * 60)
    
    # Test environment loading
    env_ok = test_env_loading()
    
    if not env_ok:
        print("\n❌ Environment test failed. Please fix the issues above.")
        print("\n📝 To fix this:")
        print("1. Copy .env.example to .env")
        print("2. Add your Groq API key to the .env file")
        print("3. Run this test again")
        return
    
    # Test AI configuration
    config_ok = test_ai_config()
    
    # Test translation service
    service_ok = test_translation_service()
    
    print("\n" + "=" * 60)
    if env_ok and config_ok and service_ok:
        print("🎉 All tests passed! Your translation service should work correctly.")
        print("\n💡 Next steps:")
        print("1. Start your backend server")
        print("2. Test translation in your chat application")
    else:
        print("❌ Some tests failed. Please check the issues above.")
        print("\n🔧 Common fixes:")
        print("1. Make sure you have a valid Groq API key")
        print("2. Check that your .env file is in the backend directory")
        print("3. Verify the .env file format is correct")

if __name__ == "__main__":
    main()
