"""
Configuration Management
Centralized configuration for all pipeline components.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
# Structure: project_root/.env
# This file: project_root/src-backend/core/config.py
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"
load_dotenv(env_path)


class Config:
    """Centralized configuration management."""

    def __init__(self):
        # LLM Configuration
        # Provider: openai or ollama (both use OpenAI-compatible API)
        self.llm_enabled = True  # Always enabled
        self.llm_provider = os.getenv("LLM_PROVIDER", "ollama")
        self.llm_api_key = os.getenv("LLM_API_KEY")
        self.llm_api_base = os.getenv("LLM_API_BASE")
        self.llm_model = os.getenv("LLM_MODEL", self._get_default_model())
        self.llm_timeout = int(os.getenv("LLM_TIMEOUT", "10"))
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.3"))
        self.llm_max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))

        # Validate configuration
        self._validate()

    def _get_default_model(self) -> str:
        """Get default model based on provider."""
        defaults = {
            "openai": "gpt-4o-mini",
            "ollama": "gpt-4o-mini",
        }
        return defaults.get(self.llm_provider, "gpt-4o-mini")

    def _validate(self):
        """Validate configuration."""
        # Validate provider (openai and ollama both use OpenAI-compatible API)
        if self.llm_provider not in ["openai", "ollama"]:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")

        # Validate timeout
        if self.llm_timeout <= 0:
            raise ValueError("LLM_TIMEOUT must be positive")

        # Validate temperature
        if not 0 <= self.llm_temperature <= 2:
            raise ValueError("LLM_TEMPERATURE must be between 0 and 2")
