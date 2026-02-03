"""
History Store
Stores transcription history for context-aware correction.
Uses SQLite for persistence and in-memory cache for fast access.
"""

import sqlite3
import logging
import time
import platform
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HistoryRecord:
    """A single transcription history record."""
    id: int
    text: str
    original: Optional[str]
    timestamp: float
    duration: Optional[float]
    language: str


class HistoryStore:
    """
    Transcription history storage with SQLite persistence and memory cache.

    Features:
    - SQLite for persistent storage across sessions
    - In-memory cache for fast recent record access
    - Automatic cleanup of old records
    """

    def __init__(self, max_history: int = 500):
        """
        Initialize the history store.

        Args:
            max_history: Maximum number of records to keep
        """
        self.max_history = max_history
        self._db_path = self._get_db_path()
        self._conn: Optional[sqlite3.Connection] = None
        self._cache: List[HistoryRecord] = []
        self._is_initialized = False

    def _get_db_path(self) -> Path:
        """Get the database file path based on platform."""
        system = platform.system()

        if system == "Darwin":  # macOS
            base = Path.home() / "Library" / "Application Support" / "Vocistant"
        elif system == "Windows":
            base = Path.home() / "AppData" / "Roaming" / "Vocistant"
        else:  # Linux and others
            base = Path.home() / ".local" / "share" / "Vocistant"

        base.mkdir(parents=True, exist_ok=True)
        return base / "history.db"

    def initialize(self) -> None:
        """Initialize the database and load cache."""
        if self._is_initialized:
            return

        try:
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._create_tables()
            self._load_cache()
            self._is_initialized = True
            logger.info(f"History store initialized at {self._db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize history store: {e}")
            raise

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcription_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                original TEXT,
                timestamp REAL NOT NULL,
                duration REAL,
                language TEXT DEFAULT 'zh'
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON transcription_history(timestamp DESC)
        """)
        self._conn.commit()

    def _load_cache(self) -> None:
        """Load recent records into memory cache."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT id, text, original, timestamp, duration, language
            FROM transcription_history
            ORDER BY timestamp DESC
            LIMIT ?
        """, (self.max_history,))

        self._cache = [
            HistoryRecord(
                id=row[0],
                text=row[1],
                original=row[2],
                timestamp=row[3],
                duration=row[4],
                language=row[5]
            )
            for row in cursor.fetchall()
        ]

    def add(
        self,
        text: str,
        original: Optional[str] = None,
        duration: Optional[float] = None,
        language: str = "zh"
    ) -> None:
        """
        Add a new transcription record.

        Args:
            text: The corrected/final text
            original: The original ASR text (before correction)
            duration: Audio duration in seconds
            language: Language code
        """
        if not self._is_initialized:
            self.initialize()

        if not text or not text.strip():
            return

        timestamp = time.time()

        try:
            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT INTO transcription_history (text, original, timestamp, duration, language)
                VALUES (?, ?, ?, ?, ?)
            """, (text, original, timestamp, duration, language))
            self._conn.commit()

            record_id = cursor.lastrowid

            # Update cache
            record = HistoryRecord(
                id=record_id,
                text=text,
                original=original,
                timestamp=timestamp,
                duration=duration,
                language=language
            )
            self._cache.insert(0, record)

            # Trim cache if needed
            if len(self._cache) > self.max_history:
                self._cache = self._cache[:self.max_history]

            # Cleanup old records periodically
            if len(self._cache) >= self.max_history:
                self._cleanup_old_records()

            logger.debug(f"Added history record: {text[:50]}...")

        except Exception as e:
            logger.error(f"Failed to add history record: {e}")

    def get_recent(self, limit: int = 3) -> List[str]:
        """
        Get the most recent transcription texts.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent transcription texts (most recent first)
        """
        if not self._is_initialized:
            self.initialize()

        return [record.text for record in self._cache[:limit]]

    def get_recent_records(self, limit: int = 3) -> List[HistoryRecord]:
        """
        Get the most recent transcription records with full details.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of HistoryRecord objects (most recent first)
        """
        if not self._is_initialized:
            self.initialize()

        return self._cache[:limit]

    def clear(self) -> None:
        """Clear all history records."""
        if not self._is_initialized:
            return

        try:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM transcription_history")
            self._conn.commit()
            self._cache.clear()
            logger.info("History cleared")
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")

    def _cleanup_old_records(self) -> None:
        """Remove records beyond max_history limit."""
        try:
            cursor = self._conn.cursor()
            cursor.execute("""
                DELETE FROM transcription_history
                WHERE id NOT IN (
                    SELECT id FROM transcription_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                )
            """, (self.max_history,))
            self._conn.commit()
            deleted = cursor.rowcount
            if deleted > 0:
                logger.debug(f"Cleaned up {deleted} old history records")
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            try:
                self._conn.close()
                self._conn = None
                self._is_initialized = False
                logger.info("History store closed")
            except Exception as e:
                logger.error(f"Failed to close history store: {e}")

    @property
    def count(self) -> int:
        """Get the number of records in cache."""
        return len(self._cache)
