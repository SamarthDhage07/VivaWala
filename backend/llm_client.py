"""
LLM Client — Unified provider abstraction
Supports:  groq (llama-3.3-70b-versatile via Groq API)
           ollama (llama3 local via Ollama)

Active provider is controlled by LLM_PROVIDER env var (default: groq).
Fallback chain: groq → ollama → error
"""

import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

# ── Provider constants ────────────────────────────────────────────────────────
PROVIDER_GROQ   = "groq"
PROVIDER_OLLAMA = "ollama"

# Groq
GROQ_API_URL    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY    = os.getenv("GROQ_API_KEY", "")

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3")

# Active provider — read once at import time, can be overridden at runtime
_ACTIVE_PROVIDER = os.getenv("LLM_PROVIDER", PROVIDER_GROQ).lower()


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _call_groq(prompt: str, system: str = "", temperature: float = 0.7) -> str:
    """Call Groq's OpenAI-compatible chat endpoint."""
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file.\n"
            "Get a free key at https://console.groq.com"
        )

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1024,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Could not reach Groq API. Check your internet connection.")
    except requests.exceptions.HTTPError as e:
        body = ""
        try:
            body = resp.json().get("error", {}).get("message", "")
        except Exception:
            pass
        raise RuntimeError(f"Groq API error {resp.status_code}: {body or str(e)}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Groq response format: {e}")


def _call_ollama(prompt: str, system: str = "") -> str:
    """Call local Ollama /api/generate endpoint."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
    }
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure it is running: `ollama serve`"
        )
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")


def _call_llm(prompt: str, system: str = "", provider: str | None = None) -> str:
    """
    Route to the correct provider.
    If provider is None, uses _ACTIVE_PROVIDER.
    Falls back to Ollama if Groq fails and GROQ_FALLBACK_TO_OLLAMA=true.
    """
    use = (provider or _ACTIVE_PROVIDER).lower()
    fallback = os.getenv("GROQ_FALLBACK_TO_OLLAMA", "true").lower() == "true"

    if use == PROVIDER_GROQ:
        try:
            return _call_groq(prompt, system)
        except RuntimeError as e:
            if fallback:
                logger.warning(f"Groq failed ({e}), falling back to Ollama…")
                return _call_ollama(prompt, system)
            raise
    elif use == PROVIDER_OLLAMA:
        return _call_ollama(prompt, system)
    else:
        raise ValueError(f"Unknown LLM provider: '{use}'. Use 'groq' or 'ollama'.")


# ─────────────────────────────────────────────────────────────────────────────
# Public API  (same signatures as the old ollama_client.py)
# ─────────────────────────────────────────────────────────────────────────────

def generate_questions(domain: str, num_questions: int = 7) -> list[str]:
    """Generate domain-specific interview questions. Returns list of strings."""
    system = (
        "You are an expert technical interviewer. "
        "Generate clear, progressively challenging interview questions. "
        "Return ONLY a JSON array of question strings, nothing else."
    )
    prompt = (
        f"Generate exactly {num_questions} interview questions for a candidate "
        f"applying for a role in: {domain}.\n"
        "Mix easy, medium, and hard difficulty. "
        "Include both conceptual and practical questions. "
        'Return ONLY a valid JSON array like: ["Q1?", "Q2?", ...]'
    )
    raw = _call_llm(prompt, system)

    try:
        start = raw.index("[")
        end   = raw.rindex("]") + 1
        questions = json.loads(raw[start:end])
        return [str(q).strip() for q in questions if q]
    except (ValueError, json.JSONDecodeError):
        lines = [
            l.strip().lstrip("0123456789.-) ")
            for l in raw.split("\n") if l.strip()
        ]
        return [l for l in lines if len(l) > 10][:num_questions]


def evaluate_answer(
    domain: str,
    question: str,
    answer: str,
    question_number: int,
) -> dict:
    """Evaluate a candidate answer. Returns dict with score, feedback, etc."""
    system = (
        "You are a strict but fair technical interviewer evaluating a job candidate. "
        "Respond ONLY with valid JSON. No extra text before or after the JSON."
    )
    prompt = f"""Domain: {domain}
Question {question_number}: {question}
Candidate's Answer: {answer}

Evaluate this answer and return ONLY this JSON structure:
{{
  "score": <integer 0-10>,
  "verdict": "<Excellent|Good|Average|Poor>",
  "feedback": "<2-3 sentence overall feedback>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "ideal_answer_hints": "<brief hint about ideal answer>",
  "follow_up": "<optional follow-up question or empty string>"
}}"""

    raw = _call_llm(prompt, system)

    try:
        start  = raw.index("{")
        end    = raw.rindex("}") + 1
        result = json.loads(raw[start:end])
        result.setdefault("score",               5)
        result.setdefault("verdict",             "Average")
        result.setdefault("feedback",            "No feedback available.")
        result.setdefault("strengths",           [])
        result.setdefault("weaknesses",          [])
        result.setdefault("ideal_answer_hints",  "")
        result.setdefault("follow_up",           "")
        result["score"] = max(0, min(10, int(result["score"])))
        return result
    except Exception as e:
        logger.warning(f"Could not parse evaluation JSON: {e}\nRaw: {raw[:300]}")
        return {
            "score": 5,
            "verdict": "Average",
            "feedback": raw[:300] if raw else "Evaluation unavailable.",
            "strengths": [],
            "weaknesses": [],
            "ideal_answer_hints": "",
            "follow_up": "",
        }


def generate_final_report_summary(
    domain: str, qa_history: list[dict], overall_score: float
) -> str:
    """Generate a narrative coach summary for the final report."""
    system = "You are a professional career coach writing an interview performance summary."
    history_text = "\n".join(
        f"Q{i+1}: {item['question']}\nA: {item['answer']}\nScore: {item['score']}/10"
        for i, item in enumerate(qa_history)
    )
    prompt = f"""Domain: {domain}
Overall Score: {overall_score:.1f}/10

Interview Q&A:
{history_text}

Write a concise 3-paragraph performance summary:
1. Overall performance assessment
2. Key strengths demonstrated
3. Areas for improvement and recommendations

Keep it professional and constructive."""

    return _call_llm(prompt, system)


# ─────────────────────────────────────────────────────────────────────────────
# Status checks
# ─────────────────────────────────────────────────────────────────────────────

def check_groq_status() -> dict:
    """Ping Groq API and verify the key works."""
    if not GROQ_API_KEY:
        return {"available": False, "reason": "GROQ_API_KEY not set", "model": GROQ_MODEL}
    try:
        resp = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=8,
        )
        if resp.status_code == 200:
            models = [m["id"] for m in resp.json().get("data", [])]
            model_ok = any(GROQ_MODEL in m for m in models)
            return {
                "available": True,
                "model": GROQ_MODEL,
                "model_available": model_ok,
                "models": models[:10],
            }
        return {"available": False, "reason": f"HTTP {resp.status_code}", "model": GROQ_MODEL}
    except Exception as e:
        return {"available": False, "reason": str(e), "model": GROQ_MODEL}


def check_ollama_status() -> dict:
    """Check if local Ollama service is running and the model is present."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        model_available = any(OLLAMA_MODEL in m for m in models)
        return {
            "running": True,
            "model_available": model_available,
            "model": OLLAMA_MODEL,
            "models": models,
        }
    except Exception:
        return {"running": False, "model_available": False, "model": OLLAMA_MODEL, "models": []}


def get_provider_status() -> dict:
    """Return status for all providers plus the active one."""
    return {
        "active_provider": _ACTIVE_PROVIDER,
        "groq":   check_groq_status(),
        "ollama": check_ollama_status(),
    }


def set_active_provider(provider: str):
    """Dynamically switch the active provider at runtime (for /api/provider endpoint)."""
    global _ACTIVE_PROVIDER
    provider = provider.lower()
    if provider not in (PROVIDER_GROQ, PROVIDER_OLLAMA):
        raise ValueError(f"Unknown provider: '{provider}'")
    _ACTIVE_PROVIDER = provider
    logger.info(f"LLM provider switched to: {_ACTIVE_PROVIDER}")


def get_active_provider() -> str:
    return _ACTIVE_PROVIDER
