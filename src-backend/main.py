"""
Vocistant AI Backend
FastAPI application with WebSocket support for real-time voice processing.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.recording_session import RecordingSession
from core.audio_capture import AudioCapture

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
    except WebSocketDisconnect:
        print("Client disconnected")
        if session and session.is_running:
            session.stop()


def main():
    """Entry point for the backend server."""
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8765,
        reload=True,
    )


if __name__ == "__main__":
    main()
