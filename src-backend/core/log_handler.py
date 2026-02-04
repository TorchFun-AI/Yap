"""
WebSocket Log Handler for real-time log streaming.
"""

import logging
import asyncio
from typing import Set
from datetime import datetime

_log_clients: Set[asyncio.Queue] = set()
_log_buffer: list = []
_buffer_max_size = 100


class WebSocketLogHandler(logging.Handler):
    """Custom logging handler that broadcasts logs to WebSocket clients."""

    def emit(self, record: logging.LogRecord):
        log_entry = {
            "type": "log",
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        _log_buffer.append(log_entry)
        if len(_log_buffer) > _buffer_max_size:
            _log_buffer.pop(0)
        for queue in _log_clients:
            try:
                queue.put_nowait(log_entry)
            except asyncio.QueueFull:
                pass


def register_log_client(queue: asyncio.Queue) -> list:
    """Register a new WebSocket client and return buffered logs."""
    _log_clients.add(queue)
    return list(_log_buffer)


def unregister_log_client(queue: asyncio.Queue):
    """Unregister a WebSocket client."""
    _log_clients.discard(queue)


def setup_websocket_logging():
    """Set up the WebSocket log handler on the root logger."""
    handler = WebSocketLogHandler()
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)
