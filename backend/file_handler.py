"""
File Handling Module
Saves interview transcripts, reports, and analytics to local files.
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _session_dir(session_id: str) -> str:
    path = os.path.join(REPORTS_DIR, session_id)
    os.makedirs(path, exist_ok=True)
    return path


def save_session_data(session_id: str, session_data: dict) -> dict:
    """
    Save complete session data as JSON.
    Returns dict with saved file paths.
    """
    sdir = _session_dir(session_id)
    saved = {}

    # ── JSON: Full session data ──
    json_path = os.path.join(sdir, "session.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2, ensure_ascii=False)
    saved["json"] = json_path
    logger.info(f"Saved session JSON: {json_path}")

    # ── TXT: Human-readable transcript ──
    txt_path = os.path.join(sdir, "transcript.txt")
    _write_transcript(txt_path, session_data)
    saved["transcript"] = txt_path

    # ── TXT: Final report ──
    report_path = os.path.join(sdir, "report.txt")
    _write_report(report_path, session_data)
    saved["report"] = report_path

    return saved


def _write_transcript(path: str, session_data: dict):
    """Write human-readable Q&A transcript."""
    domain = session_data.get("domain", "Unknown")
    ts = session_data.get("started_at", datetime.now().isoformat())
    qa = session_data.get("qa_history", [])
    analytics = session_data.get("analytics", {})

    lines = [
        "=" * 70,
        "           AI INTERVIEW PLATFORM — SESSION TRANSCRIPT",
        "=" * 70,
        f"  Domain      : {domain}",
        f"  Date/Time   : {ts}",
        f"  Session ID  : {session_data.get('session_id', 'N/A')}",
        f"  Questions   : {len(qa)}",
        f"  Final Score : {analytics.get('average_score', 'N/A')} / 10  ({analytics.get('grade', '')})",
        "=" * 70,
        "",
    ]

    for i, item in enumerate(qa, 1):
        lines += [
            f"  QUESTION {i}",
            f"  {'─'*60}",
            f"  Q: {item.get('question', '')}",
            "",
            f"  A: {item.get('answer', '[No answer recorded]')}",
            "",
            f"  Score      : {item.get('score', 'N/A')} / 10  ({item.get('verdict', '')})",
            f"  Feedback   : {item.get('feedback', '')}",
        ]
        strengths = item.get("strengths", [])
        weaknesses = item.get("weaknesses", [])
        if strengths:
            lines.append(f"  Strengths  : {', '.join(strengths)}")
        if weaknesses:
            lines.append(f"  Weaknesses : {', '.join(weaknesses)}")
        if item.get("ideal_answer_hints"):
            lines.append(f"  Hint       : {item['ideal_answer_hints']}")
        lines.append("")

    lines += [
        "=" * 70,
        "  PERFORMANCE SUMMARY",
        "=" * 70,
        f"  Average Score  : {analytics.get('average_score', 'N/A')}",
        f"  Trend          : {analytics.get('trend', 'N/A')}",
        f"  Consistency    : {analytics.get('consistency', 'N/A')}",
        "",
        session_data.get("final_summary", ""),
        "",
        "=" * 70,
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_report(path: str, session_data: dict):
    """Write concise final performance report."""
    analytics = session_data.get("analytics", {})
    domain = session_data.get("domain", "Unknown")
    ts = session_data.get("started_at", "")
    summary = session_data.get("final_summary", "")

    buckets = analytics.get("performance_buckets", {})

    lines = [
        "AI INTERVIEW PLATFORM — PERFORMANCE REPORT",
        "─" * 50,
        f"Candidate Domain  : {domain}",
        f"Interview Date    : {ts}",
        f"",
        f"SCORES",
        f"  Average      : {analytics.get('average_score', 'N/A')} / 10",
        f"  Median       : {analytics.get('median_score', 'N/A')} / 10",
        f"  Highest      : {analytics.get('max_score', 'N/A')} / 10",
        f"  Lowest       : {analytics.get('min_score', 'N/A')} / 10",
        f"  Grade        : {analytics.get('grade', 'N/A')}",
        f"  Performance  : {analytics.get('performance_percentage', 'N/A')}%",
        "",
        "ANSWER DISTRIBUTION",
        f"  Excellent (8-10) : {buckets.get('excellent', 0)} answers",
        f"  Good (6-7)       : {buckets.get('good', 0)} answers",
        f"  Average (4-5)    : {buckets.get('average', 0)} answers",
        f"  Poor (0-3)       : {buckets.get('poor', 0)} answers",
        "",
        "BEHAVIORAL ANALYTICS",
        f"  Performance Trend : {analytics.get('trend', 'N/A')}",
        f"  Consistency       : {analytics.get('consistency', 'N/A')}",
        f"  Std Deviation     : {analytics.get('std_deviation', 'N/A')}",
        "",
        "─" * 50,
        "COACH SUMMARY",
        "─" * 50,
        summary,
        "",
        "─" * 50,
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def load_session(session_id: str) -> dict | None:
    """Load a saved session by ID."""
    json_path = os.path.join(REPORTS_DIR, session_id, "session.json")
    if not os.path.exists(json_path):
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_sessions() -> list[dict]:
    """List all saved sessions with summary info."""
    sessions = []
    if not os.path.exists(REPORTS_DIR):
        return sessions
    for entry in sorted(os.listdir(REPORTS_DIR), reverse=True):
        json_path = os.path.join(REPORTS_DIR, entry, "session.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f:
                    data = json.load(f)
                sessions.append({
                    "session_id": entry,
                    "domain": data.get("domain", "Unknown"),
                    "started_at": data.get("started_at", ""),
                    "average_score": data.get("analytics", {}).get("average_score", 0),
                    "grade": data.get("analytics", {}).get("grade", "?"),
                    "total_questions": data.get("analytics", {}).get("total_questions", 0),
                })
            except Exception:
                continue
    return sessions


def save_graph_reference(session_id: str, graph_paths: dict):
    """Append graph file references to session JSON."""
    json_path = os.path.join(REPORTS_DIR, session_id, "session.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            data["graphs"] = graph_paths
            with open(json_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save graph reference: {e}")
