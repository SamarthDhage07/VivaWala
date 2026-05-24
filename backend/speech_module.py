"""
Speech-to-Text Module
Handles audio transcription using SpeechRecognition first, with Whisper fallback.
"""

import os
import shutil
import subprocess
import logging
import tempfile
import base64

logger = logging.getLogger(__name__)

# SpeechRecognition primary engine
try:
    import speech_recognition as sr

    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    logger.warning("SpeechRecognition not available.")

# Whisper fallback engine
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
    logger.warning("Whisper not available.")


def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str = "audio/webm") -> dict:
    """
    Transcribe raw audio bytes.
    Returns dict with 'text' and 'engine' used.
    Tries Python SpeechRecognition first, then falls back to Whisper.
    """
    if not audio_bytes:
        return {"text": "", "engine": "none", "error": "Empty audio data"}

    temp_paths = []

    try:
        with tempfile.NamedTemporaryFile(suffix=_suffix_for_mime_type(mime_type), delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
            temp_paths.append(tmp_path)

        errors = []

        if SR_AVAILABLE:
            result = _transcribe_sr(tmp_path, mime_type, temp_paths)
            if not result.get("error"):
                return result
            errors.append(f"SpeechRecognition: {result.get('error')}")

        if WHISPER_AVAILABLE:
            result = _transcribe_whisper(tmp_path)
            if not result.get("error"):
                return result
            errors.append(f"Whisper: {result.get('error')}")

        return {
            "text": "",
            "engine": "none",
            "error": "; ".join(errors) or "No transcription engine available. Install SpeechRecognition or whisper.",
        }
    finally:
        for path in temp_paths:
            try:
                os.unlink(path)
            except Exception:
                pass


def _suffix_for_mime_type(mime_type: str) -> str:
    """Return a useful file suffix for recorded browser audio."""
    mime_type = (mime_type or "").lower()
    if "wav" in mime_type:
        return ".wav"
    if "ogg" in mime_type:
        return ".ogg"
    if "mp4" in mime_type or "m4a" in mime_type:
        return ".mp4"
    return ".webm"


def _transcribe_whisper(audio_path: str) -> dict:
    """Transcribe using OpenAI Whisper (local)."""
    try:
        model = _get_whisper_model()
        result = model.transcribe(audio_path, language="en", fp16=False)
        text = result.get("text", "").strip()
        return {"text": text, "engine": "whisper", "error": None}
    except Exception as e:
        logger.warning(f"Whisper failed: {e}")
        return {"text": "", "engine": "whisper", "error": str(e)}


def _transcribe_sr(audio_path: str, mime_type: str, temp_paths: list[str]) -> dict:
    """Transcribe using the Python SpeechRecognition package."""
    try:
        sr_audio_path = _prepare_sr_audio_file(audio_path, mime_type, temp_paths)
        recognizer = sr.Recognizer()
        with sr.AudioFile(sr_audio_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        return {"text": text, "engine": "speech_recognition", "error": None}
    except sr.UnknownValueError:
        return {
            "text": "",
            "engine": "speech_recognition",
            "error": "Could not understand audio",
        }
    except sr.RequestError as e:
        return {
            "text": "",
            "engine": "speech_recognition",
            "error": f"Google SR API error: {e}",
        }
    except Exception as e:
        return {"text": "", "engine": "speech_recognition", "error": str(e)}


def _prepare_sr_audio_file(audio_path: str, mime_type: str, temp_paths: list[str]) -> str:
    """
    SpeechRecognition can read WAV/AIFF/FLAC. If a client sends WebM or Ogg,
    convert it to WAV before using sr.AudioFile.
    """
    if "wav" in (mime_type or "").lower():
        return audio_path

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg is required to convert browser audio for SpeechRecognition")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    temp_paths.append(wav_path)

    cmd = [
        ffmpeg_path,
        "-y",
        "-i", audio_path,
        "-ac", "1",
        "-ar", "16000",
        "-f", "wav",
        wav_path,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return wav_path


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
    if SR_AVAILABLE:
        engines.append("speech_recognition")
    if WHISPER_AVAILABLE:
        engines.append("whisper")
    return engines
