"""
Ollama Integration Module
Handles all communication with the local Ollama LLM (llama3)
"""

import requests
import json
import logging

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "llama3"


def _stream_ollama(prompt: str, system: str = "") -> str:
    """
    Send a prompt to Ollama and return the full response.
    Uses streaming internally but returns complete text.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system,
        "stream": False,
    }
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except requests.exceptions.ConnectionError:
        logger.error("Ollama is not running. Start it with: ollama serve")
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure Ollama is running: `ollama serve`"
        )
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        raise


def generate_questions(domain: str, num_questions: int = 7) -> list[str]:
    """
    Generate domain-specific interview questions using Ollama.
    Returns a list of question strings.
    """
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
    raw = _stream_ollama(prompt, system)

    # Extract JSON array from response
    try:
        # Find the first '[' and last ']'
        start = raw.index("[")
        end = raw.rindex("]") + 1
        questions = json.loads(raw[start:end])
        return [str(q).strip() for q in questions if q]
    except (ValueError, json.JSONDecodeError):
        # Fallback: split by newline if JSON parsing fails
        lines = [
            l.strip().lstrip("0123456789.-) ") for l in raw.split("\n") if l.strip()
        ]
        return [l for l in lines if len(l) > 10][:num_questions]


def evaluate_answer(
    domain: str,
    question: str,
    answer: str,
    question_number: int,
) -> dict:
    """
    Evaluate a candidate's spoken answer using Ollama.
    Returns a dict with score, feedback, strengths, weaknesses.
    """
    system = (
        "You are a strict but fair technical interviewer evaluating a job candidate. "
        "Respond ONLY with valid JSON. No extra text."
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

    raw = _stream_ollama(prompt, system)

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        result = json.loads(raw[start:end])
        # Ensure required keys exist
        result.setdefault("score", 5)
        result.setdefault("verdict", "Average")
        result.setdefault("feedback", "No feedback available.")
        result.setdefault("strengths", [])
        result.setdefault("weaknesses", [])
        result.setdefault("ideal_answer_hints", "")
        result.setdefault("follow_up", "")
        # Clamp score
        result["score"] = max(0, min(10, int(result["score"])))
        return result
    except Exception as e:
        logger.warning(f"Could not parse evaluation JSON: {e}\nRaw: {raw}")
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
    """
    Generate a narrative summary for the final interview report.
    """
    system = "You are a professional career coach writing an interview performance summary."
    history_text = "\n".join(
        [
            f"Q{i+1}: {item['question']}\nA: {item['answer']}\nScore: {item['score']}/10"
            for i, item in enumerate(qa_history)
        ]
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

    return _stream_ollama(prompt, system)


def check_ollama_status() -> dict:
    """Check if Ollama is running and the model is available."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        model_available = any(MODEL_NAME in m for m in models)
        return {
            "running": True,
            "model_available": model_available,
            "models": models,
        }
    except Exception:
        return {"running": False, "model_available": False, "models": []}
