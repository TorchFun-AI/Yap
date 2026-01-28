"""
LLM Text Corrector
Uses LLM to correct ASR transcription errors.
Supports OpenAI and Ollama (both via OpenAI-compatible API).
"""

import os
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
        provider: str = None,
        api_key: str = None,
        api_base: str = None,
        model: str = None,
        timeout: int = None,
        temperature: float = None,
        enabled: bool = None,
    ):
        # Load from environment if not provided
        self.provider = provider or os.getenv("LLM_PROVIDER", "ollama")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.api_base = api_base or os.getenv("LLM_API_BASE")
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", "10"))
        self.temperature = temperature or float(os.getenv("LLM_TEMPERATURE", "0.3"))

        # Always enabled
        self.enabled = True

        # Set default model based on provider
        if model:
            self.model = model
        else:
            default_models = {
                "openai": "gpt-4o-mini",
                "ollama": "gpt-4o-mini",
            }
            self.model = os.getenv("LLM_MODEL", default_models.get(self.provider, "gpt-4o-mini"))

        self.client = None
        self.is_initialized = False
        self.executor = ThreadPoolExecutor(max_workers=2)

    def initialize(self) -> None:
        """Initialize the LLM client."""
        if not self.enabled:
            logger.info("LLM correction is disabled")
            return

        if self.is_initialized:
            return

        try:
            if self.provider == "openai":
                self.client = OpenAI(
                    api_key=self.api_key,
                    timeout=self.timeout,
                )
            elif self.provider == "ollama":
                # Ollama uses OpenAI-compatible API
                base_url = self.api_base or "http://localhost:11434/v1"
                self.client = OpenAI(
                    base_url=base_url,
                    api_key="ollama",  # Ollama doesn't require API key
                    timeout=self.timeout,
                )
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            self.is_initialized = True
            logger.info(f"LLM corrector initialized with provider: {self.provider}, model: {self.model}")

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

待校正文本: {text}

只返回校正后的文本，不要其他内容。"""

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

            corrected_text = response.choices[0].message.content.strip()

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

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self.executor.shutdown(wait=False)
