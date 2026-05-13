#!/usr/bin/env bash
# ============================================================
#  NeuralHire — Quick Setup & Run Script
#  Usage:  bash run.sh
# ============================================================

set -e

VENV_DIR=".venv"
PYTHON=${PYTHON:-python3}

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       NeuralHire AI Interview Platform   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Python virtual environment ──────────────
if [ ! -d "$VENV_DIR" ]; then
  echo "[1/5] Creating virtual environment..."
  $PYTHON -m venv $VENV_DIR
fi

source "$VENV_DIR/bin/activate"
echo "[1/5] Virtual environment: OK"

# ── 2. Install dependencies ────────────────────
echo "[2/5] Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Optional: try to install Whisper (may fail on some systems)
pip install openai-whisper -q 2>/dev/null || echo "  ⚠  Whisper install failed — will use SpeechRecognition fallback"
echo "[2/5] Dependencies: OK"

# ── 3. Check Ollama ────────────────────────────
echo "[3/5] Checking Ollama..."
if command -v ollama &>/dev/null; then
  echo "  ✓  Ollama binary found"
  # Check if running
  if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "  ✓  Ollama service is running"
  else
    echo "  ⚠  Ollama is not running. Starting it in background..."
    ollama serve &>/dev/null &
    sleep 3
  fi
  # Check llama3 model
  if ollama list 2>/dev/null | grep -q "llama3"; then
    echo "  ✓  llama3 model is available"
  else
    echo "  ⚠  llama3 model not found. Pulling now (this may take a while)..."
    ollama pull llama3
  fi
else
  echo "  ⚠  Ollama not found."
  echo "      Install from: https://ollama.com/download"
  echo "      Then run:     ollama pull llama3"
fi
echo "[3/5] Ollama: checked"

# ── 4. Create directories ──────────────────────
echo "[4/5] Creating output directories..."
mkdir -p reports graphs
echo "[4/5] Directories: OK"

# ── 5. Copy env if needed ─────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[5/5] Created .env from .env.example"
fi

# ── Launch ──────────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
echo "  Starting NeuralHire on http://localhost:5000"
echo "══════════════════════════════════════════"
echo ""

python app.py
