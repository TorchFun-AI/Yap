"""
WebSocket Log Handler for real-time log streaming.
"""

import logging
import threading
from typing import Dict, List
from datetime import datetime
from collections import deque

# 全局历史缓冲区（用于新连接时发送历史日志）
_log_history: deque = deque(maxlen=100)
_log_history_lock = threading.Lock()

# 客户端缓冲区（每个客户端独立的待发送队列）
_client_buffers: Dict[int, deque] = {}
_client_buffers_lock = threading.Lock()
_client_id_counter = 0

# 每个客户端的缓冲区最大大小
_client_buffer_max_size = 500


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

        # 添加到全局历史缓冲区
        with _log_history_lock:
            _log_history.append(log_entry)

        # 添加到每个客户端的缓冲区
        with _client_buffers_lock:
            for client_id, buffer in _client_buffers.items():
                if len(buffer) < _client_buffer_max_size:
                    buffer.append(log_entry)


def register_log_client() -> tuple[int, list]:
    """Register a new WebSocket client and return client_id and history logs."""
    global _client_id_counter

    with _client_buffers_lock:
        _client_id_counter += 1
        client_id = _client_id_counter
        _client_buffers[client_id] = deque(maxlen=_client_buffer_max_size)

    # 返回历史日志副本
    with _log_history_lock:
        history = list(_log_history)

    return client_id, history


def unregister_log_client(client_id: int):
    """Unregister a WebSocket client."""
    with _client_buffers_lock:
        _client_buffers.pop(client_id, None)


def get_pending_logs(client_id: int) -> list:
    """Get and clear pending logs for a client."""
    with _client_buffers_lock:
        buffer = _client_buffers.get(client_id)
        if buffer:
            logs = list(buffer)
            buffer.clear()
            return logs
    return []


def setup_websocket_logging():
    """Set up the WebSocket log handler on the root logger."""
    handler = WebSocketLogHandler()
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)
