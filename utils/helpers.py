"""
Utils — Shared helper functions
"""

import re
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    """Generate a short unique session ID."""
    return str(uuid.uuid4())[:12]


def sanitize_text(text: str, max_len: int = 2000) -> str:
    """Strip dangerous chars and trim length."""
    if not text:
        return ""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text[:max_len].strip()


def score_to_color(score: float) -> str:
    """Return a hex color for a 0-10 score."""
    if score >= 8:
        return "#10b981"   # green
    elif score >= 6:
        return "#00d4ff"   # cyan
    elif score >= 4:
        return "#f59e0b"   # yellow
    else:
        return "#ef4444"   # red


def score_to_grade(score: float) -> str:
    """Map a 0-10 score to a letter grade."""
    if score >= 9:   return "A+"
    elif score >= 8: return "A"
    elif score >= 7: return "B+"
    elif score >= 6: return "B"
    elif score >= 5: return "C"
    elif score >= 4: return "D"
    else:            return "F"


def format_duration(seconds: float) -> str:
    """Format seconds into mm:ss string."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def now_iso() -> str:
    return datetime.now().isoformat()


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
