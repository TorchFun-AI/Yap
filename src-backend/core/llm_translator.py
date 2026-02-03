"""
LLM Text Translator
Uses LLM to translate text to target language.
Supports OpenAI-compatible API.
"""

import os
import re
import logging
from typing import Dict
from concurrent.futures import ThreadPoolExecutor
import asyncio
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMTranslator:
    """LLM-based text translation engine."""

    def __init__(
        self,
        provider: str = None,
        api_key: str = None,
        api_base: str = None,
        model: str = None,
        timeout: int = None,
        temperature: float = None,
    ):
        # Load from environment if not provided
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.api_base = api_base or os.getenv("LLM_API_BASE", "http://localhost:11434/v1")
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", "10"))
        self.temperature = temperature or float(os.getenv("LLM_TEMPERATURE", "0.3"))

        # Set default model
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

        self.client = None
        self.is_initialized = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        # Regex pattern for extracting translated text
        self._translated_pattern = re.compile(r'<translated>(.*?)</translated>', re.DOTALL)

    def _extract_translated_text(self, response: str, fallback: str) -> str:
        """Extract text from <translated> tag, fallback to original if not found."""
        match = self._translated_pattern.search(response)
        if match:
            return match.group(1).strip()
        logger.warning(f"No <translated> tag found in response: {response}")
        return fallback

    def initialize(self) -> None:
        """Initialize the LLM client."""
        if self.is_initialized:
            return

        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=self.timeout,
            )

            self.is_initialized = True
            logger.info(f"LLM translator initialized with model: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize LLM translator: {e}")

    def _build_prompt(self, text: str, target_language: str) -> str:
        """Build the translation prompt."""
        return f"""你是一个专业的翻译助手。

任务: 将以下文本翻译成{target_language}。

规则:
1. 保持原文的语气和风格。
2. 翻译要自然流畅，符合目标语言的表达习惯。
3. 专有名词可以保留原文或使用通用译法。
4. 不要添加任何解释或注释，只输出翻译结果。

* 待翻译文本: 
```
{text}
```

必须注意：将翻译后的文本放在<translated>标签内返回，例如：<translated>翻译后的文本</translated>"""

    def translate(self, text: str, target_language: str) -> Dict:
        """
        Translate text using LLM.

        Args:
            text: Text to translate
            target_language: Target language name (e.g., "English", "日本語")

        Returns:
            Dict with translated_text, original_text, and optional error
        """
        if not text or not text.strip() or not target_language:
            return {
                "translated_text": text,
                "original_text": text,
                "is_translated": False,
            }

        if not self.is_initialized:
            self.initialize()

        if not self.is_initialized or not self.client:
            return {
                "translated_text": text,
                "original_text": text,
                "is_translated": False,
                "error": "not_initialized",
            }

        try:
            prompt = self._build_prompt(text, target_language)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=500,
            )

            raw_response = response.choices[0].message.content.strip()

            # Extract text from <translated> tag
            translated_text = self._extract_translated_text(raw_response, text)

            # Validate response
            if not translated_text:
                logger.warning("LLM returned empty response, using original text")
                return {
                    "translated_text": text,
                    "original_text": text,
                    "is_translated": False,
                    "error": "empty_response",
                }

            logger.info(f"LLM translation result: '{text}' -> '{translated_text}'")

            return {
                "translated_text": translated_text,
                "original_text": text,
                "is_translated": True,
            }

        except Exception as e:
            logger.error(f"LLM translation failed: {e}")
            return {
                "translated_text": text,
                "original_text": text,
                "is_translated": False,
                "error": str(e),
            }

    async def translate_async(self, text: str, target_language: str) -> Dict:
        """Async wrapper for translation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self.translate, text, target_language
        )

    def reconfigure(self, **kwargs) -> None:
        """动态重新配置 LLM 客户端"""
        if 'api_key' in kwargs:
            self.api_key = kwargs['api_key'] or None
        if 'api_base' in kwargs:
            self.api_base = kwargs['api_base'] or "http://localhost:11434/v1"
        if 'model' in kwargs and kwargs['model']:
            self.model = kwargs['model']
        if 'timeout' in kwargs and kwargs['timeout']:
            self.timeout = int(kwargs['timeout'])
        if 'temperature' in kwargs and kwargs['temperature'] is not None:
            self.temperature = float(kwargs['temperature'])

        self.is_initialized = False
        self.client = None

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self.executor.shutdown(wait=False)
