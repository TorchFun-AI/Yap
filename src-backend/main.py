"""
Vocistant AI Backend
FastAPI application with WebSocket support for real-time voice processing.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from core.recording_session import RecordingSession
from core.audio_capture import AudioCapture
from core.waveform_analyzer import register_waveform_callback, unregister_waveform_callback
from core.model_manager import ModelManager
from core.log_handler import setup_websocket_logging, register_log_client, unregister_log_client, get_pending_logs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    print("Vocistant backend starting...")
    setup_websocket_logging()
    yield
    print("Vocistant backend shutting down...")


app = FastAPI(
    title="Vocistant AI",
    description="Voice Assistant Backend with VAD and ASR",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "vocistant-ai"}


@app.get("/api/devices")
async def list_devices():
    """List available audio input devices."""
    return {"devices": AudioCapture.list_devices()}


# Model Manager instance
model_manager = ModelManager()


class DownloadRequest(BaseModel):
    model_id: str


@app.get("/api/models/local")
async def list_local_models():
    """列出本地已下载的模型"""
    return {"models": model_manager.list_local_models()}


@app.get("/api/models/available")
async def list_available_models():
    """列出可下载的 MLX 格式模型"""
    return {"models": model_manager.list_available_models()}


@app.post("/api/models/download")
async def download_model(request: DownloadRequest):
    """下载模型（同步执行，适合小模型）"""
    import threading

    def do_download():
        model_manager.download_model(request.model_id)

    # 在后台线程中执行下载
    thread = threading.Thread(target=do_download)
    thread.start()

    return {"status": "started", "model_id": request.model_id}


@app.get("/api/models/progress/{model_id:path}")
async def get_download_progress(model_id: str):
    """获取下载进度"""
    progress = model_manager.get_download_progress(model_id)
    if progress:
        return progress
    return {"status": "not_found"}


@app.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):
    """WebSocket endpoint for audio control via JSON messages."""
    await websocket.accept()
    session: RecordingSession | None = None

    async def send_result(result: dict):
        """Send result to WebSocket client."""
        try:
            await websocket.send_json(result)
        except Exception as e:
            print(f"Error sending result: {e}")

    def on_result(result: dict):
        """Callback for recording session results (called from audio thread)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(send_result(result))
        except RuntimeError:
            pass

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "control":
                action = data.get("action")
                if action == "start":
                    if session is None or not session.is_running:
                        config = data.get("config", {})
                        session = RecordingSession(on_result=on_result)
                        session.start(config)
                elif action == "stop":
                    if session and session.is_running:
                        session.stop()
                        session = None
                elif action == "update_config":
                    if session and session.is_running:
                        config = data.get("config", {})
                        session.update_config(config)
                elif action == "update_llm_config":
                    if session:
                        llm_config = data.get("config", {})
                        session.update_llm_config(llm_config)
    except WebSocketDisconnect:
        print("Client disconnected")
        if session and session.is_running:
            session.stop()


@app.websocket("/ws/waveform")
async def waveform_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time waveform visualization data."""
    await websocket.accept()
    import asyncio

    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def on_waveform(levels: list):
        """Callback for waveform data (called from audio thread)."""
        try:
            loop.call_soon_threadsafe(queue.put_nowait, levels)
        except RuntimeError:
            pass

    # Register callback
    register_waveform_callback(on_waveform)

    try:
        while True:
            # Wait for waveform data
            levels = await queue.get()
            # Send to client
            await websocket.send_json({
                "type": "waveform",
                "levels": levels
            })
    except WebSocketDisconnect:
        print("Waveform client disconnected")
    finally:
        # Unregister callback
        unregister_waveform_callback(on_waveform)


@app.websocket("/ws/logs")
async def logs_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    await websocket.accept()
    import asyncio

    # Register client and get history logs
    client_id, history_logs = register_log_client()

    try:
        # Send history logs first
        for log_entry in history_logs:
            await websocket.send_json(log_entry)

        # Poll and stream new logs
        while True:
            pending_logs = get_pending_logs(client_id)
            for log_entry in pending_logs:
                await websocket.send_json(log_entry)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        print("Log client disconnected")
    finally:
        unregister_log_client(client_id)


def main():
    """Entry point for the backend server."""
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8765,
    )


if __name__ == "__main__":
    main()
