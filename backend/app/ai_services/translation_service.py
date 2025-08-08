"""
Translation Service

This module provides text translation capabilities using the Groq API.
It implements the TranslationService class that handles translation requests,
language detection, caching, and error handling for the multilingual chat application.

The service supports multiple languages and provides both synchronous and
asynchronous translation methods with proper error handling and retry logic.
"""

import asyncio
import logging
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import timedelta, datetime
from dataclasses import dataclass

from ..utils import get_current_time

try:
    from groq import AsyncGroq
    from groq.types.chat import ChatCompletion
except ImportError:
    AsyncGroq = None
    ChatCompletion = None

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None
    TIKTOKEN_AVAILABLE = False

from .base_service import BaseAIService, AIServiceError, retry_on_error
from .config import AIServiceConfig

logger = logging.getLogger(__name__)


@dataclass
class TranslationRequest:
    """
    Translation request data structure.
    
    This class represents a translation request with all necessary
    information for processing and tracking the translation.
    
    Attributes:
        text: The text to translate
        source_language: Source language code (auto-detected if None)
        target_language: Target language code
        user_id: ID of the user requesting translation
        room_id: ID of the chat room
        message_id: ID of the original message
        timestamp: When the request was created
    """
    text: str
    source_language: Optional[str]
    target_language: str
    user_id: str
    room_id: str
    message_id: str
    timestamp: Any  # Using Any to avoid circular import issues


@dataclass
class TranslationResult:
    """
    Translation result data structure.
    
    This class represents the result of a translation operation,
    including the translated text, detected language, and metadata.
    
    Attributes:
        original_text: The original text that was translated
        translated_text: The translated text
        source_language: Detected source language
        target_language: Target language
        confidence: Translation confidence score (0.0 to 1.0)
        processing_time: Time taken to process the translation
        timestamp: When the translation was completed
    """
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: float
    processing_time: float
    timestamp: Any  # Using Any to avoid circular import issues


class TranslationService(BaseAIService[TranslationResult]):
    """
    Translation service using Groq API.
    
    This service provides text translation capabilities using the Groq
    Llama-3.3-70B-Versatile model. It supports multiple languages,
    automatic language detection, caching, and batch processing.
    
    The service is designed to be efficient and reliable, with proper
    error handling, retry logic, and performance monitoring.
    
    Attributes:
        client: Groq API client
        cache: Translation cache for repeated requests
        supported_languages: List of supported language codes
        language_names: Mapping of language codes to display names
    """
    
    def __init__(self, config: AIServiceConfig):
        """
        Initialize TranslationService.
        
        Args:
            config: AI service configuration
        """
        super().__init__(config, "TranslationService")
        
        if not AsyncGroq:
            raise ImportError("Groq library not installed. Run: pip install groq")
        
        self.client: Optional[AsyncGroq] = None
        self.cache: Dict[str, Tuple[TranslationResult, datetime]] = {}
        
        # Supported languages with their display names
        self.supported_languages = {
            "en": "English",
            "es": "Spanish", 
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
            "ar": "Arabic",
            "hi": "Hindi",
            "bn": "Bengali",
            "ur": "Urdu",
            "tr": "Turkish",
            "nl": "Dutch",
            "pl": "Polish",
            "sv": "Swedish",
            "da": "Danish",
            "no": "Norwegian",
            "fi": "Finnish",
            "cs": "Czech",
            "sk": "Slovak",
            "hu": "Hungarian",
            "ro": "Romanian",
            "bg": "Bulgarian",
            "hr": "Croatian",
            "sr": "Serbian",
            "sl": "Slovenian",
            "et": "Estonian",
            "lv": "Latvian",
            "lt": "Lithuanian",
            "mt": "Maltese",
            "el": "Greek",
            "he": "Hebrew",
            "th": "Thai",
            "vi": "Vietnamese",
            "id": "Indonesian",
            "ms": "Malay",
            "tl": "Filipino",
            "sw": "Swahili",
            "af": "Afrikaans",
            "is": "Icelandic",
            "ga": "Irish",
            "cy": "Welsh",
            "eu": "Basque",
            "ca": "Catalan",
            "gl": "Galician",
            "mk": "Macedonian",
            "sq": "Albanian",
            "bs": "Bosnian",
            "me": "Montenegrin",
            "ky": "Kyrgyz",
            "kk": "Kazakh",
            "uz": "Uzbek",
            "tg": "Tajik",
            "mn": "Mongolian",
            "ka": "Georgian",
            "hy": "Armenian",
            "az": "Azerbaijani",
            "fa": "Persian",
            "ps": "Pashto",
            "ku": "Kurdish",
            "yi": "Yiddish",
            "am": "Amharic",
            "ti": "Tigrinya",
            "so": "Somali",
            "ha": "Hausa",
            "yo": "Yoruba",
            "ig": "Igbo",
            "zu": "Zulu",
            "xh": "Xhosa",
            "st": "Southern Sotho",
            "tn": "Tswana",
            "ss": "Swati",
            "ve": "Venda",
            "ts": "Tsonga",
            "nr": "Southern Ndebele",
            "nd": "Northern Ndebele"
        }
        
        # Language detection mapping for common language codes
        self.language_detection_map = {
            "zh": ["zh-cn", "zh-tw", "zh-hk", "zh-sg"],
            "pt": ["pt-br", "pt-pt"],
            "es": ["es-es", "es-mx", "es-ar", "es-co", "es-pe", "es-ve", "es-cl", "es-ec", "es-gt", "es-cu", "es-bo", "es-do", "es-hn", "es-py", "es-sv", "es-ni", "es-pr", "es-cr", "es-pa", "es-gq", "es-gy", "es-uy", "es-pa"],
            "en": ["en-us", "en-gb", "en-ca", "en-au", "en-nz", "en-ie", "en-za", "en-jm", "en-bz", "en-tt", "en-zw", "en-ph", "en-in", "en-my", "en-sg"]
        }
        
        # Language-specific token estimation coefficients (tokens per character)
        # Based on empirical analysis of different languages with OpenAI tokenizers
        self.token_coefficients = {
            # Latin-based languages (lower token density)
            "en": 0.25,   # English: ~4 chars per token
            "es": 0.28,   # Spanish: ~3.5 chars per token
            "fr": 0.30,   # French: ~3.3 chars per token
            "de": 0.22,   # German: ~4.5 chars per token (compound words)
            "it": 0.28,   # Italian: ~3.5 chars per token
            "pt": 0.28,   # Portuguese: ~3.5 chars per token
            "nl": 0.24,   # Dutch: ~4.2 chars per token
            "pl": 0.26,   # Polish: ~3.8 chars per token
            "sv": 0.25,   # Swedish: ~4 chars per token
            "da": 0.25,   # Danish: ~4 chars per token
            "no": 0.25,   # Norwegian: ~4 chars per token
            "fi": 0.20,   # Finnish: ~5 chars per token (agglutinative)
            "cs": 0.24,   # Czech: ~4.2 chars per token
            "sk": 0.24,   # Slovak: ~4.2 chars per token
            "hu": 0.18,   # Hungarian: ~5.5 chars per token (highly agglutinative)
            "ro": 0.26,   # Romanian: ~3.8 chars per token
            "bg": 0.22,   # Bulgarian: ~4.5 chars per token
            "hr": 0.24,   # Croatian: ~4.2 chars per token
            "sr": 0.22,   # Serbian: ~4.5 chars per token
            "sl": 0.24,   # Slovenian: ~4.2 chars per token
            "et": 0.20,   # Estonian: ~5 chars per token
            "lv": 0.22,   # Latvian: ~4.5 chars per token
            "lt": 0.20,   # Lithuanian: ~5 chars per token
            "mt": 0.26,   # Maltese: ~3.8 chars per token
            
            # Cyrillic-based languages
            "ru": 0.35,   # Russian: ~2.8 chars per token
            "mk": 0.32,   # Macedonian: ~3.1 chars per token
            "sq": 0.26,   # Albanian: ~3.8 chars per token
            "bs": 0.24,   # Bosnian: ~4.2 chars per token
            "me": 0.22,   # Montenegrin: ~4.5 chars per token
            "ky": 0.30,   # Kyrgyz: ~3.3 chars per token
            "kk": 0.30,   # Kazakh: ~3.3 chars per token
            "uz": 0.28,   # Uzbek: ~3.5 chars per token
            "tg": 0.30,   # Tajik: ~3.3 chars per token
            "mn": 0.28,   # Mongolian: ~3.5 chars per token
            "ka": 0.40,   # Georgian: ~2.5 chars per token
            "hy": 0.35,   # Armenian: ~2.8 chars per token
            "az": 0.28,   # Azerbaijani: ~3.5 chars per token
            
            # Greek
            "el": 0.35,   # Greek: ~2.8 chars per token
            
            # Middle Eastern languages
            "ar": 0.50,   # Arabic: ~2 chars per token
            "he": 0.45,   # Hebrew: ~2.2 chars per token
            "fa": 0.45,   # Persian: ~2.2 chars per token
            "ps": 0.45,   # Pashto: ~2.2 chars per token
            "ku": 0.40,   # Kurdish: ~2.5 chars per token
            "ur": 0.45,   # Urdu: ~2.2 chars per token
            "yi": 0.40,   # Yiddish: ~2.5 chars per token
            
            # East Asian languages (high token density)
            "zh": 1.2,    # Chinese: ~0.8 chars per token (each char often = 1+ tokens)
            "ja": 1.5,    # Japanese: ~0.6 chars per token (mixed scripts)
            "ko": 1.0,    # Korean: ~1 char per token
            
            # South/Southeast Asian languages
            "hi": 0.60,   # Hindi: ~1.6 chars per token
            "bn": 0.65,   # Bengali: ~1.5 chars per token
            "th": 1.0,    # Thai: ~1 char per token (no spaces)
            "vi": 0.40,   # Vietnamese: ~2.5 chars per token
            "id": 0.30,   # Indonesian: ~3.3 chars per token
            "ms": 0.30,   # Malay: ~3.3 chars per token
            "tl": 0.28,   # Filipino: ~3.5 chars per token
            
            # African languages
            "sw": 0.25,   # Swahili: ~4 chars per token
            "af": 0.24,   # Afrikaans: ~4.2 chars per token
            "am": 0.50,   # Amharic: ~2 chars per token
            "ti": 0.50,   # Tigrinya: ~2 chars per token
            "so": 0.30,   # Somali: ~3.3 chars per token
            "ha": 0.28,   # Hausa: ~3.5 chars per token
            "yo": 0.30,   # Yoruba: ~3.3 chars per token
            "ig": 0.28,   # Igbo: ~3.5 chars per token
            "zu": 0.22,   # Zulu: ~4.5 chars per token
            "xh": 0.22,   # Xhosa: ~4.5 chars per token
            
            # Celtic languages
            "ga": 0.20,   # Irish: ~5 chars per token
            "cy": 0.22,   # Welsh: ~4.5 chars per token
            "is": 0.18,   # Icelandic: ~5.5 chars per token
            
            # Other European languages
            "eu": 0.18,   # Basque: ~5.5 chars per token (agglutinative)
            "ca": 0.28,   # Catalan: ~3.5 chars per token
            "gl": 0.28,   # Galician: ~3.5 chars per token
            "tr": 0.22,   # Turkish: ~4.5 chars per token (agglutinative)
        }
        
        # Initialize tiktoken encoder if available
        self.tokenizer = None
        if TIKTOKEN_AVAILABLE:
            try:
                # Use cl100k_base encoding which is compatible with GPT-4 and similar models
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken encoder: {e}")
                self.tokenizer = None
    
    async def initialize(self) -> None:
        """
        Initialize the translation service.
        
        This method sets up the Groq API client and validates the configuration.
        It also performs a health check to ensure the service is ready.
        
        Raises:
            AIServiceError: If initialization fails
        """
        try:
            self._log_operation("initializing")
            
            # Initialize Groq client
            self.client = AsyncGroq(
                api_key=self.config.groq_api_key,
                timeout=self.config.groq_timeout,
                max_retries=self.config.groq_max_retries
            )
            
            if self.config.groq_base_url:
                self.client.base_url = self.config.groq_base_url
            
            # Validate configuration
            if not self.config.groq_api_key:
                raise AIServiceError(
                    self.service_name, "initialization",
                    "GROQ_API_KEY is required"
                )
            
            # Test connection with a simple request
            await self._test_connection()
            
            self.enabled = True
            logger.info(f"{self.service_name} initialized successfully")
            
        except Exception as e:
            self.enabled = False
            error = self._handle_api_error(e, "initialization")
            logger.error(f"Failed to initialize {self.service_name}: {error}")
            raise error
    
    async def cleanup(self) -> None:
        """
        Clean up the translation service.
        
        This method closes the Groq client and clears the cache.
        """
        self._log_operation("cleaning up")
        
        if self.client:
            await self.client.close()
            self.client = None
        
        self.cache.clear()
        self.enabled = False
        
        logger.info(f"{self.service_name} cleaned up")
    
    @retry_on_error(max_retries=3, base_delay=1.0)
    async def translate_text(self, request: TranslationRequest) -> TranslationResult:
        """
        Translate text using Groq API.
        
        This method translates the given text from the source language to the
        target language. It includes caching, language detection, and proper
        error handling.
        
        Args:
            request: Translation request containing text and language information
            
        Returns:
            TranslationResult containing the translated text and metadata
            
        Raises:
            AIServiceError: If translation fails
        """
        if not self.enabled:
            raise AIServiceError(
                self.service_name, "translation",
                "Service is not enabled"
            )
        
        start_time = get_current_time()
        
        try:
            logger.info(f"🔄 TranslationService: Starting translation")
            # Log truncated version to avoid leaking sensitive data
            text_preview = request.text[:50] + "..." if len(request.text) > 50 else request.text
            logger.info(f"📝 Input text (preview): '{text_preview}' (length: {len(request.text)})")
            logger.info(f"🎯 Target language: {request.target_language}")
            logger.info(f"🔍 Source language: {request.source_language or 'auto-detect'}")
            
            self._log_operation("translating", 
                              text_length=len(request.text),
                              target_lang=request.target_language)
            
            # Check cache first
            cache_key = self._generate_cache_key(request)
            if cache_key in self.cache:
                cached_result, cache_time = self.cache[cache_key]
                if get_current_time() - cache_time < timedelta(seconds=self.config.translation_cache_ttl):
                    logger.info(f"✅ Translation cache hit for key: {cache_key}")
                    logger.info(f"🔄 Cached translation: '{cached_result.translated_text}'")
                    return cached_result
            
            # Detect source language if not provided
            source_language = request.source_language
            if not source_language:
                logger.info(f"🔍 Auto-detecting source language...")
                source_language = await self._detect_language(request.text)
                logger.info(f"🔍 Detected source language: {source_language}")
            
            # Perform translation
            logger.info(f"🚀 Calling Groq API for translation...")
            translated_text = await self._call_groq_api(request.text, source_language, request.target_language)
            
            # Calculate processing time
            processing_time = (get_current_time() - start_time).total_seconds()
            
            # Create result
            result = TranslationResult(
                original_text=request.text,
                translated_text=translated_text,
                source_language=source_language,
                target_language=request.target_language,
                confidence=0.95,  # Groq doesn't provide confidence scores
                processing_time=processing_time,
                timestamp=get_current_time()
            )
            
            logger.info(f"✅ Translation completed successfully!")
            logger.info(f"📝 Original: '{result.original_text}' ({result.source_language})")
            logger.info(f"🔄 Translated: '{result.translated_text}' ({result.target_language})")
            logger.info(f"⏱️  Processing time: {result.processing_time:.2f}s")
            
            # Cache the result
            self.cache[cache_key] = (result, get_current_time())
            
            # Update statistics
            self._update_stats(True, processing_time)
            
            logger.info(f"Translation completed in {processing_time:.2f}s: "
                       f"{source_language} -> {request.target_language}")
            
            return result
            
        except Exception as e:
            processing_time = (get_current_time() - start_time).total_seconds()
            self._update_stats(False, processing_time)
            
            logger.error(f"❌ Translation failed after {processing_time:.2f}s")
            # Log truncated version to avoid leaking sensitive data
            text_preview = request.text[:50] + "..." if len(request.text) > 50 else request.text
            logger.error(f"📝 Failed text (preview): '{text_preview}' (length: {len(request.text)})")
            logger.error(f"🎯 Target language: {request.target_language}")
            
            error = self._handle_api_error(e, "translation")
            logger.error(f"Translation failed: {error}")
            raise error
    
    async def translate_batch(self, requests: List[TranslationRequest]) -> List[TranslationResult]:
        """
        Translate multiple texts in batch.
        
        This method processes multiple translation requests efficiently
        using concurrent processing while respecting rate limits.
        
        Args:
            requests: List of translation requests
            
        Returns:
            List of translation results in the same order as requests
            
        Raises:
            AIServiceError: If batch translation fails
        """
        if not self.enabled:
            raise AIServiceError(
                self.service_name, "batch_translation",
                "Service is not enabled"
            )
        
        if not requests:
            return []
        
        self._log_operation("batch_translating", request_count=len(requests))
        
        # Process in batches to respect rate limits
        batch_size = self.config.translation_batch_size
        results = []
        
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [self.translate_text(req) for req in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch translation failed for request {i + j}: {result}")
                    # Create error result
                    error_result = TranslationResult(
                        original_text=batch[j].text,
                        translated_text=f"[Translation Error: {str(result)}]",
                        source_language=batch[j].source_language or "unknown",
                        target_language=batch[j].target_language,
                        confidence=0.0,
                        processing_time=0.0,
                        timestamp=get_current_time()
                    )
                    results.append(error_result)
                else:
                    results.append(result)
            
            # Add delay between batches to respect rate limits
            if i + batch_size < len(requests):
                await asyncio.sleep(0.1)  # 100ms delay
        
        return results
    
    async def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text.
        
        Args:
            text: Text to detect language for
            
        Returns:
            Language code (e.g., 'en', 'es', 'fr')
            
        Raises:
            AIServiceError: If language detection fails
        """
        return await self._detect_language(text)
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get list of supported languages.
        
        Returns:
            Dictionary mapping language codes to display names
        """
        return self.supported_languages.copy()
    
    def is_language_supported(self, language_code: str) -> bool:
        """
        Check if a language is supported.
        
        Args:
            language_code: Language code to check
            
        Returns:
            True if language is supported, False otherwise
        """
        return language_code.lower() in self.supported_languages
    
    def _estimate_tokens(self, text: str, source_lang: str = "en", target_lang: str = "en") -> int:
        """
        Estimate the number of tokens in the given text using multiple approaches.
        
        This method provides accurate token estimation using tiktoken when available,
        falling back to language-specific heuristics for robust estimation across
        different languages and scripts.
        
        Args:
            text: The text to estimate tokens for
            source_lang: Source language code (for context)
            target_lang: Target language code (for translation expansion estimation)
            
        Returns:
            Estimated number of tokens with safety margin
        """
        if not text:
            return 0
        
        # Method 1: Use tiktoken for precise token counting (preferred)
        if self.tokenizer and TIKTOKEN_AVAILABLE:
            try:
                tokens = len(self.tokenizer.encode(text))
                logger.debug(f"Tiktoken estimation: {tokens} tokens for {len(text)} characters")
                
                # Add language-specific expansion factor for translation
                expansion_factor = self._get_translation_expansion_factor(source_lang, target_lang)
                estimated_tokens = int(tokens * expansion_factor)
                
                # Add safety margin (20% minimum, 50 tokens minimum)
                safety_margin = max(int(estimated_tokens * 0.2), 50)
                final_estimate = estimated_tokens + safety_margin
                
                logger.debug(f"Final token estimate with expansion and safety: {final_estimate}")
                return final_estimate
                
            except Exception as e:
                logger.warning(f"Tiktoken estimation failed: {e}, falling back to heuristics")
        
        # Method 2: Language-specific coefficient estimation (fallback)
        char_count = len(text)
        
        # Get coefficient for source language (primary factor)
        source_coefficient = self.token_coefficients.get(source_lang.lower(), 0.3)  # Default ~3.3 chars/token
        
        # Calculate base token estimate
        base_tokens = int(char_count * source_coefficient)
        
        # Add language-specific expansion factor for translation
        expansion_factor = self._get_translation_expansion_factor(source_lang, target_lang)
        estimated_tokens = int(base_tokens * expansion_factor)
        
        # Add safety margin (25% minimum, 100 tokens minimum for fallback method)
        safety_margin = max(int(estimated_tokens * 0.25), 100)
        final_estimate = estimated_tokens + safety_margin
        
        logger.debug(f"Heuristic estimation: {char_count} chars -> {base_tokens} base tokens -> "
                    f"{estimated_tokens} expanded -> {final_estimate} final (lang: {source_lang}->{target_lang})")
        
        return final_estimate
    
    def _get_translation_expansion_factor(self, source_lang: str, target_lang: str) -> float:
        """
        Get expansion factor for translation between language pairs.
        
        Different language pairs have different expansion characteristics:
        - English to German: ~1.3x (German compounds are longer)
        - English to Chinese: ~0.8x (Chinese is more compact)
        - Chinese to English: ~1.5x (English is more verbose)
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Expansion factor (1.0 = no change, >1.0 = expansion, <1.0 = compression)
        """
        source_lang = source_lang.lower()
        target_lang = target_lang.lower()
        
        # Same language - no expansion
        if source_lang == target_lang:
            return 1.0
        
        # Expansion factors based on empirical translation data
        expansion_rules = {
            # From English
            ("en", "de"): 1.25,  # English to German (compound words)
            ("en", "fi"): 1.15,  # English to Finnish (agglutination)
            ("en", "hu"): 1.20,  # English to Hungarian (agglutination)
            ("en", "ar"): 0.95,  # English to Arabic (more compact)
            ("en", "zh"): 0.80,  # English to Chinese (very compact)
            ("en", "ja"): 0.85,  # English to Japanese (compact)
            ("en", "ko"): 0.90,  # English to Korean (somewhat compact)
            
            # To English
            ("de", "en"): 0.85,  # German to English (decomposition)
            ("fi", "en"): 0.90,  # Finnish to English
            ("hu", "en"): 0.85,  # Hungarian to English
            ("ar", "en"): 1.10,  # Arabic to English
            ("zh", "en"): 1.40,  # Chinese to English (expansion)
            ("ja", "en"): 1.35,  # Japanese to English (expansion)
            ("ko", "en"): 1.25,  # Korean to English (expansion)
            
            # Between non-English languages (selected pairs)
            ("zh", "ja"): 1.05,  # Chinese to Japanese
            ("ja", "zh"): 0.95,  # Japanese to Chinese
            ("de", "fr"): 1.05,  # German to French
            ("fr", "de"): 0.95,  # French to German
            ("ar", "fa"): 1.05,  # Arabic to Persian
            ("fa", "ar"): 0.95,  # Persian to Arabic
        }
        
        # Check for specific language pair
        if (source_lang, target_lang) in expansion_rules:
            return expansion_rules[(source_lang, target_lang)]
        
        # Default expansion factors based on language families
        # Asian languages to European languages tend to expand
        asian_langs = {"zh", "ja", "ko", "th", "vi"}
        european_langs = {"en", "es", "fr", "de", "it", "pt", "ru", "pl", "nl"}
        
        if source_lang in asian_langs and target_lang in european_langs:
            return 1.30
        elif source_lang in european_langs and target_lang in asian_langs:
            return 0.85
        
        # Agglutinative languages expansion
        agglutinative_langs = {"fi", "hu", "tr", "eu"}
        if source_lang in agglutinative_langs and target_lang not in agglutinative_langs:
            return 0.90
        elif source_lang not in agglutinative_langs and target_lang in agglutinative_langs:
            return 1.15
        
        # Default: minimal expansion for unknown pairs
        return 1.10
    
    async def _test_connection(self) -> None:
        """
        Test the connection to Groq API.
        
        Raises:
            AIServiceError: If connection test fails
        """
        try:
            # Simple test request
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": "Hello"}],
                model=self.config.groq_model,
                max_tokens=10
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise AIServiceError(
                    self.service_name, "connection_test",
                    "Invalid response from Groq API"
                )
                
        except Exception as e:
            raise self._handle_api_error(e, "connection_test")
    
    async def _call_groq_api(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Call Groq API for translation.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Translated text
            
        Raises:
            AIServiceError: If API call fails
        """
        try:
            # Create translation prompt
            prompt = self._create_translation_prompt(text, source_lang, target_lang)
            
            # Estimate required tokens for translation output
            estimated_tokens = self._estimate_tokens(text, source_lang, target_lang)
            
            response = await self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional translator. Translate the given text accurately while preserving the original meaning, tone, and context. Only return the translated text, nothing else."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                model=self.config.groq_model,
                max_tokens=estimated_tokens,  # Use intelligent token estimation
                temperature=0.1,  # Low temperature for consistent translations
                top_p=0.9
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise AIServiceError(
                    self.service_name, "api_call",
                    "Empty response from Groq API"
                )
            
            translated_text = response.choices[0].message.content.strip()
            
            # Validate translation
            if not translated_text:
                raise AIServiceError(
                    self.service_name, "api_call",
                    "Empty translation result"
                )
            
            # Only flag as invalid if translation is identical AND languages are different
            # This allows for valid cases like same source/target language or proper nouns
            if translated_text == text and source_lang != target_lang:
                # Additional check: if text is very short (likely a proper noun), allow it
                if len(text.strip()) > 3:  # Only flag longer identical texts as potentially invalid
                    logger.warning(f"Translation unchanged for different languages: {source_lang} -> {target_lang}")
            
            return translated_text
            
        except Exception as e:
            raise self._handle_api_error(e, "api_call")
    
    async def _detect_language(self, text: str) -> str:
        """
        Detect the language of the given text.
        
        Args:
            text: Text to detect language for
            
        Returns:
            Language code
            
        Raises:
            AIServiceError: If language detection fails
        """
        try:
            prompt = f"Detect the language of this text and respond with only the ISO 639-1 language code (e.g., 'en', 'es', 'fr'):\n\n{text}"
            
            response = await self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a language detection expert. Respond with only the ISO 639-1 language code."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.config.groq_model,
                max_tokens=10,
                temperature=0.0
            )
            
            if not response.choices or not response.choices[0].message.content:
                raise AIServiceError(
                    self.service_name, "language_detection",
                    "Empty response from language detection"
                )
            
            detected_lang = response.choices[0].message.content.strip().lower()
            
            # Validate detected language
            if detected_lang not in self.supported_languages:
                # Try to map to supported language
                for lang_code, variants in self.language_detection_map.items():
                    if detected_lang in variants:
                        detected_lang = lang_code
                        break
                else:
                    # Default to English if unknown
                    detected_lang = "en"
            
            return detected_lang
            
        except Exception as e:
            raise self._handle_api_error(e, "language_detection")
    
    def _create_translation_prompt(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Create translation prompt for Groq API.
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            Formatted translation prompt
        """
        source_name = self.supported_languages.get(source_lang, source_lang)
        target_name = self.supported_languages.get(target_lang, target_lang)
        
        return f"""Translate the following text from {source_name} to {target_name}:

Text: {text}

Translation:"""
    
    def _generate_cache_key(self, request: TranslationRequest) -> str:
        """
        Generate cache key for translation request.
        
        Args:
            request: Translation request
            
        Returns:
            Cache key string
        """
        # Create a hash of the request parameters
        cache_data = {
            "text": request.text,
            "source_lang": request.source_language,
            "target_lang": request.target_language
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    def clear_cache(self) -> None:
        """Clear the translation cache."""
        self.cache.clear()
        logger.info("Translation cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        return {
            "cache_size": len(self.cache),
            "cache_entries": list(self.cache.keys()),
            "oldest_entry": min((time for _, time in self.cache.values()), default=None),
            "newest_entry": max((time for _, time in self.cache.values()), default=None)
        }
