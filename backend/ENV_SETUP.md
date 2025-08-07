# Environment Setup Guide

This guide will help you set up the environment variables needed for the translation service to work properly.

## 🚀 Quick Setup

### 1. Get a Groq API Key

1. Go to [Groq Console](https://console.groq.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the API key (it starts with `gsk_`)

### 2. Create Environment File

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your Groq API key:
   ```bash
   # Replace with your actual API key
   GROQ_API_KEY=gsk_your_actual_api_key_here
   ```

### 3. Test Your Configuration

Run the test script to verify everything is set up correctly:

```bash
python test_env_config.py
```

You should see output like:
```
🚀 Environment and Configuration Test
============================================================
🔧 Testing Environment Configuration
==================================================
✅ GROQ_API_KEY is set: gsk_123456...
✅ TRANSLATION_ENABLED: true
✅ GROQ_MODEL: llama3-70b-8192

🤖 Testing AI Service Configuration
==================================================
✅ AI Config loaded successfully
   Groq API Key available: True
   Translation enabled: True
   Groq model: llama3-70b-8192
   Groq timeout: 30.0s
   Groq max retries: 3

🌐 Testing Translation Service
==================================================
✅ Translation service created successfully
✅ Translation service is enabled

============================================================
🎉 All tests passed! Your translation service should work correctly.
```

## 🔧 Configuration Options

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GROQ_API_KEY` | Your Groq API key (required for translation) | `gsk_1234567890abcdef...` |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `GROQ_MODEL` | Groq model to use for translation | `llama3-70b-8192` | `llama3-70b-8192` |
| `GROQ_TIMEOUT` | API request timeout in seconds | `30.0` | `60.0` |
| `GROQ_MAX_RETRIES` | Maximum retry attempts | `3` | `5` |
| `TRANSLATION_ENABLED` | Enable/disable translation service | `true` | `false` |
| `TRANSLATION_CACHE_TTL` | Cache duration in seconds | `3600` | `1800` |

## 🐛 Troubleshooting

### Common Issues

1. **"GROQ_API_KEY is not set"**
   - Make sure you created a `.env` file in the backend directory
   - Verify the API key is correctly copied from Groq console
   - Check that there are no extra spaces or quotes around the key

2. **"Translation service is disabled"**
   - Check that `TRANSLATION_ENABLED=true` in your `.env` file
   - Verify the API key is valid and has sufficient credits

3. **"Failed to initialize translation service"**
   - Check your internet connection
   - Verify the Groq API key is valid
   - Check Groq service status at https://status.groq.com/

### Testing Translation

Once configured, you can test translation by:

1. Starting the backend server:
   ```bash
   python main.py
   ```

2. Opening the frontend and sending messages in different languages

3. Checking the backend logs for translation activity

## 📝 Security Notes

- **Never commit your `.env` file** - it contains sensitive API keys
- The `.env` file is already in `.gitignore` to prevent accidental commits
- Use different API keys for development and production
- Monitor your Groq API usage to avoid unexpected charges

## 🔄 Updating Configuration

If you need to change configuration:

1. Edit the `.env` file
2. Restart the backend server
3. Run `python test_env_config.py` to verify changes

## 📞 Support

If you're still having issues:

1. Check the test script output for specific error messages
2. Verify your Groq API key is active and has credits
3. Check the backend logs for detailed error information
