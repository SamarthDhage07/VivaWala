"""
Config — Central configuration for NeuralHire
All values can be overridden via environment variables or a .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Provider ─────────────────────────────────────────────────────────────
# "groq"   → Groq API (fast, cloud, free tier available)
# "ollama" → Local Ollama (private, no API key needed)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

# ── Groq ─────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL",   "llama-3.3-70b-versatile")
# If Groq fails, automatically fall back to Ollama
GROQ_FALLBACK_TO_OLLAMA = os.getenv("GROQ_FALLBACK_TO_OLLAMA", "true").lower() == "true"

# ── Ollama ───────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "llama3")
OLLAMA_TIMEOUT  = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# ── Flask ────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "neuralhire-dev-secret")
DEBUG      = os.getenv("DEBUG", "true").lower() == "true"
PORT       = int(os.getenv("PORT", "5000"))
HOST       = os.getenv("HOST", "0.0.0.0")

# ── Interview defaults ────────────────────────────────────────────────────────
DEFAULT_NUM_QUESTIONS = int(os.getenv("DEFAULT_NUM_QUESTIONS", "7"))
MIN_QUESTIONS         = 3
MAX_QUESTIONS         = 10

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(__file__)
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
GRAPHS_DIR  = os.path.join(BASE_DIR, "graphs")

# ── Speech ───────────────────────────────────────────────────────────────────
# tiny | base | small | medium | large  (larger = more accurate, slower)
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
