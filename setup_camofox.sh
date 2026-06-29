#!/bin/bash
# Camofox Setup for Reddit Automation API
# Installs deps + configures Camofox with proxy

set -e

echo "=== Reddit API — Camofox Setup ==="
echo ""

# --- 1. System dependencies ---
echo "[1/4] Installing system dependencies..."
sudo apt update -qq
sudo apt install -y -qq \
  curl \
  unzip \
  python3-minimal 2>/dev/null || true
echo "Done."
echo ""

# --- 2. Node.js ---
if ! command -v node >/dev/null 2>&1; then
  echo "[2/4] Installing Node.js..."
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt install -y -qq nodejs
else
  echo "[2/4] Node.js already installed: $(node --version)"
fi
echo ""

# --- 3. Camofox browser ---
CAMOFOX_DIR="$HOME/camofox-browser"
if [ -d "$CAMOFOX_DIR" ]; then
  echo "[3/4] Camofox already at $CAMOFOX_DIR"
else
  echo "[3/4] Cloning Camofox..."
  git clone https://github.com/jo-inc/camofox-browser "$CAMOFOX_DIR"
fi
cd "$CAMOFOX_DIR"
npm install 2>/dev/null || true
echo "Done."
echo ""

# --- 4. Proxy configuration ---
echo "[4/4] Configuration..."
echo ""
echo "To start Camofox with your Evomi proxy, run:"
echo ""
echo "  cd $CAMOFOX_DIR"
echo "  PROXY_HOST=core-residential.evomi.com \\"
echo "  PROXY_PORT=1000 \\"
echo "  PROXY_USERNAME=vaproh4 \\"
echo "  PROXY_PASSWORD=YOUR_SESSION \\"
echo "  CAMOFOX_PORT=9377 \\"
echo "  ENABLE_VNC=1 \\"
echo "  npm start"
echo ""
echo "Or for a simple start (no VNC):"
echo ""
echo "  cd $CAMOFOX_DIR"
echo "  PROXY_HOST=core-residential.evomi.com \\"
echo "  PROXY_PORT=1000 \\"
echo "  PROXY_USERNAME=vaproh4 \\"
echo "  PROXY_PASSWORD=YOUR_SESSION \\"
echo "  CAMOFOX_PORT=9377 \\"
echo "  npm start"
echo ""

# Update .env if exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
  echo "Updating .env with CAMOFOX_PORT=9377..."
  sed -i 's/CAMOFOX_PORT=.*/CAMOFOX_PORT=9377/' "$SCRIPT_DIR/.env"
fi

echo "=== Setup Complete ==="