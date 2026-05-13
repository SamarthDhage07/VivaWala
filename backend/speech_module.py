"""
Speech-to-Text Module
Handles audio recording and transcription using Whisper + SpeechRecognition fallback.
"""

import os
import io
import logging
import tempfile
import base64
import numpy as np

logger = logging.getLogger(__name__)

# Try importing Whisper (optional, fall back to SpeechRecognition)
try:
    import whisper

    _WHISPER_MODEL = None  # Lazy load

    def _get_whisper_model():
        global _WHISPER_MODEL
        if _WHISPER_MODEL is None:
            logger.info("Loading Whisper base model...")
            _WHISPER_MODEL = whisper.load_model("base")
        return _WHISPER_MODEL

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available. Using SpeechRecognition fallback.")

# SpeechRecognition fallback
try:
    import speech_recognition as sr

    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    logger.warning("SpeechRecognition not available.")


def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str = "audio/webm") -> dict:
    """
    Transcribe raw audio bytes.
    Returns dict with 'text' and 'engine' used.
    Tries Whisper first, falls back to Google SpeechRecognition.
    """
    if not audio_bytes:
        return {"text": "", "engine": "none", "error": "Empty audio data"}

    # Write to temp file
    suffix = ".webm"
    if "wav" in mime_type:
        suffix = ".wav"
    elif "ogg" in mime_type:
        suffix = ".ogg"
    elif "mp4" in mime_type:
        suffix = ".mp4"

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        if WHISPER_AVAILABLE:
            return _transcribe_whisper(tmp_path)
        elif SR_AVAILABLE:
            return _transcribe_sr(tmp_path)
        else:
            return {
                "text": "",
                "engine": "none",
                "error": "No transcription engine available. Install whisper or SpeechRecognition.",
            }
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _transcribe_whisper(audio_path: str) -> dict:
    """Transcribe using OpenAI Whisper (local)."""
    try:
        model = _get_whisper_model()
        result = model.transcribe(audio_path, language="en", fp16=False)
        text = result.get("text", "").strip()
        return {"text": text, "engine": "whisper", "error": None}
    except Exception as e:
        logger.warning(f"Whisper failed: {e}. Falling back to SpeechRecognition.")
        if SR_AVAILABLE:
            return _transcribe_sr(audio_path)
        return {"text": "", "engine": "whisper", "error": str(e)}


def _transcribe_sr(audio_path: str) -> dict:
    """Transcribe using Google SpeechRecognition API."""
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        return {"text": text, "engine": "google_sr", "error": None}
    except sr.UnknownValueError:
        return {
            "text": "",
            "engine": "google_sr",
            "error": "Could not understand audio",
        }
    except sr.RequestError as e:
        return {
            "text": "",
            "engine": "google_sr",
            "error": f"Google SR API error: {e}",
        }
    except Exception as e:
        return {"text": "", "engine": "google_sr", "error": str(e)}


def transcribe_base64_audio(b64_audio: str, mime_type: str = "audio/webm") -> dict:
    """
    Convenience wrapper: decode base64 audio and transcribe.
    """
    try:
        # Handle data URLs like "data:audio/webm;base64,XXXXX"
        if "," in b64_audio:
            header, b64_audio = b64_audio.split(",", 1)
            if "audio/" in header:
                mime_type = header.split(";")[0].replace("data:", "")
        audio_bytes = base64.b64decode(b64_audio)
        return transcribe_audio_bytes(audio_bytes, mime_type)
    except Exception as e:
        return {"text": "", "engine": "none", "error": f"Base64 decode error: {e}"}


def get_available_engines() -> list[str]:
    """Return list of available STT engines."""
    engines = []
    if WHISPER_AVAILABLE:
        engines.append("whisper")
    if SR_AVAILABLE:
        engines.append("speech_recognition")
    return engines
