#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

cd "$(dirname "$0")"

echo ""
echo "  ╭──────────────────────────────╮"
echo "  │   Yap — Dev Environment      │"
echo "  ╰──────────────────────────────╯"
echo ""

# ── Check prerequisites ──

[[ "$(uname)" == "Darwin" ]] || fail "Yap only supports macOS."
[[ "$(uname -m)" == "arm64" ]] || fail "Yap requires Apple Silicon (M1/M2/M3/M4)."
info "macOS Apple Silicon detected"

if command -v node &>/dev/null; then
    info "Node.js $(node -v)"
else
    fail "Node.js not found. Install via: brew install node"
fi

if command -v cargo &>/dev/null; then
    info "Rust $(rustc --version | awk '{print $2}')"
else
    warn "Rust not found. Installing via rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
    info "Rust installed"
fi

if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    info "Python $PY_VER"
else
    fail "Python 3.10+ not found. Install via: brew install python@3.12"
fi

if command -v uv &>/dev/null; then
    info "uv $(uv --version | awk '{print $2}')"
else
    warn "uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.local/bin/env" 2>/dev/null || true
    info "uv installed"
fi

# ── Install dependencies ──

echo ""
echo "Installing frontend dependencies..."
cd src-frontend && npm install && cd ..
info "Frontend dependencies installed"

echo ""
echo "Installing Tauri CLI..."
cd src-tauri && npm install && cd ..
info "Tauri CLI installed"

echo ""
echo "Installing backend dependencies..."
cd src-backend && uv sync && cd ..
info "Backend dependencies installed"

# ── Setup dev sidecar placeholder ──

make setup-placeholder
info "Dev sidecar placeholder ready"

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "To start development (two terminals):"
echo ""
echo "  Terminal 1 — Backend:"
echo "    cd src-backend && uv run python main.py"
echo ""
echo "  Terminal 2 — Tauri + Vue:"
echo "    make dev"
echo ""
