"""
Text Input Module
Inputs text at the current cursor position using macOS Quartz framework.
Supports Chinese and typewriter effect.
"""

import logging
import time

import Quartz

logger = logging.getLogger(__name__)


class TextInput:
    """Text input engine using macOS Quartz for Unicode support."""

    def __init__(self):
        self.is_initialized = False
        self._source = None

    def initialize(self) -> None:
        """Initialize the text input engine."""
        if self.is_initialized:
            return

        # Create event source
        self._source = Quartz.CGEventSourceCreate(
            Quartz.kCGEventSourceStateHIDSystemState
        )

        # Check if event source creation succeeded
        if self._source is None:
            logger.error(
                "[TEXT_INPUT] CGEventSourceCreate returned None - "
                "Accessibility permission likely denied"
            )
            raise PermissionError(
                "Failed to create event source. "
                "Accessibility permission may be denied."
            )

        logger.info(f"[TEXT_INPUT] Event source created: {self._source}")
        self.is_initialized = True
        logger.info("[TEXT_INPUT] Text input engine initialized with Quartz")

    def _input_char(self, char: str) -> bool:
        """Input a single character using CGEvent."""
        try:
            # Check if source is valid
            if self._source is None:
                logger.error("[TEXT_INPUT] Event source is None, cannot input char")
                return False

            # Create a keyboard event (key down)
            event = Quartz.CGEventCreateKeyboardEvent(self._source, 0, True)
            if event is None:
                logger.error(
                    f"[TEXT_INPUT] CGEventCreateKeyboardEvent (key down) "
                    f"returned None for '{char}'"
                )
                return False

            # Set the Unicode string
            Quartz.CGEventKeyboardSetUnicodeString(event, len(char), char)

            # Post the key down event
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

            # Key up event
            event_up = Quartz.CGEventCreateKeyboardEvent(self._source, 0, False)
            if event_up is None:
                logger.error(
                    f"[TEXT_INPUT] CGEventCreateKeyboardEvent (key up) "
                    f"returned None for '{char}'"
                )
                return False

            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)

            logger.debug(f"[TEXT_INPUT] Posted event for char '{char}'")
            return True
        except Exception as e:
            logger.error(f"[TEXT_INPUT] Failed to input char '{char}': {e}")
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
            logger.warning("[TEXT_INPUT] Empty text, skipping input")
            return False

        if not self.is_initialized:
            self.initialize()

        logger.info(f"[TEXT_INPUT] Starting input of {len(text)} characters")

        try:
            for i, char in enumerate(text):
                if not self._input_char(char):
                    logger.error(
                        f"[TEXT_INPUT] Input failed at position {i}, char '{char}'"
                    )
                    return False
                if interval > 0:
                    time.sleep(interval)

            logger.info(f"[TEXT_INPUT] Input completed successfully: '{text}'")
            return True

        except Exception as e:
            logger.error(f"[TEXT_INPUT] Text input failed with exception: {e}")
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
        logger.info("[TEXT_INPUT] Text input engine shutdown")
