# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vocistant — a local real-time voice-to-text input tool. Captures microphone audio, runs VAD + ASR locally on Apple Silicon (MLX), optionally corrects/translates via LLM, then auto-types the result into the active window. Built with Tauri 2 + Vue 3 + Python FastAPI.

## Build & Dev Commands

```bash
# Install all dependencies
make install-deps

# Development mode (two terminals needed):
# Terminal 1 — Python backend:
cd src-backend && uv run python main.py
# Terminal 2 — Tauri + Vue dev server:
make dev

# Production build (backend PyInstaller + Tauri bundle + DMG)
make build

# Build only backend sidecar
make build-backend

# Clean all artifacts
make clean
```

Frontend only: `cd src-frontend && npm run build` (includes vue-tsc type check).
No test suite is configured.

## Architecture (Three-Layer)

```
Vue 3 Frontend (Webview)
    ↕ Tauri IPC commands (invoke)
Tauri Core (Rust)
    ↕ WebSocket (JSON) + HTTP REST
Python Backend (FastAPI)
```

### Communication Channels

| Channel | Endpoint | Purpose |
|---------|----------|---------|
| WebSocket | `/ws/audio` | Control messages (start/stop/config) + transcription results |
| WebSocket | `/ws/waveform` | Real-time 5-band audio levels for visualization |
| WebSocket | `/ws/logs` | Backend log streaming |
| HTTP | `/api/devices`, `/api/models/*` | Device listing, model management |
| Tauri IPC | `get_backend_port`, `input_text`, `set_window_bounds`, etc. | Window mgmt, keyboard simulation, clipboard |

### Port Discovery

Tauri allocates a port (dev: 8765, prod: random), passes it to the backend sidecar via `VOCISTANT_PORT` env var. Frontend retrieves it via `get_backend_port()` IPC command, stores full URLs in localStorage.

### Recording Data Flow

1. Frontend sends `{type: "control", action: "start"}` via `/ws/audio`
2. Backend captures audio → Silero VAD detects speech → MLX ASR transcribes
3. Partial results stream back as `transcription_partial` messages
4. On speech end: finalize ASR → LLM correction → LLM translation (if enabled)
5. Backend sends `text_input_request` → Frontend calls Tauri `input_text()` → CGEvent keyboard simulation

## Key Directories

- **src-frontend/src/services/** — `signalController.ts` (main WS), `waveformController.ts`, `logController.ts`, `portService.ts`, `bridge.ts`
- **src-frontend/src/stores/appState.ts** — Single Pinia store with all app state, settings persisted to localStorage
- **src-frontend/src/components/** — `FloatingBallV2.vue` (draggable floating UI), `MessagePanel.vue`, `SettingsPanel.vue`
- **src-tauri/src/lib.rs** — All Tauri commands, sidecar lifecycle, tray menu, global shortcuts, macOS native APIs
- **src-backend/core/pipeline.py** — AudioPipeline orchestrating VAD → ASR → LLM correction → translation
- **src-backend/core/** — `asr_engine.py`, `vad_engine.py`, `llm_corrector.py`, `llm_translator.py`, `audio_capture.py`, `recording_session.py`, `history_store.py` (SQLite), `waveform_analyzer.py`

## Tech Stack Details

- **Frontend**: Vue 3 + TypeScript + Ant Design Vue + Pinia + vue-i18n (zh/en), Vite dev server on port 5173
- **Tauri**: Rust, plugins: shell (sidecar), store (persistence), global-shortcut, clipboard-manager. macOS private API enabled for transparent/click-through windows
- **Backend**: Python 3.10-3.12, FastAPI + uvicorn, Silero VAD, MLX Audio (Apple Silicon ASR), OpenAI-compatible LLM client
- **Target**: macOS arm64 (Apple Silicon). Keyboard simulation and cursor tracking use macOS-specific CGEvent/NSWindow APIs

## Conventions

- The project uses Chinese for commit messages, comments, and UI text (with i18n support)
- Frontend uses `<script setup lang="ts">` SFC style
- Path alias: `@/` → `src-frontend/src/`
- Settings sync across windows via Tauri `broadcast_settings_changed` event
- Backend sidecar is packaged as a directory (not single binary) for faster startup
