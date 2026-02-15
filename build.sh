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
echo "  │   Yap — Production Build     │"
echo "  ╰──────────────────────────────╯"
echo ""

# ── Check prerequisites ──

[[ "$(uname)" == "Darwin" ]] || fail "Yap only supports macOS."
[[ "$(uname -m)" == "arm64" ]] || fail "Yap requires Apple Silicon (M1/M2/M3/M4)."

command -v node &>/dev/null   || fail "Node.js not found. Run ./setup.sh first."
command -v cargo &>/dev/null  || fail "Rust not found. Run ./setup.sh first."
command -v uv &>/dev/null     || fail "uv not found. Run ./setup.sh first."

# Check if dependencies are installed
[[ -d src-frontend/node_modules ]] || fail "Frontend deps missing. Run ./setup.sh first."
[[ -d src-backend/.venv ]]         || fail "Backend venv missing. Run ./setup.sh first."

info "Prerequisites OK"

# ── Build backend sidecar ──

echo ""
echo "Building backend sidecar (this may take a few minutes)..."
cd src-backend && uv pip install pyinstaller && uv run pyinstaller \
    --distpath dist \
    --workpath build \
    --noconfirm \
    vocistant-backend.spec && cd ..
info "Backend compiled"

# ── Move sidecar to Tauri binaries ──

mkdir -p src-tauri/binaries
rm -rf src-tauri/binaries/vocistant-backend
mv src-backend/dist/vocistant-backend src-tauri/binaries/vocistant-backend
info "Sidecar moved to src-tauri/binaries/"

# ── Build Tauri app ──

echo ""
echo "Building Tauri application..."
cd src-tauri && npm run build && cd ..
info "Tauri app built"

echo ""
echo -e "${GREEN}Build complete!${NC}"
echo "Output: src-tauri/target/release/bundle/"
echo ""
