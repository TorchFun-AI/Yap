"""
Text Input Module
Inputs text at the current cursor position using macOS Quartz framework.
Supports Chinese and typewriter effect.
"""

import logging
import time

logger = logging.getLogger(__name__)


class TextInput:
    """Text input engine using macOS Quartz for Unicode support."""

    def __init__(self):
        self.is_initialized = False
        self._cg = None
        self._source = None

    def initialize(self) -> None:
        """Initialize the text input engine."""
        if self.is_initialized:
            return

        try:
            import Quartz
            self._cg = Quartz
            # Create event source
            self._source = Quartz.CGEventSourceCreate(
                Quartz.kCGEventSourceStateHIDSystemState
            )
            self.is_initialized = True
            logger.info("Text input engine initialized with Quartz")
        except ImportError:
            logger.error("pyobjc-framework-Quartz not installed")
            raise

    def _input_char(self, char: str) -> bool:
        """Input a single character using CGEvent."""
        try:
            # Create a keyboard event
            event = self._cg.CGEventCreateKeyboardEvent(self._source, 0, True)

            # Set the Unicode string
            self._cg.CGEventKeyboardSetUnicodeString(
                event, len(char), char
            )

            # Post the event
            self._cg.CGEventPost(self._cg.kCGHIDEventTap, event)

            # Key up event
            event_up = self._cg.CGEventCreateKeyboardEvent(self._source, 0, False)
            self._cg.CGEventPost(self._cg.kCGHIDEventTap, event_up)

            return True
        except Exception as e:
            logger.error(f"Failed to input char '{char}': {e}")
            return False

    def input_text(self, text: str, interval: float = 0) -> bool:
        """
        Input text at the current cursor position with typewriter effect.

        Args:
            text: Text to input (supports Chinese)
            interval: Delay between each character (0 for instant)

        Returns:
            True if successful, False otherwise
        """
        if not text:
            logger.warning("Empty text, skipping input")
            return False

        if not self.is_initialized:
            self.initialize()

        try:
            for char in text:
                if not self._input_char(char):
                    return False
                if interval > 0:
                    time.sleep(interval)

            logger.info(f"Text input successful: '{text}'")
            return True

        except Exception as e:
            logger.error(f"Text input failed: {e}")
            return False

    def input_text_instant(self, text: str) -> bool:
        """Input text instantly without delay."""
        return self.input_text(text, interval=0)

    def input_text_typewriter(self, text: str, interval: float = 0.016) -> bool:
        """Input text with typewriter effect."""
        return self.input_text(text, interval=interval)

    def shutdown(self) -> None:
        """Shutdown the text input engine."""
        self.is_initialized = False
        self._source = None
        self._cg = None
        logger.info("Text input engine shutdown")
