from config  import settings
from typing import List
import textwrap
from typing import List
import logging
import asyncio
import time
import google.generativeai as genai
from config import settings

logger = logging.getLogger(__name__)

class TranslationError(Exception):
    pass

class TextTranslator:
    def __init__(self):
        self.client = self._initialize_client()
        self.total_api_calls = 0
        self.total_api_time = 0
        self.last_call_time = 0

    def _initialize_client(self):
        """Initialize the Gemini client with configuration"""
        try:
            genai.configure(api_key=settings.gemini_api_key)
            # Optimize client for concurrent requests
            model = genai.GenerativeModel('gemini-1.5-flash')
            print(f"🔧 Gemini client initialized for concurrent translation")
            return model
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise TranslationError("Translation service unavailable")

    def chunk_text(self, text: str, max_chars: int = 1000) -> List[str]:
        """
        Splits text into chunks, respecting word boundaries.
        """
        return textwrap.wrap(text, max_chars, break_long_words=False, replace_whitespace=False)

    async def translate_chunk(self, chunk: str, source_lang: str, target_lang: str, chunk_index: int = 0) -> str:
        """
        Translate a single text chunk with retry logic and error handling
        """
        chunk_start_time = time.time()
        
        # Track rate limiting
        if self.last_call_time > 0:
            time_since_last = chunk_start_time - self.last_call_time
            print(f"  ⏳ Time since last API call: {time_since_last:.3f}s")
        
        try:
            prompt = (
                f"Translate the following text from {source_lang} to {target_lang}.\n\n"
                f"Instructions:\n"
                f"- Only provide the translation of the content — no extra comments or explanations.\n"
                f"- Do NOT translate or modify tags such as <Title>, <List-item>, <Table>, etc.\n"
                f"- Do NOT translate or change tokens like <TOKEN_1>, <TOKEN_2>, etc. — keep them as-is.\n\n"
                f"Text to translate:\n{chunk}"
            )
            
            api_call_start = time.time()
            response = await self.client.generate_content_async(prompt)
            api_call_time = time.time() - api_call_start
            
            # Update tracking
            self.total_api_calls += 1
            self.total_api_time += api_call_time
            self.last_call_time = time.time()
            
            text = response.text.strip() if hasattr(response, 'text') else None

            if not text:
                raise TranslationError("Empty response from translation service")
            
            total_time = time.time() - chunk_start_time
            print(f"  📊 Chunk {chunk_index + 1}: API call {api_call_time:.3f}s, Total {total_time:.3f}s, Length: {len(chunk)} → {len(text)}")
                
            return text
            
        except Exception as e:
            chunk_time = time.time() - chunk_start_time
            logger.error(f"Translation failed for chunk {chunk_index + 1} after {chunk_time:.3f}s: {str(e)}")
            print(f"  ❌ Chunk {chunk_index + 1} failed after {chunk_time:.3f}s: {str(e)}")
            raise TranslationError(f"Failed to translate chunk: {str(e)}")

    async def translate_text(self, chunks: List[str], source_lang: str, target_lang: str) -> str:
        """
        Translates text chunk-by-chunk asynchronously.
        """
        if not chunks:
            return ""

        translation_start = time.time()
        print(f"  🌍 Starting translation of {len(chunks)} chunks from {source_lang} to {target_lang}")
        
        try:
            # Launch translations concurrently
            tasks = [
                self.translate_chunk(chunk, source_lang, target_lang, i)
                for i, chunk in enumerate(chunks)
            ]
            
            concurrent_start = time.time()
            translated_chunks = await asyncio.gather(*tasks, return_exceptions=True)
            concurrent_time = time.time() - concurrent_start
            
            print(f"  ⚡ Concurrent translation completed in {concurrent_time:.3f}s")            # Handle any failed chunks
            results = []
            failed_count = 0
            for i, result in enumerate(translated_chunks):
                if isinstance(result, Exception):
                    failed_count += 1
                    logger.error(f"Failed to translate chunk {i}: {str(result)}")
                    results.append(chunks[i])  # Keep original text on failure
                else:
                    results.append(result)
            
            if failed_count > 0:
                print(f"  ⚠️  {failed_count} chunks failed translation, kept original text")
            
            total_time = time.time() - translation_start
            total_chars_in = sum(len(chunk) for chunk in chunks)
            total_chars_out = sum(len(result) for result in results)
            print(f"  📊 Translation Summary:")
            print(f"     Total time: {total_time:.3f}s")
            print(f"     Avg per chunk: {total_time/len(chunks):.3f}s")
            print(f"     Characters: {total_chars_in} → {total_chars_out}")
            print(f"     Speed: {total_chars_in/total_time:.0f} chars/sec")
            print(f"     API Stats: {self.total_api_calls} calls, avg {self.total_api_time/self.total_api_calls:.3f}s per call")
            print(f"     Concurrency efficiency: {(self.total_api_time/total_time)*100:.1f}% API time vs total time")
            
            return "\n".join(results)
            
        except Exception as e:
            total_time = time.time() - translation_start
            logger.error(f"Translation failed after {total_time:.3f}s: {str(e)}")
            print(f"  ❌ Translation failed after {total_time:.3f}s: {str(e)}")
            raise TranslationError(f"Text translation failed: {str(e)}")

