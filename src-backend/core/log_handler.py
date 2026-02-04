"""
WebSocket Log Handler for real-time log streaming.
"""

import logging
import asyncio
from typing import Dict, Tuple
from datetime import datetime
from collections import deque

# 全局历史缓冲区（用于新连接时发送历史日志）
_log_history: deque = deque(maxlen=100)

# 客户端信息：(asyncio.Queue, event_loop)
_clients: Dict[int, Tuple[asyncio.Queue, asyncio.AbstractEventLoop]] = {}
_client_id_counter = 0


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
        _log_history.append(log_entry)

        # 通过事件循环安全地将日志放入每个客户端的异步队列
        for client_id, (q, loop) in list(_clients.items()):
            try:
                loop.call_soon_threadsafe(q.put_nowait, log_entry)
            except (RuntimeError, asyncio.QueueFull):
                pass


def register_log_client(loop: asyncio.AbstractEventLoop) -> tuple[int, asyncio.Queue, list]:
    """Register a new WebSocket client with its event loop."""
    global _client_id_counter

    _client_id_counter += 1
    client_id = _client_id_counter
    client_queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    _clients[client_id] = (client_queue, loop)

    # 返回历史日志副本
    history = list(_log_history)

    return client_id, client_queue, history


def unregister_log_client(client_id: int):
    """Unregister a WebSocket client."""
    _clients.pop(client_id, None)


def setup_websocket_logging():
    """Set up the WebSocket log handler on the root logger."""
    handler = WebSocketLogHandler()
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)
