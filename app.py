"""
AI Interview Chatbot — Flask Backend
Supports Groq (llama-3.3-70b-versatile) and Ollama (llama3) as LLM providers.
Switch providers live via /api/provider endpoint.
"""

import os
import sys
import uuid
import logging
from datetime import datetime

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(__file__))

# ── LLM client (Groq + Ollama unified) ───────────────────────────────────────
from backend.llm_client import (
    generate_questions,
    evaluate_answer,
    generate_final_report_summary,
    get_provider_status,
    set_active_provider,
    get_active_provider,
)

# ── Other backend modules ─────────────────────────────────────────────────────
from backend.speech_module import transcribe_base64_audio, get_available_engines
from backend.analytics import calculate_analytics, generate_analytics_dashboard
from backend.file_handler import (
    save_session_data,
    load_session,
    list_sessions,
    save_graph_reference,
)

# ─────────────────────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "frontend", "templates"),
    static_folder=os.path.join(BASE_DIR, "frontend", "static"),
)
CORS(app)

# In-memory session store
SESSIONS: dict[str, dict] = {}

DOMAINS = [
    "Python",
    "Java",
    "Web Development",
    "Machine Learning",
    "Data Structures & Algorithms",
    "HR Interview",
    "System Design",
    "DevOps & Cloud",
    "Custom Domain",
]


# ─────────────────────────────────────────────────────────────────────────────
# Page routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/interview")
def interview():
    return render_template("interview.html")


@app.route("/results/<session_id>")
def results(session_id):
    return render_template("results.html", session_id=session_id)


# ─────────────────────────────────────────────────────────────────────────────
# API — system / provider
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/status", methods=["GET"])
def api_status():
    """Return full system status including both LLM providers."""
    providers = get_provider_status()
    return jsonify({
        "status":          "ok",
        "active_provider": providers["active_provider"],
        "providers":       providers,
        "stt_engines":     get_available_engines(),
        "domains":         DOMAINS,
        "ollama":          providers["ollama"],   # legacy compat
    })


@app.route("/api/provider", methods=["GET"])
def api_get_provider():
    """Return currently active LLM provider and status of both."""
    providers = get_provider_status()
    return jsonify({
        "active_provider": providers["active_provider"],
        "groq":            providers["groq"],
        "ollama":          providers["ollama"],
    })


@app.route("/api/provider", methods=["POST"])
def api_set_provider():
    """Switch the active LLM provider at runtime."""
    data     = request.get_json() or {}
    provider = data.get("provider", "").strip().lower()
    if not provider:
        return jsonify({"error": "provider field required ('groq' or 'ollama')"}), 400
    try:
        set_active_provider(provider)
        logger.info(f"Provider switched to: {provider}")
        return jsonify({
            "active_provider": get_active_provider(),
            "message": f"Switched to {provider}",
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ─────────────────────────────────────────────────────────────────────────────
# API — interview session
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/start", methods=["POST"])
def api_start_session():
    """Start a new interview session."""
    data              = request.get_json() or {}
    domain            = data.get("domain", "Python").strip()
    num_questions     = min(max(int(data.get("num_questions", 7)), 3), 10)
    provider_override = data.get("provider", "").strip().lower() or None

    if not domain:
        return jsonify({"error": "Domain is required"}), 400

    session_id = str(uuid.uuid4())[:12]
    active_prov = provider_override or get_active_provider()

    try:
        logger.info(
            f"Generating {num_questions} questions — domain='{domain}' provider={active_prov}"
        )
        questions = generate_questions(domain, num_questions)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        return jsonify({"error": "Failed to generate questions. Check your LLM provider."}), 500

    if not questions:
        return jsonify({"error": "No questions generated. Try again."}), 500

    SESSIONS[session_id] = {
        "session_id":    session_id,
        "domain":        domain,
        "provider":      active_prov,
        "started_at":    datetime.now().isoformat(),
        "questions":     questions,
        "current_index": 0,
        "qa_history":    [],
        "status":        "active",
    }
    logger.info(f"Session {session_id} started — {domain}, {len(questions)} Qs, {active_prov}")

    return jsonify({
        "session_id":      session_id,
        "domain":          domain,
        "provider":        active_prov,
        "total_questions": len(questions),
        "first_question":  questions[0],
        "question_number": 1,
    })


@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    """Transcribe base64-encoded audio to text."""
    data      = request.get_json() or {}
    b64_audio = data.get("audio")
    mime_type = data.get("mime_type", "audio/webm")

    if not b64_audio:
        return jsonify({"error": "No audio data provided"}), 400

    return jsonify(transcribe_base64_audio(b64_audio, mime_type))


@app.route("/api/answer", methods=["POST"])
def api_submit_answer():
    """Submit an answer — get evaluation + next question."""
    data        = request.get_json() or {}
    session_id  = data.get("session_id")
    answer_text = data.get("answer", "").strip()

    if not session_id or session_id not in SESSIONS:
        return jsonify({"error": "Invalid or expired session"}), 404

    session   = SESSIONS[session_id]
    idx       = session["current_index"]
    questions = session["questions"]

    if idx >= len(questions):
        return jsonify({"error": "Interview already complete", "finished": True}), 400

    question    = questions[idx]
    answer_text = answer_text or "[No answer provided]"

    try:
        evaluation = evaluate_answer(
            domain=session["domain"],
            question=question,
            answer=answer_text,
            question_number=idx + 1,
        )
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        evaluation = {
            "score": 5, "verdict": "Average",
            "feedback": "Evaluation unavailable.",
            "strengths": [], "weaknesses": [],
            "ideal_answer_hints": "", "follow_up": "",
        }

    session["qa_history"].append({
        "question_number": idx + 1,
        "question":        question,
        "answer":          answer_text,
        **evaluation,
    })
    session["current_index"] += 1

    next_idx = session["current_index"]
    finished = next_idx >= len(questions)

    resp_data = {"evaluation": evaluation, "question_number": idx + 1, "finished": finished}

    if not finished:
        resp_data["next_question"]        = questions[next_idx]
        resp_data["next_question_number"] = next_idx + 1
        resp_data["total_questions"]      = len(questions)
    else:
        resp_data["message"] = "Interview complete! Generating your report…"

    return jsonify(resp_data)


@app.route("/api/finish", methods=["POST"])
def api_finish_session():
    """Finalize interview — analytics, graphs, file save."""
    data       = request.get_json() or {}
    session_id = data.get("session_id")

    if not session_id or session_id not in SESSIONS:
        return jsonify({"error": "Invalid session"}), 404

    session    = SESSIONS[session_id]
    qa_history = session["qa_history"]

    if not qa_history:
        return jsonify({"error": "No answers recorded"}), 400

    session["status"]       = "completed"
    session["completed_at"] = datetime.now().isoformat()

    analytics           = calculate_analytics(qa_history)
    session["analytics"] = analytics

    try:
        summary = generate_final_report_summary(
            session["domain"], qa_history, analytics["average_score"]
        )
    except Exception as e:
        logger.warning(f"Summary generation failed: {e}")
        summary = "Interview completed. Review your scores and feedback above."
    session["final_summary"] = summary

    graphs = {}
    try:
        graphs["dashboard"] = generate_analytics_dashboard(
            qa_history, session["domain"], session_id
        )
    except Exception as e:
        logger.warning(f"Graph generation failed: {e}")
    session["graphs"] = graphs

    try:
        saved_files = save_session_data(session_id, session)
        save_graph_reference(session_id, graphs)
    except Exception as e:
        logger.warning(f"File save failed: {e}")
        saved_files = {}

    logger.info(
        f"Session {session_id} finalised — provider={session.get('provider')}, "
        f"avg={analytics['average_score']}"
    )

    return jsonify({
        "session_id":       session_id,
        "domain":           session["domain"],
        "provider":         session.get("provider"),
        "analytics":        analytics,
        "final_summary":    summary,
        "qa_history":       qa_history,
        "saved_files":      {k: os.path.basename(v) for k, v in saved_files.items()},
        "graphs_available": bool(graphs),
    })


@app.route("/api/session/<session_id>", methods=["GET"])
def api_get_session(session_id):
    session = SESSIONS.get(session_id) or load_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(session)


@app.route("/api/sessions", methods=["GET"])
def api_list_sessions():
    return jsonify(list_sessions())


@app.route("/api/graph/<session_id>/<graph_type>", methods=["GET"])
def api_get_graph(session_id, graph_type):
    path = os.path.join(BASE_DIR, "graphs", f"{session_id}_{graph_type}.png")
    if not os.path.exists(path):
        return jsonify({"error": "Graph not found"}), 404
    return send_file(path, mimetype="image/png")


@app.route("/api/report/<session_id>/<file_type>", methods=["GET"])
def api_download_report(session_id, file_type):
    name_map = {"json": "session.json", "txt": "transcript.txt", "report": "report.txt"}
    filename = name_map.get(file_type)
    if not filename:
        return jsonify({"error": "Unknown file type"}), 400
    path = os.path.join(BASE_DIR, "reports", session_id, filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    return send_file(path, as_attachment=True, download_name=filename)


# ─────────────────────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting NeuralHire on http://localhost:{port}")
    logger.info(f"Active LLM provider: {get_active_provider()}")
    app.run(host="0.0.0.0", port=port, debug=True)
