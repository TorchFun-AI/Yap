# Yap Build System
# Target: macOS arm64 (Apple Silicon)

.PHONY: all build build-backend repack-dmg build-frontend clean install-deps help setup-placeholder dev

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
	@echo "Yap Build System"
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
	cd $(TAURI_DIR) && npm install
	@echo "Installing backend dependencies..."
	cd $(BACKEND_DIR) && uv sync
	cd $(BACKEND_DIR) && uv pip install pyinstaller
	@echo "Done."

# Build backend sidecar (directory mode for faster startup)
build-backend:
	@echo "Building backend sidecar..."
	@mkdir -p $(BINARIES_DIR)
	cd $(BACKEND_DIR) && uv run pyinstaller \
		--distpath dist \
		--workpath build \
		--noconfirm \
		vocistant-backend.spec
	@# Copy directory for Tauri resources
	@rm -rf $(BINARIES_DIR)/vocistant-backend
	@mv $(BACKEND_DIR)/dist/vocistant-backend $(BINARIES_DIR)/vocistant-backend
	@echo "Backend sidecar built: $(BINARIES_DIR)/vocistant-backend/"

# Build frontend
build-frontend:
	@echo "Building frontend..."
	cd $(FRONTEND_DIR) && npm run build
	@echo "Frontend built."

# Full build
build: build-backend
	@echo "Building Tauri application..."
	cd $(TAURI_DIR) && npm run build
	@$(MAKE) repack-dmg

# Version (extracted from tauri.conf.json)
VERSION := $(shell grep '"version"' $(TAURI_DIR)/tauri.conf.json | head -1 | sed 's/.*: *"\(.*\)".*/\1/')

# DMG layout
BUNDLE_DIR := $(TAURI_DIR)/target/release/bundle
DMG_NAME := Yap_$(VERSION)_aarch64.dmg
DMG_DIR := $(BUNDLE_DIR)/dmg

# Repack DMG with Fix Security script (skip full rebuild)
repack-dmg:
	@echo "Rebuilding DMG with Fix Security script..."
	@chmod +x "$(TAURI_DIR)/resources/Fix Security.command"
	@rm -f "$(DMG_DIR)/$(DMG_NAME)"
	@"$(DMG_DIR)/bundle_dmg.sh" \
		--volname "Yap" \
		--volicon "$(DMG_DIR)/icon.icns" \
		--icon "Yap.app" 120 170 \
		--app-drop-link 540 170 \
		--add-file "Fix Security.command" "$(TAURI_DIR)/resources/Fix Security.command" 330 170 \
		--hide-extension "Yap.app" \
		--window-size 660 400 \
		"$(DMG_NAME)" \
		"$(BUNDLE_DIR)/macos/Yap.app"
	@mv "$(DMG_NAME)" "$(DMG_DIR)/$(DMG_NAME)"
	@echo "DMG repacked: $(DMG_DIR)/$(DMG_NAME)"

# Development mode (without backend packaging)
dev: setup-placeholder
	@echo "Starting development mode..."
	@echo "Note: Start backend manually with 'cd $(BACKEND_DIR) && uv run python main.py'"
	cd $(TAURI_DIR) && npm run tauri dev

# Setup placeholder sidecar for development
setup-placeholder:
	@mkdir -p $(BINARIES_DIR)/vocistant-backend
	@if [ ! -f $(BINARIES_DIR)/vocistant-backend/vocistant-backend ]; then \
		echo '#!/bin/bash' > $(BINARIES_DIR)/vocistant-backend/vocistant-backend; \
		chmod +x $(BINARIES_DIR)/vocistant-backend/vocistant-backend; \
		echo "Created placeholder sidecar for development"; \
	fi

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
