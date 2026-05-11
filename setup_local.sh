#!/usr/bin/env bash
# setup_local.sh — one-shot local setup for the Todo Agent evaluation harness
set -e

MODEL="gemma4:e2b-it-q4_K_M"

echo "=== Todo Agent — Local Setup ==="

# 1. Install Ollama if not present
if ! command -v ollama &>/dev/null; then
  echo "[1/4] Installing Ollama..."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &>/dev/null; then
      brew install ollama
    else
      echo "Homebrew not found. Install Ollama manually from https://ollama.com/download"
      exit 1
    fi
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    curl -fsSL https://ollama.com/install.sh | sh
  else
    echo "Unsupported OS. Install Ollama manually: https://ollama.com/download"
    exit 1
  fi
else
  echo "[1/4] Ollama already installed: $(ollama --version)"
fi

# 2. Start Ollama service (macOS: launchctl; Linux: systemd)
echo "[2/4] Starting Ollama service..."
if [[ "$OSTYPE" == "darwin"* ]]; then
  # Ollama on macOS runs as a menu-bar app or via 'ollama serve'
  if ! pgrep -x ollama &>/dev/null; then
    ollama serve &>/dev/null &
    sleep 2
  fi
else
  if command -v systemctl &>/dev/null; then
    sudo systemctl enable --now ollama || true
  else
    if ! pgrep -x ollama &>/dev/null; then
      ollama serve &>/dev/null &
      sleep 2
    fi
  fi
fi
echo "   Ollama service running."

# 3. Pull the model
echo "[3/4] Pulling model '${MODEL}'  (this may take several minutes on first run)..."
ollama pull "${MODEL}"
echo "   Model ready."

# 4. Install Python dependencies
echo "[4/4] Installing Python dependencies..."
if command -v pip3 &>/dev/null; then
  pip3 install -r requirements.txt
elif command -v pip &>/dev/null; then
  pip install -r requirements.txt
else
  echo "pip not found. Install Python 3 and pip, then run: pip install -r requirements.txt"
  exit 1
fi

echo ""
echo "=== Setup complete ==="
echo "Run the agent:         python3 todo_agent.py"
echo "Run the eval harness:  python3 tester_agent.py"
