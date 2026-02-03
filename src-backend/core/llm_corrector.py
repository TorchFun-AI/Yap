"""
LLM Text Corrector
Uses LLM to correct ASR transcription errors.
Supports OpenAI-compatible API.
"""

import os
import re
import logging
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMCorrector:
    """LLM-based text correction engine."""

    def __init__(
        self,
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

        # Always enabled
        self.enabled = True

        # Set default model
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

        self.client = None
        self.is_initialized = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        # Regex pattern for extracting corrected text
        self._corrected_pattern = re.compile(r'<corrected>(.*?)</corrected>', re.DOTALL)

    def _extract_corrected_text(self, response: str, fallback: str) -> str:
        """Extract text from <corrected> tag, fallback to original if not found."""
        match = self._corrected_pattern.search(response)
        if match:
            return match.group(1).strip()
        logger.warning(f"No <corrected> tag found in response: {response}")
        return fallback

    def initialize(self) -> None:
        """Initialize the LLM client."""
        if not self.enabled:
            logger.info("LLM correction is disabled")
            return

        if self.is_initialized:
            return

        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=self.timeout,
            )

            # Warm up the LLM by sending a simple request
            logger.info(f"Warming up LLM with model: {self.model}, base_url: {self.api_base}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0,
                max_tokens=10,
            )
            logger.info(f"LLM warmup response: {response.choices[0].message.content.strip()}")

            self.is_initialized = True
            logger.info(f"LLM corrector initialized with model: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize LLM corrector: {e}")
            self.enabled = False

    def _build_prompt(self, text: str, language: str = "zh") -> str:
        """Build the correction prompt."""
        lang_name = "中文" if language in ["zh", "chinese"] else "English"

        return f"""你是一个语音识别文本校正助手。

任务: 将语音识别文本转换为标准、友好、流畅的书面语。

规则:
1. 修正识别错误（同音字、拼写错误）。
2. 去除无意义的口语词（如"那个"、"呃"、"嗯"）和冗余重复。
3. 去除无意义的数字和符号（如"今天12天气3" -> "今天天气"）。
4. 调整语序，使其符合书面语习惯，逻辑通顺。
5. 添加或调整标点符号，使断句准确自然。
6. 保持原意不变，语气友好自然。
7. 语言: {lang_name}

* 待校正文本: 
```
{text}
```

必须注意：将校正后的文本放在<corrected>标签内返回，例如：<corrected>校正后的文本</corrected>"""

    def correct(self, text: str, language: str = "zh") -> Dict:
        """
        Correct text using LLM.

        Args:
            text: Text to correct
            language: Language code (zh, en, etc.)

        Returns:
            Dict with corrected_text, original_text, is_corrected, and optional error
        """
        if not self.enabled or not text or not text.strip():
            return {
                "corrected_text": text,
                "original_text": text,
                "is_corrected": False,
            }

        if not self.is_initialized:
            self.initialize()

        if not self.is_initialized or not self.client:
            return {
                "corrected_text": text,
                "original_text": text,
                "is_corrected": False,
                "error": "not_initialized",
            }

        try:
            prompt = self._build_prompt(text, language)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=500,
            )

            raw_response = response.choices[0].message.content.strip()

            # Extract text from <corrected> tag
            corrected_text = self._extract_corrected_text(raw_response, text)

            # Validate response
            if not corrected_text:
                logger.warning("LLM returned empty response, using original text")
                return {
                    "corrected_text": text,
                    "original_text": text,
                    "is_corrected": False,
                    "error": "empty_response",
                }

            is_corrected = corrected_text != text

            logger.info(f"LLM correction result: '{text}' -> '{corrected_text}' (corrected: {is_corrected})")

            return {
                "corrected_text": corrected_text,
                "original_text": text,
                "is_corrected": is_corrected,
            }

        except Exception as e:
            logger.error(f"LLM correction failed: {e}")
            return {
                "corrected_text": text,
                "original_text": text,
                "is_corrected": False,
                "error": str(e),
            }

    async def correct_async(self, text: str, language: str = "zh") -> Dict:
        """Async wrapper for correction."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.correct, text, language)

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
