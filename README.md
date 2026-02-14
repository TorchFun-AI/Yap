<p align="center">
  <img src="docs/logo.png" alt="Yap" width="120" />
</p>

<h1 align="center">Yap</h1>

<p align="center">
  <strong>The voice input layer for agentic coding.</strong><br/>
  Speak in any language. It transcribes, corrects, translates, and types — right where your cursor is.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-CC%20BY--NC%204.0-blue.svg" alt="License" /></a>
  <img src="https://img.shields.io/badge/platform-macOS%20(Apple%20Silicon)-black?logo=apple" alt="Platform" />
  <img src="https://img.shields.io/badge/runtime-100%25%20local-brightgreen" alt="Local" />
</p>

---

## 🎬 Demo

> 🎥 Demo video coming soon — stay tuned!

> 💡 **Inspired by the agentic coding movement** — like [OpenClaw](https://github.com/openclaw/openclaw)'s founder voice-chatting with 10+ agents to build software. Yap is the missing input layer that makes talking to your dev tools feel native.

<!-- Optional: embed a video showing Yap + Claude Code / Cursor workflow -->
<!-- https://github.com/user-attachments/assets/agentic-workflow.mp4 -->

---

## 🤔 Why Yap?

The agentic coding era is here. You're talking to Claude Code, Cursor, Copilot — but you're still *typing* every prompt with your fingers.

**Your voice is 3x faster than your keyboard.** Yap bridges the gap.

- 🗣️ **Voice-first workflow** — Talk to your agents, your terminal, your browser. Yap types it out.
- 🔒 **100% local** — On-device VAD + ASR via MLX. No cloud. No data leaves your machine.
- 🌍 **Multilingual** — Speak Chinese, English, Japanese, Korean, and more. Real-time translation built in.
- ✨ **Smart correction** — LLM-powered spoken → written style conversion. Your voice, but polished.

---

## ⚡ How It Works

Yap lives as a floating ball on your screen. Toggle input mode, and it listens:

```
🎙️ Voice ──→ 🔇 VAD ──→ 🧠 ASR ──→ 💬 LLM ──→ ⌨️ Input
             Silero      MLX       Correct    Types into
             detects     on-device  & Translate active app
             speech      transcribe (optional)
```

Models auto-download from HuggingFace on first launch. Zero config to get started.

---

## ✨ Features

| | Feature | Description |
|---|---------|-------------|
| 🎙️ | **Multilingual Voice Input** | Chinese, English, Japanese, and more — switch on the fly |
| 🌐 | **Real-time Translation** | Speak in one language, type in another |
| ✍️ | **Formal Correction** | Spoken → written style, powered by any LLM |
| 🖥️ | **Universal Input** | Works with any app — Claude Code, Cursor, VS Code, Terminal, browser, Slack... |
| 🫧 | **Floating Ball UI** | Always-on-top, draggable, with live waveform visualization |
| 🔒 | **Fully Local** | On-device ASR, no cloud dependency, your data stays yours |
| 🌏 | **i18n Menu** | 中文 / English interface |

---

## 🚀 Quick Start

### Prerequisites

- macOS with Apple Silicon (M1/M2/M3/M4)
- Node.js 18+
- Rust (latest stable)
- Python 3.10 – 3.12
- [uv](https://github.com/astral-sh/uv)

### Install & Run

```bash
# Clone
git clone https://github.com/TorchFun-AI/Yap.git && cd Yap

# Install frontend dependencies
cd src-frontend && npm install && cd ..

# Install Python dependencies
cd src-backend && uv sync && cd ..

# Terminal 1 — Start Python AI backend
cd src-backend && uv run python main.py

# Terminal 2 — Start Tauri dev server
cd src-tauri && npm run tauri dev
```

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vue 3 UI      │◄───►│   Tauri Core    │◄───►│  Python AI      │
│   (Webview)     │ IPC │   (Rust)        │ WS  │  (FastAPI)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                        │
                              ▼                        ▼
                        ┌───────────┐           ┌───────────┐
                        │ Keyboard  │           │ VAD + ASR │
                        │ Simulation│           │   + LLM   │
                        └───────────┘           └───────────┘
```

| Layer | Stack |
|-------|-------|
| Frontend | Vue 3 + TypeScript + Ant Design Vue + Pinia |
| Core | Tauri 2 (Rust) |
| Backend | Python + FastAPI + Silero VAD + MLX Audio |

---

## 🔧 LLM Configuration

Yap uses any **OpenAI-compatible API** for text correction and translation. Configure in Settings:

- API Key
- Base URL (e.g. `https://api.openai.com/v1`, or a local Ollama endpoint)
- Model name

> This is optional — without it, Yap still does voice-to-text perfectly fine.

---

## 📄 License

[CC BY-NC 4.0](LICENSE) — Free to use, modify, and share. Not for commercial use.
