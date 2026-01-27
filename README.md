# Vocistant

> 本地运行的实时语音转文字输入工具，基于 Tauri + Vue 3 + Python AI 构建，支持将语音实时转写并自动输入到任意应用程序。

## 特性

- **本地运行** - 所有 AI 推理在本地完成，无需联网，保护隐私
- **实时转写** - 流式识别，边说边出字，延迟低
- **自动输入** - 识别结果自动输入到当前活动窗口
- **后台常驻** - 系统托盘运行，随时唤醒
- **中文优化** - 使用 MLX Audio 模型，中文识别效果优秀

## 技术栈

| 层级 | 技术 |
|------|------|
| **Frontend** | Vue 3 + TypeScript + Ant Design Vue + Pinia |
| **Core** | Tauri 2 (Rust) |
| **Backend** | Python 3.12 + FastAPI + Silero VAD + MLX Audio |

## 项目结构

```
Vocistant/
├── src-frontend/          # Vue 3 前端
│   └── src/
│       ├── components/    # UI 组件 (FloatingBall, StatusPanel)
│       ├── views/         # 页面 (Settings)
│       ├── stores/        # Pinia 状态管理
│       └── services/      # 服务层 (bridge, audioRecorder)
├── src-tauri/             # Tauri Rust 核心
│   └── src/
│       └── main.rs        # 应用入口
└─ src-backend/           # Python AI 后端
    ├── core/
    │   └── pipeline.py    # AI 处理管线
    ├── models/            # ASR 模型文件
    └── main.py            # FastAPI 服务入口

```

## 系统要求

| 平台 | 最低要求 |
|------|----------|
| **macOS** | 10.15+ (Catalina) |
| **Windows** | Windows 10 64-bit |
| **Linux** | Ubuntu 20.04+ |
| **内存** | 4GB RAM |
| **存储** | 1GB 可用空间 |

## 快速开始

### 前置条件

- Node.js 18+
- Rust (最新稳定版)
- Python 3.10 - 3.12
- uv (Python 包管理器)

### 安装与运行

```bash
# 1. 克隆项目
git clone <repo-url>
cd Vocistant

# 2. 安装前端依赖
cd src-frontend && npm install && cd ..

# 3. 安装 Python 依赖
cd src-backend && uv sync && cd ..

# 4. 启动 Python AI 服务
cd src-backend && uv run python main.py

# 5. 启动 Tauri 开发服务 (新终端)
cd src-tauri && npm run tauri dev
```

## 架构概览

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vue 3 UI      │◄───►│   Tauri Core    │◄───►│  Python AI      │
│   (Webview)     │ IPC │   (Rust)        │ WS  │  (FastAPI)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                        │
                              ▼                        ▼
                        ┌───────────┐           ┌───────────┐
                        │ 键盘模拟   │           │ VAD + ASR │
                        └───────────┘           └───────────┘
```

## License

MIT
