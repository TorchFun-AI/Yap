# Vocistant Build System
# Target: macOS arm64 (Apple Silicon)

.PHONY: all build build-backend build-frontend clean install-deps help

# Directories
BACKEND_DIR := src-backend
FRONTEND_DIR := src-frontend
TAURI_DIR := src-tauri
BINARIES_DIR := $(TAURI_DIR)/binaries

# Target triple for Apple Silicon
TARGET_TRIPLE := aarch64-apple-darwin

# Default target
all: build

# Help
help:
	@echo "Vocistant Build System"
	@echo ""
	@echo "Usage:"
	@echo "  make install-deps    Install all dependencies"
	@echo "  make build-backend   Build Python backend with PyInstaller"
	@echo "  make build-frontend  Build Vue frontend"
	@echo "  make build           Full build (backend + Tauri app)"
	@echo "  make clean           Clean all build artifacts"
	@echo ""

# Install dependencies
install-deps:
	@echo "Installing frontend dependencies..."
	cd $(FRONTEND_DIR) && npm install
	@echo "Installing backend dependencies..."
	cd $(BACKEND_DIR) && pip install -r requirements.txt
	@echo "Installing PyInstaller..."
	pip install pyinstaller
	@echo "Done."

# Build backend sidecar
build-backend:
	@echo "Building backend sidecar..."
	@mkdir -p $(BINARIES_DIR)
	cd $(BACKEND_DIR) && pyinstaller \
		--distpath ../$(BINARIES_DIR) \
		--workpath build \
		--clean \
		--noconfirm \
		vocistant-backend.spec
	@# Rename to include target triple for Tauri sidecar
	@mv $(BINARIES_DIR)/vocistant-backend $(BINARIES_DIR)/vocistant-backend-$(TARGET_TRIPLE)
	@echo "Backend sidecar built: $(BINARIES_DIR)/vocistant-backend-$(TARGET_TRIPLE)"

# Build frontend
build-frontend:
	@echo "Building frontend..."
	cd $(FRONTEND_DIR) && npm run build
	@echo "Frontend built."

# Full build
build: build-backend
	@echo "Building Tauri application..."
	cd $(TAURI_DIR) && cargo tauri build
	@echo "Build complete!"
	@echo "Output: $(TAURI_DIR)/target/release/bundle/"

# Development mode (without backend packaging)
dev:
	@echo "Starting development mode..."
	@echo "Note: Start backend manually with 'cd $(BACKEND_DIR) && python main.py'"
	cd $(TAURI_DIR) && cargo tauri dev

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BACKEND_DIR)/build
	rm -rf $(BACKEND_DIR)/dist
	rm -rf $(BINARIES_DIR)/vocistant-backend*
	rm -rf $(FRONTEND_DIR)/dist
	rm -rf $(TAURI_DIR)/target
	@echo "Clean complete."

# Clean only backend
clean-backend:
	@echo "Cleaning backend build artifacts..."
	rm -rf $(BACKEND_DIR)/build
	rm -rf $(BACKEND_DIR)/dist
	rm -rf $(BINARIES_DIR)/vocistant-backend*
	@echo "Backend clean complete."
